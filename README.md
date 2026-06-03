# BLC Website Audit Automation

Local-first Phase 1 repository for the Builder Lead Converter website audit MVP.

The Phase 1 build focuses on a website audit pipeline: URL submission, Playwright crawling, PageSpeed data collection, SEO and UX/UI extraction, deterministic scoring, grounded OpenAI/ChatGPT commentary, branded PDF generation, and an internal operator UI.

Production and AWS deployment work is intentionally prepared after the local application works end-to-end.

## Phase 1 Foundation Through Epic P1-E6

The repo now includes the local app foundation, Epic P1-E2 collection pipeline, Epic
P1-E3 scoring/commentary pipeline, Epic P1-E4 PDF report generation, the Epic
P1-E5 internal operator UI, and the Epic P1-E6 QA, packaging, and handoff work:

- FastAPI backend in `apps/api`.
- Celery worker in `apps/worker`.
- Shared settings, database, models, and lifecycle states in `apps/shared`.
- Next.js TypeScript operator UI in `apps/frontend` (audit submission, live progress,
  result view, and audit history).
- Alembic migrations in `migrations`.
- Shared folders for `rubrics/`, `prompts/`, `templates/`, and `tests/fixtures/`.
- Local Docker Compose stack for PostgreSQL, Redis, API, worker, and local report storage.
- Playwright crawler for homepage plus selected same-site internal pages.
- PageSpeed Insights collection for each selected crawled page, mobile and desktop, with `PSI_SCOPE` / `PSI_MAX_PAGES` controls and graceful skip/failure handling.
- Deterministic SEO and UX/UI fact extractors backed by fixture tests.
- YAML scoring rubrics in `rubrics/` with schema validation and versioning.
- Rule-based SEO, UX/UI, and Lead Generation Readiness scoring.
- ChatGPT commentary prompts in `prompts/`, with a local fallback when no OpenAI key is configured.
- Grounding validation that strips unsupported numeric commentary claims.
- Report payload composition from audit metadata, scores, findings, recommendations, validation,
  PageSpeed, and crawl QA artifacts.
- Branded WeasyPrint/Jinja2 PDF rendering with the BLC logo asset and text fallback.
- Local PDF output in `storage/reports/` and download support through `GET /audits/{job_id}/report`.
- Operator UI screens: audit submission with validation and error handling, an
  auto-polling progress + result page (stage stepper, percentage, scores, findings,
  PDF download), and an audit history table with status, scores, and report links.
- Hermetic QA harness in `scripts/` that runs the real pipeline end-to-end and
  proves reproducibility with no PostgreSQL, Docker, or paid API keys required.
- A `Makefile` of common developer and QA commands.
- Developer, architecture, rubric, operator, and known-limitations documentation
  plus a QA report under `docs/`.

## Local Setup

1. Create and activate the Conda environment:

   ```bash
   conda env create -f environment.yml
   conda activate social-audit
   ```

   If the environment already exists, update it instead:

   ```bash
   conda env update -f environment.yml --prune
   conda activate social-audit
   ```

   The Conda environment includes native Pango/GLib/font libraries required by WeasyPrint.

2. Copy environment defaults:

   ```bash
   cp .env.template .env
   ```

3. Install Python dependencies with Poetry inside the Conda environment:

   ```bash
   poetry install --with dev
   ```

4. Install the Playwright Chromium browser used by the crawler:

   ```bash
   python -m playwright install chromium chromium-headless-shell
   ```

5. Start the local backend stack:

   ```bash
   docker compose up --build
   ```

   The API is available at `http://localhost:8000`.

6. Run migrations manually when working outside Docker Compose:

   ```bash
   alembic upgrade head
   ```

7. Run backend tests:

   ```bash
   pytest
   ```

8. Run linting and formatting:

   ```bash
   ruff check .
   ruff format .
   ```

9. Install pre-commit hooks:

   ```bash
   pre-commit install
   ```

10. Start the operator UI:

   ```bash
   cd apps/frontend
   npm install
   npm run dev
   ```

   The UI is available at `http://localhost:3000` and talks to the API at
   `http://localhost:8000` by default. Point it at a different API with the
   `NEXT_PUBLIC_API_BASE_URL` environment variable, e.g.:

   ```bash
   NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev
   ```

   The API's `API_CORS_ORIGINS` setting must include the UI origin
   (`http://localhost:3000` by default).

## API Endpoints

- `GET /health`
- `GET /docs`
- `GET /openapi.json`
- `POST /audits`
- `GET /audits`
- `GET /audits/{job_id}` (audit detail with scores and composed report payload)
- `GET /audits/{job_id}/status`
- `GET /audits/{job_id}/report`

The current worker runs collection, scoring, commentary, grounding validation, report payload
composition, and branded PDF rendering. It crawls pages, collects or skips PageSpeed facts,
extracts SEO/UX facts, scores the audit through YAML rubrics, generates ChatGPT commentary when
`OPENAI_API_KEY` is configured, falls back locally when it is not, validates numeric claims,
renders a PDF into local storage, and stores the final `pdf_path` in `audit_results`.

## Common Commands

A `Makefile` wraps the everyday commands (run `make help` for the full list):

```bash
make install      # poetry install --with dev
make browsers     # install the Playwright Chromium browser
make migrate      # alembic upgrade head
make run-api      # uvicorn on :8000
make run-worker   # celery worker
make test         # pytest
make qa           # P1-23 local end-to-end QA (hermetic; no infra/keys needed)
make qa-repro     # P1-24 reproducibility QA
make docker-up    # build + start the local stack
```

## Documentation

| Doc | Contents |
|---|---|
| [docs/01_REQUIREMENTS.md](docs/01_REQUIREMENTS.md) | Product requirements |
| [docs/02_IMPLEMENTATION.md](docs/02_IMPLEMENTATION.md) | Implementation plan |
| [docs/03_PHASE1_JIRA_PLAN.md](docs/03_PHASE1_JIRA_PLAN.md) | Epics, tasks, done criteria |
| [docs/04_PHASE1_CONFLUENCE_HANDOFF.md](docs/04_PHASE1_CONFLUENCE_HANDOFF.md) | Stakeholder handoff |
| [docs/05_CODE_WALKTHROUGH.md](docs/05_CODE_WALKTHROUGH.md) | Line-by-line code tour |
| [docs/06_CURRENT_ARCHITECTURE.mmd](docs/06_CURRENT_ARCHITECTURE.mmd) | Architecture diagram (Mermaid) |
| [docs/07_SETUP_GUIDE.md](docs/07_SETUP_GUIDE.md) | Developer setup guide |
| [docs/08_ARCHITECTURE_OVERVIEW.md](docs/08_ARCHITECTURE_OVERVIEW.md) | Architecture overview |
| [docs/09_RUBRIC_GUIDE.md](docs/09_RUBRIC_GUIDE.md) | Scoring rubric guide & tuning |
| [docs/10_OPERATOR_GUIDE.md](docs/10_OPERATOR_GUIDE.md) | Operator usage guide |
| [docs/11_KNOWN_LIMITATIONS.md](docs/11_KNOWN_LIMITATIONS.md) | Known limitations |
| [docs/12_QA_REPORT.md](docs/12_QA_REPORT.md) | End-to-end & reproducibility QA results |
| [docs/13_INTERNAL_DEPLOYMENT_GUIDE.md](docs/13_INTERNAL_DEPLOYMENT_GUIDE.md) | Internal deployment guide & Epic P1-E7 plan |
