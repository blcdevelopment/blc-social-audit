# Phase 2 Implementation Plan & Architecture

**Project:** Social Media & Website Auditing Automation — Phase 2
**Client:** Builder Lead Converter (BLC)
**Execution model:** Extend the proven Phase 1 spine; do not rewrite it.
**Companion docs:** scope & rationale → [`docs/08_PHASE2_PLAN.md`](08_PHASE2_PLAN.md);
Jira epics/tasks + tracking board → [`docs/09_PHASE2_JIRA_PLAN.md`](09_PHASE2_JIRA_PLAN.md).

> **Numbering.** Phase 2 uses sequential IDs like Phase 1 — epics `P2-E1…P2-E5`, tasks
> `P2-1…P2-28`. Epic map: **P2-E1** discovery · **P2-E2** productionization · **P2-E3** deepen
> website · **P2-E4** social · **P2-E5** enrichment (v3).

> **Status reconciliation (2026-06-16).** Several Workstream-A / Epic-P2-E2
> productionization items have **already shipped — ahead of this build manual**: **team
> auth (Clerk)** (opt-in via `CLERK_ISSUER`; §4.1), **managed hosting (Linode + Caddy)**,
> and **CI/CD auto-deploy on merge to `main`** (§4.4). The root **`DEPLOYMENT.md`** is the
> authoritative as-built description. The §1 baseline and the touch-points below were
> written against pre-auth Phase 1; treat §4.1/§4.4 as partly delivered. The rest of
> P2-E2 (S3 storage, full request-level SSRF interception, observability/retention,
> dashboard/share) and all of P2-E3/P2-E4/P2-E5 remain unbuilt.

---

## 0. How to read this document

This is the **build manual** for Phase 2. It answers: *given the locked Phase 2 scope, and
the Phase 1 code as it actually exists today, exactly what do we change and where?*

Sections:
- **§1:** What Phase 1 actually shipped (the spine we extend) — verified against the repo.
- **§2:** Architecture — how Phase 2 extends Phase 1.
- **§3:** Data-model changes (exact columns + migrations).
- **§4:** P2-E2 — productionization (auth, storage, SSRF, hosting, observability, dashboard).
- **§5:** P2-E3 — deepen the website audit (extractors + rubric rules).
- **§6:** P2-E4 — social media audit (adapter, backends, extractor, rubric, commentary, report).
- **§7:** P2-E5 — enrichment (v3).
- **§8:** Sequencing, quality gates, and acceptance.

Every code path named below was verified against the repo at Phase 2 start. If a path
moved, fix it here too.

---

## 1. What Phase 1 actually shipped (verified)

The Phase 1 pipeline is a single Celery task — `run_collection_audit` in
[`apps/worker/tasks.py`](../apps/worker/tasks.py) — that runs these stages in order, writing
progress into `audit_jobs` via `_mark_job`:

1. **Crawl** — `crawler.crawl_site_sync(job.url, settings, job_id)` (Playwright; homepage +
   selected internal pages, capped by `CRAWLER_MAX_PAGES`).
2. **PageSpeed** — `psi_client.collect_pagespeed_facts(urls, settings)` (mobile+desktop,
   `PSI_SCOPE`/`PSI_MAX_PAGES`, graceful skip).
3. **Extract** — `extractor_seo.extract_seo_facts(pages)` + `extractor_uxui.extract_uxui_facts(pages)`.
4. **Score** — `scoring.score_audit(seo_facts, uxui_facts, psi_facts, settings)`.
5. **Commentate** — `commentary.generate_commentary(...)` (Phase 1 is **fully deterministic**:
   it returns a `build_content_plan` result with `provider`/`model` == `"deterministic"` and
   never calls OpenAI; `_call_openai` is dormant scaffolding for Phase 2 polish).
6. **Validate** — `grounding_validator.validate_commentary_grounding(...)`.
7. **Compose + render** — `report_payload.compose_report_payload(job, result)` →
   `pdf_renderer.render_audit_pdf(job, result, settings)` → PDF written under
   `settings.local_report_storage_dir`, path stored in `audit_results.pdf_path`.

Key facts that shape Phase 2:

- **Scoring is rubric-driven and pure.** `score_audit` loads `rubrics/seo.yaml`,
  `rubrics/uxui.yaml`, `rubrics/composite.yaml` and is deterministic. There is **no
  per-domain score module** — adding a category is a rubric + a small `scoring.py` change.
- **The composite is type-locked to two categories.** In
  [`apps/worker/stages/scoring.py`](../apps/worker/stages/scoring.py):
  `Rubric.category` is `Literal["seo", "uxui"]`; `CompositeRubric.weights` is
  `dict[Literal["seo", "uxui"], float]`; `validate_weights` requires the set to be **exactly**
  `{"seo", "uxui"}` summing to 1.0. **Adding `social` (or any new scored category) is a code
  change here, not just YAML.**
- **The job stores only `url`, `niche`, `target_audience`.** See `AuditJob` in
  [`apps/shared/models.py`](../apps/shared/models.py) and `AuditCreateRequest` in
  [`apps/api/schemas/audits.py`](../apps/api/schemas/audits.py). Social handles are new input.
- **There is no storage abstraction.** `pdf_renderer.render_audit_pdf` writes straight to
  `settings.local_report_storage_dir`; screenshots go to `settings.local_screenshot_storage_dir`.
- **Auth is now live (Clerk), opt-in via `CLERK_ISSUER`.** *(Updated 2026-06-16 — shipped
  ahead of this plan; see `DEPLOYMENT.md`.)* `apps/api/auth.py` `require_user()` verifies a
  Clerk JWT and the `/audits/*` router is gated with `Depends(require_user)`. When
  `CLERK_ISSUER` is unset the dependency returns `None` and the API runs **open** — which is
  exactly how local dev, the QA harness, and tests run unauthenticated. The original Phase-1
  baseline (CORS only, every route open) survives only in that key-less mode; P2-6's
  remaining work is hardening (open sign-up → invite-only).
- **SSRF is partial.** The crawler validates the start URL + blocks private hosts by default
  (`crawler_allow_private_hosts=False`), but does not re-validate redirects/sub-resources.
- **The report payload is two-section + composite.** `report_payload.py` types
  `ReportSectionId = Literal["seo", "uxui", "lead_generation"]` and `ScoreCard.id =
  Literal["lead_gen", "seo", "uxui"]`. A social section/card is a typed addition here.
- **18 unit-test files** under `tests/unit/` pass (`pytest`), covering scoring, extractors,
  grounding, report payload, PDF/DOCX, PSI, crawler utils, external-SEO (site-health,
  Screaming Frog, GSC), commentary/content-plan, API, lifecycle, and the full worker run,
  plus a hermetic QA harness (`scripts/qa_e2e.py`, `scripts/qa_reproducibility.py`).

---

## 2. Architecture — how Phase 2 extends Phase 1

Phase 2 keeps the spine and adds collectors, rubrics, and report sections. It does **not**
rewrite the pipeline.

```text
Operator UI (Next.js, + team auth)          ← P2-6, P2-11 (dashboard/history/share/white-label)
        |
        v
FastAPI API (+ team auth)  ──►  Celery workers + Redis
        |                              |
        |     +------------------------+-----------+----------------------+
        |     |                        |           |                      |
        v  Website (DEEPER, P2-E3)  Social (NEW, P2-E4)            Enrichment (v3, P2-E5)
 PostgreSQL  crawler/PSI/CrUX      Bright Data (IG/FB) ·              SEMrush/Ahrefs,
 (managed)   SEO/UX/schema/a11y    YouTube API (official)             GA4/GSC/Clarity
        |        \                   /        \                          /
        |         v                 v          v                        v
        |   deterministic scoring (YAML rubrics: seo, uxui, social, composite)   ← P2-23 composite code change
        |                                   |
        |        grounded commentary (existing pipeline) + validation            ← P2-24
        v                                   |
   S3 report storage (signed URLs) ◄─────  report payload → PDF + dashboard       ← P2-7, P2-25
```

New vs Phase 1: team auth (no multi-tenancy), storage interface + S3, deeper website signals,
a social collector + `social.yaml` + Social Score folded into the composite, a dashboard, and
(v3) enrichment sources.

---

## 3. Data-model changes

All changes are additive Alembic migrations under `migrations/versions/` (Phase 1 already has
`20260528_0001_create_audit_tables.py`). PostgreSQL JSONB suits the nested social facts.

### 3.1 Input — social handles (P2-19 / P2-22)

- `AuditCreateRequest` (`apps/api/schemas/audits.py`): add optional social handles, e.g.
  `instagram: str | None`, `facebook: str | None`, `youtube: str | None` (or a single
  `social_handles: dict[str, str] | None`). Keep them optional so website-only audits are unchanged.
- `AuditJob` (`apps/shared/models.py`): add a `social_handles` JSONB column (nullable) + a
  migration. Pass them through `routes/audits.py` on create.

### 3.2 Results — social facts + social score (P2-22 / P2-23 / P2-25)

Two viable shapes — pick one in P2-5:

- **Extend `audit_results`** (simplest, matches Phase 1): add `social_score INT NULL`,
  `social_facts JSONB`, and fold social into `score_breakdown` (already JSONB). Add
  `social_score` to `AuditResult` + a migration; `AuditListItem`/`AuditDetailResponse` expose it.
- **Add `social_*` tables** (if per-platform rows are wanted later). Heavier; not needed for core.

> Recommendation: **extend `audit_results`** for Phase 2 core. It mirrors the existing
> `seo_score`/`uxui_score`/`lead_gen_score` columns and keeps `_upsert_audit_result` in
> `tasks.py` a small change.

### 3.3 Storage key, not local path (P2-7)

`audit_results.pdf_path` already exists; when S3 is active it stores a **storage key**, not a
filesystem path. No schema change required — only the value's meaning + how the report route
resolves it.

---

## 4. P2-E2 — Productionization & Platform

### 4.1 Team authentication (P2-6)

- Add a FastAPI auth dependency (e.g. `apps/api/deps.py` already exists for DI) that verifies
  a session/JWT from the chosen provider (Clerk / Supabase Auth / Workspace SSO).
- Apply it to the audit router in `apps/api/routes/audits.py` (keep `routes/health.py` public;
  gate `/docs`/`/openapi.json` in non-local envs via `app_env`).
- UI: add login + attach the token in `apps/frontend/lib/api.ts`.
- **No multi-tenancy** — one shared org; do not add `tenant_id`.

### 4.2 Storage interface + S3 (P2-7)

- New `apps/shared/storage.py`:
  ```python
  class ReportStorage(Protocol):
      def save(self, key: str, data: bytes, content_type: str) -> str: ...
      def get(self, key: str) -> bytes: ...
      def url(self, key: str, expires_s: int = 3600) -> str | None: ...
  ```
  with `LocalReportStorage` (default, wraps today's `local_report_storage_dir`) and
  `S3ReportStorage`. Select by config (`storage_backend: local|s3`).
- Route `pdf_renderer.render_audit_pdf` output + crawler screenshot writes through the interface.
- `GET /audits/{id}/report` returns a redirect to `storage.url(key)` when S3 is active, else
  streams the local file as today.

### 4.3 Complete SSRF interception (P2-8)

- In `crawler.py`, register a Playwright route/request handler that resolves each request's host
  and rejects private/loopback/link-local/metadata IPs — for the initial nav, **every redirect
  target**, and sub-resources. Reuse the existing private-host check; add DNS-rebinding mitigation
  (validate the resolved IP, not just the hostname). Blocked requests are logged + skipped, never crash.
- Add tests: public→internal redirect, internal sub-resource, `169.254.169.254`.
- Update [`docs/06_KNOWN_LIMITATIONS.md`](06_KNOWN_LIMITATIONS.md) §2 once closed.

### 4.4 Hosting + CI/CD (P2-9)

- Reuse `apps/api/Dockerfile` + `apps/worker/Dockerfile`. Managed Postgres + Redis; API+worker
  on Railway/Render (or ECS/Fargate); UI on Vercel; TLS at the edge; migrations run on deploy.
- CI runs `pytest` + `ruff` (the repo already has `.pre-commit-config.yaml` + `.github/workflows/`);
  merge to main deploys.

### 4.5 Observability + retention (P2-10)

- Sentry in API + worker; secrets to the platform secret store (out of `.env`).
- Metrics + an alert on failure rate / queue backlog; automated DB backups (test a restore).
- A retention task (Celery beat or a scheduled job) prunes old `audit_jobs`/`audit_results`
  rows + stored reports/screenshots past a configured TTL.
- Celery retry / dead-letter handling beyond `celery_task_soft_time_limit_seconds`.

### 4.6 Dashboard + share + white-label (P2-11)

- The backend already returns the full composed `ReportPayload` from `GET /audits/{id}`
  (`AuditDetailResponse.report`). The dashboard is a **frontend** consumer of that — no new
  contract. Add history filter/sort + re-run (re-`POST /audits` with the same inputs), shareable
  read-only links, and white-label branding (reuse the `brand/blc.yaml` pattern).

---

## 5. P2-E3 — Deepen the website audit

**Pattern for every P2-E3 task:** add facts to the existing bundle → add YAML rubric rules →
**bump the rubric `version`** (per [`docs/04_RUBRIC_GUIDE.md`](04_RUBRIC_GUIDE.md)) → re-run the
strong/weak calibration gate (`make qa`). The fact bundle passed to scoring is
`{"seo": seo_facts, "uxui": uxui_facts, "psi": psi_facts}` (see `score_audit`), and rules
reference facts by `fact_path` (e.g. `seo.summary.pages_with_schema`).

| Task | New facts (where) | New rules (where) | Notes |
|---|---|---|---|
| P2-12 schema/JSON-LD | `extractor_seo.py` → `seo.schema.*` | `rubrics/seo.yaml` | LocalBusiness/Org/Service/Review/FAQ/Breadcrumb presence+validity |
| P2-13 AEO/GEO | extractor → `seo.aeo.*` | `rubrics/seo.yaml` | `llms.txt`, AI-crawler allow/deny, answer structure |
| P2-14 CrUX field CWV | `psi_client.py` (or new CrUX client) → `psi.crux.*` | `rubrics/seo.yaml` | LCP/INP/CLS; `skip_if_missing: true` like existing PSI rules |
| P2-15 accessibility | axe-core via Playwright in `crawler.py` → `uxui.a11y.*` | `rubrics/uxui.yaml` | counts by impact/category |
| P2-16 crawlability/links | `extractor_seo.py` + crawl output → `seo.crawlability.*`, `seo.links.*` | `rubrics/seo.yaml` | sitemap/robots/canonical/redirects + broken/orphan links |
| P2-17 local SEO | `extractor_seo.py` (+ reuse P2-12 schema) → `seo.local.*` | `rubrics/seo.yaml` | NAP, GBP link, location pages, map, LocalBusiness |
| P2-18 trust + security | `extractor_uxui.py` → `uxui.trust.*`, `seo.security.*` | `rubrics/uxui.yaml` (+ optional technical) | testimonials/badges/forms + HTTPS/HSTS/headers/mixed-content |

**Optional AEO sub-score:** if "AI Visibility / AEO" should be its **own scored category**
rather than SEO rules, it takes the *same composite code change as social* (§6.4): extend the
`Literal[...]` + rebalance `composite.yaml`. Otherwise it is YAML-only.

> **No `scoring.py` change for P2-E3** unless a new *category* is introduced. Adding rules to
> the existing `seo`/`uxui` categories is pure YAML + new extractor facts.

---

## 6. P2-E4 — Social media audit

Architecturally a **clone of the website pipeline**. Reuse Extract → Score → Commentate →
Validate; add a social collector + extractor, a `social.yaml` rubric, social commentary, and a
social report section.

### 6.1 Provider adapter + backends (P2-19, P2-20, P2-21)

- New package, e.g. `apps/worker/stages/social/` with an adapter interface:
  ```python
  class SocialProvider(Protocol):
      def fetch_profile(self, platform: str, handle: str) -> dict: ...
      def fetch_recent_posts(self, platform: str, handle: str, limit: int) -> list[dict]: ...
  ```
  and a registry that picks a backend per platform.
- **YouTube backend (P2-19, first):** YouTube Data API v3 — `channels.list` (1 quota unit) for
  subs/views/video count; recent uploads. Free, just an API key; build first to prove the pipeline.
- **Bright Data backend (P2-20, IG/FB):** any public account (business or personal), post-level
  depth, pay-per-success (~$0.75/1K). **Gated on the P2-3 smoke test; legal sign-off ✅ given (P2-1).**
- **No OAuth and no IG Business Discovery** — dropped by BLC decision (both need a Facebook
  app / account approval Darius declined; Bright Data already covers Instagram). **LinkedIn
  excluded; TikTok deferred** (same adapter supports TikTok later with no rework).
- **Graceful degradation:** missing/failed social data is skipped (like missing PSI), never aborts
  the audit — mirror the `psi_client` skip pattern.

### 6.2 New worker stages in the pipeline (`tasks.py`)

In `run_collection_audit`, after extraction, add a social collect+extract step (guarded by
"are any social handles present?") and pass social facts into scoring/commentary/validation.
New `AuditStatus` values can be added in
[`apps/shared/audit_states.py`](../apps/shared/audit_states.py) (e.g. `COLLECTING_SOCIAL`) and a
progress step in `_mark_job` — optional but improves UX.

### 6.3 Social fact extractor + schema (P2-22)

- New `apps/worker/stages/extractor_social.py` (matches `extractor_seo.py`/`extractor_uxui.py`
  naming) → a **common social-facts schema** regardless of source: followers, posting cadence +
  consistency, engagement-rate estimate, content-type mix, bio/CTA, link-in-bio/funnel signals.
- Fixtures under `tests/fixtures/` from the P2-3 captures (strong/weak/malformed), with expected
  outputs + unit tests — mirroring the website extractor fixtures.

### 6.4 `social.yaml` + the composite code change (P2-23)

This is the one genuinely-not-just-YAML change. In
[`apps/worker/stages/scoring.py`](../apps/worker/stages/scoring.py):

1. `Rubric.category`: `Literal["seo", "uxui"]` → `Literal["seo", "uxui", "social"]`.
2. `CompositeRubric.weights`: `dict[Literal["seo", "uxui"], float]` → add `"social"`.
3. `validate_weights`: `expected = {"seo", "uxui"}` → `{"seo", "uxui", "social"}`.
4. `score_audit`: load `rubrics/social.yaml`, score the social category, include it in
   `scores`/`categories`, and extend `compose_lead_generation_score` to take three inputs.
5. `rubrics/composite.yaml`: rebalance to three weights summing to 1.0 — the Plan's proposed
   default is **0.35 SEO / 0.40 UX/UI / 0.25 social** (`docs/08_PHASE2_PLAN.md` / `docs/03_ARCHITECTURE.md` §6).
6. Calibrate `social.yaml` against the strong/weak accounts from P2-4; the gate must still hold.

> Keep `compose_lead_generation_score` backward-compatible for website-only audits (social
> weight applies only when social facts exist — decide whether to renormalize the two website
> weights when social is absent, so a website-only audit isn't penalized for missing social).

### 6.5 Commentary + grounding (P2-24)

- Add social commentary prompt(s) in `prompts/`; pass social facts + social score into
  `generate_commentary` (`commentary.py`). The local fallback must produce correct generic social
  prose when no LLM key is set (Phase 1 pattern).
- Extend `validate_commentary_grounding` (`grounding_validator.py`) `fact_sources` to include
  `social_facts` so unsupported social numbers are stripped.

### 6.6 Report + PDF + dashboard (P2-25)

In [`apps/worker/stages/report_payload.py`](../apps/worker/stages/report_payload.py):

- `ReportSectionId`: add `"social"`; `ScoreCard.id`: add `"social"`; `SECTION_LABELS`: add a
  Social label; compose a social section + score card; the Lead-Gen card reflects the new composite.
- Extend the WeasyPrint template (`templates/report.html` + `templates/report.css`) with a Social
  section (findings + tiered recommendations) and verify pagination.
- Surface social in the dashboard (P2-11).
- End-to-end QA on real builder site+social pairs; reproducible for identical inputs.

---

## 7. P2-E5 — Enrichment (v3)

Deferred (Plan §6). Competitor benchmarking (SEMrush/Ahrefs/Similarweb) + user-authorized
analytics (GA4, Search Console, Clarity, SEMrush). These move from anonymous public-data audits
to user-authorized data sources — a separate phase, recurring cost, OAuth flows. Not built in
Phase 2 core.

---

## 8. Sequencing, quality gates, acceptance

### 8.1 Order

1. **P2-E1** (2–3 days) — keys + Bright Data account, draft `social.yaml` (legal ✅ given; no OAuth/Business Discovery).
2. **P2-E2** + **P2-E3** in parallel — both low-risk, reuse what works.
3. **P2-E4** — start once P2-3 (Bright Data smoke test) is done; YouTube first, then Bright Data.
4. **P2-E5** — v3 only.

(Matches the week-by-week in [`docs/08_PHASE2_PLAN.md`](08_PHASE2_PLAN.md) §9.1.)

### 8.2 Quality gates (extend Phase 1's)

| # | Gate | How to verify |
|---|---|---|
| Q1 | Website audit still reproducible | Same facts → identical SEO/UX/Lead-Gen scores (existing `make qa-repro`) |
| Q2 | P2-E3 calibration holds | After each P2-E3 task, `make qa` strong ≥ threshold, weak ≤ threshold; rubric version bumped |
| Q3 | Social score reproducible | Same social facts → identical Social + Lead-Gen scores |
| Q4 | Social grounding | An unsupported social number in commentary is stripped by the validator |
| Q5 | Auth enforced | Unauthenticated API calls get 401; `/health` stays public |
| Q6 | SSRF closed | public→internal redirect, internal sub-resource, and metadata IP are blocked |
| Q7 | S3 + signed URLs | A report saves to S3 and downloads via a signed URL |
| Q8 | Composite integrity | `rubrics/composite.yaml` validates with three weights summing to 1.0; website-only audits aren't wrongly penalized |
| Q9 | End-to-end on real data | A real builder site + its IG/FB/YouTube produce a combined report (PDF + dashboard) |

### 8.3 Acceptance

Phase 2 core acceptance = the Done Criteria in
[`docs/09_PHASE2_JIRA_PLAN.md`](09_PHASE2_JIRA_PLAN.md) §5 and the acceptance criteria in
[`docs/08_PHASE2_PLAN.md`](08_PHASE2_PLAN.md) §12 — auth-gated, S3-stored, SSRF-hardened, hosted,
observable; deeper website signals scored with the calibration gate holding; and a deterministic
Social Score folded into Lead-Gen Readiness, validated on real builder sites **and** their social
accounts.

---

**End of Phase 2 implementation plan.** Keep this in lockstep with `08_PHASE2_PLAN.md` (scope)
and `09_PHASE2_JIRA_PLAN.md` (tickets). If a code path named here moves, update it here too.
