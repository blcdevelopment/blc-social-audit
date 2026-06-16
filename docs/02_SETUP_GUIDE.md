# Developer Setup Guide (P1-26)

Step-by-step setup for the local-first BLC Website Audit system. This expands on
the quick start in the repository `README.md`.

> **Last reconciled: 2026-06-16.** For *production* deployment (Linode VM, Docker
> Compose prod stack, Caddy/TLS, CI/CD) see [`DEPLOYMENT.md`](../DEPLOYMENT.md) —
> this guide covers local development only.

---

## 1. Prerequisites

| Tool | Why |
|---|---|
| Conda (Miniconda/Anaconda) | Provides the native Pango/GLib/font libraries WeasyPrint needs |
| Poetry | Python dependency management |
| Node.js 18+ and npm | Operator UI (`apps/frontend`) |
| Docker + Docker Compose | Local PostgreSQL, Redis, API, and worker stack |

You can run the backend either **with Docker Compose** (recommended, includes
PostgreSQL + Redis) or **natively** in the Conda environment (you then provide
your own PostgreSQL and Redis).

---

## 2. Python Environment

```bash
# Create (or update) the Conda environment with native WeasyPrint libs
conda env create -f environment.yml      # first time
conda env update -f environment.yml --prune   # subsequent updates
conda activate social-audit

# Install Python dependencies (Poetry, inside the Conda env)
poetry install --with dev                # or: make install

# Install the Playwright browser used by the crawler
python -m playwright install chromium chromium-headless-shell   # or: make browsers
```

---

## 3. Configuration

```bash
cp .env.template .env
```

Then edit `.env`. Every setting is documented in `.env.template` and parsed by
`apps/shared/config.py`. Key groups:

| Group | Keys | Notes |
|---|---|---|
| Database | `DATABASE_URL`, `POSTGRES_*` | PostgreSQL connection |
| Queue | `REDIS_URL`, `CELERY_*` | Celery broker/result backend |
| OpenAI | `OPENAI_API_KEY`, `OPENAI_MODEL` | **Phase 1 does not call OpenAI** — commentary is fully deterministic. These keys feed only the dormant Phase 2 LLM-polish path |
| PageSpeed | `GOOGLE_PSI_API_KEY`, `PSI_*` | Optional; PSI rules skip gracefully when empty |
| Crawler | `CRAWLER_*` | Page cap, timeouts, robots, private-host policy |
| Storage | `LOCAL_REPORT_STORAGE_DIR`, `LOCAL_SCREENSHOT_STORAGE_DIR`, `LOCAL_TOOL_EXPORT_STORAGE_DIR` | Local filesystem paths for PDFs, screenshots, and external-tool exports |
| Rubrics/prompts/templates | `RUBRIC_*`, `COMMENTARY_*`, `REPORT_*`, `BRAND_CONFIG_PATH` | Paths to scoring/branding assets |

### Optional integrations (all off by default)

The app runs **open and fully functional** with none of these configured; each
degrades gracefully (sources that aren't `complete` have their summary stripped
before scoring, so a missing/failed integration never penalizes a score or aborts
an audit). Add them only when you want the corresponding capability.

| Group | Keys | Notes |
|---|---|---|
| Clerk auth | `CLERK_ISSUER`, `CLERK_SECRET_KEY`, `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_AUTHORIZED_PARTIES` | **Opt-in.** Leave `CLERK_ISSUER` empty and the API is **open** (this is how local dev, tests, and the QA harness run unauthenticated). Set `CLERK_ISSUER` to gate the whole `/audits/*` router behind a Clerk JWT |
| Site Health sweep | `SITE_HEALTH_*` | Built-in technical-crawl source (tool id `site_health_sweep`), **enabled by default**, zero extra dependencies. Caps internal/external URL counts, concurrency, and time budget |
| Screaming Frog | `SCREAMING_FROG_*` | Optional licensed CLI for technical crawl; `SCREAMING_FROG_ENABLED=false` by default. When enabled it is preferred over the site-health sweep, which remains the fallback |
| Google OAuth / Search Console | `GOOGLE_OAUTH_*`, `GOOGLE_OAUTH_STATE_SECRET`, `GSC_*`, `URL_INSPECTION_MAX_URLS` | Optional OAuth connection for Search Analytics + URL Inspection facts |

> Without `OPENAI_API_KEY`, `GOOGLE_PSI_API_KEY`, `CLERK_ISSUER`, Screaming Frog, or
> Google OAuth, the system still completes a full audit: the API is open, commentary
> is the deterministic content plan, PageSpeed rules are skipped, and external-SEO
> sources fall back (the built-in site-health sweep) or skip. This is exactly what the
> QA harness relies on.

---

## 4. Run the Backend

### Option A — Docker Compose (recommended)

```bash
docker compose up --build        # or: make docker-up
```

This starts PostgreSQL, Redis, the API (which runs `alembic upgrade head` then
Uvicorn), and the Celery worker. The API is at `http://localhost:8000`
(`/docs` for OpenAPI).

### Option B — Native processes

Run each in its own terminal (PostgreSQL and Redis must already be running):

```bash
make migrate        # alembic upgrade head
make run-api        # uvicorn on :8000
make run-worker     # celery worker
```

---

## 5. Run the Operator UI

```bash
cd apps/frontend
npm install
npm run dev          # or: make run-frontend
```

The UI is served at `http://localhost:3000` and calls the API at
`http://localhost:8000` by default. Override with `NEXT_PUBLIC_API_BASE_URL`. The
API's `API_CORS_ORIGINS` must include the UI origin (`http://localhost:3000` by
default).

---

## 6. Quality & QA Commands

```bash
make test            # pytest unit suite
make lint            # ruff check .
make format          # ruff format .
pre-commit install   # enable pre-commit hooks

make qa              # P1-23 local end-to-end QA (hermetic, no infra/keys)
make qa-repro        # P1-24 reproducibility QA
```

See [`docs/03_ARCHITECTURE.md`](03_ARCHITECTURE.md) §8 for what the QA harness proves.

---

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| WeasyPrint import / font errors | Native libs missing | Use the Conda env (`conda activate social-audit`); it bundles Pango/GLib/fonts |
| Crawler cannot launch a browser | Playwright browser not installed | `make browsers`; or set `CRAWLER_CHROMIUM_EXECUTABLE_PATH` |
| `alembic upgrade head` fails on SQLite | Migration targets PostgreSQL (`pgcrypto`) | Run against PostgreSQL; the SQLite path is only used by the hermetic QA harness via `create_all` |
| API returns 503 on submit | Worker/Redis not reachable | Ensure Redis and the Celery worker are running |
| Commentary provider is `deterministic` | Phase 1 design — no LLM is called | Expected; the deterministic content plan is the output unconditionally. `OPENAI_API_KEY` only feeds the dormant Phase 2 polish path |

---

## 8. Where Things Live

| Path | Contents |
|---|---|
| `apps/api/` | FastAPI app, routes, schemas |
| `apps/worker/` | Celery app, `tasks.py` orchestrator, `stages/` pipeline modules |
| `apps/shared/` | Settings, database engine/session, ORM models, audit-state enum (storage dirs are config values in `config.py`) |
| `apps/frontend/` | Next.js operator UI |
| `rubrics/` | YAML scoring rubrics (see `docs/04_RUBRIC_GUIDE.md`) |
| `prompts/` | Commentary system/user prompts (wired into the dormant Phase 2 LLM-polish path only) |
| `templates/`, `brand/`, `assets/` | PDF template, CSS, branding |
| `migrations/` | Alembic migrations |
| `scripts/` | QA harness (`qa_e2e.py`, `qa_reproducibility.py`, `qa_common.py`) |
| `tests/` | Unit tests + HTML fixtures |
| `docs/` | Requirements, implementation, architecture, and handoff docs |
