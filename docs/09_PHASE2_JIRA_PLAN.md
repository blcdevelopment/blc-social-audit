# Phase 2 Jira Plan & Tracking Board

> **UPDATE 2026-06-25 — Epic P2-E4 / SMWA-70 board reconciliation.** The Jira board still shows
> SMWA-71…77 as **TO DO**, but the epic is **SHIPPED** (the board is the stale artifact, not the
> code). Resolution of each story against the working tree:
> - **P2-19/SMWA-71** (Provider Adapter + YouTube) — **DONE.** Formalized 2026-06-25 with a
>   `SocialProvider` Protocol + registry (`social/providers.py`); the collector now dispatches
>   over the registry instead of a hardcoded `if/elif`. YouTube backend already present.
> - **P2-20/SMWA-72** (Apify IG/FB) — **DONE** (`social/apify_provider.py`, incl. the Posts actor).
> - **P2-21/SMWA-73** (IG Business Discovery shortcut) — **CLOSED, won't-do.** The Apify Instagram
>   Scraper already covers IG; Business Discovery needs a Facebook Graph app + token + app review
>   (high cost, low marginal value). Decision confirmed with the maintainer 2026-06-25.
> - **P2-22/SMWA-74** (Fact Extractors + Common Schema + Fixtures) — **DONE.** Common schema
>   formalized 2026-06-25 as typed `SocialProfileFacts`/`SocialSummary` (`social/schema.py`);
>   IG/FB/YouTube fixtures present.
> - **P2-23/SMWA-75 & P2-25/SMWA-77** ("…Lead-Gen update / Updated Lead-Gen Score") — the rubric +
>   scoring + report/PDF/dashboard are **DONE**, but the **"fold social into the website Lead-Gen
>   composite"** sub-scope is **SUPERSEDED**: the Social audit is deliberately **standalone** (own
>   Social Score, own PDF; website composite untouched). Decision confirmed 2026-06-25.
> - **P2-24/SMWA-76** (Commentary Prompts + Grounding-Validator Extension) — **DONE.** The social
>   grounding backstop was unified 2026-06-25 into one shared `NumericGrounding` in
>   `grounding_validator.py` (used by both the website and social paths).
>
> **UPDATE 2026-06-24 — YouTube RE-ADDED.** The "YouTube is dropped" notes in P2-2 / P2-19 / the
> banner / P2-E4 done-criteria are **superseded**. The P2-19 provider adapter now has a YouTube
> Data API v3 backend (`youtube_provider.py`) alongside the Apify IG/FB backends; provisioning adds
> a free `YOUTUBE_API_KEY` (no OAuth). **Bright Data and IG Business Discovery remain dropped.**
> Trust `CLAUDE.md` §5 and `README` for as-built truth.

**Project:** BLC Website Audit Automation → Social Media & Website Auditing Automation
**Client:** Builder Lead Converter (BLC)
**Fix Version:** Phase 2
**Document purpose:** The Jira-ready Phase 2 plan **and** the live tracking board.
Every epic, task, acceptance criterion, and subtask below is written to be **copy-pasted
straight into Jira**, in the same format as Phase 1 (`Epic P2-E1: …` for epics, `P2-1 …`
for tasks). The tables in §3 are the "what's done / what's not" tracker.
**Companion docs:** scope & rationale in [`docs/08_PHASE2_PLAN.md`](08_PHASE2_PLAN.md);
the build manual in [`docs/10_PHASE2_IMPLEMENTATION.md`](10_PHASE2_IMPLEMENTATION.md).

> **Numbering.** Phase 2 uses **sequential IDs like Phase 1** — epics `P2-E1…P2-E5`,
> tasks `P2-1…P2-28`. The four *workstreams* from the Plan (A = productionization,
> B = social, C = enrichment, D = deepen website) are a planning concept only; in Jira they
> become **epics**, not part of the ID. The mapping is: **A → P2-E2**, **D → P2-E3**,
> **B → P2-E4**, **C → P2-E5**, with **P2-E1** as discovery.

> **Status reconciliation (2026-06-16).** Several Workstream-A (Epic P2-E2)
> productionization items have **already shipped — ahead of this plan**: **team auth
> (Clerk)**, **managed hosting (Linode + Caddy)**, and **CI/CD auto-deploy on merge to
> `main`**. The corresponding rows in the §3 tracking board are marked **Done (shipped
> ahead of plan, 2026-06-16)**; everything else is unchanged. See the root
> **`DEPLOYMENT.md`** for the authoritative as-built description. The remaining P2-E2
> items (~~S3 storage, full request-level SSRF interception, observability/retention,~~
> dashboard/share) and all of P2-E3/P2-E4/P2-E5 remain to do.
> > **Superseded by the 2026-06-23 round-2 update below:** S3 storage (P2-7) is now **REMOVED**
> > (local FS), request-level SSRF interception (P2-8) is **DONE**, and observability/retention
> > (P2-10) is **partly DONE** (retention + env-gated Sentry shipped). So of the parenthetical
> > list above, only **dashboard/share (P2-11)** remains.

> **Update (2026-06-23) — two operator decisions:**
> 1. **Social audit becomes STANDALONE & fully independent (Epic P2-E4 reshaped).** The
>    Social audit is no longer bolted onto the website audit. It is a **separate product**:
>    its own UI tab and handle inputs (**no website URL required**), its own **separate
>    report (separate PDF)**, and its own **standalone Social Score**. It does **NOT** fold
>    into the website Lead-Gen composite — **the website audit's scoring is UNCHANGED**
>    (`composite.yaml` stays `seo:0.45 / uxui:0.55`; no recalibration, no regression). There
>    is **no combined website+social number** (a blended dashboard view is not foreclosed
>    for later, but it would live at the dashboard level, not in any rubric). Concretely:
>    **P2-23** drops the composite `Literal`/weights code change and the Lead-Gen fold-in
>    (Social gets its **own** `rubrics/social.yaml` scored by the **reused** engine);
>    **P2-25** becomes a **separate** Social report + a Social Audit tab, not a section bolted
>    onto the website report. The recommended data shape adds an `audit_type` discriminator
>    (`"website" | "social"`, default `"website"`) to `audit_jobs`, makes `url` nullable, and
>    adds `social_handles` (JSONB); `run_collection_audit` branches on `audit_type`. See the
>    notes under **P2-E4 / P2-19**.
> 2. **AI Insights is PARKED — not part of Phase 2.** The AI-visibility work
>    ([`docs/13_AI_INSIGHTS_INTEGRATION_PLAN.md`](13_AI_INSIGHTS_INTEGRATION_PLAN.md) +
>    [`docs/14_AI_VISIBILITY_VENDOR_SELECTION.md`](14_AI_VISIBILITY_VENDOR_SELECTION.md)) is
>    **deferred/parked**: it is blocked on an unpurchased paid vendor subscription (Rank
>    Prompt API Starter $99/mo; live billing unverified). Phase 2 proceeds **without** it;
>    verified safe — no Phase-2 task depends on AI Insights. To be resumed once the
>    subscription is sorted.
>
> WS D (deepen the website audit, Epic P2-E3) is the chosen immediate starting work; its new
> signals stay as **rules under the existing SEO/UX categories** (YAML-only, no new scored
> category).

> **Update (2026-06-23) — round 2, operator decisions:**
> 1. **Social data provider = Apify (free tier), replacing Bright Data everywhere.** The social
>    source is now **Apify** ([apify.com](https://apify.com)) running actors for Instagram +
>    Facebook public data behind the existing provider-adapter, on its **free-tier credits**
>    (self-serve, no paid gate). TikTok remains an optional later add via Apify. All "Bright
>    Data" references below are **superseded by Apify** (kept struck/quoted per convention).
> 2. **YouTube is DROPPED entirely.** No YouTube Data API, no YouTube backend, no "build
>    YouTube first." **Social platforms in scope = Instagram + Facebook (via Apify) only.**
> 3. **Provisioning/paid gates removed.** **P2-3** (Bright Data paid smoke test) is **REMOVED**
>    — Apify's free tier is self-serve, so there is no paid smoke test and no "gated on P2-3"
>    dependency on P2-20/P2-22. **P2-2** simplifies to "create a free Apify account + API token"
>    (no YouTube key, no paid/blocked gate). **P2-19** becomes "provider adapter + **Apify**
>    backend (IG/FB)" (no YouTube-first), and **P2-20** becomes the **Apify** IG/FB backend.
> 4. **P2-7 (Storage interface + S3 backend) is REMOVED/descoped.** No AWS/S3 — **local
>    filesystem storage on the VM** is the intended design for this internal ~5–10-user tool.
>    Storage retention is handled by **P2-10** (cleanup job), not S3.
> 5. **Status updates (shipped 2026-06-23):**
>    - **P2-8 (request-level SSRF interception) = DONE.** The crawler now validates every
>      sub-resource/redirect host against the private/loopback/metadata-IP block-list during
>      rendering (`apps/worker/stages/crawler.py`: `_host_blocked_for_subrequest` + a Playwright
>      route guard on each context; new `crawler_intercept_requests` setting, auto-disabled when
>      `crawler_allow_private_hosts` is true; unit-tested).
>    - **P2-10 = partly DONE.** **Retention** is DONE (`apps/shared/retention.py` +
>      `scripts/cleanup_storage.py` + `storage_retention_days` setting; prunes
>      reports/screenshots/tool-exports older than N days; cron-run, no in-app scheduler;
>      unit-tested). **Sentry** is DONE as optional env-gated error reporting
>      (`apps/shared/observability.py` + `SENTRY_DSN`; no-op when unset). **Metrics / alerts /
>      backups** remain **VM ops tasks** (not code; lighter scope for a 5–10-user internal tool).

> **Update (2026-06-23) — Epic P2-E4 (Social Media Audit) is SHIPPED, end-to-end.** The
> standalone Social audit is built, runnable from the browser, fully independent of the website
> audit, and tested (119 unit tests pass; ruff clean; live IG+FB Apify runs verified). The
> DONE tickets: **P2-19** (provider adapter + Apify backend), **P2-20** (Apify IG/FB backend),
> **P2-22** (extractors + common schema + fixtures), **P2-23** (`rubrics/social.yaml` →
> standalone Social Score, **no** website-composite change), **P2-25** (separate Social report
> PDF + Social Audit tab). **P2-24** is **DONE via deterministic rule-derived findings** (not
> LLM commentary). **P2-21** stays **Dropped**. As-built map:
> - **Data model** (`apps/shared/models.py`): `audit_jobs.audit_type` (`"website"` default |
>   `"social"`) + `audit_jobs.social_handles` (JSONB); `audit_results` gained `social_score`
>   (nullable INT) + `social_facts` (JSONB), and the website scores
>   (`seo_score`/`uxui_score`/`lead_gen_score`) are now **nullable** so a social result leaves
>   them empty. Alembic head is now **`20260623_0004`** (chain 0001→0002→0003→0004).
> - **Provider** = **Apify (free tier)** — `apps/worker/stages/social/apify_provider.py` wires
>   two actors: Instagram Scraper (`apify~instagram-scraper`) + Facebook Pages Scraper
>   (`apify~facebook-pages-scraper`). YouTube, Bright Data, and IG Business Discovery are all
>   dropped.
> - **Pipeline** (`apps/worker/stages/social/`): `extractor.py` (pure normalize IG+FB →
>   `social.*` facts), `collector.py` (orchestrate, graceful skip), `apify_provider.py`
>   (network), `report.py` (`compose_social_report_payload`). `tasks.py`
>   `run_collection_audit` branches on `audit_type` → `_run_social_pipeline` (collect →
>   `score_social_audit` → `render_social_pdf` → store), reusing the `_mark_job` spine;
>   `social_collector` is an injectable param (default `collect_social_facts`).
> - **Scoring** (`scoring.py`): `score_social_audit()` produces a **standalone** Social Score
>   (0–100) from `rubrics/social.yaml` (`phase2-social-v1` → now `phase2-social-v3`, `category: social`);
>   `Rubric.category` `Literal` now includes `"social"`. The website `CompositeRubric` weights
>   stay exactly `{seo, uxui}` — Social is **not** folded into the website composite; website
>   scoring is unchanged.
> - **Findings** are **deterministic**, derived from the rubric rule metadata
>   (`finding_label`/`remediation`/`impact`/`tier`) in `social/report.py` — **no LLM**.
> - **Report** = separate `templates/social_report.html` rendered by `render_social_pdf`
>   (PDF only; **no DOCX** for social); new config `report_social_template_path`;
>   `compose_social_report_payload` is the shared seam (API detail + renderer).
> - **API** (`apps/api`): `POST /audits` accepts `audit_type` + `social_handles` (`url`
>   optional for social); `AuditCreateRequest` validates website needs `url`, social needs ≥1
>   handle. List/detail expose `audit_type` + `social_score`; detail returns `social_report`
>   (dict) for social audits, `report` (`ReportPayload`) for website.
> - **Frontend**: new **Social Audit** tab + `/social` submit page (paste an IG/FB profile
>   link or `@handle`; no login/OAuth/account-connection); history shows a Web/Social badge +
>   the right score; detail renders a social view (score + findings + per-platform table) with
>   Download PDF + Share.
> - **FB limitation:** the FB pages actor returns page **metadata, not posts**, so
>   cadence/recency/engagement **skip** for FB (rescale, never penalize); IG has full post data
>   (`social/extractor.py`).
> - **Config**: `rubric_social_path`, `report_social_template_path`, `apify_api_token`,
>   `apify_timeout_seconds`. **Scripts**: `scripts/run_social_audit.py` (CLI end-to-end:
>   link → Apify → score), `scripts/check_apify_social.py` (live probe). **Tests**:
>   `test_extractor_social.py`, `test_social_scoring.py`, `test_worker_social.py`.
>
> The website audit is **untouched** and still passes its QA. **P2-E3** (deepen the website
> audit, WS D) is the only remaining unbuilt Phase-2-core epic. AI Insights stays **PARKED**;
> P2-7 (S3) stays **REMOVED**.

---

## 1. Jira Settings

Use these defaults for all Phase 2 Jira issues.

| Field | Value |
|---|---|
| Project | BLC Website Audit Automation (SMWA) |
| Fix Version | Phase 2 |
| Epic labels | `phase-2`, `blc` |
| Track labels | `productionization` (E2), `website-deepening` (E3), `social-audit` (E4), `enrichment` (E5) |
| Issue Types | Epic → Task/Story → Sub-task |
| Decision labels | `internal-tool`, `scraper-first`, `no-multitenancy` |
| Out-of-scope labels | `no-linkedin-scrape`, `tiktok-deferred`, `v3-enrichment` |
| Due Dates | Leave blank; set per sprint once Phase 2.0 sign-off lands |

**Decision context to attach to the epic (locked — see [`docs/08_PHASE2_PLAN.md`](08_PHASE2_PLAN.md) §3):**

- **Internal tool, not SaaS.** One shared org, shared audit history. No multi-tenancy.
- ~~**Bright Data scraping only.** Bright Data is the social source for IG/FB; YouTube uses
  its free official API.~~ **Update (2026-06-23, round 2): Apify (free tier) is the social
  source, running actors for IG/FB; YouTube is dropped — platforms in scope are Instagram +
  Facebook only (TikTok optional later via Apify).** **No OAuth, no IG Business Discovery**
  (both need account approvals BLC declined). **LinkedIn excluded**; **TikTok deferred**.
- **Legal sign-off ✅ given** (Darius, 2026-06-05): public-data, logged-out scraping, minimal retention, no LinkedIn.

---

## 2. Phase 2 Scope Lock

Phase 2 completes the original three-audit product and makes it safe + hosted for the
internal BLC team. It builds on the proven Phase 1 spine (FastAPI + Celery/Redis +
Playwright + YAML rubric engine + grounded commentary + WeasyPrint PDF) **without
rewriting it**.

**In scope (Phase 2 core = Epics P2-E1 + P2-E2 + P2-E3 + P2-E4):**

- Phase 2.0 discovery & scope lock (accounts, keys, legal sign-off, draft `social.yaml`).
- Lightweight **team authentication** on API + UI (single internal org, no public sign-up).
- ~~**Storage interface + S3 backend**; reports served via signed URLs.~~ **REMOVED
  (2026-06-23):** no AWS/S3 — local filesystem storage on the VM is the intended design for
  this ~5–10-user internal tool; retention is handled by the P2-10 cleanup job.
- **Complete request-level SSRF interception** in the crawler.
- **Managed hosting + CI/CD**, TLS at the edge.
- **Observability** (Sentry, metrics, alerts), DB backups, data-retention cleanup.
- **Web dashboard** + audit history/re-run/share + white-label branding.
- **Deepen the website audit:** structured data/schema, AEO/answer-engine readiness, CrUX
  field Core Web Vitals, axe-core accessibility, crawlability/link health, local SEO,
  trust/conversion + security-hygiene signals.
- **Social media audit:** provider adapter, ~~YouTube backend, Bright Data backend (primary)
  for IG/FB~~ **Apify backend for IG/FB (2026-06-23 round 2)**, social fact extractors,
  `social.yaml` rubric, social commentary + grounding, and a **standalone Social report +
  standalone Social Score**.
  > **Update (2026-06-23):** the Social audit is now a **standalone, fully independent
  > product** — its own UI tab and handle inputs (no website URL), its own separate report,
  > and its own Social Score. It does **NOT** fold into the website Lead-Gen composite (the
  > website scoring is unchanged). See the banner above and Epic P2-E4.
  > **Update (2026-06-23, round 2):** the social source is **Apify (free tier)**, not Bright
  > Data; **YouTube is dropped** — platforms in scope are **Instagram + Facebook (via Apify)**
  > only (TikTok optional later via Apify).

**Out of scope for Phase 2 core (Epic P2-E5 / v3):**

- Live competitor-benchmarking provider clients (SEMrush/Ahrefs/Similarweb). The no-cost
  benchmarking scaffold/rendering path has shipped, but paid vendor fetchers remain deferred.
- Analytics integrations (GA4, Search Console, Microsoft Clarity, SEMrush keyword data).
- LinkedIn scraping (enforcement risk).
- TikTok collector (deferred; the same adapter supports it later).
- Multi-tenant SaaS, billing, public self-service sign-up.

---

## 3. Tracking Board (what's done / what's not)

**Status legend:** ✅ Done · 🟡 In progress · ◐ Doc/spec ready, pending human action · ⬜ To do · ⛔ Out of Phase 2 core (v3).

### 3.1 Epic-level

| Epic | Name | Track | Tasks | Status |
|---|---|---|---|---|
| P2-E1 | Phase 2.0 Discovery & Scope Lock | — | P2-1 … P2-5 | ⬜ |
| P2-E2 | Productionization & Platform | A | P2-6 … P2-11 | ✅ Done (code) — metrics/alerts/backups remain VM ops |
| P2-E3 | Deepen the Website Audit | D | P2-12 … P2-18 | ✅ Done (2026-06-25) |
| P2-E4 | Social Media Audit | B | P2-19 … P2-25 | ✅ Done (2026-06-23) |
| P2-E5 | Enrichment (v3) | C | P2-26 … P2-28 | 🟡 scaffold shipped; live providers/analytics v3 |

### 3.2 Task-level

| Task | Title | Type | Epic | Status | Notes |
|---|---|---|---|---|---|
| P2-1 | Lock the Social-Data Path, Budget & Legal Sign-Off | Task | P2-E1 | ✅ | DECIDED: ~~Bright Data only~~ **Apify free tier (2026-06-23 r2)**, no OAuth/Business Discovery; legal given (Darius 2026-06-05) |
| P2-2 | Provision Accounts & Keys | Task | P2-E1 | ⬜ | **Create free Apify account + API token (self-serve, free tier) (2026-06-23 r2)**; ~~Bright Data + YouTube key~~ — YouTube dropped, no paid gate |
| P2-3 | ~~Bright Data Paid Smoke Test on Real Builder Accounts~~ | Task | P2-E1 | ❌ REMOVED | **REMOVED (2026-06-23 r2):** Apify free tier is self-serve — no paid smoke test, no P2-20 gate |
| P2-4 | Draft `rubrics/social.yaml` & Gather Calibration Accounts | Task | P2-E1 | ⬜ | Feeds P2-23 |
| P2-5 | Choose Hosting / Auth / Storage Stack & Confirm Volume | Task | P2-E1 | ⬜ | Feeds P2-6/P2-7/P2-9 |
| P2-6 | Lightweight Team Authentication (API + UI) | Task | P2-E2 | ✅ Done (shipped ahead of plan, 2026-06-16) | Clerk auth live, opt-in via `CLERK_ISSUER`; no multi-tenancy (see `DEPLOYMENT.md`) |
| P2-7 | ~~Storage Interface + S3 Report/Screenshot Backend~~ | Task | P2-E2 | ❌ REMOVED | **REMOVED/descoped (2026-06-23 r2):** no AWS/S3 — local FS on the VM is the intended design for this ~5–10-user internal tool; retention via P2-10 |
| P2-8 | Complete Request-Level SSRF Interception | Task | P2-E2 | ✅ Done (shipped 2026-06-23) | Request-level interception live (`crawler.py` `_host_blocked_for_subrequest` + Playwright route guard; `crawler_intercept_requests`); closes Known-Limitations §2 |
| P2-9 | Managed Hosting + CI/CD Deploy | Task | P2-E2 | ✅ Done (shipped ahead of plan, 2026-06-16) | Live on Linode + Caddy (TLS); CI/CD auto-deploy on merge to main (see `DEPLOYMENT.md`) |
| P2-10 | Observability: Sentry, Metrics, Alerts, Backups, Retention | Task | P2-E2 | 🟡 Partly Done (2026-06-23) | **Retention DONE** (`retention.py` + `cleanup_storage.py` + `storage_retention_days`, cron-run) + **env-gated Sentry DONE** (`observability.py` + `SENTRY_DSN`); metrics/alerts/backups = VM ops (not code) |
| P2-11 | Web Dashboard + History/Re-run/Share + White-Label | Story | P2-E2 | ✅ Done (2026-06-25) | On-screen report (`pages/audit/[id].tsx` `ScoreCards`/sections/roadmap), history filter/sort + one-click re-run (`rerunAuditEnrichment`), token-gated share links (`shareAudit`/`/shared`), and **white-label controls on the new-audit form** (`pages/index.tsx` `brand_overrides` → `report_branding.apply_brand_overrides`) |
| P2-12 | Structured-Data (JSON-LD) Extractor + Schema Rubric Rules | Task | P2-E3 | ✅ Done (2026-06-25) | `_extract_schema_types` (shared `_collect_jsonld`); `seo.schema.{present,business_identity,valid_json_ld,breadcrumb}` |
| P2-13 | AEO/GEO Readiness Signals | Task | P2-E3 | ✅ Done (2026-06-25) | `_extract_aeo`; `seo.aeo.{heading_hierarchy,question_headings,extractable_structure}`. **Research-vetted: `llms.txt` DROPPED** (off-page fetch + near-zero 2026 evidence) |
| P2-14 | CrUX Field Core Web Vitals (LCP/INP/CLS) | Task | P2-E3 | ✅ Done (2026-06-25) | `psi_client` CrUX origin field data → `seo.cwv.{lcp,inp,cls}` (skip_if_missing) |
| P2-15 | ~~axe-core~~ **Static-HTML** Accessibility Pass + Rubric Rules | Task | P2-E3 | ✅ Done (2026-06-25) | **Research-driven deviation: NO axe-core** (needs live DOM, breaks deterministic-from-stored-HTML invariant). `_extract_a11y` deterministic WCAG A/AA subset → `seo.a11y.*` (lang/zoom/landmark/labels/link+button names/tabindex/dup-referenced-ids); see docs/04 §3 known-limitation |
| P2-16 | Crawlability/Indexability + Link-Health + Redirect Checks | Task | P2-E3 | ✅ Done (2026-06-25) | `site_health` redirect-hop tracking; `seo.technical_crawl.{canonicals,redirect_chains}` |
| P2-17 | Local-SEO Signals (NAP, GBP, Location Pages, Local Schema) | Task | P2-E3 | ✅ Done (2026-06-25) | `_extract_local`; `seo.local.{nap_schema,service_area,map_or_gbp,visible_address}` |
| P2-18 | Trust/Conversion UX Signals + Security-Hygiene Checks | Task | P2-E3 | ✅ Done (2026-06-25) | Security-hygiene: `_extract_security` → `seo.security.{https,no_mixed_content}`; trust/conversion UX already covered by Phase-1 `uxui.trust.*` |
| P2-19 | Social Data Provider Adapter (Interface + ~~YouTube~~ **Apify IG/FB** Backend) | Task | P2-E4 | ✅ Done (2026-06-23) | **Apify provider shipped:** `apps/worker/stages/social/apify_provider.py` (IG actor `apify~instagram-scraper`, FB actor `apify~facebook-pages-scraper`) + `collector.py` (`collect_social_facts`, injectable, graceful skip); no YouTube |
| P2-20 | ~~Bright Data~~ **Apify** Backend for IG/FB | Task | P2-E4 | ✅ Done (2026-06-23) | Apify free-tier IG+FB backend live (folded with P2-19 in `apify_provider.py`); ~~gated on P2-3~~ — P2-3 removed, no paid gate (legal ✅ given). Live IG+FB runs verified |
| P2-21 | ~~Instagram Business Discovery Shortcut~~ | Task | P2-E4 | ❌ Dropped | No account approvals (BLC); ~~Bright Data~~ **Apify** covers IG |
| P2-22 | Social Fact Extractors + Common Schema + Fixtures | Task | P2-E4 | ✅ Done (2026-06-23) | `apps/worker/stages/social/extractor.py` normalizes IG+FB → `social.*` facts; `tests/unit/test_extractor_social.py` |
| P2-23 | Social Rubric + Standalone Social Score | Task | P2-E4 | ✅ Done (2026-06-23) | `rubrics/social.yaml` (`phase2-social-v1` → now `phase2-social-v3`, `category: social`) scored by `scoring.score_social_audit()` → standalone Social Score; website composite UNCHANGED (`composite.yaml` still `seo:0.45/uxui:0.55`); `test_social_scoring.py` |
| P2-24 | ~~Social Commentary Prompts~~ **Deterministic Social Findings** + Grounding-Validator Extension | Task | P2-E4 | ✅ Done (2026-06-23) | Delivered as **deterministic rule-derived findings/roadmap** (`social/report.py`, no LLM), not LLM commentary; no grounding-validator extension needed (numbers come straight from rule metadata) |
| P2-25 | Separate Social Report (PDF) + Social Audit Tab | Task | P2-E4 | ✅ Done (2026-06-23) | Separate `templates/social_report.html` via `pdf_renderer.render_social_pdf` (PDF only); `compose_social_report_payload` shared seam; new Social Audit tab + `/social` page; **no** Lead-Gen fold-in |
| P2-26 | Competitor Benchmarking Provider + Benchmarked Scoring | Task | P2-E5 | 🟡 Scaffold shipped | Provider registry, normalized facts, graceful skip, and report rendering are built; live paid clients remain v3 |
| P2-27 | GA4 + Search Console OAuth Integrations | Task | P2-E5 | ⛔ v3 | |
| P2-28 | Microsoft Clarity + SEMrush Integrations | Task | P2-E5 | ⛔ v3 | |

> **Update this board as you go.** Flip the Status cell when a task moves. Keep it the
> single source of truth for Phase 2 progress; the prose in §4 is the copy-paste detail.

### 3.3 Recommended delivery order

1. **P2-E1** (2–3 days) — discovery, free Apify token, legal sign-off, draft `social.yaml`.
2. **P2-E2** and **P2-E3** in parallel — both low-risk and reuse what works.
3. **P2-E4** — the marquee feature; ~~start once P2-3 + legal sign-off (P2-1) are green~~
   **(2026-06-23 r2)** P2-3 is removed (Apify free tier is self-serve), so the only
   prerequisite is a free Apify token (P2-2) + legal sign-off (P2-1, ✅ given).
4. **P2-E5** — v3, only if pulled forward.

---

## 4. Jira Epics And Tasks (copy-paste ready)

> Each task below is a self-contained copy-paste unit: **Summary**, **Issue type**,
> **Labels**, **Description**, **Acceptance criteria**, **Subtasks**. Paste the Summary line
> into the Jira summary field and the rest into the description.

---

## Epic P2-E1: Phase 2.0 Discovery & Scope Lock

**Epic name:** `Epic P2-E1: Phase 2.0 Discovery & Scope Lock`
**Labels:** `phase-2`, `blc`, `internal-tool`, `scraper-first`
**Description:** Resolve the architectural forks and gather the accounts, keys, legal
sign-off, and calibration data needed before the build epics start. The major decisions are
already drafted in [`docs/08_PHASE2_PLAN.md`](08_PHASE2_PLAN.md) §3; this epic confirms them
and turns them into provisioned resources.

### P2-1 Lock the Social-Data Path, Budget & Legal Sign-Off

**Issue type:** Task · **Status: ✅ DECIDED (2026-06-05; provider revised 2026-06-23 r2)**
**Labels:** `phase-2`, `social-audit`, `scraper-first`
**Description:** **DECIDED — scraping over OAuth.** BLC (Darius) chose scraping over
OAuth: *"we can just scrape the data."* ~~Bright Data is the social source for IG/FB; YouTube
uses its free official API.~~ **Update (2026-06-23, round 2): the social source is Apify
([apify.com](https://apify.com)) on its free-tier credits, running actors for Instagram +
Facebook public data behind the existing provider-adapter; YouTube is dropped (platforms in
scope = IG + FB only; TikTok optional later via Apify).** **No OAuth and no IG Business
Discovery** (both need account approvals BLC declined). LinkedIn excluded; TikTok deferred.
**Acceptance criteria:**

- ✅ Social-data strategy recorded: ~~Bright Data only~~ **Apify free tier (IG/FB)**, no OAuth/Business Discovery.
- ✅ Budget posture agreed: **Apify free-tier credits (self-serve, no paid gate)** ~~(pay-as-you-go; optional Bright Data spend alert, e.g. $25/mo)~~.
- ✅ Legal go-ahead given by BLC: public data only, never log into target accounts, minimal retention, no LinkedIn.

**Subtasks:**

- ✅ Re-verify Plan specifics: **Apify free-tier IG/FB actors** ~~(Bright Data ~$0.75/1K pay-per-success; YouTube 10k units/day, 1 unit/channel call)~~.
- ✅ Confirm budget posture: **Apify free tier (no paid alert needed)**.
- ✅ Record the legal go-ahead.
- ✅ Confirm LinkedIn excluded and TikTok deferred.

### P2-2 Provision Accounts & Keys

**Issue type:** Task
**Labels:** `phase-2`, `productionization`, `social-audit`
**Description:** Stand up the external account the social MVP needs — scraping only. No
Facebook app, no OAuth provider, no YouTube key. **Update (2026-06-23, round 2): this
simplifies to creating a free Apify account + API token (self-serve, free tier) — it is no
longer a paid/blocked gate.** Hosting/auth/storage are **not** part of the MVP (they belong to
E2 productionization, deferred until the tool graduates from internal use).
**Acceptance criteria:**

- A free **Apify** account is created and an **API token** is issued (free tier), with the IG/FB actors identified. ~~A **Bright Data** account is created with the IG/FB social scrapers enabled.~~
- ~~A working **YouTube Data API** key (Google Cloud project) is available.~~ **YouTube dropped (2026-06-23 r2) — no YouTube key needed.**
- Secrets are stored safely (interim `.env`; a real secret store comes with E2).

**Subtasks:**

- Create the free Apify account; issue an API token; note the actor IDs for IG + FB. ~~Create the Bright Data account; note dataset/endpoint IDs for IG + FB.~~
- ~~Create Google Cloud project + enable YouTube Data API v3; issue a key.~~ *(Dropped 2026-06-23 r2.)*
- *(No Facebook app, no IG professional account, no auth/hosting/S3 — dropped or deferred to E2.)*
- Record where the Apify token lives.

### P2-3 ~~Bright Data Paid Smoke Test on Real Builder Accounts~~ — ❌ REMOVED (2026-06-23 r2)

**Issue type:** Task · **Status: ❌ REMOVED**
**Labels:** `phase-2`, `social-audit`, `scraper-first`
**Description:** **REMOVED (2026-06-23, round 2).** The social provider is now **Apify on its
free tier**, which is **self-serve and free** — there is no paid smoke test to run and no
spend to validate, so this gate no longer makes sense. The "gated on P2-3" dependency on
**P2-20** (and the P2-22 fixtures dependency) is dropped; fixtures for P2-22 are captured
directly from free Apify actor runs as part of building the Apify backend (P2-20). The
struck-through original below is kept for history.

> ~~**Description:** Before committing to the Bright Data backend build (P2-20), run a small
> **paid** smoke test against 3–5 real builder/remodeler IG + FB accounts to confirm data
> shape, field coverage, success rate, and per-call cost at internal volume.~~
> ~~**Acceptance criteria:**~~
> - ~~Raw Bright Data responses for ≥3 real builder IG accounts + ≥2 FB pages are captured.~~
> - ~~The fields needed for the social rubric (followers, media/post count, recent post engagement, bio, link-in-bio) are confirmed present.~~
> - ~~Observed success rate and per-call cost are recorded and within Plan §10 expectations.~~
> ~~**Subtasks:**~~
> - ~~Pick 3–5 representative builder/remodeler social accounts (mix of strong/weak).~~
> - ~~Run the Bright Data IG profile + posts and FB page collectors once each.~~
> - ~~Save raw JSON samples as fixtures for P2-22.~~
> - ~~Record success rate, latency, and cost; flag any missing fields.~~

### P2-4 Draft `rubrics/social.yaml` & Gather Calibration Accounts

**Issue type:** Task
**Labels:** `phase-2`, `social-audit`
**Description:** Draft the first social scoring rubric (same engine/format as
`rubrics/seo.yaml`) and assemble strong + weak builder social accounts to calibrate it,
mirroring the website strong/weak fixtures.
**Acceptance criteria:**

- A draft `rubrics/social.yaml` exists covering profile/bio, posting cadence, engagement, content mix, and funnel/lead-capture signals.
- A list of ≥2 strong and ≥2 weak builder social accounts is recorded for calibration.

**Subtasks:**

- Map the original-scope social evaluation points (Plan §5.1) to candidate rules + weights.
- Draft the rubric YAML with `version`, `category: social`, and per-rule `fact_path`s.
- Collect strong/weak example accounts for the calibration gate (used in P2-23).

### P2-5 Choose Hosting / Auth / Storage Stack & Confirm Volume

**Issue type:** Task
**Labels:** `phase-2`, `productionization`
**Description:** Lock the concrete platform choices (auth provider, managed Postgres,
hosting, object storage) and the expected audits/month so P2-6/P2-7/P2-9 build against fixed targets.
**Acceptance criteria:**

- Auth provider, managed Postgres, hosting target, and S3-compatible storage are chosen and recorded.
- Expected volume (audits/month) is agreed and used to size workers/DB/caching.

**Subtasks:**

- Decide auth (Clerk / Supabase Auth / Workspace SSO).
- Decide managed Postgres (Supabase / Neon / RDS) and hosting (Vercel + Railway/Render or AWS).
- Decide S3-compatible storage + signed-URL approach.
- Record expected monthly volume.

---

## Epic P2-E2: Productionization & Platform

**Epic name:** `Epic P2-E2: Productionization & Platform`
**Labels:** `phase-2`, `blc`, `productionization`, `internal-tool`, `no-multitenancy`
**Description:** Take the proven website tool from "internal/local" to "hosted and safe
for the BLC team." Closes the items in [`docs/06_KNOWN_LIMITATIONS.md`](06_KNOWN_LIMITATIONS.md).
**Internal-tool scope:** lightweight team auth, **no** multi-tenancy, no public sign-up.

> **Note:** An org/tenant data-model & isolation task was considered and **dropped** — the
> internal-tool decision (Plan §3.1) removes multi-tenancy from Phase 2.

### P2-6 Lightweight Team Authentication (API + UI)

**Issue type:** Task
**Labels:** `phase-2`, `productionization`, `internal-tool`
**Description:** Protect every audit endpoint behind a single internal-team login. Today
there is **no auth** — anyone who can reach the API can run audits and read results
(`apps/api/main.py`, all routes in `apps/api/routes/audits.py`). Add a single shared-org
auth (Clerk / Supabase Auth, or Google Workspace SSO) enforced by FastAPI dependencies and
wired into the Next.js UI. No public sign-up, billing, or per-user isolation.
**Acceptance criteria:**

- All audit endpoints (`POST /audits`, `GET /audits`, `GET /audits/{id}`, `/status`, `/report`) require a valid authenticated session; unauthenticated requests get 401.
- `/health` stays public; `/docs` is gated or behind auth in deployed environments.
- The operator UI has a login flow and attaches the session/token to API calls (`apps/frontend/lib/api.ts`).
- No multi-tenancy: one shared org, shared audit history.

**Subtasks:**

- Choose + integrate the auth provider (from P2-5).
- Add a FastAPI auth dependency and apply it to the audit router.
- Keep `/health` public; gate `/docs` in non-local envs.
- Add login/session handling to the Next.js UI and the typed API client.
- Add tests for authorized vs unauthorized access.

### P2-7 ~~Storage Interface + S3 Report/Screenshot Backend~~ — ❌ REMOVED (2026-06-23 r2)

**Issue type:** Task · **Status: ❌ REMOVED/descoped**
**Labels:** `phase-2`, `productionization`
**Description:** **REMOVED/descoped (2026-06-23, round 2).** No AWS/S3 — **local filesystem
storage on the VM** is the intended design for this internal ~5–10-user tool. The app already
writes PDFs and screenshots to the local filesystem (`storage/`), and that is the as-built
design we're keeping. **Storage retention is handled by P2-10** (the `cleanup_storage.py`
retention job that prunes reports/screenshots/tool-exports past a configured age), not by an
S3 lifecycle. There is no storage-interface/signed-URL work to do. The struck-through original
below is kept for history.

> ~~**Description:** There is **no storage abstraction today** — `pdf_renderer.py` writes PDFs
> directly under `local_report_storage_dir`, and screenshots go to
> `local_screenshot_storage_dir`. Introduce a small storage interface
> (`save_report` / `get_report` / `get_report_url`), keep the local filesystem backend as the
> default, add an S3-compatible backend, and serve reports via **signed URLs**.~~
> ~~**Acceptance criteria:**~~
> - ~~A storage interface exists with at least `save(key, bytes)`, `get(key)`, `url(key)`.~~
> - ~~`pdf_renderer.py` and the crawler screenshot writes go through the interface, not raw paths.~~
> - ~~An S3-compatible backend is selectable by config; local FS remains the default.~~
> - ~~`GET /audits/{id}/report` returns/redirects to a signed URL when S3 is active.~~
> - ~~`audit_results.pdf_path` stores a storage key, not a hard local path, when S3 is active.~~
> ~~**Subtasks:**~~
> - ~~Add `apps/shared/storage.py` (interface + local + S3 backends) + config switch.~~
> - ~~Route `pdf_renderer.render_audit_pdf` output through the interface.~~
> - ~~Route crawler screenshot writes through the interface.~~
> - ~~Update the report route to serve signed URLs.~~
> - ~~Add tests for both backends (local + mocked S3).~~

### P2-8 Complete Request-Level SSRF Interception — ✅ DONE (2026-06-23)

**Issue type:** Task · **Status: ✅ DONE (shipped 2026-06-23)**
**Labels:** `phase-2`, `productionization`, `security`

> **Update (2026-06-23) — DONE.** Request-level interception shipped in
> `apps/worker/stages/crawler.py`: `_host_blocked_for_subrequest` + a Playwright **route
> guard on each context** re-validate every sub-resource/redirect host against the
> private/loopback/link-local/metadata-IP block-list during rendering. New setting
> `crawler_intercept_requests` gates it (auto-disabled when `crawler_allow_private_hosts` is
> true so the QA harness can still hit localhost). Unit-tested. Known-Limitations §2 gap is
> closed. Original description/AC/subtasks retained below for reference.

**Description:** Phase 1 only validates the **start URL** and blocks private/loopback hosts
by default (`CRAWLER_ALLOW_PRIVATE_HOSTS=false`). Redirects and sub-resources that resolve
to internal IPs mid-crawl are **not** intercepted (see Known Limitations §2). Add
request-level interception in the Playwright crawler so every navigation/redirect/resource
fetch is re-validated against the private-IP blocklist.
**Acceptance criteria:**

- Every request the crawler issues (initial, redirect target, sub-resource) is checked against the private/loopback/link-local/metadata-IP blocklist, not just the start URL.
- A redirect from a public URL to an internal IP is blocked and logged, and the audit degrades gracefully (does not crash).
- DNS-rebinding is mitigated (resolve + validate the resolved IP, not just the hostname).
- Tests cover: public→internal redirect, internal sub-resource, and the metadata IP (169.254.169.254).

**Subtasks:**

- Add a Playwright request/route interceptor that validates resolved IPs.
- Reuse/extend the existing private-host check from the crawler.
- Add graceful-skip handling + logging for blocked requests.
- Add SSRF interception tests.
- Update Known Limitations §2 to reflect the closed gap.

### P2-9 Managed Hosting + CI/CD Deploy

**Issue type:** Task
**Labels:** `phase-2`, `productionization`
**Description:** Deploy the stack to managed hosting with TLS at the edge: managed Postgres,
API + Celery workers on Railway/Render (or AWS ECS/Fargate), the Next.js UI on Vercel.
Add a CI/CD pipeline that runs tests/lint and deploys on merge. The repo already ships
`apps/api/Dockerfile`, `apps/worker/Dockerfile`, and migrations that run on start.
**Acceptance criteria:**

- API, worker, DB, Redis, and UI run on managed hosting reachable over HTTPS.
- Alembic migrations run automatically on deploy.
- CI runs `pytest` + `ruff` and blocks merge on failure; merge to main deploys.
- Environment config is per-environment (local / staging / prod).

**Subtasks:**

- Provision managed Postgres + Redis.
- Deploy API + worker containers; deploy the UI to Vercel with `NEXT_PUBLIC_API_BASE_URL`.
- Terminate TLS at the edge; set `API_CORS_ORIGINS` to the deployed UI origin.
- Add a CI/CD workflow (test + lint + deploy).
- Smoke-test an end-to-end audit on the deployed environment.

### P2-10 Observability: Sentry, Metrics, Alerts, Backups, Retention — 🟡 PARTLY DONE (2026-06-23)

**Issue type:** Task · **Status: 🟡 Partly Done (shipped 2026-06-23)**
**Labels:** `phase-2`, `productionization`

> **Update (2026-06-23) — partly DONE; remainder rescoped lighter.**
> - ✅ **Retention DONE:** `apps/shared/retention.py` + `scripts/cleanup_storage.py` +
>   `storage_retention_days` setting prune reports/screenshots/tool-exports older than N days.
>   Run from **cron** (no in-app scheduler). Unit-tested. *(This also covers the storage
>   retention that the removed P2-7/S3 task would otherwise have implied.)*
> - ✅ **Sentry DONE (optional, env-gated):** `apps/shared/observability.py` + `SENTRY_DSN`
>   setting; **no-op when unset**.
> - ⬜ **Metrics / alerts / DB backups (+ Celery retry/DLQ)** remain **VM ops tasks — not
>   code**, intentionally **lighter scope** for a 5–10-user internal tool on a single VM.
>
> Original description/AC/subtasks retained below for reference; the retention + Sentry items
> are now satisfied.

**Description:** Add the operational baseline the app now warrants: error tracking (Sentry)
in API + worker, basic metrics/alerting, automated DB backups, Celery retry/dead-letter
handling, and a **data-retention cleanup** for old audit rows, PDFs, and screenshots (none
exists today — they accumulate under `storage/`).
**Acceptance criteria:**

- ✅ Sentry captures unhandled API + worker errors with release/environment tags. *(env-gated; no-op when `SENTRY_DSN` unset)*
- ⬜ Basic metrics + at least one alert (e.g. job failure rate / queue backlog) exist. *(VM ops, lighter scope)*
- ⬜ Automated DB backups are configured and a restore has been tested once. *(VM ops, lighter scope)*
- ✅ A retention job prunes ~~audit rows +~~ stored reports/screenshots/tool-exports past a configured age. *(`cleanup_storage.py`, cron-run)*
- ⬜ Celery has retry + dead-letter (or equivalent) handling beyond the soft time limit. *(VM ops, lighter scope)*

**Subtasks:**

- ✅ Wire Sentry into API + worker (env-gated via `SENTRY_DSN`); move secrets into the platform secret store.
- ⬜ Add metrics + an alert on failure rate / backlog. *(VM ops)*
- ⬜ Configure DB backups; document + test restore. *(VM ops)*
- ✅ Add a retention/cleanup task (storage) with a configurable TTL (`storage_retention_days`, cron-run).
- ⬜ Add Celery retry / dead-letter handling. *(VM ops)*

### P2-11 Web Dashboard + History/Re-run/Share + White-Label

**Issue type:** Story
**Labels:** `phase-2`, `productionization`
**Description:** Turn the operator UI into a product surface. Add an interactive **dashboard
view** that reuses the existing `ReportPayload` (so no new backend contract), improved audit
history, **re-run**, **shareable links** for prospect-facing reports, and **white-label**
branding. The PDF stays; the dashboard is the on-screen complement.
**Acceptance criteria:**

- A dashboard renders scores, findings, recommendations, and the score breakdown from `GET /audits/{id}` (the composed `ReportPayload`).
- Audit history supports filtering and a one-click **re-run** of a prior audit.
- A **shareable link** can expose a single report read-only (respecting auth/share rules) for a prospect.
- White-label branding (logo/colors) can be applied to a shared/prospect-facing report.

**Subtasks:**

- Build the dashboard view consuming `ReportPayload`.
- Improve the history page (filter/sort) and add re-run.
- Add shareable-link generation + a read-only report view.
- Add white-label branding controls (reuse `brand/blc.yaml` pattern).
- Add UI tests for dashboard + share flows.

---

## Epic P2-E3: Deepen the Website Audit

**Epic name:** `Epic P2-E3: Deepen the Website Audit`
**Labels:** `phase-2`, `blc`, `website-deepening`
**Description:** Make the website audit visibly better and more modern **without touching
the architecture**. Every task is **new extractor signals + new YAML rubric rules** that
reuse the existing crawler, rubric engine (`apps/worker/stages/scoring.py`), commentary,
grounding validator, and report. **Bump the rubric version** per
[`docs/04_RUBRIC_GUIDE.md`](04_RUBRIC_GUIDE.md) and re-run the strong/weak calibration gate
(`make qa`) after tuning.

> **Composite note.** Per the 2026-06-23 decision, **WS D signals stay as rules under the
> existing SEO/UX categories — YAML-only, no new scored category and no `scoring.py`
> composite change.** (The website composite `{seo, uxui}` is deliberately left untouched;
> P2-23 no longer changes it either — Social now has its own standalone rubric/score.) If a
> future signal genuinely needed its *own* scored sub-category folded into the website
> composite, that would be a separate, explicitly-approved code change — not assumed here.

### P2-12 Structured-Data (JSON-LD) Extractor + Schema Rubric Rules

**Issue type:** Task
**Labels:** `phase-2`, `website-deepening`
**Description:** Detect and validate JSON-LD structured data (`LocalBusiness`,
`Organization`, `Service`, `Review`/`AggregateRating`, `FAQPage`, `BreadcrumbList`). In 2026
this is the #1 lever for AI-citation visibility and rich results, and it is currently not
audited. Emit the new facts into the existing SEO fact bundle and add SEO rubric rules.
**Acceptance criteria:**

- The extractor reports which schema types are present + whether each parses as valid JSON-LD.
- New `rubrics/seo.yaml` rules score schema presence/validity; the SEO rubric version is bumped.
- The strong/weak calibration gate still holds after re-tuning.

**Subtasks:**

- Extend `extractor_seo.py` to parse JSON-LD blocks + report types and validity.
- Add fixtures (page with rich schema, page with none, malformed JSON-LD).
- Add SEO rubric rules + bump the version.
- Re-run `make qa` calibration.

### P2-13 AEO/GEO Readiness Signals

**Issue type:** Task
**Labels:** `phase-2`, `website-deepening`
**Description:** Add answer-engine-optimization signals: `llms.txt` presence, AI-crawler
access in `robots.txt` (GPTBot, ClaudeBot, PerplexityBot, Google-Extended), and
content-structured-for-extraction proxies (clear headings, FAQ blocks, entity clarity).
Cheap to check, increasingly decisive for discovery.
**Acceptance criteria:**

- The extractor reports `llms.txt` presence, per-AI-crawler allow/deny from `robots.txt`, and answer-structure proxies.
- New rubric rules score these signals; rubric version bumped; calibration holds.

**Subtasks:**

- Extend the extractor to fetch/parse `llms.txt` + AI-crawler directives.
- Add answer-structure proxies (FAQ blocks, heading clarity).
- Add rubric rules + fixtures + bump version.
- Re-run calibration.

### P2-14 CrUX Field Core Web Vitals (LCP/INP/CLS)

**Issue type:** Task
**Labels:** `phase-2`, `website-deepening`
**Description:** Pull **CrUX field data** (LCP, **INP**, CLS) alongside the existing lab PSI
numbers. Field CWV is the actual ranking signal and INP replaced FID in 2024. Surface and
score it (PSI already returns some of this — expose it as facts and add rules).
**Acceptance criteria:**

- The pipeline collects CrUX field LCP/INP/CLS (origin and/or URL level) and stores them in `psi_facts` (or a sibling fact bundle).
- New rubric rules score field CWV with `skip_if_missing: true` (graceful when CrUX has no data), mirroring the existing PSI rules.
- Calibration holds.

**Subtasks:**

- Add a CrUX API client (or extend `psi_client.py`) for field LCP/INP/CLS.
- Normalize into the fact bundle with graceful skip when unavailable.
- Add rubric rules (`skip_if_missing: true`) + bump version.
- Re-run calibration.

### P2-15 axe-core Accessibility Pass + Rubric Rules

**Issue type:** Task
**Labels:** `phase-2`, `website-deepening`
**Description:** Run **axe-core** via the existing Playwright render to detect WCAG issues
(alt text, form labels, color contrast, heading order, landmarks). Accessibility doubles as
a conversion + legal-risk signal for SMB sites. Emit facts into the UX/UI bundle + add rules.
**Acceptance criteria:**

- axe-core runs against rendered pages in the crawl and produces a normalized issue summary (counts by impact/category).
- New `rubrics/uxui.yaml` rules score accessibility; version bumped; calibration holds.

**Subtasks:**

- Inject axe-core into the Playwright page context during the crawl.
- Normalize results into the UX/UI fact bundle.
- Add rubric rules + fixtures + bump version.
- Re-run calibration.

### P2-16 Crawlability/Indexability + Link-Health + Redirect Checks

**Issue type:** Task
**Labels:** `phase-2`, `website-deepening`
**Description:** Add the most common real-world SEO failures: `robots.txt` / `noindex` /
canonical correctness, XML sitemap presence + validity, redirect chains, and **link health**
(broken internal/outbound links, orphan pages within the crawled set — reuses crawl output,
no new fetch budget).
**Acceptance criteria:**

- The extractor reports sitemap presence/validity, canonical/noindex correctness, redirect-chain depth, and broken/orphan link counts within the crawled set.
- New rubric rules score these; version bumped; calibration holds.

**Subtasks:**

- Extend the extractor for sitemap/robots/canonical/redirect facts.
- Compute link-health + orphan pages from existing crawl output.
- Add rubric rules + fixtures + bump version.
- Re-run calibration.

### P2-17 Local-SEO Signals (NAP, GBP, Location Pages, Local Schema)

**Issue type:** Task
**Labels:** `phase-2`, `website-deepening`
**Description:** High value for this niche: NAP (name/address/phone) consistency, a Google
Business Profile link, service-area / location pages, embedded map, and `LocalBusiness`
schema. Builders/remodelers live and die by local search.
**Acceptance criteria:**

- The extractor reports NAP presence/consistency, GBP link presence, location/service-area page presence, embedded map, and local schema.
- New rubric rules score local SEO; version bumped; calibration holds.

**Subtasks:**

- Extend the extractor for NAP + GBP + location-page + map signals.
- Reuse the P2-12 schema extractor for `LocalBusiness`.
- Add rubric rules + fixtures + bump version.
- Re-run calibration.

### P2-18 Trust/Conversion UX Signals + Security-Hygiene Checks

**Issue type:** Task
**Labels:** `phase-2`, `website-deepening`
**Description:** Sharpen UX lead-capture scoring with trust/conversion signals
(testimonials/reviews, trust badges, contact/quote-form depth + friction, click-to-call
above the fold, social-proof density) and add light **security-hygiene** checks (HTTPS
enforcement, HSTS, basic security headers, mixed-content) for professional polish.
**Acceptance criteria:**

- The extractor reports trust/conversion signals + security-hygiene facts (HTTPS/HSTS/headers/mixed-content).
- New UX/UI (+ optionally SEO/technical) rubric rules score them; version bumped; calibration holds.

**Subtasks:**

- Extend `extractor_uxui.py` for trust/conversion signals.
- Add a light security-header/mixed-content check.
- Add rubric rules + fixtures + bump version.
- Re-run calibration.

---

## Epic P2-E4: Social Media Audit — ✅ DONE (2026-06-23)

**Epic name:** `Epic P2-E4: Social Media Audit`
**Labels:** `phase-2`, `blc`, `social-audit`, `scraper-first`
**Status: ✅ DONE (2026-06-23)**

> **Update (2026-06-23) — SHIPPED, end-to-end.** The standalone Social audit is built and
> runnable from the browser, fully independent of the website audit, and tested (119 unit
> tests pass; ruff clean; live IG+FB Apify runs verified). DONE: **P2-19, P2-20, P2-22, P2-23,
> P2-25**; **P2-24 DONE via deterministic rule-derived findings** (not LLM commentary);
> **P2-21 Dropped**. The full as-built map (data model, Apify provider/actors, social pipeline,
> standalone scoring, separate report, API, frontend, FB limitation, config, scripts, tests)
> is in the epic-level banner near the top of this doc. The website audit and its `{seo, uxui}`
> composite are unchanged.

**Description:** Add the third audit type from the original scope. Architecturally it
**reuses the existing pipeline framework** — the same Extract → Score → Commentate →
Validate pattern — so most of the framework is reused. ~~Bright Data scraping only: Bright
Data for IG/FB, YouTube via its free official API.~~ **Update (2026-06-23, round 2): Apify
(free tier) for IG/FB; YouTube dropped — platforms in scope = Instagram + Facebook only
(TikTok optional later via Apify).** **No OAuth, no IG Business Discovery** (account approvals
BLC declined). **LinkedIn excluded; TikTok deferred.** Legal sign-off ✅ given. ~~do not start
P2-20 until **P2-3** (paid smoke test) is done~~ **(2026-06-23 r2) P2-3 is removed (Apify free
tier is self-serve), so P2-20 has no paid-smoke-test gate — only a free Apify token (P2-2).**

> **Update (2026-06-23) — Social is now a STANDALONE, fully independent audit.** It is no
> longer "submit website + social handles → one combined report → Social folded into the
> website Lead-Gen composite." Instead the Social audit is its **own product**:
> - **Own UI tab + own handle inputs — NO website URL required.**
> - **Own SEPARATE report (separate PDF)** and its **own standalone Social Score**.
> - It **does NOT fold into the website Lead-Gen composite.** The website audit's scoring is
>   **UNCHANGED** (`composite.yaml` stays `seo:0.45 / uxui:0.55`). **No combined
>   website+social number** (a blended dashboard view is not foreclosed for later, but lives
>   at the dashboard level, not in any rubric).
>
> **Reuse vs. new.** The Social branch reuses ~80% of the shared spine — job lifecycle,
> status polling, storage, the deterministic commentary + grounding engine, WeasyPrint /
> branding, and Clerk auth. What's **new/leaner**: a social-only pipeline =
> collect (~~Bright Data IG/FB + YouTube Data API~~ **Apify IG/FB, free tier — 2026-06-23 r2;
> no YouTube**) → `extractor_social` → score `social.yaml` **only** → deterministic
> commentary → grounding → render a **separate** social report template. **No crawl / PSI /
> external-SEO** in the social branch.
>
> **Data-model change (now differs from the website audit).** Add an `audit_type`
> discriminator (`"website" | "social"`, default `"website"`) to `audit_jobs`; make `url`
> **nullable**; add `social_handles` (JSONB). Require `url` for website audits and **≥1
> handle** for social audits. `run_collection_audit` **branches on `audit_type`** (social
> takes the leaner pipeline above). Status / report / detail API endpoints stay
> **`job_id`-keyed (type-agnostic)**. The frontend adds a new **Social Audit** tab with a
> handle-input submit page; history/detail branch on type. ~~Bright Data IG/FB remains **gated
> on provisioning** (Bright Data account + YouTube key + the P2-3 paid smoke test) before
> P2-20~~ **(2026-06-23 r2): Apify IG/FB only needs a free Apify token (P2-2) — no YouTube
> key, no P2-3 paid-smoke-test gate.**

### P2-19 Social Data Provider Adapter (Interface + ~~YouTube~~ Apify IG/FB Backend) — ✅ DONE (2026-06-23)

**Issue type:** Task · **Status: ✅ DONE (shipped 2026-06-23)**
**Labels:** `phase-2`, `social-audit`

> **Update (2026-06-23) — DONE.** Shipped as `apps/worker/stages/social/apify_provider.py`
> (the Apify network adapter wiring two actors: IG `apify~instagram-scraper`, FB
> `apify~facebook-pages-scraper`) + `collector.py` (`collect_social_facts` orchestrates the
> fetches, graceful skip when no token / no data). The social collector is an **injectable**
> param of `run_collection_audit` (`social_collector`, default `collect_social_facts`), so it
> drops in like the website crawler/PSI collectors. Folded together with **P2-20** as planned.
> Missing/failed social data degrades gracefully (status vocabulary skipped/failed/partial/
> complete in `extractor.py`), never aborting the audit. The struck original (YouTube-first) is
> kept below.

> **Update (2026-06-23, round 2).** This becomes **provider adapter + Apify backend (IG/FB)**,
> not YouTube-first. **YouTube is dropped** (no YouTube Data API backend). Since Apify's free
> tier is self-serve, the Apify IG/FB backend is the first (and only) backend built here — it
> may be folded together with **P2-20**. The struck original (YouTube-first) is kept below.

**Description:** Build one swappable provider-adapter interface for social data, plus the
**Apify** backend (free tier) for Instagram + Facebook public data behind the adapter, run
via Apify actors. This proves the social pipeline end-to-end on the free tier. ~~plus the
**YouTube Data API** backend first (the one official API that is open, free, and stable —
channel stats: subs, views, video count at 1 quota unit/call). This proves the social
pipeline end-to-end before any paid scraping.~~
**Acceptance criteria:**

- A provider-adapter interface exists (e.g. `fetch_profile(handle)` / `fetch_recent_posts(handle)`) with a backend registry.
- An **Apify** backend returns IG profile + recent-post engagement and FB page public data via Apify actors (free tier). ~~A YouTube backend returns channel stats + recent uploads via the Data API.~~
- New worker stages live alongside the existing ones (a social **collector** module next to `crawler.py`/`psi_client.py`).
- Missing/failed social data degrades gracefully (skip, like missing PSI), never aborts the audit.

**Subtasks:**

- Add a social provider-adapter package + interface + registry.
- Implement the **Apify IG/FB** backend (free tier). ~~Implement the YouTube Data API backend.~~
- Add the social collector worker stage.
- Add graceful-skip handling + tests with mocked **Apify** responses.

### P2-20 ~~Bright Data~~ Apify Backend for IG/FB — ✅ DONE (2026-06-23)

**Issue type:** Task · **Status: ✅ DONE (shipped 2026-06-23)**
**Labels:** `phase-2`, `social-audit`, `scraper-first`

> **Update (2026-06-23) — DONE.** The Apify free-tier IG + FB backend is live in
> `apps/worker/stages/social/apify_provider.py` (folded with P2-19): the IG actor returns
> profile + recent-post engagement; the FB pages actor returns page **metadata** (followers,
> about, website, contact). Live IG+FB runs verified. Failures degrade gracefully (the audit
> completes with the platform marked skipped/failed/partial); no logins to target accounts.
> Tests use captured Apify fixtures (`tests/unit/test_extractor_social.py`,
> `test_worker_social.py`). The struck original (Bright Data) is kept below.

> **Update (2026-06-23, round 2).** The backend is now **Apify (free tier)**, not Bright Data,
> and the **P2-3 paid-smoke-test gate is removed** — Apify's free tier is self-serve, so the
> only prerequisite is a free Apify token (P2-2). May be folded into **P2-19**. Struck
> original (Bright Data) kept below.

**Description:** Implement the social backend: **Apify** (free tier) actors for Instagram and
Facebook — any public account (business **or** personal), competitors, and post-level depth,
behind the P2-19 adapter. ~~Implement the **primary** social backend: Bright Data for
Instagram and Facebook … ~$0.75/1K, pay-per-success. **Gated on P2-3 (Bright Data smoke
test);**~~ legal sign-off ✅ given (P2-1).
**Acceptance criteria:**

- An **Apify** backend returns IG profile + recent-post engagement and FB page public data through the adapter interface (via Apify actors, free tier). ~~A Bright Data backend returns …~~
- Failures degrade gracefully (audit completes with social marked skipped/partial).
- Usage is observable (log per-call success / Apify credit usage); no logins to target accounts.

**Subtasks:**

- Implement the **Apify** IG + FB backend behind the adapter. ~~Implement the Bright Data IG + FB backend behind the adapter.~~
- Normalize responses toward the common social-facts schema (P2-22).
- Add graceful-skip + retry handling.
- Add tests using fixtures captured from free **Apify** actor runs. ~~Add tests using the P2-3 captured fixtures.~~

### P2-21 ~~Instagram Business Discovery Shortcut~~ — ❌ DROPPED (2026-06-05)

**Issue type:** Task · **Status: ❌ DROPPED**
**Labels:** `phase-2`, `social-audit`
**Description:** **Dropped by BLC decision.** Business Discovery would require BLC to stand
up a Facebook Login app + an IG professional account — an approval Darius explicitly
declined (*"we can just scrape the data"*). ~~Bright Data~~ **Apify (2026-06-23 r2)** (P2-20)
already covers Instagram for any public account, so this shortcut adds setup for ~no benefit.
**Not building it.**
(LinkedIn remains excluded; TikTok deferred — the adapter supports TikTok later with no rework.)

### P2-22 Social Fact Extractors + Common Schema + Fixtures — ✅ DONE (2026-06-23)

**Issue type:** Task · **Status: ✅ DONE (shipped 2026-06-23)**
**Labels:** `phase-2`, `social-audit`

> **Update (2026-06-23) — DONE.** Shipped as `apps/worker/stages/social/extractor.py` (a pure,
> deterministic normalizer for both IG + FB into the common `social.*` facts schema —
> followers, posting cadence/recency, engagement-rate estimate, content mix, bio/CTA,
> link-in-bio/funnel signals). When no profile has post data (e.g. the FB pages actor returns
> no posts), cadence/recency/engagement are emitted as `None` (not `0`) so the corresponding
> `skip_if_missing` rules rescale out rather than unfairly failing. Strong/weak/malformed
> fixtures + extractor tests live in `tests/unit/test_extractor_social.py`. Note the as-built
> module is `social/extractor.py` (under the `social/` package), not a flat
> `extractor_social.py`. Original description/AC/subtasks below.

**Description:** Add deterministic parsers (`extractor_social.py`, matching the
`extractor_seo.py`/`extractor_uxui.py` naming) that normalize each platform's raw data into a
**common social-facts schema** (followers, posting cadence, engagement rate, content-type
mix, bio/CTA, link-in-bio/funnel signals). Add fixtures from ~~the P2-3 captures~~ **free
Apify actor runs (2026-06-23 r2; P2-3 removed)**.
**Acceptance criteria:**

- A common social-facts schema is defined and produced identically regardless of source ~~(YouTube / Bright Data)~~ **(Instagram / Facebook via Apify; 2026-06-23 r2)**.
- `extractor_social.py` computes follower size, posting cadence/consistency, and an engagement-rate estimate deterministically.
- Strong/weak social fixtures + extractor tests exist (mirroring the website fixtures).

**Subtasks:**

- Define the common social-facts schema.
- Implement `extractor_social.py` + per-platform normalization.
- Add strong/weak/malformed social fixtures + expected outputs.
- Add extractor unit tests.

### P2-23 Social Rubric + Standalone Social Score — ✅ DONE (2026-06-23)

> **Update (2026-06-23) — DONE.** `rubrics/social.yaml` (`version: "phase2-social-v1"`, since advanced to `"phase2-social-v3"`,
> `category: social`) is scored by `scoring.score_social_audit()` into a **standalone Social
> Score (0–100)** via the reused rubric engine, with the same `skip_if_missing` graceful
> rescaling as the website rubrics. `scoring.Rubric.category` `Literal` now includes
> `"social"`. **The website composite is untouched** — `rubrics/composite.yaml` still reads
> `seo: 0.45` / `uxui: 0.55` and `compose_lead_generation_score` / the `Literal["seo","uxui"]`
> set are unchanged. Scoring + reproducibility tests in `tests/unit/test_social_scoring.py`.
> Original (rewritten) banner + body below.

> **Update (2026-06-23).** Rewritten for the standalone-Social decision. The original ticket
> made the website composite a code change (extend `Literal["seo","uxui"]` → add `"social"`,
> require `validate_weights` to expect `{seo, uxui, social}`, rebalance `composite.yaml` to
> three weights, fold social into `compose_lead_generation_score`). **All of that is
> DROPPED.** The website composite stays `{seo, uxui}` (`seo:0.45 / uxui:0.55`) — untouched.
> Social now produces its **own standalone Social Score** from its own `rubrics/social.yaml`
> via the **reused scoring engine**, with **no** change to the website Lead-Gen composite.

**Issue type:** Task
**Labels:** `phase-2`, `social-audit`
**Description:** Add `rubrics/social.yaml` (same rubric engine and YAML format as
`rubrics/seo.yaml`) and run it through the existing `scoring.py` engine to produce a
**standalone Social Score**. This is **rubric-only** for the website side: the website
composite (`rubrics/composite.yaml`, `compose_lead_generation_score`, the
`Literal["seo","uxui"]` types) is **NOT** changed — the website Lead-Gen score is unaffected.
The Social Score stands on its own and is rendered in the separate Social report (P2-25).
**Acceptance criteria:**

- `rubrics/social.yaml` exists (with `version`, `category: social`, per-rule `fact_path`s) and scores cleanly through the existing rubric engine.
- The pipeline produces a **deterministic standalone Social Score** for identical social facts (reproducible), with the same `skip_if_missing` graceful-degradation behavior as the website rubrics.
- **The website composite is untouched** — `composite.yaml` stays `{seo, uxui}` summing to 1.0, the website Lead-Gen score is unchanged, and there is no `{seo, uxui, social}` set anywhere.
- `social.yaml` is calibrated against the strong/weak accounts from P2-4; the gate holds.

**Subtasks:**

- Add `rubrics/social.yaml` with rules + weights + version (`category: social`).
- Wire the social fact bundle into the existing scoring engine to emit a standalone Social Score (no composite change).
- Calibrate against strong/weak accounts; add scoring + reproducibility tests for the Social Score.

### P2-24 ~~Social Commentary Prompts~~ Deterministic Social Findings + ~~Grounding-Validator Extension~~ — ✅ DONE (2026-06-23)

**Issue type:** Task · **Status: ✅ DONE (shipped 2026-06-23)**
**Labels:** `phase-2`, `social-audit`

> **Update (2026-06-23) — DONE, delivered as DETERMINISTIC rule-derived findings (not LLM
> commentary).** Mirroring Phase-1's deterministic commentary, the social findings + tiered
> roadmap (Quick Wins / Mid-Term / Long-Term) come **straight from the social rubric's rule
> metadata** (`finding_label` / `remediation` / `impact` / `tier`) in
> `apps/worker/stages/social/report.py` — **no OpenAI/LLM call**, so the social report is
> reproducible. Because every surfaced number originates from rule metadata + the scored facts
> (not free-form prose), **no grounding-validator extension was needed** — there are no
> unsupported numeric claims to strip. (So the planned "commentary prompts + grounding
> extension" was satisfied by the deterministic path, not by adding `prompts/` social prompts.)
> Original (LLM-style) description/AC/subtasks retained below for history.

**Description:** Reuse the existing commentary pipeline to write social findings + tiered
recommendations from facts + scores, and extend the grounding validator
(`grounding_validator.py`) to cover social facts so unsupported numeric claims are stripped.
**Acceptance criteria:**

- Social commentary produces findings + Quick Wins / Mid-Term / Long-Term recommendations grounded only in extracted social facts.
- The grounding validator checks social numeric claims against the social fact sources.
- A local fallback (no LLM key) still produces correct, generic social commentary, matching the Phase 1 pattern.

**Subtasks:**

- Add social commentary prompt(s) (extend `prompts/`).
- Pass social facts + social score into `generate_commentary`.
- Extend `validate_commentary_grounding` fact sources to include social facts.
- Add tests (grounding strips an unsupported social number).

### P2-25 Separate Social Report (PDF) + Social Audit Tab — ✅ DONE (2026-06-23)

> **Update (2026-06-23) — DONE.** Shipped as a **separate** social report: its own
> `templates/social_report.html` rendered by `pdf_renderer.render_social_pdf` (**PDF only — no
> DOCX** for social), driven by `compose_social_report_payload` (`social/report.py`) — the
> shared seam used by **both** the API detail response and the renderer. New config
> `report_social_template_path`. The frontend adds a **Social Audit** tab + `/social` submit
> page (paste an IG/FB profile link or `@handle`; **no login/OAuth/account-connection**);
> history shows a Web/Social badge + the right score, and the detail page renders a social view
> (score + findings + per-platform table) with Download PDF + Share. The website report
> payload, template, and Lead-Gen card are **untouched**. Verified end-to-end on live IG+FB
> runs. Original (rewritten) banner + body below.

> **Update (2026-06-23).** Rewritten for the standalone-Social decision. The original ticket
> bolted a Social **section** onto the website report and surfaced an "updated three-part
> Lead-Gen Readiness score" / a Lead-Gen card reflecting a new composite. **That is
> DROPPED.** Social now renders a **SEPARATE report** (its own template + payload + PDF) and
> gets its **own Social Audit UI tab** — the website report and its Lead-Gen card are
> **unchanged**.

**Issue type:** Task
**Labels:** `phase-2`, `social-audit`
**Description:** Build a **standalone Social report** and a **Social Audit tab**, reusing the
shared rendering spine (WeasyPrint + branding, deterministic commentary/grounding output) but
producing a **separate** report — its own payload shape and its own template, distinct from
the website report. Render the **standalone Social Score** (P2-23) with the social findings +
tiered recommendations. Add a new **Social Audit** frontend tab with a handle-input submit
page; history/detail branch on `audit_type`. The website report payload, template, and
Lead-Gen card are **not** touched.
**Acceptance criteria:**

- A **separate** social report payload + template render a standalone Social report (PDF) showing the standalone Social Score, findings, and tiered recommendations, with correct pagination.
- The Social report is rendered/stored via the shared spine (WeasyPrint + branding) but is a **distinct** artifact from the website report — **no** Social section is added to the website report and **no** Lead-Gen card change.
- The frontend has a **Social Audit tab** with handle inputs (no website URL); history/detail correctly distinguish `audit_type` (`"website"` vs `"social"`).
- Validated end-to-end on real builder **social accounts**; reproducible for identical inputs.

**Subtasks:**

- Add a separate social report payload + WeasyPrint template + CSS (do **not** modify the website report payload/template).
- Render the standalone Social Score + social findings/recommendations into the social report.
- Add the **Social Audit** frontend tab + handle-input submit page; branch history/detail on `audit_type`.
- Run end-to-end QA on real social accounts; add social report-payload tests.

---

## Epic P2-E5: Enrichment (v3 — out of Phase 2 core)

**Epic name:** `Epic P2-E5: Enrichment (v3)`
**Labels:** `phase-2`, `blc`, `enrichment`, `v3-enrichment`
**Description:** Deferred until the core (P2-E2 + P2-E3 + P2-E4) is validated. These
materially change the architecture (anonymous public-data audits → user-authorized data
sources), so they are their own phase. Keep as ⛔ in the tracker unless explicitly pulled
forward (Plan §3.3).

### P2-26 Competitor Benchmarking Provider + Benchmarked Scoring

**Issue type:** Task
**Labels:** `phase-2`, `enrichment`, `v3-enrichment`
**Description:** Benchmark SEO/UX/Social scores against competitors or industry norms via
SEMrush / Ahrefs / Similarweb APIs (higher tiers; recurring cost — no free reliable source).
**Status update (2026-07-02):** scaffold shipped. The app now has `benchmark_enabled`,
`benchmark_provider`, and `benchmark_api_key`; a provider registry for `semrush`, `ahrefs`, and
`similarweb`; typed normalized benchmark facts; a graceful collector that skips in every not-ready
state; and PDF/DOCX/web report rendering. Live paid vendor HTTP clients are still no-op stubs until
cost and provider choice are approved.
**Acceptance criteria:**

- Scaffold is integrated and scores can be presented relative to competitor/industry baselines when
  a provider returns data.
- A live benchmarking provider fetcher is implemented before enabling real baselines.
- Recurring cost is approved before enabling.

**Subtasks:**

- Select + integrate a live benchmarking provider.
- Add benchmarked presentation to the report/dashboard. **Done for the scaffold.**
- Document recurring cost + enablement gate.

### P2-27 GA4 + Search Console OAuth Integrations

**Issue type:** Task
**Labels:** `phase-2`, `enrichment`, `v3-enrichment`
**Description:** User-authorized GA4 (behavior flow, bounce/exit, conversions, funnel
drop-offs) + Search Console (keyword performance, technical SEO, indexing) integrations for
BLC's onboarded clients.
**Acceptance criteria:**

- A client can OAuth-connect GA4 + Search Console; insights are extracted and surfaced.

**Subtasks:**

- Add GA4 + Search Console OAuth + insight extraction.
- Surface insights in the report/dashboard.

### P2-28 Microsoft Clarity + SEMrush Integrations

**Issue type:** Task
**Labels:** `phase-2`, `enrichment`, `v3-enrichment`
**Description:** Add Microsoft Clarity (heatmaps/session-recording references) + SEMrush
(keyword/traffic data) integrations.
**Acceptance criteria:**

- Clarity + SEMrush data is integrated and surfaced where useful.

**Subtasks:**

- Add Clarity integration.
- Add SEMrush integration.

---

## 5. Phase 2 Done Criteria

Phase 2 **core** (P2-E1 + P2-E2 + P2-E3 + P2-E4) is complete when:

- **P2-E1:** Social-data path, budget, and legal sign-off are locked; ~~accounts/keys provisioned; Bright Data paid smoke test passed~~ **a free Apify token is provisioned (2026-06-23 r2 — P2-3 paid smoke test removed)**; `social.yaml` drafted; hosting/auth/storage chosen.
- **P2-E2:** A team member must authenticate; ~~reports are stored in S3 and served via signed URLs~~ **reports are stored on the VM's local filesystem with a retention cleanup (2026-06-23 r2 — S3/P2-7 removed)**; the crawler blocks internal IPs at request level **(✅ done 2026-06-23)**; the system is deployed to managed hosting with TLS **and optional env-gated error tracking (Sentry, ✅ done)** ~~, error tracking, and backups~~ *(metrics/alerts/backups are VM ops, lighter scope)*; a dashboard shows results and history.
- **P2-E3:** The website audit produces and scores the new signals (schema, AEO, field CWV, accessibility, crawlability/link-health, local SEO, trust/security); the strong/weak calibration gate still holds; rubric versions are bumped.
- **P2-E4: ✅ DONE (2026-06-23).** Submitting **social handles only** (no website URL) via the Social Audit tab produces a deterministic **standalone Social Score** **without the audited account logging in** (~~Bright Data for IG/FB; YouTube official API~~ **Apify for IG + FB, free tier — 2026-06-23 r2; YouTube dropped**), **deterministic rule-derived** findings with tiered recommendations (not LLM commentary), and a **separate Social report (PDF)** — reproducible for identical inputs. **The website audit and its Lead-Gen composite are unchanged** (no combined website+social number). Tested (119 unit tests pass; ruff clean; live IG+FB runs verified).
  > **Update (2026-06-23):** the original "combined Lead-Generation Readiness score that includes social" criterion is **superseded** — Social is standalone and does not fold into the website composite.
- Validated on real builder/remodeler social accounts.

Enrichment (P2-E5) is **explicitly out of Phase 2 core** and remains v3 unless pulled forward.

---

## 6. Alignment Note

This Jira plan is the operational twin of [`docs/08_PHASE2_PLAN.md`](08_PHASE2_PLAN.md)
(scope/rationale) and [`docs/10_PHASE2_IMPLEMENTATION.md`](10_PHASE2_IMPLEMENTATION.md)
(build manual). Numbering is sequential like Phase 1: **5 epics (P2-E1…P2-E5), 28 tasks
(P2-1…P2-28)**. Workstreams map to epics A→P2-E2, D→P2-E3, B→P2-E4, C→P2-E5, with P2-E1 as
discovery. Internal-tool scope, scraper-first social data, no multi-tenancy, LinkedIn
excluded, TikTok deferred, enrichment deferred to v3.
