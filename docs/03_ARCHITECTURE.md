# Architecture & Code Guide

**Project:** Social Media & Website Auditing Automation (BLC)
**Scope:** How the Phase 1 system is built — components, data flow, the data model,
the non-negotiable patterns, and a file-by-file code map. This is the prose
architecture reference (it replaces the earlier separate implementation plan, code
walkthrough, and overview). The up-to-date Mermaid diagrams `architecture.mmd` and
`audit-flow.mmd` are the visual companions to this doc.

---

## 1. High-level shape

```text
Next.js Operator UI (apps/frontend)
        |  HTTP / JSON (Clerk Bearer token / __session cookie)
        v
FastAPI Backend (apps/api)  ───────────────►  PostgreSQL
        |  enqueue                              (audit_jobs, audit_results,
        v                                        google_search_console_connections)
Redis broker ──► Celery Worker (apps/worker)  ────────────────────────────────┘
                      │  run_collection_audit (tasks.py)
                      ▼
              Pipeline stages (apps/worker/stages):
              crawler → psi_client → extractor_seo / extractor_uxui
              → external_seo → scoring → commentary → grounding_validator
              → report_payload → pdf_renderer / docx_renderer
                      │
                      ▼
              Local report storage (storage/reports/*.pdf)
```

The design separates **product risk** (crawl / score / commentary / PDF quality)
from **infrastructure risk** (hosting), so the local app is proven before any
production hosting work. Phase 2 extends this spine without rewriting it (see
[`docs/08_PHASE2_PLAN.md`](08_PHASE2_PLAN.md) and
[`docs/10_PHASE2_IMPLEMENTATION.md`](10_PHASE2_IMPLEMENTATION.md)).

---

## 2. Components

| Component | Module | Responsibility |
|---|---|---|
| Operator UI | `apps/frontend` | Submit URL, poll progress, list audits, download PDF (Clerk-gated) |
| API | `apps/api/routes/audits.py` | Create jobs, status/detail reads, report/DOCX download, list, rerun-enrichment |
| Google routes | `apps/api/routes/google.py` | GSC OAuth connect / callback / properties |
| Auth | `apps/api/auth.py` | `require_user()` — Clerk JWT verification (opt-in via `CLERK_ISSUER`) |
| API health | `apps/api/routes/health.py` | `GET /health` |
| App + CORS | `apps/api/main.py` | FastAPI app, CORS, Swagger redirect |
| Settings | `apps/shared/config.py` | Env-driven `Settings` (single source of config) |
| Models | `apps/shared/models.py` | `AuditJob`, `AuditResult`, `GoogleSearchConsoleConnection` (+ portable `GUID`/JSON types) |
| Lifecycle | `apps/shared/audit_states.py` | `AuditStatus` enum + terminal states |
| DB session | `apps/shared/database.py` | SQLAlchemy engine + `SessionLocal` |
| Worker app | `apps/worker/celery_app.py` | Celery configuration (Redis broker/backend) |
| Orchestrator | `apps/worker/tasks.py` | `run_collection_audit` + `rerun_external_enrichment` drive stages + status updates |
| Crawler | `apps/worker/stages/crawler.py` | Playwright render, link discovery, robots, SSRF guards |
| PageSpeed | `apps/worker/stages/psi_client.py` | PSI mobile/desktop collection, retries, cache, graceful skip |
| Extractors | `extractor_seo.py`, `extractor_uxui.py` | Deterministic SEO / UX facts |
| External SEO | `external_seo.py`, `site_health.py`, `screaming_frog.py`, `google_search_console.py` | Technical-crawl sweep (+ optional Screaming Frog CLI) and GSC facts; always degrades gracefully |
| Scoring | `apps/worker/stages/scoring.py` | YAML rubric engine → SEO/UX/Lead-Gen scores |
| Commentary | `apps/worker/stages/commentary.py`, `content_plan.py` | Deterministic content plan (Phase 1); LLM polish is dormant scaffolding |
| Grounding | `apps/worker/stages/grounding_validator.py` | Strip unsupported numeric claims |
| Report payload | `apps/worker/stages/report_payload.py` | Compose the report data model |
| Branding | `apps/worker/stages/report_branding.py` | BLC brand config + placeholder fallback |
| PDF renderer | `apps/worker/stages/pdf_renderer.py` | WeasyPrint/Jinja2 branded PDF → `storage/reports/` |
| DOCX renderer | `apps/worker/stages/docx_renderer.py` | Hand-written OOXML DOCX (failure never aborts the audit) |

**Versioned assets** (tunable without code): `rubrics/*.yaml`, `prompts/*.md`,
`templates/report.html` + `report.css`, `brand/blc.yaml`. See
[`docs/04_RUBRIC_GUIDE.md`](04_RUBRIC_GUIDE.md) for rubric structure and tuning.

---

## 3. Audit lifecycle (states)

`AuditStatus` (`apps/shared/audit_states.py`) drives the progress the UI shows:

```text
queued → crawling → collecting_performance → extracting → scoring
       → commenting → validating → rendering → complete
                                              (or → failed)
```

`tasks.py` updates `status`, `current_stage`, and `progress_pct` on the
`audit_jobs` row at each transition. The full progression is:

```text
15  crawling
45  collecting_performance (PSI)
70  extracting (SEO + UX/UI)
76  extracting (external SEO — technical-crawl sweep + GSC)
80  scoring
88  commenting
95  validating
98  rendering
100 complete   (or → failed)
```

`_mark_job` is the single writer of job state: it commits each transition, clears
`error_message` on a success transition, and sets `started_at`/`completed_at`. On any
exception the transaction is rolled back, the job is marked `failed` with the error
message, and the exception is re-raised so Celery records the failure
(`SoftTimeLimitExceeded` is always re-raised).

**Re-enrichment path.** An already-`complete` audit can be re-run for *external SEO
only* via the `rerun_external_enrichment` Celery task (orchestrated by
`rerun_external_enrichment_for_audit`): it re-collects external SEO → rescores (pct 82)
→ re-comments → re-renders, **without** re-crawling or re-running PSI. It snapshots the
result fields first and restores them — keeping the job `complete` with the prior
report — if the rerun fails. Exposed via `POST /audits/{job_id}/rerun-enrichment`.

---

## 4. Data model

| Table | Key fields |
|---|---|
| `audit_jobs` | `id`, `url`, `niche`, `target_audience`, `status`, `current_stage`, `progress_pct`, `error_message`, timestamps |
| `audit_results` | `job_id` (1:1, CASCADE, unique), `seo_score`, `uxui_score`, `lead_gen_score`, plus JSON blobs: `crawled_pages`, `seo_facts`, `uxui_facts`, `psi_facts`, `external_seo_facts`, `score_breakdown`, `commentary`, `validation_log`, `report_metadata`, `pdf_path`, `rubric_version`, `llm_model` |
| `google_search_console_connections` | Standalone (no FK to jobs/results), keyed by unique `account_email`; stores Google OAuth tokens (`access_token`, `refresh_token`, `token_expires_at`), `scopes` (JSON), `properties` (JSON), timestamps |

JSON columns use PostgreSQL `JSONB` in production and portable `JSON` elsewhere; a
`GUID` type decorator maps to Postgres UUID or `CHAR(36)`. This portability is what
lets the hermetic QA harness run on SQLite. Migrations live in `migrations/`
(`alembic upgrade head`; head = `20260611_0002`, which adds the `external_seo_facts`
column and creates `google_search_console_connections`); the Compose `api` service
runs them on start. Alembic targets PostgreSQL only (`CREATE EXTENSION pgcrypto`,
`JSONB`); SQLite tables are created via `Base.metadata.create_all` in tests/QA, never
via Alembic.

### 4.1 The stage contract

Each stage produces a structured artifact the next stage consumes; the fact bundle
passed to scoring is
`{"seo": seo_facts, "uxui": uxui_facts, "psi": psi_facts, "external_seo": external_seo_facts}`,
and rubric rules reference facts by `fact_path` (e.g. `seo.summary.pages_with_schema`,
`external_seo.technical_crawl.summary.missing_titles`,
`uxui.pages[0].forms.total_field_count`). The unified external-SEO key is
`external_seo.technical_crawl.*` (the legacy `external_seo.screaming_frog.*` key is still
read for backward compat). This is the seam Phase 2 plugs the social audit into (a
`social` fact bundle + a `social.yaml` rubric + a `social` composite weight).

---

## 5. Key design decisions (non-negotiable)

- **Scores are deterministic and rule-based.** Commentary never produces a score.
  Identical facts always yield identical scores.
- **Phase 1 commentary is fully deterministic.** `commentary.py` builds its prose from
  the deterministic content plan (`content_plan.py`) and reports
  `status/provider/model == "deterministic"` — Phase 1 never calls OpenAI. A dormant
  `_call_openai()` path and `prompts/*.md` are retained scaffolding for Phase 2 LLM
  polish. (When that path is enabled, the rule still holds: rules produce numbers, the
  LLM only produces prose — never invert this.)
- **Grounded commentary.** Numeric claims in commentary are checked against the
  extracted facts; unsupported claims are stripped (`grounding_validator.py`). Timeframe
  phrases ("1–3 months") are masked first so they survive, and if stripping would empty a
  field it reverts to baseline prose.
- **Config-driven rubrics.** Scoring rules live in external YAML, not in code, and
  are versioned (bump the version when you tune — see [`docs/04_RUBRIC_GUIDE.md`](04_RUBRIC_GUIDE.md)).
- **Structured pipeline, not autonomous agents.** Each audit is a fixed
  Extract → Score → Commentate → Validate sequence. No free-form agent loops.
- **Graceful degradation.** Missing PSI keys, an absent/failed external-SEO source
  (Screaming Frog / GSC / site-health), failed internal pages, and missing performance
  data never abort an audit — they downgrade to fallbacks or skipped rules. Only
  `status == "complete"` external-SEO summaries are scored; non-complete sources have
  their summary stripped before scoring (`scoring._trusted_external_seo_facts`).
- **Config is environment-only.** All settings come from environment variables
  (`apps/shared/config.py`, documented in `.env.template`).
- **Authentication is Clerk, opt-in by env.** `apps/api/auth.py` `require_user()`
  verifies a Clerk RS256 JWT (from the `Authorization: Bearer` header or the `__session`
  cookie) against the issuer's JWKS. It is **opt-in**: if `CLERK_ISSUER` is empty,
  `require_user()` returns `None` and the API is open — exactly how local dev, the QA
  harness, and tests run unauthenticated. Production sets `CLERK_ISSUER` (with a
  fail-fast guard); the whole `/audits/*` router is gated, as are the Google routes
  except the unauthenticated GSC OAuth callback (protected instead by an HMAC-signed,
  time-limited CSRF state).
- **Reports are stored on the local filesystem** under `storage/reports/`
  (an object-storage backend is Phase 2 work).

---

## 6. Scoring & the Lead-Generation Readiness score

`scoring.py` is a pure, config-driven rubric engine:

- `load_rubric` validates each `rubrics/*.yaml` (Pydantic, `extra="forbid"`). Phase 1:
  `seo.yaml` (`phase1-seo-v4`, 23 rules), `uxui.yaml` (`phase1-uxui-v2`, 14 rules),
  `composite.yaml` (`phase1-composite-v1`, weights only). The combined `rubric_version`
  stored on the result is `phase1-seo-v4+phase1-uxui-v2+phase1-composite-v1`.
- Each rule has a `weight`, a `fact_path`, and an `evaluator`
  (`boolean`, `presence`, `range`, `exact_match`, `threshold`, `linear_scale`),
  optionally `skip_if_missing` (used for PSI rules with `linear_scale` so a missing API
  key doesn't penalize — the fact is dropped from both numerator and denominator and the
  category rescales). `threshold` is overloaded: `min`/`partial_min` = higher-is-better;
  `max`/`partial_max` = lower-is-better (used for all external-crawl/GSC count rules).
- Each rule also carries content-plan metadata consumed by `content_plan.py`: `impact`,
  `tier`, `finding_label`, `remediation`, `surface_as_finding` (defaults `impact=medium`,
  `tier=quick_win`, `surface_as_finding=true`).
- `score_category` evaluates rules, rescales to `max_score`, and emits a per-rule
  audit trail.
- `compose_lead_generation_score` combines the category scores via
  `rubrics/composite.yaml` weights. Phase 1: **0.45 SEO + 0.55 UX/UI** (weights must sum
  to 1.0 over exactly `{seo, uxui}`). Phase 2 adds `social` and rebalances (proposed
  **0.35 / 0.40 / 0.25**) — note this is a typed code change in `scoring.py` (the
  `Literal["seo","uxui"]` category set), not YAML-only.

Reproducibility is the whole point: same facts in → same scores out, with a visible
breakdown explaining every contribution.

---

## 7. API surface

| Endpoint | Purpose |
|---|---|
| `GET /health` | Liveness |
| `GET /` | 307 redirect → `/docs` |
| `POST /audits` | Create + enqueue an audit job (201) |
| `GET /audits` | List recent audits (`limit` 1–100, default 25; `offset`) |
| `GET /audits/{job_id}` | Audit detail + composed report payload |
| `GET /audits/{job_id}/status` | Progress (stage, percentage, report availability) |
| `POST /audits/{job_id}/rerun-enrichment` | Re-run external SEO → rescore/recomment/re-render (404 no job / 409 no result / 503 enqueue fail) |
| `GET /audits/{job_id}/report` | Download the generated PDF |
| `GET /audits/{job_id}/docx` | Download the DOCX (rendered on demand if absent) |
| `GET /google/search-console/connect` | Start GSC OAuth |
| `GET /google/search-console/connect-url` | Return the GSC OAuth URL |
| `GET /google/search-console/callback` | GSC OAuth callback (**unauthenticated**; protected by an HMAC-signed CSRF state) |
| `GET /google/search-console/properties` | List connected GSC properties |
| `GET /docs`, `GET /redoc`, `GET /openapi.json` | Interactive API docs |

`compose_report_payload(job, result)` (`apps/worker/stages/report_payload.py`,
`REPORT_PAYLOAD_VERSION` `phase1-report-v2`) is **pure** and imported by both the worker
(to render) and the API (to build the detail response) — keep it pure.

**Authentication is Clerk, opt-in by env** (see §5 and `apps/api/auth.py`). When
`CLERK_ISSUER` is set, the whole `/audits/*` router and the Google routes (except the
unauthenticated GSC callback) require a verified Clerk JWT. When `CLERK_ISSUER` is empty
the API is open — local dev, the QA harness, and tests run this way. Clerk is currently a
**dev** instance and open sign-up is a known gap (invitation is a manual operator step);
see [`docs/06_KNOWN_LIMITATIONS.md`](06_KNOWN_LIMITATIONS.md). CORS has a credential guard
in `main.py`: if `*` is in `API_CORS_ORIGINS`, `allow_credentials` is forced off.

---

## 8. Tests & verification

There are **18** unit test files in `tests/unit/` and they run on every commit
(pre-commit + CI). `tests/integration/` exists but is empty (`.gitkeep` only); there is
no `conftest.py`. Highlights:

- `test_scoring_engine.py` — rubric validation, calibration (strong ≥ / weak ≤), reproducibility.
- `test_extractors.py` — strong/weak/malformed fixtures vs expected JSON.
- `test_crawler_utils.py` — URL safety, same-site rules, HTTP-failure logic.
- `test_psi_client.py` — normalization, skip path, API-key header.
- `test_commentary.py`, `test_content_plan.py`, `test_grounding_validator.py` — deterministic content plan, schema, claim stripping.
- `test_external_seo`-family: `test_site_health.py`, `test_screaming_frog.py`, `test_google_search_console.py` — technical-crawl sweep, Screaming Frog adapter, GSC facts.
- `test_report_payload.py`, `test_pdf_renderer.py`, `test_docx_renderer.py` — report composition, pagination edges, DOCX rendering.
- `test_audit_api.py`, `test_audit_lifecycle.py`, `test_worker_collection.py`, `test_time_budget.py`, `test_qa_harness.py` — API + persistence + full worker artifacts + harness.

The hermetic QA harness (`scripts/qa_common.py`, `scripts/qa_e2e.py`,
`scripts/qa_reproducibility.py`, `make qa` / `make qa-repro`) runs the real pipeline
end-to-end on ephemeral SQLite with no PostgreSQL, Docker, or paid API keys required
(PSI / OpenAI / Screaming Frog / GSC / site-health are all forced onto their skip paths).
It is operator-run, not wired into CI.

For setup/run instructions see [`docs/02_SETUP_GUIDE.md`](02_SETUP_GUIDE.md); to
operate the tool see [`docs/05_OPERATOR_GUIDE.md`](05_OPERATOR_GUIDE.md).

---

## 9. Deployment

This app runs **live in production**. For the authoritative deployment topology — the
single Linode VM, the `docker-compose.prod.yml` six-service stack (postgres, redis, api,
worker, frontend, caddy), Caddy TLS + single-origin reverse proxy, and the
PR → pre-commit → merge → SSH deploy CI/CD flow — see
[`DEPLOYMENT.md`](../DEPLOYMENT.md). `alembic upgrade head` runs automatically on the
`api` container start.

---

*Last reconciled with the code: 2026-06-16.*
