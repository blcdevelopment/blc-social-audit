# Code Walkthrough And System Explanation

**Project:** BLC Website Audit Automation
**Phase:** Phase 1 foundation + Epic P1-E2 collection pipeline + Epic P1-E3 scoring/commentary + Epic P1-E4 PDF reports + Epic P1-E5 operator UI
**Audience:** Developer/operator handoff
**Important note:** This document explains the current implemented code. Epic P1-E2 provides the real crawler, PageSpeed collector, and SEO/UX extractors. Epic P1-E3 adds YAML scoring, ChatGPT commentary, local fallback commentary, and deterministic grounding validation. Epic P1-E4 adds report payload composition, BLC branding configuration, and WeasyPrint PDF rendering. Epic P1-E5 adds the internal operator UI (audit submission, live progress/result, history) and the `GET /audits/{job_id}` detail endpoint that serves per-audit scores and the composed report payload to the UI.

---

## 1. What This Repo Is

This repo is the local-first foundation for the BLC Website Audit Automation app.

The goal of Phase 1 is:

1. A BLC operator submits a website URL.
2. The backend creates an audit job.
3. A worker processes that job asynchronously.
4. The system tracks job status and progress.
5. Epic P1-E2 collects website crawl, PageSpeed, SEO, and UX/UI facts.
6. Epic P1-E3 scores those facts, generates commentary, and validates numeric grounding.
7. Epic P1-E4 renders a branded PDF report and stores its local `pdf_path`.
8. Epic P1-E5 provides the operator UI screens (submit, progress/result, history) plus the audit detail endpoint they consume.

Right now Epic P1-E1 through P1-E5 are implemented:

- Backend API foundation.
- Worker foundation.
- Worker-driven collection pipeline.
- Playwright crawler.
- PageSpeed Insights client.
- SEO and UX/UI extractors.
- YAML SEO, UX/UI, and composite scoring rubrics.
- Deterministic scoring engine with per-rule audit trails.
- ChatGPT commentary client and prompt templates.
- Local fallback commentary when `OPENAI_API_KEY` is not configured.
- Grounding validator that strips unsupported numeric claims.
- Report payload composer.
- Branding config with the BLC logo asset and text fallback.
- Jinja2/WeasyPrint PDF renderer.
- Branded HTML/CSS report template.
- Database models and migration.
- Docker Compose local stack.
- Conda/Poetry/Python tooling.
- Next.js operator UI: audit submission, live progress/result, and history screens.
- `GET /audits/{job_id}` detail endpoint serving per-audit scores and report content to the UI.
- Swagger UI.
- Tests and pre-commit.

---

## 2. High-Level Runtime Architecture

When running locally with Docker Compose, the system has four main services:

```text
Browser / Swagger UI
        |
        v
FastAPI backend  <------>  PostgreSQL
        |
        v
Redis queue
        |
        v
Celery worker
```

What each service does:

- **FastAPI backend:** receives API requests, validates payloads, creates audit jobs, returns status/report responses.
- **PostgreSQL:** stores `audit_jobs` and `audit_results`.
- **Redis:** acts as the Celery message broker and result backend.
- **Celery worker:** receives queued audit tasks and updates job lifecycle progress.

The operator UI under `apps/frontend` (Epic P1-E5) is a separate Next.js process. In local
development it runs on `http://localhost:3000` and calls the FastAPI backend over HTTP/CORS
(`NEXT_PUBLIC_API_BASE_URL`, default `http://localhost:8000`). It submits audits, polls the audit
detail endpoint for live progress, and links to the PDF report endpoint for download.

---

## 3. Main Request Flow: What Calls What

### 3.1 API Startup

When Docker starts the API service, this command runs:

```bash
alembic upgrade head &&
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Call chain:

```text
docker-compose.yml
  -> api service command
    -> alembic upgrade head
      -> migrations/env.py
      -> migrations/versions/20260528_0001_create_audit_tables.py
    -> uvicorn apps.api.main:app
      -> apps/api/main.py
      -> includes health router
      -> includes audits router
```

The API is available at:

- `http://localhost:8000`
- `http://localhost:8000/docs`
- `http://localhost:8000/openapi.json`

`GET /` redirects to `/docs`.

### 3.2 Submit An Audit

When a user submits an audit through Swagger or any API client:

```http
POST /audits
```

Example request:

```json
{
  "url": "https://example.com",
  "niche": "builder",
  "target_audience": "homeowners"
}
```

Call chain:

```text
POST /audits
  -> apps/api/routes/audits.py:create_audit()
    -> apps/api/schemas/audits.py:AuditCreateRequest validates input
    -> apps/shared/database.py:get_db_session() provides DB session
    -> apps/shared/models.py:AuditJob object is created
    -> SQLAlchemy inserts row into audit_jobs
    -> if AUDIT_ENQUEUE_ENABLED=true:
      -> apps.worker.tasks.run_audit.delay(job_id)
        -> Celery sends task to Redis
    -> API returns job_id and status_url
```

Response shape:

```json
{
  "job_id": "uuid-here",
  "status": "queued",
  "status_url": "/audits/{job_id}/status"
}
```

### 3.3 Worker Processes The Audit

The worker starts with:

```bash
celery -A apps.worker.celery_app.celery_app worker --loglevel=info
```

Call chain:

```text
docker-compose.yml
  -> worker service command
    -> apps/worker/celery_app.py creates Celery app
    -> includes apps.worker.tasks
    -> worker waits for Redis tasks
```

When the API enqueues a task:

```text
Redis receives task
  -> Celery worker receives task
    -> apps/worker/tasks.py:run_audit(job_id)
      -> run_collection_audit(job_id)
        -> load job from PostgreSQL
        -> crawl homepage and selected internal pages
        -> collect or skip PageSpeed Insights facts
        -> extract SEO and UX/UI facts
        -> score facts through YAML rubrics
        -> generate ChatGPT or local fallback commentary
        -> validate commentary grounding
        -> write audit artifacts to audit_results
        -> render branded PDF report
        -> write report metadata and pdf_path
        -> mark job complete
```

Current worker stages:

| Status | Stage label | Progress |
|---|---|---|
| `crawling` | Rendering website pages | 15 |
| `collecting_performance` | Collecting PageSpeed Insights | 45 |
| `extracting` | Extracting SEO and UX/UI facts | 70 |
| `scoring` | Scoring extracted facts | 80 |
| `commenting` | Generating grounded commentary | 88 |
| `validating` | Validating commentary grounding | 95 |
| `rendering` | Rendering branded PDF report | 98 |
| `complete` | Audit report complete | 100 |

The current worker proves that:

- API can enqueue jobs.
- Worker can pick jobs up.
- Worker can connect to DB.
- Worker can update progress.
- Worker can create or update an `audit_results` row with crawler, PSI, SEO, and UX/UI facts.
- API can read job status/result state.

### 3.4 Poll Audit Status

```http
GET /audits/{job_id}/status
```

Call chain:

```text
GET /audits/{job_id}/status
  -> apps/api/routes/audits.py:get_audit_status()
    -> db.get(AuditJob, job_id)
    -> _status_response(job)
    -> returns job status, stage, progress, timestamps, report_available
```

Response includes:

- `job_id`
- `url`
- `status`
- `current_stage`
- `progress_pct`
- `error_message`
- `created_at`
- `started_at`
- `completed_at`
- `report_available`

### 3.5 List Audits

```http
GET /audits
```

Call chain:

```text
GET /audits
  -> apps/api/routes/audits.py:list_audits()
    -> SELECT audit jobs ordered by created_at desc
    -> _list_item(job)
    -> returns recent audits and scores if a result exists
```

Query parameters:

- `limit`, default `25`, min `1`, max `100`
- `offset`, default `0`

### 3.6 Download Report

```http
GET /audits/{job_id}/report
```

Call chain:

```text
GET /audits/{job_id}/report
  -> apps/api/routes/audits.py:get_audit_report()
    -> load AuditJob
    -> check job.result exists
    -> check job.result.pdf_path exists
    -> return FileResponse if PDF exists
```

Current behavior:

- This endpoint exists.
- It streams the generated local PDF once the worker has stored `pdf_path`.
- It returns `404` if the audit has no generated PDF or the local file is missing.

---

## 4. How The Audit Pipeline Works

Current implemented audit:

```text
Submit URL
  -> create DB job
  -> enqueue Celery task
  -> render/crawl homepage and internal pages
  -> collect or gracefully skip PageSpeed mobile and desktop data for selected crawled pages
  -> extract SEO facts
  -> extract UX/UI facts
  -> score facts through YAML rubrics
  -> generate OpenAI/ChatGPT commentary from facts and scores
  -> validate commentary grounding
  -> compose report payload
  -> render PDF
  -> save PDF path
  -> mark complete
```

The DB schema and API lifecycle are now wired through PDF generation, and the Epic P1-E5 operator
UI consumes them. The remaining Phase 1 work is Epic P1-E6 (end-to-end QA, reproducibility QA,
production packaging, and handoff documentation).

---

## 5. Folder And File Inventory

This section explains every source folder and important file currently in the repo.

### 5.1 Root Files

#### `README.md`

Human-facing setup guide.

It explains:

- What the project is.
- How to create/activate `social-audit`.
- How to install dependencies.
- How to run Docker Compose.
- How to run tests/lint.
- Where API endpoints live.

#### `.env`

Local secret configuration file.

Important:

- Contains real local secrets like `OPENAI_API_KEY` and `GOOGLE_PSI_API_KEY`.
- Is ignored by git.
- Should not be committed.
- Should not be pasted into docs.

The code reads this file through Pydantic Settings in `apps/shared/config.py`.

#### `.env.template`

Safe template version of `.env`.

It documents all required environment variables without real secrets.

Main sections:

- App mode.
- Backend API.
- Frontend.
- PostgreSQL.
- Redis/Celery.
- Local storage.
- OpenAI/ChatGPT.
- PageSpeed.
- Playwright crawler settings.
- Scoring/report paths.

#### `.gitignore`

Tells git what not to commit.

Important ignored items:

- `.env`
- virtual environments
- Python cache folders
- test/lint caches
- local PDF/screenshot outputs
- frontend `node_modules`
- frontend `.next`
- macOS `.DS_Store`

#### `.dockerignore`

Tells Docker what not to copy into images.

This keeps images smaller and avoids copying local caches/secrets/build outputs.

#### `docker-compose.yml`

Defines the local runtime stack.

Services:

- `postgres`
- `redis`
- `api`
- `worker`

Key behavior:

- Postgres uses a named Docker volume `postgres_data`.
- Redis exposes port `6379`.
- API builds from `apps/api/Dockerfile`.
- Worker builds from `apps/worker/Dockerfile`.
- API waits for Postgres and Redis health checks.
- API runs migrations before starting Uvicorn.
- Worker starts Celery and listens to Redis.

#### `environment.yml`

Conda environment definition.

Environment name:

```text
social-audit
```

It installs:

- Python 3.12
- pip
- Poetry
- pre-commit

Project dependencies are installed with Poetry after activating the Conda env.

#### `pyproject.toml`

Main Python project metadata and tooling config.

It defines:

- Project name/version.
- Python version requirement.
- Runtime dependencies.
- Dev dependencies.
- Poetry settings.
- pytest config.
- Ruff lint/format config.

Important dependencies include:

- FastAPI
- SQLAlchemy
- Alembic
- Celery
- Redis support
- PostgreSQL driver
- Pydantic Settings
- OpenAI SDK
- pytest
- Ruff
- pre-commit

#### `poetry.lock`

Locked Python dependency graph.

Purpose:

- Makes dependency installation repeatable.
- Records exact versions Poetry resolved.
- Should be committed.

#### `poetry.toml`

Local Poetry behavior.

Current setting:

```toml
[virtualenvs]
create = false
```

This means Poetry installs into the active Conda env instead of creating a second virtualenv.

#### `requirements.txt`

Pinned dependency list for simple pip-based installs or deployment environments that expect requirements files.

Poetry lock is the stronger source of truth, but this file is useful for compatibility.

#### `.pre-commit-config.yaml`

Defines checks that run before commits.

Current hooks:

- Ruff check with auto-fix.
- Ruff format.
- Backend tests.
- Frontend typecheck when frontend files are involved.

#### `alembic.ini`

Alembic configuration file.

It points Alembic to:

- Migration scripts in `migrations/`.
- Default DB URL, overridden at runtime by `.env` through `migrations/env.py`.

---

## 6. `apps/` Folder

`apps/` contains the application code.

```text
apps/
  api/
  shared/
  worker/
  frontend/
```

### 6.1 `apps/__init__.py`

Marks `apps` as a Python package so imports like this work:

```python
from apps.shared.config import get_settings
```

---

## 7. Backend API: `apps/api/`

The API is a FastAPI service.

### 7.1 `apps/api/main.py`

Creates the FastAPI app.

Responsibilities:

- Loads settings.
- Creates `FastAPI(...)`.
- Configures Swagger UI.
- Configures CORS.
- Includes routers.
- Redirects `/` to `/docs`.

Important objects/functions:

- `app = FastAPI(...)`: the ASGI app Uvicorn serves.
- `app.add_middleware(CORSMiddleware, ...)`: allows frontend/API cross-origin calls.
- `app.include_router(health.router)`: registers health endpoint.
- `app.include_router(audits.router)`: registers audit endpoints.
- `redirect_to_swagger()`: sends browser users from `/` to Swagger UI.

### 7.2 `apps/api/deps.py`

Small dependency export file.

It imports and re-exports:

```python
get_db_session
```

FastAPI routes use this dependency to get DB sessions.

### 7.3 `apps/api/routes/health.py`

Defines:

```http
GET /health
```

Function:

```python
health_check()
```

Returns:

- status
- app name
- environment

Used for local smoke tests and container health checks later.

### 7.4 `apps/api/routes/audits.py`

This is the main audit API router.

Router:

```python
router = APIRouter(prefix="/audits", tags=["audits"])
```

All routes here start with `/audits`.

#### Helper type aliases

```python
DbSession = Annotated[Session, Depends(get_db_session)]
AuditLimit = Annotated[int, Query(ge=1, le=100)]
AuditOffset = Annotated[int, Query(ge=0)]
```

Purpose:

- Keep FastAPI dependency declarations clean.
- Avoid lint warnings about calling `Depends(...)` in default arguments.
- Validate pagination query parameters.

#### `_report_available(job)`

Returns `True` if:

- the job has an `AuditResult`
- that result has `pdf_path`
- and the local PDF file exists

#### `_status_response(job)`

Converts an `AuditJob` SQLAlchemy model into an `AuditStatusResponse` Pydantic object.

Used by:

- `GET /audits/{job_id}/status`

#### `_list_item(job)`

Converts an `AuditJob` plus optional `AuditResult` into an `AuditListItem`.

Used by:

- `GET /audits`

It includes scores only if an audit result exists.

#### `_detail_response(job)`

Converts an `AuditJob` into an `AuditDetailResponse`.

Used by:

- `GET /audits/{job_id}`

If the job has an `AuditResult`, it reuses the worker's `compose_report_payload(job, result)` to
build the full report payload (scores, executive summary, findings, recommendations, roadmap,
PageSpeed/validation summaries). While the audit is still running there is no result yet, so
`report` is `null`. This keeps a single source of truth for report shaping shared by the PDF and the
UI.

#### `create_audit(payload, db)`

Route:

```http
POST /audits
```

Responsibilities:

1. Validate the request body with `AuditCreateRequest`.
2. Create an `AuditJob`.
3. Save it to PostgreSQL.
4. If enqueueing is enabled, call Celery task:

   ```python
   run_audit.delay(str(job.id))
   ```

5. Return `job_id`, `status`, and `status_url`.

Failure behavior:

- If job enqueue fails, it marks the job as `failed`.
- It stores the error message.
- It returns HTTP `503`.

#### `list_audits(db, limit, offset)`

Route:

```http
GET /audits
```

Responsibilities:

- Query recent audit jobs.
- Sort newest first.
- Apply pagination.
- Return list response.

#### `get_audit_status(job_id, db)`

Route:

```http
GET /audits/{job_id}/status
```

Responsibilities:

- Load the job by UUID.
- Return `404` if missing.
- Return current status/progress if found.

#### `get_audit_detail(job_id, db)`

Route:

```http
GET /audits/{job_id}
```

Responsibilities:

- Load the job by UUID.
- Return `404` if missing.
- Return job status/timestamps plus a composed `report` payload when a result exists.

This is the endpoint the operator UI polls for the progress and result screen, because it returns
per-audit scores and report content that `GET /audits/{job_id}/status` does not.

#### `get_audit_report(job_id, db)`

Route:

```http
GET /audits/{job_id}/report
```

Responsibilities:

- Load job.
- Check result exists.
- Check `pdf_path` exists.
- Return PDF file response.

Current limitation:

- The Phase 1 endpoint serves local filesystem PDFs. Future object storage would need a storage
  adapter rather than a direct `FileResponse`.

### 7.5 `apps/api/schemas/audits.py`

Pydantic schemas for API input/output.

#### `AuditCreateRequest`

Request body for `POST /audits`.

Fields:

- `url`: validated as HTTP URL.
- `niche`: optional string.
- `target_audience`: optional string.

#### `AuditCreateResponse`

Response from `POST /audits`.

Fields:

- `job_id`
- `status`
- `status_url`

#### `AuditStatusResponse`

Response from `GET /audits/{job_id}/status`.

Fields:

- job identity
- URL
- status
- stage
- progress
- errors
- timestamps
- report availability

#### `AuditListItem`

One row in the audit history response.

Includes:

- job fields
- optional scores
- report availability

#### `AuditListResponse`

Wrapper response:

```python
audits: list[AuditListItem]
```

#### `AuditDetailResponse`

Response from `GET /audits/{job_id}`.

Fields:

- job identity, URL, niche, target audience
- status, stage, progress, error message
- timestamps
- report availability
- `report`: the composed `ReportPayload` (from `apps/worker/stages/report_payload.py`) when a result
  exists, otherwise `null`. Reusing that model keeps the schema typed and the report shape identical
  to the PDF.

---

## 8. Shared Backend Code: `apps/shared/`

Shared code is used by both API and worker.

### 8.1 `apps/shared/config.py`

Central app settings.

Uses:

```python
pydantic-settings
```

Main class:

```python
class Settings(BaseSettings)
```

It reads from:

- process environment variables
- `.env`
- default values in code

Important fields:

- `app_env`
- `app_name`
- `api_host`
- `api_port`
- `api_base_url`
- `api_cors_origins`
- `database_url`
- `redis_url`
- `celery_broker_url`
- `celery_result_backend`
- `audit_enqueue_enabled`
- local storage paths
- `openai_api_key`
- `openai_model`
- OpenAI token, timeout, and temperature settings
- rubric paths
- commentary prompt paths

#### `api_cors_origins`

Uses `NoDecode` because `.env` stores it as:

```text
API_CORS_ORIGINS=http://localhost:3000
```

Without `NoDecode`, Pydantic Settings tries to parse list fields as JSON.

#### `parse_origins(...)`

Turns a comma-separated string into a Python list.

Example:

```text
http://localhost:3000,http://localhost:3001
```

becomes:

```python
["http://localhost:3000", "http://localhost:3001"]
```

#### `get_settings()`

Returns a cached `Settings` instance.

The `@lru_cache` avoids re-reading `.env` for every request.

### 8.2 `apps/shared/database.py`

Creates the SQLAlchemy engine and session factory.

Important objects:

#### `engine`

Created with:

```python
create_engine(settings.database_url, ...)
```

This is the connection pool for the database.

#### `SessionLocal`

Factory for database sessions.

Used by:

- FastAPI dependencies.
- Worker tasks.

#### `get_db_session()`

FastAPI dependency generator.

It:

1. Opens a DB session.
2. Yields it to the route.
3. Closes it when the request finishes.

### 8.3 `apps/shared/audit_states.py`

Defines allowed audit lifecycle states.

Main enum:

```python
class AuditStatus(StrEnum)
```

Allowed states:

- `queued`
- `crawling`
- `collecting_performance`
- `extracting`
- `scoring`
- `commenting`
- `validating`
- `rendering`
- `complete`
- `failed`

`JOB_STATUS_VALUES` is used by the model to build a DB check constraint.

`TERMINAL_STATUSES` identifies final states:

- `complete`
- `failed`

### 8.4 `apps/shared/models.py`

SQLAlchemy ORM models.

#### `GUID`

Custom SQLAlchemy type.

Why it exists:

- PostgreSQL uses native UUID.
- SQLite tests use string UUIDs.

This type lets the same model work in production-like Postgres and local SQLite unit tests.

#### `json_type()`

Returns a JSON column type that uses:

- PostgreSQL `JSONB` in Postgres.
- normal `JSON` in other DBs like SQLite.

This keeps tests simple while using the right type in Postgres.

#### `Base`

SQLAlchemy declarative base.

All ORM models inherit from it.

Alembic imports `Base.metadata` to understand the model structure.

#### `AuditJob`

Tracks the lifecycle of a submitted audit.

Table:

```text
audit_jobs
```

Important columns:

- `id`: UUID primary key.
- `url`: submitted website URL.
- `niche`: optional metadata.
- `target_audience`: optional metadata.
- `status`: lifecycle state.
- `current_stage`: human-readable current stage.
- `progress_pct`: 0 to 100.
- `error_message`: stored failure message.
- `created_at`
- `started_at`
- `completed_at`

Constraints/indexes:

- progress must be between 0 and 100.
- status must be one of `AuditStatus`.
- indexed by status.
- indexed by created date.

Relationship:

```python
result: AuditResult | None
```

One job can have one result.

#### `AuditResult`

Stores completed audit output.

Table:

```text
audit_results
```

Important columns:

- `job_id`: FK to `audit_jobs`.
- `seo_score`
- `uxui_score`
- `lead_gen_score`
- `crawled_pages`
- `seo_facts`
- `uxui_facts`
- `psi_facts`
- `score_breakdown`
- `commentary`
- `validation_log`
- `report_metadata`
- `pdf_path`
- `rubric_version`
- `llm_model`
- `created_at`

Most output fields are JSON/JSONB because audit data is nested and will grow as later stages are added.

---

## 9. Worker Code: `apps/worker/`

The worker runs async/background audit tasks.

### 9.1 `apps/worker/celery_app.py`

Creates the Celery application.

Important config:

- Broker: `settings.celery_broker_url`
- Result backend: `settings.celery_result_backend`
- Includes: `apps.worker.tasks`
- JSON serializer.
- UTC timezone.
- task tracking enabled.

This is what the Celery CLI points at:

```bash
celery -A apps.worker.celery_app.celery_app worker --loglevel=info
```

### 9.2 `apps/worker/tasks.py`

Defines the current task implementation.

#### Module-level task helpers

`apps/worker/tasks.py` defines the real audit task plus small helpers (there is no placeholder or
fake-stage logic):

- `_psi_page_urls(crawl_result, fallback_url)`: chooses the page URLs to send to PageSpeed.
- `_upsert_audit_result(...)`: creates or updates the `AuditResult` row from the collected facts,
  scores, commentary, and validation log.
- `_store_pdf_result(db, result, pdf_result)`: saves the rendered PDF path and report metadata.

#### `_mark_job(db, job, status, stage, progress_pct, error_message=None)`

Updates job state.

It:

1. Sets `started_at` if this is the first non-queued state.
2. Sets `completed_at` for `complete` or `failed`.
3. Updates status.
4. Updates current stage.
5. Updates progress.
6. Saves optional error message.
7. Commits DB transaction.
8. Refreshes the ORM object.

#### `run_collection_audit(job_id)`

Current Epic P1-E2 through P1-E4 audit process (collection, scoring, commentary, validation, and PDF
rendering).

It:

1. Reads settings.
2. Parses job UUID.
3. Opens DB session.
4. Loads the `AuditJob`.
5. Returns silently if the job no longer exists.
6. Marks the job as `crawling`.
7. Runs the Playwright crawler.
8. Marks the job as `collecting_performance`.
9. Collects per-page PageSpeed facts, or stores a skipped/failed PSI artifact.
10. Marks the job as `extracting`.
11. Runs the SEO and UX/UI extractors.
12. Marks the job as `scoring`.
13. Scores SEO, UX/UI, and Lead Generation Readiness through versioned YAML rubrics.
14. Marks the job as `commenting`.
15. Generates ChatGPT commentary when `OPENAI_API_KEY` is configured, or local fallback commentary when it is not.
16. Marks the job as `validating`.
17. Strips unsupported numeric commentary claims and stores the validation log.
18. Creates or updates the `AuditResult`.
19. Marks the job as `rendering`.
20. Renders the branded PDF and stores its local `pdf_path` and report metadata.
21. Marks the job complete.

If an exception happens:

1. Roll back DB transaction.
2. Mark job failed.
3. Store error message.
4. Re-raise the exception so Celery logs it.

#### `run_audit(job_id)`

Celery task.

This is what the API enqueues.

```python
run_audit.delay(str(job.id))
```

It calls:

```python
run_collection_audit(job_id)
```

The task now runs collection, scoring, commentary, grounding validation, report payload
composition, PDF rendering, and final `pdf_path` persistence.

### 9.3 `apps/worker/stages/`

Package for worker pipeline stages.

Current modules:

- `crawler.py`: Playwright crawl orchestration, same-site link discovery, robots checks, screenshots, failed-page logs.
- `psi_client.py`: PageSpeed Insights wrapper with retries, cache, normalization, `PSI_SCOPE` / `PSI_MAX_PAGES` page selection, API-key header auth, and graceful skip/failure artifacts.
- `extractor_seo.py`: deterministic SEO facts from rendered HTML.
- `extractor_uxui.py`: deterministic UX/UI and lead-capture heuristics from rendered HTML.
- `scoring.py`: safe YAML rubric loading, evaluator primitives, score composition, and rubric version tracking.
- `commentary.py`: OpenAI Structured Outputs commentary call, Pydantic output schema, prompt loading, and local fallback commentary.
- `grounding_validator.py`: numeric claim extraction, fact comparison, unsupported-claim stripping, and validation log output.

Later module:

- PDF renderer

---

## 10. Frontend Code: `apps/frontend/`

The frontend is the Epic P1-E5 internal operator UI: a Next.js (pages router) TypeScript app.

It uses plain CSS (no Tailwind/component library, no extra runtime dependencies), a small typed API
client, and a shared layout with the BLC logo. The three operator screens are submission, live
progress/result, and audit history. All data is fetched client-side from the API using
`NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`).

### 10.1 `apps/frontend/package.json`

Defines frontend dependencies and scripts.

Important scripts:

- `npm run dev`
- `npm run build`
- `npm run start`
- `npm run lint`
- `npm run typecheck`

Dependencies:

- Next.js
- React
- React DOM
- TypeScript
- ESLint

### 10.2 `apps/frontend/package-lock.json`

Locks frontend dependency versions.

This makes `npm install` repeatable.

### 10.3 `apps/frontend/next.config.js`

Next.js config.

Current setting:

```js
reactStrictMode: true
```

### 10.4 `apps/frontend/tsconfig.json`

TypeScript compiler settings.

It enforces strict TypeScript and Next-compatible module settings.

### 10.5 `apps/frontend/next-env.d.ts`

Next.js generated type references.

Committed so TypeScript tooling works cleanly before first local dev run.

### 10.6 `apps/frontend/.eslintrc.json`

ESLint config.

Extends:

```json
"next/core-web-vitals"
```

### 10.7 `apps/frontend/pages/_app.tsx`

Global Next.js app wrapper.

It imports:

```tsx
../styles/globals.css
```

Then renders the current page component.

### 10.8 `apps/frontend/lib/api.ts`

Typed API client shared by every screen.

Contents:

- `API_BASE_URL` from `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`).
- TypeScript interfaces mirroring the backend schemas (`AuditListItem`, `AuditDetail`,
  `ReportPayload`, `ScoreCard`, etc.).
- `ApiError` (carries the HTTP status) and a `request()` helper that parses FastAPI error detail
  shapes and reports a clear message when the backend is unreachable.
- Functions: `createAudit`, `listAudits`, `getAuditDetail`, and `reportUrl` (builds the PDF link).

### 10.9 `apps/frontend/lib/format.ts`

Presentation helpers shared across screens.

Contents:

- `isTerminal(status)` — true for `complete`/`failed`.
- `statusLabel(status)` — human-readable label per audit status.
- `statusTone(status)` — badge tone (`success`/`danger`/`progress`/`neutral`).
- `scoreTone(score)` — colour band (`strong`/`fair`/`weak`/`empty`) matching the report bands.
- `formatDate(value)` — locale date/time formatting with a `—` fallback.

### 10.10 `apps/frontend/components/Layout.tsx`

Shared page chrome.

Renders the sticky top bar with the BLC logo (`/blc-logo.svg`) and primary nav (New Audit, Audit
History), the page `<main>`, and the footer. Sets the page `<title>` per screen.

### 10.11 `apps/frontend/pages/index.tsx`

Audit submission page (story P1-20).

Behavior:

- Inputs: website URL (required), optional niche, optional target audience.
- Client validation normalizes a missing scheme to `https://` and rejects whitespace or a
  non-dotted host, showing an inline field error.
- Submitting shows a loading spinner and disables inputs; on success it routes to
  `/audit/{job_id}`.
- API/network failures surface as an error alert via `ApiError`.

### 10.12 `apps/frontend/pages/audit/[id].tsx`

Audit progress and result page (story P1-21).

Example route:

```text
/audit/123
```

Behavior:

- Polls `GET /audits/{id}` every 2.5s until the status is terminal (chained `setTimeout`, cleaned up
  on unmount); retries transient/network errors and stops on `404`.
- While running: shows the current stage, a percentage progress bar, and a pipeline stepper.
- On failure: shows the `error_message`.
- On completion: shows the three score cards, executive summary, per-section findings and
  recommendations, a metadata footer (PageSpeed, validation, rubric, model), and the
  **Download PDF report** button (links to `GET /audits/{id}/report`).

### 10.13 `apps/frontend/pages/audits.tsx`

Audit history page (story P1-22).

Behavior:

- Loads `GET /audits` (most recent first) with a manual refresh button.
- Table columns: website (links to detail), status badge, submitted date, scores
  (Lead · SEO · UX), and Details/PDF actions.
- Score column shows colour-coded chips when complete, or `Failed` / `Incomplete` / `In progress`
  labels otherwise. The PDF link appears only when `report_available` is true.
- Empty and loading states are handled explicitly.

### 10.14 `apps/frontend/public/blc-logo.svg`

The Builder Lead Converter logo asset (copied from `assets/brand/blc-logo.svg`), served by Next.js
at `/blc-logo.svg` and used in the layout header.

### 10.15 `apps/frontend/styles/globals.css`

Global CSS and the small branded design system.

Defines:

- BLC brand CSS variables (primary `#1f74b7`, accent `#28864b`) and base typography.
- App shell: top bar, nav, content container, footer.
- Components: cards, form fields, buttons, alerts, spinner, status badges, score cards/chips,
  progress bar and stepper, severity tags, the history table, and responsive rules.

---

## 11. Database Migrations: `migrations/`

Alembic handles schema migrations.

### 11.1 `migrations/env.py`

Alembic runtime configuration.

It:

1. Adds repo root to Python path.
2. Imports settings.
3. Imports `Base.metadata`.
4. Reads `DATABASE_URL` from settings.
5. Configures online/offline migration modes.

### 11.2 `migrations/script.py.mako`

Template Alembic uses when generating new migration files.

### 11.3 `migrations/versions/20260528_0001_create_audit_tables.py`

Initial migration.

Creates:

- `pgcrypto` extension for `gen_random_uuid()`.
- `audit_jobs`.
- `audit_results`.
- indexes.
- constraints.

This migration ran successfully in Docker logs.

---

## 12. Tests: `tests/`

### 12.1 `tests/unit/test_audit_api.py`

Tests API behavior.

#### `test_swagger_ui_is_available()`

Verifies:

- `/` redirects to `/docs`.
- `/docs` returns Swagger UI.
- `/openapi.json` returns the correct app title.

#### `test_create_and_read_audit_lifecycle(...)`

Uses in-memory SQLite.

Important setup:

- `StaticPool` keeps the in-memory DB shared across sessions.
- overrides FastAPI DB dependency.
- disables enqueueing so the test does not need Redis/Celery.

Verifies:

- `POST /audits` returns 201.
- job starts as `queued`.
- status endpoint returns job state.
- list endpoint returns one audit.

### 12.2 `tests/unit/test_audit_lifecycle.py`

Tests ORM persistence.

It:

- creates an `AuditJob`
- commits it
- creates an `AuditResult`
- confirms relationship works

### 12.3 `tests/fixtures/`

Reserved for fixture files.

Current use:

- strong website fixture
- weak website fixture
- malformed HTML fixture
- expected extractor outputs

Current `.gitkeep` remains alongside the fixture files.

### 12.4 `tests/integration/`

Reserved for integration tests.

Future use:

- full API + worker + DB tests
- crawler integration tests
- report generation integration tests

Current `.gitkeep` exists so the empty folder is preserved.

---

## 13. Planning And Handoff Docs: `docs/`

### `docs/01_REQUIREMENTS.md`

Requirements and scope source.

Explains:

- what Phase 1 is
- what is in scope
- what is out of scope
- business/technical decisions

### `docs/02_IMPLEMENTATION.md`

Detailed implementation architecture.

Explains:

- target architecture
- data model
- pipeline design
- future scoring/commentary/PDF/UI plans

### `docs/03_PHASE1_JIRA_PLAN.md`

Jira-ready plan.

Contains:

- Jira settings
- 6 epics
- 26 implementation tasks
- subtasks
- Phase 1 done criteria

### `docs/04_PHASE1_CONFLUENCE_HANDOFF.md`

Stakeholder handoff doc.

Summarizes:

- scope
- architecture
- risks
- acceptance criteria
- deferred work

### `docs/05_CODE_WALKTHROUGH.md`

This document.

Explains:

- current repo structure
- runtime flow
- what each file/folder does
- how the audit lifecycle works today
- what remains for later epics

---

## 14. Reserved Product Folders

These are intentionally present now so later epics have stable locations.

### `rubrics/`

Versioned YAML scoring rubrics used by Epic P1-E3.

Files:

- `seo.yaml`
- `uxui.yaml`
- `composite.yaml`

Purpose:

- deterministic scoring
- tunable weights
- reproducible score breakdowns

### `prompts/`

ChatGPT prompt templates used by Epic P1-E3.

Files:

- `commentary_system.md`
- `commentary_user.md`
- grounding validator prompt if needed

Purpose:

- keep prompts versioned
- avoid hard-coding long prompt text inside Python functions

### `templates/`

Implemented report templates.

Files:

- `report.html`
- `report.css`
- partial templates

Purpose:

- branded PDF report generation

### `templates/partials/`

Reusable report sections for the Jinja2 PDF template.

Examples:

- cover
- summary
- score breakdown
- findings
- recommendations

### `storage/`

Local output storage.

### `storage/reports/`

Future PDF report output folder.

Current `.gitkeep` preserves folder.

### `storage/screenshots/`

Crawler screenshot output folder.

Current `.gitkeep` preserves folder.

---

## 15. DOCX Source Folders

The repo also contains DOCX source/reference folders.

### `docx/current docx/`

Current DOCX source material.

Contains:

- `Phase_1.docx`

### `docx/starting docx/`

Earlier source/reference DOCX files.

Contains initial project planning material.

These files are reference inputs, not runtime code.

---

## 16. Generated / Local-Only Folders

These may exist locally after running commands, but they are not source code.

Examples:

- `apps/frontend/node_modules/`
- `apps/frontend/.next/`
- `__pycache__/`
- `.pytest_cache/`
- `.ruff_cache/`
- `.DS_Store`

They are ignored because:

- they are generated
- they can be recreated
- they are large/noisy
- they do not belong in source control

---

## 17. Tooling Workflow

### 17.1 Conda

Create the environment:

```bash
conda env create -f environment.yml
```

Activate it:

```bash
conda activate social-audit
```

### 17.2 Poetry

Install Python dependencies into the active Conda env:

```bash
poetry install --with dev
```

Why Poetry is used:

- dependency locking
- repeatable installs
- clear dependency groups

Why `poetry.toml` disables virtualenv creation:

- the project uses Conda as the environment boundary
- Poetry should not create a nested virtualenv

### 17.3 requirements.txt

Alternative install path:

```bash
pip install -r requirements.txt
```

Use this when a deployment system expects requirements files.

### 17.4 Pre-commit

Install hook:

```bash
pre-commit install
```

Run manually:

```bash
pre-commit run --all-files
```

Current hooks:

- Ruff check
- Ruff format
- backend tests
- frontend typecheck for frontend files

### 17.5 Backend Checks

```bash
pytest
ruff check .
python -m compileall apps/api apps/shared apps/worker migrations tests
```

### 17.6 Frontend Checks

```bash
cd apps/frontend
npm run typecheck
npm run lint
npm run build
```

### 17.7 Docker

Start stack:

```bash
docker compose up --build
```

Start in background:

```bash
docker compose up --build -d
```

Stop:

```bash
docker compose down
```

Stop and remove DB volume:

```bash
docker compose down -v
```

Only use `-v` when you want to delete the local database.

---

## 18. API Endpoints

### `GET /`

Redirects to Swagger UI at `/docs`.

### `GET /docs`

Swagger UI.

Use this to test API endpoints from the browser.

### `GET /openapi.json`

Raw OpenAPI schema.

Useful for API clients and generated documentation.

### `GET /health`

Health endpoint.

Expected response:

```json
{
  "status": "ok",
  "app": "blc-website-audit",
  "environment": "local"
}
```

### `POST /audits`

Creates an audit job and enqueues worker task.

### `GET /audits`

Lists recent audits.

### `GET /audits/{job_id}/status`

Returns one audit's lifecycle state.

### `GET /audits/{job_id}/report`

Returns generated PDF when available.

Returns `404` only when the audit has no generated PDF or the local PDF file is missing.

---

## 19. Environment Variables

Important environment variables:

| Variable | Purpose |
|---|---|
| `APP_ENV` | local/dev/prod marker |
| `APP_NAME` | app display/internal name |
| `API_PORT` | API port |
| `API_CORS_ORIGINS` | allowed frontend origins |
| `DATABASE_URL` | SQLAlchemy DB connection |
| `REDIS_URL` | Redis connection |
| `CELERY_BROKER_URL` | Celery task broker |
| `CELERY_RESULT_BACKEND` | Celery result backend |
| `AUDIT_ENQUEUE_ENABLED` | lets tests/dev disable worker enqueueing |
| `LOCAL_REPORT_STORAGE_DIR` | local PDF storage |
| `LOCAL_SCREENSHOT_STORAGE_DIR` | local screenshot storage |
| `OPENAI_API_KEY` | OpenAI API key |
| `OPENAI_MODEL` | OpenAI model, currently `gpt-4o` |
| `OPENAI_MAX_TOKENS` | commentary token budget |
| `OPENAI_TEMPERATURE` | commentary randomness |
| `OPENAI_TIMEOUT_SECONDS` | ChatGPT request timeout |
| `RUBRIC_SEO_PATH` | SEO rubric YAML path |
| `RUBRIC_UXUI_PATH` | UX/UI rubric YAML path |
| `RUBRIC_COMPOSITE_PATH` | composite rubric YAML path |
| `COMMENTARY_SYSTEM_PROMPT_PATH` | system prompt path |
| `COMMENTARY_USER_PROMPT_PATH` | user prompt template path |

Never commit `.env`.

---

## 20. Current Limitations

This is expected at the current stage:

- The worker crawls real websites, but only up to `CRAWLER_MAX_PAGES` total pages including the homepage and selected same-site internal pages.
- PageSpeed is skipped unless `GOOGLE_PSI_API_KEY` is configured.
- PageSpeed can be capped separately with `PSI_MAX_PAGES`, or limited to homepage-only mode with `PSI_SCOPE=homepage`.
- PageSpeed failures are stored as PSI artifacts instead of failing the whole audit.
- SEO facts are extracted from rendered HTML.
- UX/UI facts are extracted with deterministic heuristics, not visual AI judgment.
- Scores are deterministic and produced from YAML rubrics.
- ChatGPT commentary is called when `OPENAI_API_KEY` is configured.
- Local fallback commentary is stored when no OpenAI key is configured.
- Grounding validation checks numeric claims and strips unsupported numeric sentences.
- PDF files are generated in `storage/reports/` with the BLC logo from `assets/brand/blc-logo.svg`.
- `/audits/{job_id}/report` streams the generated PDF when the file exists.
- `/audits/{job_id}` returns per-audit scores and the composed report payload for the UI.
- The operator UI screens (submit, progress/result, history) are implemented and call the API.

The remaining application work is primarily Epic P1-E6: end-to-end QA, reproducibility QA,
production packaging, and handoff documentation.

---

## 21. What To Build Next

Recommended next implementation order (Epic P1-E6):

1. Run local end-to-end QA through the UI.
2. Run reproducibility QA (same site twice, compare scores and rule breakdowns).
3. Prepare production packaging.
4. Render 5-10 sample reports from real builder/remodeler sites.
5. Finalize deployment and handoff checks.

The current foundation is ready for those additions because:

- job lifecycle states exist
- DB schema has JSON result fields
- API endpoints exist
- worker queue exists
- storage folders exist
- tests and tooling are in place
