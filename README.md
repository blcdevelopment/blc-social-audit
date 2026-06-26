# BLC Website Audit Automation

Local-first Phase 1 repository for the Builder Lead Converter website audit MVP.

The Phase 1 build focuses on a website audit pipeline: URL submission, Playwright crawling, PageSpeed data collection, SEO and UX/UI extraction, deterministic scoring, deterministic grounded commentary, branded PDF/DOCX generation, and an internal operator UI (Clerk-gated). The Website Audit page also accepts optional social profile links: when one or more is provided the run becomes a **combined audit** that appends a Social Media Audit section and an Overall Lead-Gen Readiness score to the same report.

The application is deployed and live at https://ai.builderleadconverter.com. See [DEPLOYMENT.md](DEPLOYMENT.md) for the authoritative production deployment reference (Linode VM, Docker Compose, Caddy TLS, and GitHub Actions CI/CD).

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
- Optional Screaming Frog SEO Spider CLI enrichment for deeper technical SEO facts
  (broken URLs, non-indexable pages, missing/duplicate metadata, H1s, canonicals, and
  image alt issues) when installed/licensed on the worker.
- Optional Google Search Console enrichment through official Google APIs, including
  search analytics, property matching, and URL Inspection for priority URLs.
- Deterministic SEO and UX/UI fact extractors backed by fixture tests.
- YAML scoring rubrics in `rubrics/` with schema validation and versioning.
- Rule-based SEO, UX/UI, and Lead Generation Readiness scoring.
- Fully deterministic Phase 1 commentary built from a content plan (no LLM call); `prompts/` are wired only into a dormant OpenAI polish path reserved for Phase 2.
- Grounding validation that strips unsupported numeric commentary claims.
- Report payload composition from audit metadata, scores, findings, recommendations, validation,
  PageSpeed, and crawl QA artifacts.
- Branded WeasyPrint/Jinja2 PDF rendering with the BLC logo asset and text fallback.
- Local PDF/DOCX output in `storage/reports/` and download support through
  `GET /audits/{job_id}/report` and `GET /audits/{job_id}/docx`.
- Operator UI screens: a single Website Audit submission page (with optional Instagram /
  Facebook / YouTube fields — providing any handle makes the run a combined audit), an
  auto-polling progress + result page (stage stepper, percentage, scores, findings,
  PDF download; for combined audits it appends a Social Media Audit block and an Overall
  Lead-Gen Readiness block at the end), and an audit history dashboard with client-side
  search, status filter, and sort (loads up to 100 audits; combined rows show a "Full" badge
  and an Overall score). The top nav is just **Website Audit** and **Audit History** — the
  separate Social Audit tab/page was removed.
- Request-level SSRF hardening: each crawl browser context attaches a Playwright route
  guard that aborts sub-resource and redirect requests resolving to private/loopback/
  link-local/reserved/metadata IPs (`CRAWLER_INTERCEPT_REQUESTS`, on by default; auto-
  disabled when `CRAWLER_ALLOW_PRIVATE_HOSTS` is true for local/QA).
- Storage retention cleanup that prunes reports, screenshots, and tool exports older than
  `STORAGE_RETENTION_DAYS` (default 90; 0 disables) via `scripts/cleanup_storage.py`
  (run from cron on the host — there is no in-app scheduler).
- Optional Sentry error reporting for the API and worker, enabled only when `SENTRY_DSN`
  is set and `sentry-sdk` is installed (no-op otherwise, mirroring the Clerk opt-in pattern).
- Lightweight operational observability (no Prometheus stack): a gated `GET /metrics` JSON
  endpoint (audit counts by status, 24h throughput, in-flight/oldest job, avg duration, storage
  usage), a cron health-alert script (`scripts/health_alert.py` → `ALERT_WEBHOOK_URL` on
  failed-audit/stuck-job thresholds), and a cron PostgreSQL backup script
  (`scripts/backup_db.py` → timestamped `.sql.gz` with retention).
- Read-only share links: generate a random, time-limited token (default 7 days) so a
  client can view or download a report without an account, plus revoke support.
- Per-client white-label branding: optional brand overrides (name, short name, primary/
  accent color, logo URL) on the create form merge over the default BLC branding in the
  rendered PDF.
- Combined audit (the headline flow): from the same Website Audit page, paste a URL **and** any
  optional Instagram / Facebook / YouTube links and the run becomes a combined audit
  (`audit_type="combined"`). The unchanged website SEO/UX-UI pipeline runs **first**, then the
  social audit runs, producing **one report** (PDF and DOCX) — today's website report with a
  **Social Media Audit** section and an **Overall Lead-Gen Readiness** score appended at the end.
  Overall Readiness = `0.70 × website Lead-Gen composite + 0.30 × Social Score`, computed by
  `scoring.compose_overall_readiness_score()` from the config-driven `rubrics/overall.yaml`
  (`phase2-overall-v1`; rescales to the website score alone when social is missing). It lives in
  `score_breakdown["overall_readiness"]` — no new DB column or migration (Alembic head is still
  `20260625_0005`; `audit_jobs.audit_type` is now `website | social | combined`). The combined
  branch runs after the website result is committed and **degrades gracefully**: any failure in
  the social/overall step completes the audit as a website-only report rather than failing the
  whole job. Website scoring and the existing report sections are byte-for-byte unchanged.
- Social audit data layer (`apps/worker/stages/social/`): reads an Instagram, Facebook, or
  YouTube profile link (or `@handle`) — no login, OAuth, or account connection — via Apify
  (Instagram Scraper + Facebook Pages & Posts Scrapers, free tier) and/or the free YouTube Data
  API v3, each behind a uniform `SocialProvider` adapter + registry (`social/providers.py`) the
  collector dispatches over, normalizes the payload into a typed common fact schema
  (`social/schema.py`) of `social.*` facts, and scores it against `rubrics/social.yaml`
  (`phase2-social-v1`) into a 0–100 Social Score via `scoring.score_social_audit()`. Findings and
  recommendations are derived deterministically from the rubric rule metadata (in the standalone
  social path, optionally polished into client-ready prose by GPT-4o when `OPENAI_API_KEY` is set
  — grounded, with the deterministic version as the no-key fallback; the combined report's social
  findings are deterministic, no LLM). Facebook page metadata (Pages scraper) is augmented with
  recent posts (Posts scraper), so FB yields cadence/recency/engagement like Instagram; if the
  Posts scraper returns nothing those rules skip and rescale rather than penalize. Instagram and
  YouTube carry full post/upload data. The backend still supports a **standalone** Social audit
  type (`audit_type="social"`, own `social_score` + `social_facts` and its own
  `templates/social_report.html` PDF; the website composite `{seo, uxui}` is unchanged), but the
  separate Social Audit UI page was removed — social now runs from the Website Audit page as part
  of a combined audit. Past standalone social audits still render in history and detail.
- Clerk authentication (opt-in): the `/audits/*` router and most Google routes require
  a verified Clerk session when `CLERK_ISSUER` is set; with `CLERK_ISSUER` empty the API
  is open, which is how local dev, the QA harness, and tests run unauthenticated.
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
- `GET /metrics` (gated; aggregate audit counts by status, 24h throughput, in-flight/oldest, avg duration, and local report-storage usage as JSON)
- `GET /` (redirects to `/docs`)
- `GET /docs`, `GET /redoc`, `GET /openapi.json`
- `POST /audits` (create + enqueue, 201; body takes `audit_type` `website` (default) | `social` | `combined` plus `social_handles` — website requires `url`, social requires ≥1 handle, combined requires **both** `url` and ≥1 handle)
- `GET /audits` (`limit` 1–100, default 25; `offset`; rows expose `audit_type`, `social_score`, and `overall_score`)
- `GET /audits/{job_id}` (audit detail with scores incl. `overall_score`; website and combined audits return the composed `report` payload — for combined it carries the appended social + overall sections — and social-only audits return a `social_report`)
- `GET /audits/{job_id}/status`
- `POST /audits/{job_id}/rerun-enrichment` (re-runs external SEO → rescore → recomment → re-render)
- `POST /audits/{job_id}/share` (generates a time-limited share token)
- `DELETE /audits/{job_id}/share` (revokes the share token)
- `GET /audits/{job_id}/report` (streams the PDF)
- `GET /audits/{job_id}/docx` (renders the DOCX on demand if absent)
- `GET /shared/{token}` (public, token-gated report payload; 410 expired, 404 missing/revoked)
- `GET /shared/{token}/report` (public, token-gated PDF download)
- `GET /google/search-console/connect`
- `GET /google/search-console/connect-url`
- `GET /google/search-console/callback` (unauthenticated; Google calls it, protected by an HMAC-signed, time-limited CSRF state)
- `GET /google/search-console/properties`

When `CLERK_ISSUER` is configured, the `/audits/*` router and the Google routes (except the
OAuth callback) require a verified Clerk Bearer token or `__session` cookie. The `/shared/*`
routes are intentionally unauthenticated — access is granted only by a valid, unexpired,
non-revoked share token.

The current worker runs collection, scoring, commentary, grounding validation, report payload
composition, and branded PDF/DOCX rendering. It crawls pages, collects or skips PageSpeed facts,
extracts SEO/UX facts, optionally enriches with the built-in site-health sweep (or Screaming Frog
when licensed) and Google Search Console facts, scores the audit through YAML rubrics, generates
deterministic grounded commentary, validates numeric claims, renders exports into local storage,
and stores the final export paths in `audit_results`.

## Optional SEO Enrichment

The default technical crawl is a built-in site-health sweep (tool id `site_health_sweep`) that
needs no extra dependencies and re-validates every redirect hop through the SSRF guard. Screaming
Frog is an optional alternative, disabled by default. To enable it on a worker that has SEO Spider
installed and licensed, set:

```bash
SCREAMING_FROG_ENABLED=true
SCREAMING_FROG_BINARY=/path/to/screamingfrogseospider
```

Google Search Console enrichment requires OAuth credentials and verified property access:

```bash
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/google/search-console/callback
```

Connect once through `GET /google/search-console/connect`, then run a new audit or use
`POST /audits/{job_id}/rerun-enrichment` on an existing audit. Missing Screaming Frog or
Google data is marked as skipped and does not penalize scores.

## Optional Configuration

These settings are all optional and ship with safe defaults (most are documented in
`.env.template`):

- `CRAWLER_INTERCEPT_REQUESTS` (default `true`) — enable request-level SSRF interception on
  the crawler; auto-disabled when `CRAWLER_ALLOW_PRIVATE_HOSTS` is true.
- `STORAGE_RETENTION_DAYS` (default `90`, `0` disables) — retention window used by
  `scripts/cleanup_storage.py`.
- `SENTRY_DSN` (empty by default) — set to enable Sentry error reporting for the API and
  worker; `SENTRY_TRACES_SAMPLE_RATE` tunes tracing. Disabled when empty.
- `SHARE_LINK_TTL_DAYS` (default `7`) — lifetime of generated read-only share links.
- `APIFY_API_TOKEN` (empty by default) / `APIFY_TIMEOUT_SECONDS` (default `120`) — credentials
  and timeout for the social audit's Apify provider (Instagram + Facebook scrapers). Without a
  token the social collector skips gracefully.
- `YOUTUBE_API_KEY` (empty by default) / `YOUTUBE_TIMEOUT_SECONDS` (default `30`) — the free
  YouTube Data API v3 backend for the social audit (a plain API key, no OAuth). Empty key ⇒ the
  YouTube backend skips gracefully, like Apify.
- `RUBRIC_OVERALL_PATH` (default `./rubrics/overall.yaml`) — the config-driven rubric that blends
  the website Lead-Gen composite (0.70) with the Social Score (0.30) into the combined audit's
  Overall Lead-Gen Readiness score; tune the two weights (must sum to 1.0) and bump its `version`.
- `ALERT_WEBHOOK_URL` (empty by default) / `ALERT_FAILED_AUDITS_THRESHOLD` (default `5`) /
  `ALERT_STUCK_AUDIT_MINUTES` (default `60`) — operational alerting for `scripts/health_alert.py`
  (cron). Empty webhook ⇒ it only logs findings; otherwise posts a Slack/Discord/generic
  `{"text": …}` message when failed-audit or stuck-job thresholds are breached.
- `BACKUP_STORAGE_DIR` (default `./storage/backups`) / `BACKUP_RETENTION_DAYS` (default `14`) /
  `PG_DUMP_PATH` (default `pg_dump`) — PostgreSQL backups for `scripts/backup_db.py` (cron).

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

A few maintenance/exploration scripts are run directly:

```bash
python scripts/cleanup_storage.py [--dry-run] [--days N]   # prune old reports/screenshots/exports (run from cron on the host)
python scripts/health_alert.py [--dry-run]                 # check audit health vs thresholds, alert via ALERT_WEBHOOK_URL (cron)
python scripts/backup_db.py [--days N]                      # pg_dump the database to a timestamped .sql.gz + prune old backups (cron)
python scripts/run_social_audit.py <handle_or_url>         # standalone Social audit end-to-end (Apify scrape -> Social Score), no DB/web app
python scripts/check_apify_social.py [handle_or_url]        # live Apify social probe (Instagram/Facebook) for the social data layer
```

## Documentation

| Doc | Contents |
|---|---|
| [docs/01_REQUIREMENTS.md](docs/01_REQUIREMENTS.md) | Product requirements & scope of record |
| [docs/02_SETUP_GUIDE.md](docs/02_SETUP_GUIDE.md) | Developer setup guide |
| [docs/03_ARCHITECTURE.md](docs/03_ARCHITECTURE.md) | Architecture & code guide (components, data model, patterns, code map) |
| [docs/04_RUBRIC_GUIDE.md](docs/04_RUBRIC_GUIDE.md) | Scoring rubric guide & tuning |
| [docs/05_OPERATOR_GUIDE.md](docs/05_OPERATOR_GUIDE.md) | Operator usage guide |
| [docs/06_KNOWN_LIMITATIONS.md](docs/06_KNOWN_LIMITATIONS.md) | Known limitations |
| [docs/07_DEPLOYMENT_GUIDE.md](docs/07_DEPLOYMENT_GUIDE.md) | Internal deployment guide |
| [docs/08_PHASE2_PLAN.md](docs/08_PHASE2_PLAN.md) | Phase 2 scope, approach & timeline |
| [docs/09_PHASE2_JIRA_PLAN.md](docs/09_PHASE2_JIRA_PLAN.md) | Phase 2 Jira epics, tasks & tracking board (copy-paste ready) |
| [docs/10_PHASE2_IMPLEMENTATION.md](docs/10_PHASE2_IMPLEMENTATION.md) | Phase 2 build manual — code touch-points & sequencing |
| [docs/11_COMMENTARY_CONSISTENCY_PLAN.md](docs/11_COMMENTARY_CONSISTENCY_PLAN.md) | Commentary consistency plan |
| [docs/13_AI_INSIGHTS_INTEGRATION_PLAN.md](docs/13_AI_INSIGHTS_INTEGRATION_PLAN.md) | AI-visibility insights integration plan (parked) |
| [docs/14_AI_VISIBILITY_VENDOR_SELECTION.md](docs/14_AI_VISIBILITY_VENDOR_SELECTION.md) | AI-visibility vendor selection (parked) |
| [docs/15_FUTURE_ARCHITECTURE_OPTIONS.md](docs/15_FUTURE_ARCHITECTURE_OPTIONS.md) | Future design reference: combine social into the website Lead-Gen score; Apify→Bright Data swap; S3 |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Authoritative production deployment reference (live stack, CI/CD) |
