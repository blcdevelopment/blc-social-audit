# BLC Website Audit Automation

Local-first Phase 1 repository for the Builder Lead Converter website audit MVP.

The Phase 1 build focuses on a website audit pipeline: URL submission, Playwright crawling, PageSpeed data collection, SEO and UX/UI extraction, deterministic scoring, grounded OpenAI/ChatGPT commentary, branded PDF generation, and an internal operator UI.

Production and AWS deployment work is intentionally prepared after the local application works end-to-end.

## Phase 1 Foundation And Epic P1-E2 Collection Pipeline

The repo now includes the local app foundation and the Epic P1-E2 audit collection pipeline:

- FastAPI backend in `apps/api`.
- Celery worker in `apps/worker`.
- Shared settings, database, models, and lifecycle states in `apps/shared`.
- Next.js TypeScript frontend shell in `apps/frontend`.
- Alembic migrations in `migrations`.
- Shared folders for `rubrics/`, `prompts/`, `templates/`, and `tests/fixtures/`.
- Local Docker Compose stack for PostgreSQL, Redis, API, worker, and local report storage.
- Playwright crawler for homepage plus selected same-site internal pages.
- PageSpeed Insights collection for each selected crawled page, mobile and desktop, with `PSI_SCOPE` / `PSI_MAX_PAGES` controls and graceful skip/failure handling.
- Deterministic SEO and UX/UI fact extractors backed by fixture tests.

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

2. Copy environment defaults:

   ```bash
   cp .env.example .env
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

10. Start the frontend shell:

   ```bash
   cd apps/frontend
   npm install
   npm run dev
   ```

   The frontend is available at `http://localhost:3000`.

## API Endpoints

- `GET /health`
- `GET /docs`
- `GET /openapi.json`
- `POST /audits`
- `GET /audits`
- `GET /audits/{job_id}/status`
- `GET /audits/{job_id}/report`

The current worker runs the Epic P1-E2 collection pipeline. It crawls pages, collects or skips PageSpeed facts, extracts SEO/UX facts, and stores those artifacts in `audit_results`. Scoring, OpenAI commentary, validation, and PDF rendering remain explicit later-epic placeholders.
