# Architecture & Code Guide

**Project:** Social Media & Website Auditing Automation (BLC)
**Scope:** How the Phase 1 system is built — components, data flow, the data model,
the non-negotiable patterns, and a file-by-file code map. This is the single
architecture reference (it replaces the earlier separate implementation plan,
code walkthrough, overview, and Mermaid diagram).

---

## 1. High-level shape

```text
Next.js Operator UI (apps/frontend)
        |  HTTP / JSON
        v
FastAPI Backend (apps/api)  ───────────────►  PostgreSQL (audit_jobs, audit_results)
        |  enqueue                                    ▲
        v                                             │ read / write
Redis broker ──► Celery Worker (apps/worker)  ────────┘
                      │  run_collection_audit (tasks.py)
                      ▼
              Pipeline stages (apps/worker/stages):
              crawler → psi_client → extractor_seo / extractor_uxui
              → scoring → commentary → grounding_validator
              → report_payload → pdf_renderer
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
| Operator UI | `apps/frontend` | Submit URL, poll progress, list audits, download PDF |
| API | `apps/api/routes/audits.py` | Create jobs, status/detail reads, report download, list |
| API health | `apps/api/routes/health.py` | `GET /health` |
| App + CORS | `apps/api/main.py` | FastAPI app, CORS, Swagger redirect |
| Settings | `apps/shared/config.py` | Env-driven `Settings` (single source of config) |
| Models | `apps/shared/models.py` | `AuditJob`, `AuditResult` (+ portable `GUID`/JSON types) |
| Lifecycle | `apps/shared/audit_states.py` | `AuditStatus` enum + terminal states |
| DB session | `apps/shared/database.py` | SQLAlchemy engine + `SessionLocal` |
| Worker app | `apps/worker/celery_app.py` | Celery configuration (Redis broker/backend) |
| Orchestrator | `apps/worker/tasks.py` | `run_collection_audit` drives stages + status updates |
| Crawler | `apps/worker/stages/crawler.py` | Playwright render, link discovery, robots, SSRF guards |
| PageSpeed | `apps/worker/stages/psi_client.py` | PSI mobile/desktop collection, retries, cache, graceful skip |
| Extractors | `extractor_seo.py`, `extractor_uxui.py` | Deterministic SEO / UX facts |
| Scoring | `apps/worker/stages/scoring.py` | YAML rubric engine → SEO/UX/Lead-Gen scores |
| Commentary | `apps/worker/stages/commentary.py` | OpenAI commentary + local fallback |
| Grounding | `apps/worker/stages/grounding_validator.py` | Strip unsupported numeric claims |
| Report payload | `apps/worker/stages/report_payload.py` | Compose the report data model |
| Branding | `apps/worker/stages/report_branding.py` | BLC brand config + placeholder fallback |
| PDF renderer | `apps/worker/stages/pdf_renderer.py` | WeasyPrint/Jinja2 branded PDF → `storage/reports/` |

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
`audit_jobs` row at each transition (15% crawl … 100% complete). On any exception
the job is marked `failed` with the error message, and the exception is re-raised
so Celery records the failure.

---

## 4. Data model

| Table | Key fields |
|---|---|
| `audit_jobs` | `id`, `url`, `niche`, `target_audience`, `status`, `current_stage`, `progress_pct`, `error_message`, timestamps |
| `audit_results` | `job_id` (1:1), `seo_score`, `uxui_score`, `lead_gen_score`, plus JSON blobs: `crawled_pages`, `seo_facts`, `uxui_facts`, `psi_facts`, `score_breakdown`, `commentary`, `validation_log`, `report_metadata`, `pdf_path`, `rubric_version`, `llm_model` |

JSON columns use PostgreSQL `JSONB` in production and portable `JSON` elsewhere; a
`GUID` type decorator maps to Postgres UUID or `CHAR(36)`. This portability is what
lets the hermetic QA harness run on SQLite. Migrations live in `migrations/`
(`alembic upgrade head`); the Compose `api` service runs them on start.

### 4.1 The stage contract

Each stage produces a structured artifact the next stage consumes; the fact bundle
passed to scoring is `{"seo": seo_facts, "uxui": uxui_facts, "psi": psi_facts}`, and
rubric rules reference facts by `fact_path` (e.g. `seo.summary.pages_with_schema`).
This is the seam Phase 2 plugs the social audit into (a `social` fact bundle + a
`social.yaml` rubric + a `social` composite weight).

---

## 5. Key design decisions (non-negotiable)

- **Scores are deterministic and rule-based.** The LLM writes commentary only; it
  never produces a score. Identical facts always yield identical scores.
- **Hybrid scoring.** Deterministic Python rules produce numbers; the LLM produces
  prose. Never invert this.
- **Grounded commentary.** Numeric claims in commentary are checked against the
  extracted facts; unsupported claims are stripped (`grounding_validator.py`).
- **Config-driven rubrics.** Scoring rules live in external YAML, not in code, and
  are versioned (bump the version when you tune — see [`docs/04_RUBRIC_GUIDE.md`](04_RUBRIC_GUIDE.md)).
- **Structured pipeline, not autonomous agents.** Each audit is a fixed
  Extract → Score → Commentate → Validate sequence. No free-form agent loops.
- **Graceful degradation.** Missing OpenAI/PSI keys, failed internal pages, and
  missing performance data never abort an audit — they downgrade to fallbacks or
  skipped rules.
- **Config is environment-only.** All settings come from environment variables
  (`apps/shared/config.py`, documented in `.env.template`).
- **Reports are stored on the local filesystem** under `storage/reports/`
  (an object-storage backend is Phase 2 work).

---

## 6. Scoring & the Lead-Generation Readiness score

`scoring.py` is a pure, config-driven rubric engine:

- `load_rubric` validates each `rubrics/*.yaml` (Pydantic, `extra="forbid"`).
- Each rule has a `weight`, a `fact_path`, and an `evaluator`
  (`boolean`, `presence`, `range`, `exact_match`, `threshold`, `linear_scale`),
  optionally `skip_if_missing` (used for PSI rules so a missing API key doesn't penalize).
- `score_category` evaluates rules, rescales to `max_score`, and emits a per-rule
  audit trail.
- `compose_lead_generation_score` combines the category scores via
  `rubrics/composite.yaml` weights. Phase 1: **0.45 SEO + 0.55 UX/UI**. Phase 2 adds
  `social` and rebalances (proposed **0.35 / 0.40 / 0.25**) — note this is a typed
  code change in `scoring.py` (the `Literal[...]` category set), not YAML-only.

Reproducibility is the whole point: same facts in → same scores out, with a visible
breakdown explaining every contribution.

---

## 7. API surface

| Endpoint | Purpose |
|---|---|
| `GET /health` | Liveness |
| `POST /audits` | Create + enqueue an audit job |
| `GET /audits` | List recent audits (with scores + report availability) |
| `GET /audits/{job_id}` | Audit detail + composed report payload |
| `GET /audits/{job_id}/status` | Progress (stage, percentage, report availability) |
| `GET /audits/{job_id}/report` | Download the generated PDF |
| `GET /docs`, `GET /openapi.json` | Interactive API docs |

There is **no authentication** in Phase 1 (internal/local only) — see
[`docs/06_KNOWN_LIMITATIONS.md`](06_KNOWN_LIMITATIONS.md). Team auth is Phase 2.

---

## 8. Tests & verification

Unit tests live in `tests/` and run on every commit (pre-commit + CI):

- `test_scoring_engine.py` — rubric validation, calibration (strong ≥ / weak ≤), reproducibility.
- `test_extractors.py` — strong/weak/malformed fixtures vs expected JSON.
- `test_crawler_utils.py` — URL safety, same-site rules, HTTP-failure logic.
- `test_psi_client.py` — normalization, skip path, API-key header.
- `test_commentary.py`, `test_grounding_validator.py` — schema, fallback, claim stripping.
- `test_report_payload.py`, `test_pdf_renderer.py` — report composition + pagination edges.
- `test_audit_api.py`, `test_audit_lifecycle.py`, `test_worker_collection.py` — API + persistence + full worker artifacts.

The hermetic QA harness (`scripts/qa_e2e.py`, `scripts/qa_reproducibility.py`,
`make qa` / `make qa-repro`) runs the real pipeline end-to-end on SQLite with no
PostgreSQL, Docker, or paid API keys required.

For setup/run instructions see [`docs/02_SETUP_GUIDE.md`](02_SETUP_GUIDE.md); to
operate the tool see [`docs/05_OPERATOR_GUIDE.md`](05_OPERATOR_GUIDE.md).
