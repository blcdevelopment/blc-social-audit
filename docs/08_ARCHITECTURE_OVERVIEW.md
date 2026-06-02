# Architecture Overview (P1-26)

A concise map of the local-first BLC Website Audit system. For the full diagram
see `docs/06_CURRENT_ARCHITECTURE.mmd`; for a line-by-line tour see
`docs/05_CODE_WALKTHROUGH.md`.

---

## 1. High-Level Shape

```text
Next.js Operator UI (apps/frontend)
        |  HTTP/JSON
        v
FastAPI Backend (apps/api)  ──────────────►  PostgreSQL (audit_jobs, audit_results)
        |  enqueue                                   ▲
        v                                            │ read/write
Redis broker ──► Celery Worker (apps/worker)  ───────┘
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

The design separates **product risk** (crawl/score/commentary/PDF quality) from
**infrastructure risk** (hosting), so the local app is proven before any
production hosting work.

---

## 2. Components

| Component | Module | Responsibility |
|---|---|---|
| Operator UI | `apps/frontend` | Submit URL, poll progress, list audits, download PDF |
| API | `apps/api/routes/audits.py` | Create jobs, status/detail reads, report download, list |
| API health | `apps/api/routes/health.py` | `GET /health` |
| Settings | `apps/shared/config.py` | Env-driven `Settings` (single source of config) |
| Models | `apps/shared/models.py` | `AuditJob`, `AuditResult` (+ portable `GUID`/JSON types) |
| Lifecycle | `apps/shared/audit_states.py` | `AuditStatus` enum + terminal states |
| Worker app | `apps/worker/celery_app.py` | Celery configuration |
| Orchestrator | `apps/worker/tasks.py` | `run_collection_audit` drives stages + status updates |
| Crawler | `apps/worker/stages/crawler.py` | Playwright render, link discovery, robots, SSRF guards |
| PageSpeed | `apps/worker/stages/psi_client.py` | PSI mobile/desktop collection, retries, graceful skip |
| Extractors | `extractor_seo.py`, `extractor_uxui.py` | Deterministic SEO/UX facts |
| Scoring | `apps/worker/stages/scoring.py` | YAML rubric engine → SEO/UX/Lead Gen scores |
| Commentary | `apps/worker/stages/commentary.py` | OpenAI commentary + local fallback |
| Grounding | `apps/worker/stages/grounding_validator.py` | Strip unsupported numeric claims |
| Report payload | `apps/worker/stages/report_payload.py` | Compose the report data model |
| PDF renderer | `apps/worker/stages/pdf_renderer.py` | WeasyPrint/Jinja2 branded PDF written to local `storage/reports/` |

---

## 3. Audit Lifecycle (states)

`AuditStatus` (`apps/shared/audit_states.py`) drives the progress the UI shows:

```text
queued → crawling → collecting_performance → extracting → scoring
       → commenting → validating → rendering → complete
                                              (or → failed)
```

`tasks.py` updates `status`, `current_stage`, and `progress_pct` on the
`audit_jobs` row at each transition (15% crawl … 100% complete). On any
exception the job is marked `failed` with the error message, and the exception is
re-raised so Celery records the failure.

---

## 4. Data Model

| Table | Key fields |
|---|---|
| `audit_jobs` | `id`, `url`, `niche`, `target_audience`, `status`, `current_stage`, `progress_pct`, `error_message`, timestamps |
| `audit_results` | `job_id` (1:1), `seo_score`, `uxui_score`, `lead_gen_score`, plus JSON blobs: `crawled_pages`, `seo_facts`, `uxui_facts`, `psi_facts`, `score_breakdown`, `commentary`, `validation_log`, `report_metadata`, `pdf_path`, `rubric_version`, `llm_model` |

JSON columns use PostgreSQL `JSONB` in production and portable `JSON` elsewhere; a
`GUID` type decorator maps to Postgres UUID or `CHAR(36)`. This portability is
what lets the QA harness run on SQLite.

---

## 5. Key Design Decisions

- **Scores are deterministic and rule-based.** The LLM writes commentary only; it
  never produces a score. Identical facts always yield identical scores
  (verified in `docs/12_QA_REPORT.md`).
- **Graceful degradation.** Missing OpenAI/PSI keys, failed internal pages, and
  missing performance data never abort an audit — they downgrade to fallbacks or
  skipped rules.
- **Grounded commentary.** Numeric claims in commentary are checked against the
  extracted facts; unsupported claims are stripped.
- **Config is environment-only.** All settings come from environment variables
  (`apps/shared/config.py`, documented in `.env.template`).
- **Reports are stored on the local filesystem** under `storage/reports/`.

---

## 6. API Surface

| Endpoint | Purpose |
|---|---|
| `GET /health` | Liveness |
| `POST /audits` | Create + enqueue an audit job |
| `GET /audits` | List recent audits (with scores + report availability) |
| `GET /audits/{job_id}` | Audit detail + composed report payload |
| `GET /audits/{job_id}/status` | Progress (stage, percentage, report availability) |
| `GET /audits/{job_id}/report` | Download the generated PDF |
| `GET /docs`, `GET /openapi.json` | Interactive API docs |
