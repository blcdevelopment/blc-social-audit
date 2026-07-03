# Phase 2 Implementation Plan & Architecture

> **UPDATE 2026-06-24 — YouTube RE-ADDED.** The "YouTube is dropped" notes (Collect stage,
> `social_handles` "no youtube key", P2-19) are **superseded**. The social pipeline's Collect stage
> now dispatches Instagram + Facebook (Apify) **AND YouTube** (`youtube_provider.py`, YouTube Data
> API v3); `social_handles` accepts a `youtube` key (parsed by the frontend YouTube field) and
> `YOUTUBE_API_KEY` is a real default-empty setting (empty ⇒ graceful skip). **Bright Data and IG
> Business Discovery remain dropped.** Trust `CLAUDE.md` §5 and `README` for as-built truth.

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
> written against pre-auth Phase 1; treat §4.1/§4.4 as partly delivered. ~~The rest of
> P2-E2 (S3 storage, full request-level SSRF interception, observability/retention,
> dashboard/share) and all of P2-E3/P2-E4/P2-E5 remain unbuilt.~~
> *(Superseded by the 2026-06-23 round-2 banner below: **P2-8 SSRF interception is DONE**, **P2-10
> retention + Sentry are DONE**, and **P2-7 S3 storage is REMOVED/descoped** in favour of local VM
> storage. Remaining P2-E2 = dashboard/share + ops-scope metrics/alerts/backups; all of
> P2-E3/P2-E4/P2-E5 remain unbuilt.)*

> **Update (2026-06-23) — two operator decisions reshape this manual:**
> 1. **AI Insights PARKED.** The AI-visibility / AI Insights work
>    ([`docs/13_AI_INSIGHTS_INTEGRATION_PLAN.md`](13_AI_INSIGHTS_INTEGRATION_PLAN.md),
>    [`docs/14_AI_VISIBILITY_VENDOR_SELECTION.md`](14_AI_VISIBILITY_VENDOR_SELECTION.md)) is
>    **deferred** — blocked on an unpurchased paid vendor subscription (Rank Prompt API
>    Starter, $99/mo; live billing unverified). Phase 2 proceeds **without** it. Verified safe:
>    no Phase-2 task depends on AI Insights; AI Insights depends only on the shipped Phase-1
>    spine and on its own vendor trial. To be resumed once the subscription is sorted.
> 2. **Social media audit is now STANDALONE & FULLY INDEPENDENT.** It is a **separate product**,
>    not a section bolted onto the website audit: its own UI tab, its own handle inputs (**no
>    website URL required**), its own **separate report (separate PDF)** and its own
>    **standalone Social Score**. It does **NOT** fold into the website Lead-Gen composite. The
>    website audit's scoring is **UNCHANGED** — `composite.yaml` stays **seo:0.45 / uxui:0.55**,
>    no recalibration, no regression to the live website product. There is **no combined
>    website+social number** (a blended dashboard view is not foreclosed for later, but it would
>    live at the dashboard level, not in any rubric). The scoring **engine** is reused; the
>    website **composite** is not changed. **§3, §6.2, §6.4, and §6.6 social specifics below are
>    updated for this** (and §2's diagram is annotated). The recommended implementation shape:
>    an `audit_type` discriminator (`"website" | "social"`, default `"website"`) on
>    `audit_jobs`, nullable `url`, `social_handles` JSONB; `run_collection_audit` **branches** on
>    `audit_type` (the social branch is a leaner standalone pipeline — no crawl/PSI/external-SEO).
>    ~~Social remains **gated on provisioning** (Bright Data account + YouTube API key + the paid
>    Bright Data smoke test P2-3 before the IG/FB backend P2-20) — unchanged.~~
>    *(Superseded by the 2026-06-23 round-2 banner below: provider is now **Apify** free tier
>    (self-serve, no paid gate), **YouTube is dropped**, and the paid-smoke-test gate P2-3 is
>    removed.)*

> **Update (2026-06-23, round 2) — five operator decisions further reshape this manual:**
> 1. **Social data provider = Apify** ([apify.com](https://apify.com)) on its **free-tier credits**.
>    This **replaces Bright Data everywhere** in the social-audit plan. Apify runs **actors** for
>    **Instagram + Facebook** public data behind the existing provider-adapter (§6.1). TikTok stays
>    an optional later add via Apify.
> 2. **YouTube is dropped entirely.** No YouTube Data API, no YouTube backend, no "build YouTube
>    first". **Social platforms in scope = Instagram + Facebook (via Apify).** Remove YouTube from
>    the pipeline / collector / scope wording (§6.1, §6.2, §6.7, §3.1).
> 3. **Provisioning / paid gates removed.** The paid **Bright Data smoke test P2-3 is REMOVED** (no
>    paid smoke test — Apify free tier is self-serve), and the "gated on P2-3 / don't start P2-20
>    until P2-3" dependencies are dropped. **P2-2** simplifies to *create a free Apify account + API
>    token* (self-serve, free, not a blocked gate; no YouTube key needed). **P2-20** ("Bright Data
>    backend for IG/FB") becomes the **Apify backend for IG/FB** (or folds into P2-19); **P2-19**
>    ("provider adapter + YouTube backend first") becomes **"provider adapter + Apify backend
>    (IG/FB)"**.
> 4. **P2-7 (storage interface + S3) is REMOVED / descoped.** No AWS/S3 — **local filesystem storage
>    on the VM** is the intended design for this internal ~5–10-user tool. Storage retention is
>    handled by **P2-10** (`scripts/cleanup_storage.py`), not S3. See §3.3, §4.2, §8.2 Q7.
> 5. **Productionization status — these shipped in code on 2026-06-23 (§4.3/§4.5):**
>    - **P2-8 request-level SSRF interception = DONE.** The crawler validates **every
>      sub-resource/redirect host** against the private/loopback/metadata-IP block-list during
>      rendering (`apps/worker/stages/crawler.py`: `_host_blocked_for_subrequest` + a Playwright route
>      guard on each context; new setting `crawler_intercept_requests`, auto-disabled when
>      `crawler_allow_private_hosts` is true; unit-tested).
>    - **P2-10 retention = DONE.** `apps/shared/retention.py` + `scripts/cleanup_storage.py` +
>      `storage_retention_days` setting delete reports/screenshots/tool-exports older than N days,
>      run from **cron** (no in-app scheduler); unit-tested.
>    - **Sentry = DONE** (optional, env-gated): `apps/shared/observability.py` + `SENTRY_DSN` setting
>      (no-op when unset). Metrics/alerts/backups remain **VM-ops** tasks (lighter scope for a
>      5–10-user internal tool), not code.

> ## ✅ BUILT — Standalone Social Audit shipped (2026-06-23, round 3 / as-built)
>
> **P2-E4 is DONE and runnable from the browser, end-to-end, fully standalone.** Everything the
> three 2026-06-23 banners above *planned* for social is now **code** (119 unit tests pass — 117
> `test_*` functions counted across `tests/unit/`; ruff clean; live IG + FB Apify runs verified).
> The website audit is **untouched** and still passes its QA (11/11). This banner is the
> authoritative pointer; §3 / §6 subsections carry the per-path detail and dated DONE notes.
>
> As-built map (verify against code — paths cited):
> - **Discriminator + migration.** `audit_jobs.audit_type` (`"website"` default | `"social"`) +
>   `audit_jobs.social_handles` JSONB; `audit_results.social_score` (INT, nullable) +
>   `social_facts` (JSONB); website scores (`seo_score`/`uxui_score`/`lead_gen_score`) made
>   **nullable** so a social result leaves them empty. `apps/shared/models.py:71,73,110,111`;
>   the social-audit migration is **`20260623_0004`** (current head is now **`20260625_0005`**;
>   see CLAUDE.md §6) (`migrations/versions/20260623_0004_add_social_audit_type.py`;
>   chain `0001→0002→0003→0004→0005`).
> - **Provider = Apify (free tier).** `apps/worker/stages/social/apify_provider.py` wires **two
>   actors**: Instagram Scraper (`apify~instagram-scraper`, `apify_provider.py:18`) and Facebook
>   Pages Scraper (`apify~facebook-pages-scraper`, `apify_provider.py:22`) via the sync
>   `run-sync-get-dataset-items` endpoint. **YouTube and Bright Data dropped; IG Business
>   Discovery dropped.**
> - **Stage package** `apps/worker/stages/social/`: `extractor.py` (pure IG+FB → `social.*`
>   facts), `collector.py` (orchestrate + graceful skip), `apify_provider.py` (network),
>   `report.py` (`compose_social_report_payload`), `__init__.py`.
> - **Scoring.** `rubrics/social.yaml` (**version `phase2-social-v1`** — now `phase2-social-v3`, `category: social`) is
>   scored by `scoring.score_social_audit()` (`apps/worker/stages/scoring.py:143`) → a
>   **standalone** Social Score (0–100). `Rubric.category` Literal now includes `"social"`
>   (`scoring.py:47`); the website `CompositeRubric.weights` stays exactly `{seo, uxui}`
>   (`scoring.py:66`) and `composite.yaml` stays **seo:0.45 / uxui:0.55** — **website scoring is
>   unchanged**.
> - **Findings are DETERMINISTIC, not LLM.** Social findings/roadmap come straight from the rubric
>   rule metadata (`finding_label`/`remediation`/`impact`/`tier`/`surface_as_finding`) in
>   `social/report.py:38-54`. (So P2-24's "commentary prompts" was delivered as deterministic
>   rule-derived findings — there is **no** social commentary prompt file and **no** LLM call.)
> - **Report.** A separate `templates/social_report.html` rendered by
>   `pdf_renderer.render_social_pdf` (`apps/worker/stages/pdf_renderer.py:101`) → its own branded
>   PDF (**PDF only; no DOCX for social**). New config `report_social_template_path`.
>   `compose_social_report_payload` is the shared seam (API detail + renderer).
> - **Pipeline.** `tasks.run_collection_audit` **branches** on `audit_type`
>   (`apps/worker/tasks.py:300`) → `_run_social_pipeline` (`tasks.py:256`): collect →
>   `score_social_audit` → `render_social_pdf` → store, reusing `_mark_job`/the spine.
>   `social_collector` is an injectable param (default `collect_social_facts`, `tasks.py:288`).
> - **API.** `POST /audits` accepts `audit_type` + `social_handles` (`url` optional for social;
>   website needs `url`, social needs ≥1 handle — `apps/api/schemas/audits.py:30-37`).
>   List/detail expose `audit_type` + `social_score`; detail returns `social_report` (dict) for
>   social audits, `report` (ReportPayload) for website (`apps/api/routes/audits.py:85-114`).
> - **Frontend.** New **"Social Audit"** tab (`apps/frontend/components/Layout.tsx:14`) + a
>   `/social` submit page (`apps/frontend/pages/social.tsx`) accepting a pasted IG/FB profile link
>   or `@handle` — **no login / OAuth / account-connection**. History shows a Web/Social badge +
>   the right score; detail renders a social view (score + findings + per-platform table) with
>   Download PDF + Share.
> - **Config.** `rubric_social_path`, `report_social_template_path`, `apify_api_token`,
>   `apify_timeout_seconds` (`apps/shared/config.py:117,118,138,144`).
> - **FB limitation.** The FB pages actor returns page **metadata, not posts** → cadence /
>   recency / engagement are `None` for FB and **skip-rescale (never penalize)** via
>   `skip_if_missing` in `social.yaml` (`extractor.py:110-140`). IG has full post data.
> - **Scripts.** `scripts/run_social_audit.py` (CLI: link → Apify → score) and
>   `scripts/check_apify_social.py` (live probe) — both reuse the real code.
> - **Tests.** New `tests/unit/test_extractor_social.py`, `test_social_scoring.py`,
>   `test_worker_social.py`.
>
> **Parked / removed (unchanged):** AI Insights stays **PARKED** (banner above); **P2-7 (S3)**
> stays **REMOVED**; **P2-E3** (deepen the website audit / WS D, §5) is the **only remaining
> unbuilt epic**.

---

## 0. How to read this document

This is the **build manual** for Phase 2. It answers: *given the locked Phase 2 scope, and
the Phase 1 code as it actually exists today, exactly what do we change and where?*

Sections:
- **§1:** What Phase 1 actually shipped (the spine we extend) — verified against the repo.
- **§2:** Architecture — how Phase 2 extends Phase 1.
- **§3:** Data-model changes (exact columns + migrations).
- **§4:** P2-E2 — productionization (auth, storage, SSRF, hosting, observability, dashboard).
- **§5:** P2-E3 — deepen the website audit (extractors + rubric rules). *(the only remaining
  unbuilt epic, as of 2026-06-23.)*
- **§6:** P2-E4 — social media audit (adapter, backends, extractor, rubric, commentary, report).
  **✅ DONE (2026-06-23) — built end-to-end & standalone; see the BUILT banner above and the
  per-subsection DONE notes.**
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
  > **Update (2026-06-23) — as-built.** Standalone social shipped exactly this code change for the
  > *rubric category* but **not** for the composite: `Rubric.category` is now
  > `Literal["seo", "uxui", "social"]` (`scoring.py:47`) so `social.yaml` validates and scores via
  > the same engine, while `CompositeRubric.weights` **stays** `dict[Literal["seo", "uxui"], float]`
  > (`scoring.py:66`) and `validate_weights`'s expected set **stays** `{"seo", "uxui"}`. Social is
  > scored by a **separate** `score_social_audit()` (`scoring.py:143`), **not** folded into the
  > composite — so the website score is unchanged. See §6.4.
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

> **Update (2026-06-23).** The diagram below predates the standalone-social decision. Read it
> as: **website and social are two independent branches off the shared spine** (selected by
> `audit_type`), **each producing its own report and its own score**. There is **no** merge into
> a single composite — the "scoring (… social, composite) ← P2-23 composite code change" node and
> the "PDF + dashboard" merge are **superseded**: the website composite is untouched (seo:0.45 /
> uxui:0.55) and the social branch scores `social.yaml` into a **standalone** Social Score with
> its **own** report. See §3, §6.2, §6.4, §6.6.

```text
Operator UI (Next.js, + team auth)          ← P2-6, P2-11 (dashboard/history/share/white-label)
        |                                      (Website tab  ·  Social Audit tab)
        v
FastAPI API (+ team auth)  ──►  Celery workers + Redis   (run_collection_audit BRANCHES on audit_type)
        |                              |
        |     +------------------------+-----------+----------------------+
        |     |                        |           |                      |
        v  Website (DEEPER, P2-E3)  Social (NEW, P2-E4, STANDALONE)  Enrichment (v3, P2-E5)
 PostgreSQL  crawler/PSI/CrUX      Apify actors (IG/FB)               SEMrush/Ahrefs,
 (managed)   SEO/UX/schema/a11y    [free tier]                        GA4/GSC/Clarity
        |        |                       |                                |
        |        v                       v                                v
        |   website scoring          social scoring                  (separate phase)
        |   (seo, uxui, composite    (social.yaml ONLY →
        |    UNCHANGED: 0.45/0.55)    standalone Social Score)
        |        |                       |
        |        v                       v
        |   grounded commentary + validation (shared engine, per branch)   ← P2-24
        v        |                       |
   report storage ◄── website report payload → website PDF + dashboard
   (local VM)    ◄── social  report payload → SEPARATE social PDF + dashboard   ← P2-25
```

> **Update (2026-06-23, round 2).** The social collector backend is **Apify (IG/FB), free tier**
> (no Bright Data, **no YouTube** — see top banner). Report storage is **local filesystem on the
> VM** — the **P2-7 S3 storage interface is REMOVED/descoped** (so the diagram no longer cites P2-7).

New vs Phase 1: team auth (no multi-tenancy), deeper website signals, and a **standalone social
product** (its own Apify-backed collector + `social.yaml` + a separate report and standalone Social
Score — **not** folded into the website composite), a dashboard, and (v3) enrichment sources.
~~storage interface + S3~~ is **removed** (local VM storage; see §4.2).

---

## 3. Data-model changes

All changes are additive Alembic migrations under `migrations/versions/` (Phase 1 already has
`20260528_0001_create_audit_tables.py`). PostgreSQL JSONB suits the nested social facts.

> **Update (2026-06-23) — standalone social changes the data model.** A social audit is now a
> **separate audit row** (its own job + its own result + its own report), not extra columns on a
> website audit's result. The shape below is updated to introduce an `audit_type` discriminator
> on `audit_jobs`, make `url` nullable, and add `social_handles` JSONB. Both branches still write
> to the existing `audit_jobs`/`audit_results` tables (additive migration), but a given row is
> **either** a website audit **or** a social audit — never both merged. The status/report/detail
> API stays `job_id`-keyed and type-agnostic.

### 3.1 Audit type + input — discriminator, nullable url, social handles (P2-19 / P2-22)

- **`AuditJob` (`apps/shared/models.py`)** — add an `audit_type` column,
  `Mapped[str]` (`"website" | "social"`, **default `"website"`**, with a CHECK constraint mirroring
  the literal set, like the existing `status` CHECK); **make `url` nullable**; add a
  `social_handles` JSONB column (nullable). One additive migration covers all three.
- **`AuditCreateRequest` (`apps/api/schemas/audits.py`)** — add `audit_type` (default `"website"`)
  and `social_handles: dict[str, str] | None` (e.g. `{"instagram": "...", "facebook": "..."}`
  — *(updated 2026-06-23 round 2: **no `youtube`** key; in scope = Instagram + Facebook via Apify)*).
  **Validation by type:** website audits **require** `url`; social audits
  **require ≥1 handle** and need **no** `url`. Enforce with a model validator so the wrong shape is
  a 422, not a runtime failure.
- **`routes/audits.py`** — pass `audit_type` + `social_handles` through on create; otherwise the
  create/enqueue path is unchanged (still inserts a `queued` `AuditJob` and calls `run_audit.delay`).
- Website-only audits are unchanged: `audit_type` defaults to `"website"`, `url` stays required for
  them, `social_handles` stays null.

> **DONE (2026-06-23) — as-built.** Shipped as planned in one additive migration
> **`20260623_0004`** (head; chain `0001→0002→0003→0004`):
> - `AuditJob.audit_type` `Mapped[str]` (`String(20)`, default `"website"`, `models.py:71`) +
>   `AuditJob.social_handles` JSONB (`models.py:73`); `url` is nullable.
>   *(Implementation note: the discriminator is enforced by the `Literal` in `AuditCreateRequest`
>   and the model default rather than a DB-level CHECK on `audit_type` — the status CHECK is
>   unchanged.)*
> - `AuditCreateRequest` (`apps/api/schemas/audits.py:20`) adds `audit_type:
>   Literal["website","social"]` (default `"website"`) and `social_handles: dict[str,str] | None`;
>   the `@model_validator` `_validate_inputs` (`schemas/audits.py:30`) makes a **website** audit
>   require `url` and a **social** audit require ≥1 non-empty handle (422 otherwise). No `youtube`
>   key — scope is Instagram + Facebook.
> - `routes/audits.py` `create_audit` (`routes/audits.py:147`) branches on `payload.audit_type` and
>   stores `audit_type` + filtered `social_handles` (social) or `url` (website); enqueue path
>   otherwise unchanged.

### 3.2 Results — social audits write their OWN result row (P2-22 / P2-23 / P2-25)

> **Superseded (2026-06-23).** The original recommendation here was to **extend a website audit's
> `audit_results`** with `social_score INT NULL` + `social_facts JSONB` and **fold social into that
> audit's `score_breakdown`**. That is **dropped** — social is now a separate audit, not extra
> columns on a website result. *(Original text kept below struck-through for history.)*
>
> ~~Two viable shapes — pick one in P2-5: **Extend `audit_results`** (add `social_score INT NULL`,
> `social_facts JSONB`, fold social into `score_breakdown`) **or** add `social_*` tables.
> Recommendation: extend `audit_results`.~~

**As-built target (standalone):** a social audit reuses the existing `audit_results` table (1:1 with
its own `audit_jobs` row) and stores **its own** values there:

- `social_score` — add an `INT NULL` column to `audit_results` (mirrors the existing
  `seo_score`/`uxui_score`/`lead_gen_score` columns); for a **social** audit it holds the standalone
  Social Score, and `seo_score`/`uxui_score`/`lead_gen_score` stay `NULL`. For a **website** audit
  `social_score` stays `NULL` and the existing three scores are written as today (no change).
- `social_facts` — add a `JSONB NULL` column for the social fact bundle (parallel to
  `seo_facts`/`uxui_facts`); social audits populate it, website audits leave it `NULL`. (The
  website fact/score columns are **not** repurposed.)
- `score_breakdown` (already JSONB) — for a social audit holds the **social** rule trail only; for a
  website audit it is unchanged. **Social is never merged into a website audit's `score_breakdown`.**
- Add `social_score` to `AuditResult` + a migration; `AuditListItem`/`AuditDetailResponse` expose
  `audit_type` + `social_score` so the UI can branch on type.

> Recommendation: **reuse `audit_results`** (additive columns) rather than new `social_*` tables —
> it keeps `_upsert_audit_result` in `tasks.py` a small change and keeps the report/detail/list API
> `job_id`-keyed and type-agnostic. Per-platform tables remain a later option if wanted, not needed
> for core.

> **DONE (2026-06-23) — as-built (standalone, reused `audit_results`).** Migration `0004`:
> - `audit_results.social_score` INT **nullable** (`models.py:110`) and `social_facts` JSONB
>   **nullable** (`models.py:111`). For a social audit `social_score`/`social_facts` are populated
>   and `seo_score`/`uxui_score`/`lead_gen_score` stay `NULL`.
> - The three **website** score columns were made **nullable** (`migration 0004` lines 31-33;
>   `models.py:106` comment) so a social result can legitimately leave them empty — website audits
>   still write all three.
> - `score_breakdown` (already JSONB) holds the **social** rule trail only for a social audit (set
>   by `_upsert_social_result`, `tasks.py:241`); it is never merged into a website audit.
> - `AuditListItem` (`schemas/audits.py:69,78`) and `AuditDetailResponse`
>   (`schemas/audits.py:89,104`) expose `audit_type` + `social_score` so the UI branches on type.
> - The result writer is a **dedicated** `_upsert_social_result` (`tasks.py:207`) alongside the
>   website `_upsert_audit_result`, rather than overloading the latter.

### 3.3 ~~Storage key, not local path (P2-7)~~ — REMOVED/descoped (2026-06-23 round 2)

> **REMOVED (2026-06-23, round 2).** P2-7 (storage interface + S3) is **descoped** — local
> filesystem storage on the VM is the intended design for this internal ~5–10-user tool, and
> retention is handled by **P2-10** (`scripts/cleanup_storage.py`). So `audit_results.pdf_path`
> keeps its **Phase-1 meaning** (a local filesystem path under `local_report_storage_dir`); there
> is **no storage-key reinterpretation and no schema change**. *(Original text kept below.)*
>
> ~~`audit_results.pdf_path` already exists; when S3 is active it stores a **storage key**, not a
> filesystem path. No schema change required — only the value's meaning + how the report route
> resolves it.~~

---

## 4. P2-E2 — Productionization & Platform

### 4.1 Team authentication (P2-6)

- Add a FastAPI auth dependency (e.g. `apps/api/deps.py` already exists for DI) that verifies
  a session/JWT from the chosen provider (Clerk / Supabase Auth / Workspace SSO).
- Apply it to the audit router in `apps/api/routes/audits.py` (keep `routes/health.py` public;
  gate `/docs`/`/openapi.json` in non-local envs via `app_env`).
- UI: add login + attach the token in `apps/frontend/lib/api.ts`.
- **No multi-tenancy** — one shared org; do not add `tenant_id`.

### 4.2 ~~Storage interface + S3 (P2-7)~~ — REMOVED/descoped (2026-06-23 round 2)

> **REMOVED (2026-06-23, round 2).** No `apps/shared/storage.py`, no `S3ReportStorage`, no
> `storage_backend` config. **Local filesystem storage on the VM is the intended design** for this
> internal ~5–10-user tool — Phase 1's `local_report_storage_dir` / `local_screenshot_storage_dir`
> stay as-is and `GET /audits/{id}/report` keeps streaming the local file. Storage **retention** is
> handled by **P2-10** (DONE: `apps/shared/retention.py` + `scripts/cleanup_storage.py` +
> `storage_retention_days`, run from cron — see §4.5), not by an S3 backend. *(Original S3 plan kept
> below, struck-through, for history.)*
>
> ~~- New `apps/shared/storage.py`:~~
> ~~  `class ReportStorage(Protocol): save(...) / get(...) / url(...)` with `LocalReportStorage`
>    (default) and `S3ReportStorage`, selected by config (`storage_backend: local|s3`).~~
> ~~- Route `pdf_renderer.render_audit_pdf` output + crawler screenshot writes through the interface.~~
> ~~- `GET /audits/{id}/report` returns a redirect to `storage.url(key)` when S3 is active, else
>    streams the local file as today.~~

### 4.3 Complete SSRF interception (P2-8) — DONE (2026-06-23)

> **DONE (2026-06-23).** Shipped in `apps/worker/stages/crawler.py`: a Playwright **route guard
> registered on each context** plus `_host_blocked_for_subrequest` validate **every
> sub-resource/redirect host** against the private/loopback/link-local/metadata-IP block-list during
> rendering (not just the start URL). A new setting **`crawler_intercept_requests`** toggles it (it
> **auto-disables when `crawler_allow_private_hosts` is true**, so the QA harness/localhost path is
> unaffected). Blocked requests are skipped, never crash. Unit-tested. The original plan text is kept
> below for history.

- ~~In `crawler.py`, register a Playwright route/request handler that resolves each request's host
  and rejects private/loopback/link-local/metadata IPs — for the initial nav, **every redirect
  target**, and sub-resources. Reuse the existing private-host check; add DNS-rebinding mitigation
  (validate the resolved IP, not just the hostname). Blocked requests are logged + skipped, never crash.~~
- ~~Add tests: public→internal redirect, internal sub-resource, `169.254.169.254`.~~
- Update [`docs/06_KNOWN_LIMITATIONS.md`](06_KNOWN_LIMITATIONS.md) §2 once closed.

### 4.4 Hosting + CI/CD (P2-9)

- Reuse `apps/api/Dockerfile` + `apps/worker/Dockerfile`. Managed Postgres + Redis; API+worker
  on Railway/Render (or ECS/Fargate); UI on Vercel; TLS at the edge; migrations run on deploy.
- CI runs `pytest` + `ruff` (the repo already has `.pre-commit-config.yaml` + `.github/workflows/`);
  merge to main deploys.

### 4.5 Observability + retention (P2-10) — retention + Sentry DONE (2026-06-23)

> **Status (2026-06-23).** **Retention DONE** and **Sentry DONE**; metrics/alerts/backups remain
> VM-ops tasks (intentionally lighter scope for a 5–10-user internal tool).

- **Sentry — DONE (optional, env-gated):** `apps/shared/observability.py` + the `SENTRY_DSN` setting
  wire error reporting into API + worker; it is a **no-op when `SENTRY_DSN` is unset**.
- **Retention — DONE:** `apps/shared/retention.py` + `scripts/cleanup_storage.py` +
  `storage_retention_days` delete **reports/screenshots/tool-exports older than N days**, run from
  **cron** (no in-app scheduler / no Celery beat); unit-tested. *(This is the storage-retention path
  now that S3/P2-7 is descoped — see §4.2.)*
- ~~Metrics + an alert on failure rate / queue backlog; automated DB backups (test a restore).~~
  **Not code — VM ops** (lighter scope; deferred for this internal tool).
- ~~Celery retry / dead-letter handling beyond `celery_task_soft_time_limit_seconds`.~~ Still
  unbuilt; ops-scope, not required for the 5–10-user internal tool.

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

**Optional AEO sub-score:** if "AI Visibility / AEO" should be its **own scored category** *inside
the website composite* rather than SEO rules, that **would** require the composite code change
(extend `scoring.py`'s `Literal[...]` + rebalance `composite.yaml`). Otherwise it is YAML-only.
*(Note 2026-06-23: this is **not** the social path — social is now standalone and does **not** touch
the website composite (§6.4); and the AI-visibility work is **parked**, see the top banner.)*
Decision 3 keeps the chosen immediate WS D / P2-E3 website-deepening signals as **YAML-only rules
under the existing SEO/UX categories** — no new scored category.

> **No `scoring.py` change for P2-E3** unless a new *category* is introduced. Adding rules to
> the existing `seo`/`uxui` categories is pure YAML + new extractor facts.

---

## 6. P2-E4 — Social media audit

Architecturally a **clone of the website pipeline**. Reuse Extract → Score → Commentate →
Validate; add a social collector + extractor, a `social.yaml` rubric, social commentary, and a
social report section.

> **Update (2026-06-23) — STANDALONE social.** Per the operator decision, the social audit is a
> **separate, fully-independent product**, not a section inside the website audit. Net shape:
> - It reuses **~80% of the shared spine** (job lifecycle, status polling, storage, the
>   deterministic commentary + grounding engine, WeasyPrint/branding, Clerk auth) but runs as its
>   **own leaner branch** of `run_collection_audit`, selected by `audit_type` (§3.1).
> - **No website URL** is required or used in the social branch; **no crawl / PSI / external-SEO**
>   runs there.
> - It produces a **separate report (separate PDF)** and a **standalone Social Score**. It does
>   **NOT** fold into the website Lead-Gen composite, and the website composite is **unchanged**
>   (seo:0.45 / uxui:0.55). There is **no combined website+social number** in any rubric.
> The subsections below (§6.2 pipeline, §6.4 rubric/scoring, §6.6 report) are updated accordingly;
> §6.1 (backends), §6.3 (extractor), §6.5 (commentary/grounding) still apply, now within the
> social branch.

> ## ✅ DONE (2026-06-23) — all of §6 (P2-E4) is built.
> The plan text in §6.1–§6.7 below is retained for rationale/history; the per-subsection DONE
> notes give the as-built code paths. Summary: provider package `apps/worker/stages/social/`
> (Apify IG+FB), `rubrics/social.yaml` (`phase2-social-v1`, now `phase2-social-v3`) scored by `score_social_audit`,
> deterministic rule-derived findings (no LLM, no social commentary prompt), a separate
> `templates/social_report.html` + `render_social_pdf`, a `_run_social_pipeline` branch in
> `run_collection_audit`, API `audit_type`/`social_handles`/`social_report`, and a `/social` UI tab.
> One scope correction vs the plan: **§6.5's social *commentary/grounding* was delivered as
> deterministic rule-metadata findings, not a commentary prompt + grounding pass** (see §6.5 note).

### 6.1 Provider adapter + backends (P2-19, P2-20, P2-21)

> **Update (2026-06-23, round 2) — provider = Apify (IG/FB), YouTube dropped.** The provider for
> the social data is now **Apify** ([apify.com](https://apify.com)) on its **free-tier credits**,
> **replacing Bright Data**. The `SocialProvider` adapter's **first and only backend is Apify**
> (running Apify **actors** for Instagram + Facebook public data). **YouTube is dropped entirely**
> (no YouTube Data API, no YouTube backend, no "build YouTube first"). Subsections below are updated;
> original Bright-Data/YouTube text is kept struck-through for history.

- New package, e.g. `apps/worker/stages/social/` with an adapter interface:
  ```python
  class SocialProvider(Protocol):
      def fetch_profile(self, platform: str, handle: str) -> dict: ...
      def fetch_recent_posts(self, platform: str, handle: str, limit: int) -> list[dict]: ...
  ```
  and a registry that picks a backend per platform.
- **Apify backend (P2-19/P2-20, IG/FB) — the first and only backend:** call Apify **actors** for
  Instagram + Facebook public profiles/posts via the Apify API token (§3 of the round-2 banner; free
  tier, **self-serve, no paid gate**). Build this to prove the pipeline. *(P2-20 "Bright Data backend
  for IG/FB" is reframed as this Apify backend — it may fold into P2-19.)*
- ~~**YouTube backend (P2-19, first):** YouTube Data API v3 — `channels.list` (1 quota unit) for
  subs/views/video count; recent uploads. Free, just an API key; build first to prove the pipeline.~~
  **DROPPED (2026-06-23 round 2)** — YouTube is out of scope.
- ~~**Bright Data backend (P2-20, IG/FB):** any public account (business or personal), post-level
  depth, pay-per-success (~$0.75/1K). **Gated on the P2-3 smoke test; legal sign-off ✅ given (P2-1).**~~
  **Superseded (2026-06-23 round 2)** — replaced by the Apify backend above; the **paid P2-3 smoke
  test gate is REMOVED** (Apify free tier is self-serve).
- **No OAuth and no IG Business Discovery** — dropped by BLC decision (both need a Facebook
  app / account approval Darius declined; ~~Bright Data~~ **Apify** already covers Instagram).
  **LinkedIn excluded; TikTok deferred** (same adapter supports TikTok later — via Apify — with no
  rework).
- **Graceful degradation:** missing/failed social data is skipped (like missing PSI), never aborts
  the audit — mirror the `psi_client` skip pattern.

> **DONE (2026-06-23) — as-built (Apify, IG + FB).** Shipped in
> [`apps/worker/stages/social/`](../apps/worker/stages/social/):
> - `apify_provider.py` is the network backend — **two free-tier Apify actors** called via the
>   synchronous `run-sync-get-dataset-items` endpoint: `fetch_instagram_profile`
>   (`apify~instagram-scraper`, `apify_provider.py:18,45`) and `fetch_facebook_page`
>   (`apify~facebook-pages-scraper`, `apify_provider.py:22,54`). Token from
>   `settings.apify_api_token` (never logged); any error/`>=400` returns `None` so collection
>   degrades gracefully. **No OAuth / no IG Business Discovery; no YouTube; no Bright Data.**
> - **Shape note:** the as-built adapter is a small **functions-per-platform** module
>   (`fetch_instagram_profile` / `fetch_facebook_page`) plus a per-platform dispatch in the
>   collector — not the `SocialProvider`/`fetch_profile`+`fetch_recent_posts` `Protocol` sketched
>   above. Same separation (network adapter vs orchestrator vs extractor); simpler surface.
> - `collector.collect_social_facts(settings, handles)` (`collector.py:34`) orchestrates: empty
>   handles → `skipped("no_social_handles")`; no token → `skipped("missing_apify_api_token")`;
>   else fetch each platform, then hand off to `extract_social_facts`. Unknown platforms degrade to
>   `failed` in the extractor. This is the PSI-style graceful-skip path (never penalizes/aborts).
> - TikTok remains a later add via the same Apify shape; LinkedIn excluded.

### 6.2 New worker branch in the pipeline (`tasks.py`)

> **Updated (2026-06-23) — branch, don't inline.** The original plan inlined a social
> collect+extract step **inside** the website audit (after extraction, guarded by "are any
> social handles present?", passing social facts into the website's scoring/commentary/validation).
> That is **superseded** by the standalone decision.

`run_collection_audit` **branches on `audit_type`** (loaded from the `AuditJob`):

- **`audit_type == "website"`** — the existing pipeline, **unchanged**: crawl → PSI → extract →
  score (`seo`/`uxui`/composite) → commentary → grounding → website report payload → website PDF.
- **`audit_type == "social"`** — a **standalone, leaner** branch (no `url`, **no crawl / no PSI /
  no external-SEO**):
  1. **Collect** — social provider adapter (§6.1): ~~Bright Data (IG/FB) + YouTube Data API~~
     **Apify actors for Instagram + Facebook** *(updated 2026-06-23 round 2 — Apify free tier; no
     YouTube)*, per the `social_handles`.
  2. **Extract** — `extractor_social.extract_social_facts(...)` (§6.3) → the common social-facts bundle.
  3. **Score** — `scoring` against **`rubrics/social.yaml` ONLY** → a **standalone Social Score**
     (§6.4). **No composite, no website categories, no Lead-Gen merge.**
  4. **Commentate** — `generate_commentary(...)` over social facts + Social Score (deterministic
     Phase-1 pattern; §6.5).
  5. **Validate** — `validate_commentary_grounding(...)` with `social_facts` as a fact source (§6.5).
  6. **Compose + render** — a **separate social report payload** → a **separate social report
     template** → a separate social PDF under the same storage dir (§6.6).

Factor the social branch as its own helper (e.g. `_run_social_audit(job, ...)` alongside the
existing website flow) so the two pipelines stay readable and the website path is untouched.
`_mark_job` remains the single writer of job state for both branches. Add social-specific
`AuditStatus` values in [`apps/shared/audit_states.py`](../apps/shared/audit_states.py)
(e.g. `COLLECTING_SOCIAL`) and progress steps in `_mark_job` for the social branch — optional but
improves UX. Status/report/detail endpoints stay `job_id`-keyed and type-agnostic.

> **DONE (2026-06-23) — as-built.** `run_collection_audit` branches at
> `apps/worker/tasks.py:300` on `(job.audit_type or "website") == "social"` →
> `_run_social_pipeline(db, job, settings, social_collector)` (`tasks.py:256`), which runs:
> 1. **Collect** — `social_collector(settings, job.social_handles)` (`tasks.py:263`; default
>    `collect_social_facts`, injectable via the `social_collector=` param at `tasks.py:288`).
> 2. **Score** — `score_social_audit(social_facts, settings)` (`tasks.py:266`) → standalone Social
>    Score. **No crawl / no PSI / no external-SEO / no composite** in this branch.
> 3. **Store** — `_upsert_social_result` (`tasks.py:268`, defined `tasks.py:207`).
> 4. **Render** — `render_social_pdf(job, result, settings)` (`tasks.py:271`) → separate social PDF.
>
> `_mark_job` is the single writer for both branches. **Scope note:** the social branch **reuses
> the existing `AuditStatus` values** (`CRAWLING`→"Collecting social profiles" at 40,
> `SCORING`→"Scoring social profiles" at 80, `RENDERING` at 95, `COMPLETE` at 100 — see
> `tasks.py:262,265,270,280`) — **no new `COLLECTING_SOCIAL` enum value was added** (the optional
> nicety above was not taken; statuses stay type-agnostic). The website branch (`tasks.py:304+`) is
> untouched.

### 6.3 Social fact extractor + schema (P2-22)

- New `apps/worker/stages/extractor_social.py` (matches `extractor_seo.py`/`extractor_uxui.py`
  naming) → a **common social-facts schema** regardless of source: followers, posting cadence +
  consistency, engagement-rate estimate, content-type mix, bio/CTA, link-in-bio/funnel signals.
- Fixtures under `tests/fixtures/` from sample **Apify actor** captures (strong/weak/malformed) —
  *(updated 2026-06-23 round 2: from Apify free-tier runs, not the removed P2-3 paid smoke test)* —
  with expected outputs + unit tests, mirroring the website extractor fixtures.

> **DONE (2026-06-23) — as-built.** Shipped as
> [`apps/worker/stages/social/extractor.py`](../apps/worker/stages/social/extractor.py)
> (`extract_social_facts(...)`) — **inside the `social/` package**, not a top-level
> `extractor_social.py` as the plan named it (function name still
> `extract_social_facts`). Pure, deterministic normalization of raw Apify items into the
> `social.*` facts bundle (`status` + `summary` + per-platform `platforms[]`). Per-platform
> normalizers: `normalize_instagram_profile` (followers, `posts_count`, `posts_per_month`,
> `avg_engagement_rate_pct`, `has_video`, bio/link signals — derived from `latestPosts`,
> `extractor.py:82-106`) and `normalize_facebook_profile` (`extractor.py:110`). Strong/weak
> fixtures live at `tests/fixtures/social_instagram_{strong,weak}.json`, exercised by
> `tests/unit/test_extractor_social.py` and `test_social_scoring.py`.
>
> **FB limitation (load-bearing):** the Facebook Pages actor returns page **metadata, not posts**,
> so `posts_per_month` / recency / `avg_engagement_rate_pct` are `None` for FB
> (`extractor.py:110-140`). The summary aggregator emits `None` (not `0`) when **no** profile has
> post data so the cadence/recency/engagement rules **`skip_if_missing`-rescale** instead of
> unfairly failing (`extractor.py:164-178`). IG has full post data.

### 6.4 `social.yaml` → standalone Social Score (P2-23)

> **SUPERSEDED (2026-06-23) — no website composite change.** The standalone decision **drops the
> composite code change entirely**. The website composite is **NOT** touched: `scoring.py`
> `Rubric.category` stays `Literal["seo", "uxui"]`, `CompositeRubric.weights` stays
> `dict[Literal["seo", "uxui"], float]`, `validate_weights` keeps `expected = {"seo", "uxui"}`,
> and `rubrics/composite.yaml` keeps **seo:0.45 / uxui:0.55** — **no rebalance, no recalibration,
> no regression** to the live website product. The scoring **engine** is reused for social; the
> website **composite** is not changed. *(Original P2-23 steps kept struck-through below for
> history.)*
>
> ~~In `apps/worker/stages/scoring.py`: (1) `Rubric.category` `Literal["seo","uxui"]` →
> `Literal["seo","uxui","social"]`; (2) `CompositeRubric.weights` add `"social"`;
> (3) `validate_weights` `expected` → `{"seo","uxui","social"}`; (4) `score_audit` load
> `rubrics/social.yaml`, include social in `scores`/`categories`, extend
> `compose_lead_generation_score` to three inputs; (5) `rubrics/composite.yaml` rebalance to three
> weights (proposed 0.35/0.40/0.25); (6) calibrate. Plus: keep `compose_lead_generation_score`
> backward-compatible / renormalize when social is absent.~~

**As-built target (standalone Social Score):**

- Author `rubrics/social.yaml` as a **standalone category** scored by the **same engine**
  (`score_audit`'s rule evaluators — `boolean`/`presence`/`range`/`exact_match`/`threshold`/
  `linear_scale`, with `skip_if_missing` for missing/failed social data). It produces a **standalone
  Social Score** (0–100), with the usual per-rule audit trail in `score_breakdown`.
- The social branch (§6.2) calls scoring with the social fact bundle against `social.yaml` **only**.
  It does **not** load `composite.yaml`, does **not** compute `compose_lead_generation_score`, and
  does **not** touch the website categories. There is **no combined website+social number**.
- Reuse the social-source trust + `skip_if_missing` rescaling pattern (a missing/failed IG/FB
  source — *(updated 2026-06-23 round 2: IG/FB via Apify; no YouTube)* — never penalizes the Social
  Score and never aborts the audit — mirror the existing external-source trust vocabulary).
- **Bump `version:` in `social.yaml`** (per [`docs/04_RUBRIC_GUIDE.md`](04_RUBRIC_GUIDE.md)); it is
  recorded in `rubric_version` for reproducibility (its own value, independent of the website
  `seo+uxui+composite` version string).
- Calibrate `social.yaml` against the strong/weak accounts from P2-4 (Q3 gate); the **website**
  calibration gate is untouched because the website composite is untouched.

> **DONE (2026-06-23) — as-built (standalone Social Score, website composite untouched).**
> - `rubrics/social.yaml` authored: **`version: phase2-social-v1`** (since advanced to `phase2-social-v3`, 14 rules), `category: social`,
>   `max_score: 100`, `normalization: rescale_to_max` — scored by the **same engine** via
>   `scoring.score_social_audit(social_facts, settings)` (`scoring.py:143`). It loads
>   `settings.rubric_social_path`, returns `score: None` when collection status isn't
>   `complete`/`partial` (skip — never penalizes/aborts, `scoring.py:151-159`), else scores
>   `score_category({"social": social_facts}, rubric)` and returns the standalone score + per-rule
>   `category` breakdown (`scoring.py:160-167`). Rule fact_paths are `social.*`.
> - **Website composite untouched:** `Rubric.category` is `Literal["seo","uxui","social"]`
>   (`scoring.py:47`) but `CompositeRubric.weights` stays `dict[Literal["seo","uxui"], float]`
>   (`scoring.py:66`) and `composite.yaml` stays **seo:0.45 / uxui:0.55**. Social never enters
>   `compose_lead_generation_score`; the social branch never loads `composite.yaml`.
> - The social rubric `version` is recorded independently in `rubric_version` via the result writer
>   (`tasks.py:213`), separate from the website `seo+uxui+composite` string.
> - Calibrated against `tests/fixtures/social_instagram_{strong,weak}.json` in
>   `tests/unit/test_social_scoring.py` (strong scores high, weak low).

### 6.5 Commentary + grounding (P2-24)

> **Update (2026-06-23).** Still applies — now within the **social branch** (§6.2). Social
> commentary is **deterministic** (Phase-1 pattern; the LLM path stays dormant), and grounding is
> extended to social facts. The shared commentary + grounding **engine** is reused; nothing here
> changes the website branch.

- Add social commentary prompt(s) in `prompts/`; pass social facts + the standalone Social Score
  into `generate_commentary` (`commentary.py`). The **deterministic** content plan must produce
  correct generic social prose (Phase-1 pattern; no LLM call in Phase 1).
- Extend `validate_commentary_grounding` (`grounding_validator.py`) `fact_sources` to include
  `social_facts` so unsupported social numbers are stripped.

> **DONE — but DELIVERED DIFFERENTLY (2026-06-23) — deterministic rule-derived findings, not a
> commentary prompt + grounding pass.** The intent (deterministic, grounded social prose; no LLM)
> shipped, but via a leaner mechanism than the two bullets above:
> - **No social commentary prompt was added** — `prompts/` still contains only
>   `commentary_system.md` + `commentary_user.md` (website). The social branch **does not call**
>   `generate_commentary` (those calls are website-only at `tasks.py:343`/`468`).
> - **No grounding extension** — `grounding_validator.py` has no `social` handling and the social
>   branch **does not call** `validate_commentary_grounding`. Grounding isn't needed because the
>   findings are built **directly from the rubric's scored rules** (every number/claim already comes
>   from the deterministic rule trail — nothing to strip).
> - **What ships instead:** `social/report.py:compose_social_report_payload` (`report.py:38-54`)
>   turns each failed/partial rule (where `surface_as_finding` is true) into a finding using the
>   rule's `finding_label` / `remediation` / `impact` / `tier` metadata, and buckets them into a
>   `quick_win` / `mid_term` / `long_term` roadmap. Deterministic, reproducible, no LLM — the same
>   spirit as the website's deterministic content plan. (So P2-24's "commentary prompts" was
>   satisfied by rule-derived findings.)

### 6.6 Report + PDF + dashboard (P2-25)

> **SUPERSEDED (2026-06-23) — separate report, not a website section.** The original plan added a
> `"social"` section/card to the **website** `report_payload.py` + a Social section in the
> **website** `templates/report.html`. That is **dropped**: the website report payload and template
> are **unchanged**. *(Original text kept struck-through below for history.)*
>
> ~~In `report_payload.py`: `ReportSectionId` add `"social"`; `ScoreCard.id` add `"social"`;
> `SECTION_LABELS` add a Social label; compose a social section + score card; the Lead-Gen card
> reflects the new composite. Extend `templates/report.html` + `templates/report.css` with a Social
> section.~~

**As-built target (separate social report):**

- Compose a **separate social report payload** — either a dedicated
  `compose_social_report_payload(job, result)` (mirroring the pure
  [`report_payload.py`](../apps/worker/stages/report_payload.py) seam) or a clearly social-only
  payload type, with its **own** section ids / score card for the standalone Social Score. The
  existing website `ReportSectionId = Literal["seo","uxui","lead_generation"]` and
  `ScoreCard.id` are **left unchanged**.
- Render via a **separate social report template** (e.g. `templates/report_social.html` +
  `templates/report_social.css`) — **reusing WeasyPrint + the `brand/blc.yaml` branding** — into a
  **separate social PDF**. Verify pagination. The website `templates/report.html` is untouched.
- Like the website branch, this payload seam should stay **pure** (takes job + result, returns a
  Pydantic model) so the API can compose the social detail response from the stored result the same
  way it does for website audits.
- Surface social in the dashboard (P2-11) as its own item; a **blended** website+social dashboard
  view is **not foreclosed for later** but would live at the **dashboard level**, not in any rubric
  or composite.
- End-to-end QA on real builder **social accounts** (standalone); reproducible for identical inputs.

> **DONE (2026-06-23) — as-built (separate social report, PDF only).**
> - **Pure payload seam:** `social/report.py:compose_social_report_payload(job, result)`
>   (`report.py:23`) returns a dict (`version: phase2-social-report-v1`, `score`, `status`,
>   `handles`, `summary`, `platforms`, `findings`, `roadmap`) — shared by the renderer **and** the
>   API detail response (`routes/audits.py:91`), exactly like `compose_report_payload` is for the
>   website. It only surfaces `status == "complete"` platforms (`report.py:30-34`).
> - **Separate template + renderer:** `templates/social_report.html` (its **own** template; CSS is
>   **inlined** in a `<style>` block — there is **no** separate `report_social.css`), rendered by
>   `pdf_renderer.render_social_pdf(job, result, settings)` (`pdf_renderer.py:101`) via
>   WeasyPrint + the shared `brand/blc.yaml` branding (incl. brand-overrides). **PDF only — no DOCX
>   for social.** Config knob `report_social_template_path` (`config.py:144`).
> - **Naming note:** the file is `templates/social_report.html`, not `templates/report_social.html`
>   as the plan named it.
> - **API detail:** `AuditDetailResponse.social_report` (`schemas/audits.py:106`) carries the dict
>   for social audits; website audits still return `report` (the typed `ReportPayload`). The
>   website `ReportSectionId` / `ScoreCard.id` literals are **left unchanged**.
> - Dashboard surfaces social rows as their own items (§6.7); a blended website+social number is
>   still **not** built (and would live at the dashboard level, not in any rubric).

### 6.7 Frontend — Social Audit tab (P2-19 / P2-22 / P2-11)

> **New (2026-06-23) — standalone social UI.** Social gets its **own UI tab** and its **own submit
> page**; it does not share the website submit form.

- Add a **"Social Audit"** tab/route alongside the existing website submit page in
  `apps/frontend/pages/`, with a **handle-input** form (Instagram / Facebook ~~/ YouTube~~ —
  *(updated 2026-06-23 round 2: Instagram + Facebook only, via Apify; no YouTube)*; **no website
  URL field**). It `POST`s `/audits` with `audit_type: "social"` + `social_handles` (§3.1).
- The website submit page stays as-is (`audit_type` defaults to `"website"`, `url` required).
- **History + detail branch on `audit_type`** (exposed by `AuditListItem`/`AuditDetailResponse`,
  §3.2): website rows show the website report + SEO/UX/Lead-Gen scores; social rows show the
  separate social report + the standalone Social Score. Status polling, the `GET /audits/{id}`,
  `/report`, and `/docx` endpoints stay `job_id`-keyed and type-agnostic in `lib/api.ts`.

> **DONE (2026-06-23) — as-built.**
> - **Tab + submit page:** `apps/frontend/components/Layout.tsx:14` adds the **"Social Audit"** nav
>   item → `apps/frontend/pages/social.tsx`. The form takes an **Instagram** and an optional
>   **Facebook** field, each accepting a **pasted profile link or bare `@handle`**
>   (`extractHandle` regex strips `instagram.com`/`facebook.com` URLs, `social.tsx:13-15`); **no
>   website-URL field, no login/OAuth/account-connection** (public scrape). It requires ≥1 handle
>   client-side (`social.tsx:35`) and `POST`s `/audits` with `audit_type: "social"` +
>   `social_handles` (`social.tsx:46-47`). Instagram + Facebook only — **no YouTube**.
> - **History:** `apps/frontend/pages/audits.tsx` shows a **Web/Social badge**
>   (`audits.tsx:237-241`) and renders the **right score** per type (`social_score` for social,
>   `audits.tsx:29-34`).
> - **Detail:** `apps/frontend/pages/audit/[id].tsx` branches on `detail.audit_type` — a
>   `SocialReportView` (`[id].tsx:352`) renders the Social Score, the handles, the deterministic
>   findings, and a **per-platform table** (followers / posts-per-month / engagement / days-since-
>   last-post, `[id].tsx:408-415`), with **Download PDF** + **Share**. The website detail
>   (`[id].tsx:632`) is unchanged.
> - The website submit page is untouched (`audit_type` defaults to `"website"`, `url` required).

---

## 7. P2-E5 — Enrichment (v3)

Partly scaffolded. Competitor benchmarking now has a feature flag, provider registry
(`semrush` / `ahrefs` / `similarweb`), typed normalized facts, graceful skip paths, and
PDF/DOCX/web report-section rendering. It is presentation-only, never changes scores, stores any
real baseline payload under `score_breakdown["benchmark"]`, and is disabled/no-op until a paid
vendor client is selected, implemented, and funded.

Still deferred to v3: live SEMrush/Ahrefs/Similarweb HTTP clients and user-authorized analytics
(GA4, Search Console, Clarity, SEMrush). Those move beyond anonymous public-data audits into
recurring cost and/or OAuth flows.

---

## 8. Sequencing, quality gates, acceptance

### 8.1 Order

> **Update (2026-06-23, round 2).** No paid smoke-test gate (P2-3 removed) and no YouTube — so the
> P2-E4 ordering no longer waits on P2-3 and no longer "builds YouTube first". Apify free tier is
> self-serve, so P2-E4 can start as soon as the free Apify token (P2-2) exists. Original order kept
> struck-through.

1. **P2-E1** (2–3 days) — ~~keys + Bright Data account~~ **a free Apify account + API token**, draft
   `social.yaml` (legal ✅ given; no OAuth/Business Discovery).
2. **P2-E2** + **P2-E3** in parallel — both low-risk, reuse what works.
3. **P2-E4** — ~~start once P2-3 (Bright Data smoke test) is done; YouTube first, then Bright Data.~~
   **start once the free Apify token is in hand (no paid gate); build the Apify IG/FB backend.**
   **✅ DONE (2026-06-23)** — built end-to-end (see the §6 DONE notes); IG + FB Apify runs verified live.
4. **P2-E5** — v3 only.

> **Update (2026-06-23) — status.** **P2-E4 is DONE** (built, runnable from the browser). The
> **only remaining unbuilt epic is P2-E3** (deepen the website audit, §5); P2-E5 stays deferred and
> AI Insights stays parked.

(Matches the week-by-week in [`docs/08_PHASE2_PLAN.md`](08_PHASE2_PLAN.md) §9.1.)

### 8.2 Quality gates (extend Phase 1's)

> **Update (2026-06-23) — standalone social adjusts Q3/Q8/Q9.** With social standalone, "Social +
> Lead-Gen" / "three weights" / "combined report" no longer apply; the gates are restated below.

| # | Gate | How to verify |
|---|---|---|
| Q1 | Website audit still reproducible | Same facts → identical SEO/UX/Lead-Gen scores (existing `make qa-repro`) |
| Q2 | P2-E3 calibration holds | After each P2-E3 task, `make qa` strong ≥ threshold, weak ≤ threshold; rubric version bumped |
| Q3 | Social score reproducible | *(DONE 2026-06-23)* Same social facts → identical **standalone Social Score** (pure rule engine; covered by `tests/unit/test_social_scoring.py`) *(updated 2026-06-23: no Lead-Gen recompute — social is independent)* |
| Q4 | Social grounding | *(N/A as-built 2026-06-23 — see §6.5)* Social findings are derived **deterministically from the scored rule trail** (no LLM commentary, no grounding pass), so there are no unsupported numbers to strip; reproducibility is guaranteed by Q3 instead |
| Q5 | Auth enforced | Unauthenticated API calls get 401; `/health` stays public |
| Q6 | SSRF closed | *(DONE 2026-06-23)* public→internal redirect, internal sub-resource, and metadata IP are blocked (`crawler_intercept_requests` per-request route guard; §4.3) |
| Q7 | ~~S3 + signed URLs~~ **Local storage + retention** | *(updated 2026-06-23 round 2 — P2-7/S3 REMOVED)* A report saves to the **local VM** storage dir and downloads via `GET /audits/{id}/report`; `scripts/cleanup_storage.py` prunes artifacts older than `storage_retention_days` (§4.2, §4.5) |
| Q8 | Website composite untouched | *(updated 2026-06-23)* `rubrics/composite.yaml` still validates as **seo:0.45 / uxui:0.55** (two weights); website scores are **unchanged** (no recalibration); social never enters the composite |
| Q9 | End-to-end on real data | *(DONE 2026-06-23)* A website audit produces the website report; a **separate** social audit (**IG/FB handles via Apify**, no URL, no YouTube) produces a **separate** social report (PDF + dashboard) — each reproducible for identical inputs. Verified live (IG + FB Apify runs); website QA still 11/11; `tests/unit/test_worker_social.py` covers the social branch end-to-end |

### 8.3 Acceptance

Phase 2 core acceptance = the Done Criteria in
[`docs/09_PHASE2_JIRA_PLAN.md`](09_PHASE2_JIRA_PLAN.md) §5 and the acceptance criteria in
[`docs/08_PHASE2_PLAN.md`](08_PHASE2_PLAN.md) §12 — auth-gated, ~~S3-stored~~ **local-VM-stored
with retention** *(updated 2026-06-23 round 2 — P2-7/S3 descoped; §4.2)*, **SSRF-hardened**
*(DONE; §4.3)*, hosted, **observable** *(Sentry DONE; §4.5)*; deeper website signals scored with the
calibration gate holding; and a deterministic **standalone Social Score** with its **own separate
report**, validated on real builder social accounts **(Instagram + Facebook via Apify; no YouTube)**.

> **Update (2026-06-23).** Original wording read "a deterministic Social Score **folded into
> Lead-Gen Readiness**, validated on real builder sites **and** their social accounts." Per the
> standalone decision the Social Score is **not** folded into Lead-Gen — it is an independent score
> with its own report, validated on real social accounts (no website URL required). The website
> acceptance is unchanged.

> **DONE (2026-06-23) — social acceptance met.** The standalone Social audit is **built and
> runnable from the browser** end-to-end: deterministic standalone Social Score
> (`scoring.score_social_audit`, `rubrics/social.yaml` `phase2-social-v1`, now `phase2-social-v3`) with its **own** PDF
> (`render_social_pdf` + `templates/social_report.html`), Apify-backed IG + FB collection, a
> `/social` UI tab, and deterministic rule-derived findings (no LLM). ~119 unit tests pass (incl.
> `test_extractor_social.py` / `test_social_scoring.py` / `test_worker_social.py`), ruff clean, and
> live IG + FB runs verified; the website audit is untouched (QA 11/11). **Remaining for Phase 2
> core: only P2-E3** (deepen the website audit, §5); P2-E5 deferred; AI Insights parked.

---

**End of Phase 2 implementation plan.** Keep this in lockstep with `08_PHASE2_PLAN.md` (scope)
and `09_PHASE2_JIRA_PLAN.md` (tickets). If a code path named here moves, update it here too.
