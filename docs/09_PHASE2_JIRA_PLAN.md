# Phase 2 Jira Plan & Tracking Board

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
- **Bright Data scraping only.** Bright Data is the social source for IG/FB; YouTube uses
  its free official API. **No OAuth, no IG Business Discovery** (both need account
  approvals BLC declined). **LinkedIn excluded**; **TikTok deferred**.
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
- **Storage interface + S3 backend**; reports served via signed URLs.
- **Complete request-level SSRF interception** in the crawler.
- **Managed hosting + CI/CD**, TLS at the edge.
- **Observability** (Sentry, metrics, alerts), DB backups, data-retention cleanup.
- **Web dashboard** + audit history/re-run/share + white-label branding.
- **Deepen the website audit:** structured data/schema, AEO/answer-engine readiness, CrUX
  field Core Web Vitals, axe-core accessibility, crawlability/link health, local SEO,
  trust/conversion + security-hygiene signals.
- **Social media audit:** provider adapter, YouTube backend, Bright Data backend (primary)
  for IG/FB, social fact extractors, `social.yaml` rubric, social commentary + grounding,
  social report section, and **Social folded into the Lead-Gen score**.

**Out of scope for Phase 2 core (Epic P2-E5 / v3):**

- Competitor benchmarking (SEMrush/Ahrefs/Similarweb).
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
| P2-E2 | Productionization & Platform | A | P2-6 … P2-11 | ⬜ |
| P2-E3 | Deepen the Website Audit | D | P2-12 … P2-18 | ⬜ |
| P2-E4 | Social Media Audit | B | P2-19 … P2-25 | ⬜ |
| P2-E5 | Enrichment (v3) | C | P2-26 … P2-28 | ⛔ v3 |

### 3.2 Task-level

| Task | Title | Type | Epic | Status | Notes |
|---|---|---|---|---|---|
| P2-1 | Lock the Social-Data Path, Budget & Legal Sign-Off | Task | P2-E1 | ✅ | DECIDED: Bright Data only, no OAuth/Business Discovery; legal given (Darius 2026-06-05) |
| P2-2 | Provision Accounts & Keys | Task | P2-E1 | ⬜ | Bright Data + YouTube key only (FB app/auth/hosting dropped or deferred to E2) |
| P2-3 | Bright Data Paid Smoke Test on Real Builder Accounts | Task | P2-E1 | ⬜ | Gate before P2-20 |
| P2-4 | Draft `rubrics/social.yaml` & Gather Calibration Accounts | Task | P2-E1 | ⬜ | Feeds P2-23 |
| P2-5 | Choose Hosting / Auth / Storage Stack & Confirm Volume | Task | P2-E1 | ⬜ | Feeds P2-6/P2-7/P2-9 |
| P2-6 | Lightweight Team Authentication (API + UI) | Task | P2-E2 | ⬜ | No multi-tenancy |
| P2-7 | Storage Interface + S3 Report/Screenshot Backend | Task | P2-E2 | ⬜ | None exists today |
| P2-8 | Complete Request-Level SSRF Interception | Task | P2-E2 | ⬜ | Closes Known-Limitations §2 |
| P2-9 | Managed Hosting + CI/CD Deploy | Task | P2-E2 | ⬜ | DB, workers, API, UI, TLS |
| P2-10 | Observability: Sentry, Metrics, Alerts, Backups, Retention | Task | P2-E2 | ⬜ | |
| P2-11 | Web Dashboard + History/Re-run/Share + White-Label | Story | P2-E2 | ⬜ | Reuses report payload |
| P2-12 | Structured-Data (JSON-LD) Extractor + Schema Rubric Rules | Task | P2-E3 | ⬜ | |
| P2-13 | AEO/GEO Readiness Signals | Task | P2-E3 | ⬜ | `llms.txt`, AI-crawler access |
| P2-14 | CrUX Field Core Web Vitals (LCP/INP/CLS) | Task | P2-E3 | ⬜ | |
| P2-15 | axe-core Accessibility Pass + Rubric Rules | Task | P2-E3 | ⬜ | Reuses Playwright browser |
| P2-16 | Crawlability/Indexability + Link-Health + Redirect Checks | Task | P2-E3 | ⬜ | |
| P2-17 | Local-SEO Signals (NAP, GBP, Location Pages, Local Schema) | Task | P2-E3 | ⬜ | High value for niche |
| P2-18 | Trust/Conversion UX Signals + Security-Hygiene Checks | Task | P2-E3 | ⬜ | |
| P2-19 | Social Data Provider Adapter (Interface + YouTube Backend) | Task | P2-E4 | ⬜ | Build first |
| P2-20 | Bright Data Backend for IG/FB | Task | P2-E4 | ⬜ | Gated on P2-3 (legal ✅ given) |
| P2-21 | ~~Instagram Business Discovery Shortcut~~ | Task | P2-E4 | ❌ Dropped | No account approvals (BLC); Bright Data covers IG |
| P2-22 | Social Fact Extractors + Common Schema + Fixtures | Task | P2-E4 | ⬜ | |
| P2-23 | Social Rubric + Scoring & Lead-Gen Update | Task | P2-E4 | ⬜ | Composite code change |
| P2-24 | Social Commentary Prompts + Grounding-Validator Extension | Task | P2-E4 | ⬜ | |
| P2-25 | Report/PDF/Dashboard Social Section + Updated Lead-Gen Score | Task | P2-E4 | ⬜ | |
| P2-26 | Competitor Benchmarking Provider + Benchmarked Scoring | Task | P2-E5 | ⛔ v3 | |
| P2-27 | GA4 + Search Console OAuth Integrations | Task | P2-E5 | ⛔ v3 | |
| P2-28 | Microsoft Clarity + SEMrush Integrations | Task | P2-E5 | ⛔ v3 | |

> **Update this board as you go.** Flip the Status cell when a task moves. Keep it the
> single source of truth for Phase 2 progress; the prose in §4 is the copy-paste detail.

### 3.3 Recommended delivery order

1. **P2-E1** (2–3 days) — discovery, keys, legal sign-off, draft `social.yaml`.
2. **P2-E2** and **P2-E3** in parallel — both low-risk and reuse what works.
3. **P2-E4** — the marquee feature; start once P2-3 + legal sign-off (P2-1) are green.
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

**Issue type:** Task · **Status: ✅ DECIDED (2026-06-05)**
**Labels:** `phase-2`, `social-audit`, `scraper-first`
**Description:** **DECIDED — Bright Data scraping only.** BLC (Darius) chose scraping over
OAuth: *"we can just scrape the data."* Bright Data is the social source for IG/FB;
YouTube uses its free official API. **No OAuth and no IG Business Discovery** (both need
account approvals BLC declined). Pay-as-you-go budget (optional spend alert). LinkedIn
excluded; TikTok deferred.
**Acceptance criteria:**

- ✅ Social-data strategy recorded and matches Plan §3.2.5: Bright Data only, no OAuth/Business Discovery.
- ✅ Budget posture agreed (pay-as-you-go; optional Bright Data spend alert, e.g. $25/mo).
- ✅ Legal go-ahead given by BLC: public data only, never log into target accounts, minimal retention, no LinkedIn.

**Subtasks:**

- ✅ Re-verify Plan §3.2 / §10 specifics (Bright Data ~$0.75/1K pay-per-success; YouTube 10k units/day, 1 unit/channel call).
- ✅ Confirm pay-as-you-go budget + optional spend alert.
- ✅ Record the legal go-ahead.
- ✅ Confirm LinkedIn excluded and TikTok deferred.

### P2-2 Provision Accounts & Keys

**Issue type:** Task
**Labels:** `phase-2`, `productionization`, `social-audit`
**Description:** Stand up the external accounts the social MVP needs — scraping only. No
Facebook app, no OAuth provider. Hosting/auth/storage are **not** part of the MVP (they
belong to E2 productionization, deferred until the tool graduates from internal use).
**Acceptance criteria:**

- A **Bright Data** account is created with the IG/FB social scrapers enabled.
- A working **YouTube Data API** key (Google Cloud project) is available.
- Secrets are stored safely (interim `.env`; a real secret store comes with E2).

**Subtasks:**

- Create the Bright Data account; note dataset/endpoint IDs for IG + FB.
- Create Google Cloud project + enable YouTube Data API v3; issue a key.
- *(No Facebook app, no IG professional account, no auth/hosting/S3 — dropped or deferred to E2.)*
- Record where each secret lives.

### P2-3 Bright Data Paid Smoke Test on Real Builder Accounts

**Issue type:** Task
**Labels:** `phase-2`, `social-audit`, `scraper-first`
**Description:** Before committing to the Bright Data backend build (P2-20), run a small
**paid** smoke test against 3–5 real builder/remodeler IG + FB accounts to confirm data
shape, field coverage, success rate, and per-call cost at internal volume.
**Acceptance criteria:**

- Raw Bright Data responses for ≥3 real builder IG accounts + ≥2 FB pages are captured.
- The fields needed for the social rubric (followers, media/post count, recent post engagement, bio, link-in-bio) are confirmed present.
- Observed success rate and per-call cost are recorded and within Plan §10 expectations.

**Subtasks:**

- Pick 3–5 representative builder/remodeler social accounts (mix of strong/weak).
- Run the Bright Data IG profile + posts and FB page collectors once each.
- Save raw JSON samples as fixtures for P2-22.
- Record success rate, latency, and cost; flag any missing fields.

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

### P2-7 Storage Interface + S3 Report/Screenshot Backend

**Issue type:** Task
**Labels:** `phase-2`, `productionization`
**Description:** There is **no storage abstraction today** — `pdf_renderer.py` writes PDFs
directly under `local_report_storage_dir`, and screenshots go to
`local_screenshot_storage_dir`. Introduce a small storage interface
(`save_report` / `get_report` / `get_report_url`), keep the local filesystem backend as the
default, add an S3-compatible backend, and serve reports via **signed URLs**.
**Acceptance criteria:**

- A storage interface exists with at least `save(key, bytes)`, `get(key)`, `url(key)`.
- `pdf_renderer.py` and the crawler screenshot writes go through the interface, not raw paths.
- An S3-compatible backend is selectable by config; local FS remains the default.
- `GET /audits/{id}/report` returns/redirects to a signed URL when S3 is active.
- `audit_results.pdf_path` stores a storage key, not a hard local path, when S3 is active.

**Subtasks:**

- Add `apps/shared/storage.py` (interface + local + S3 backends) + config switch.
- Route `pdf_renderer.render_audit_pdf` output through the interface.
- Route crawler screenshot writes through the interface.
- Update the report route to serve signed URLs.
- Add tests for both backends (local + mocked S3).

### P2-8 Complete Request-Level SSRF Interception

**Issue type:** Task
**Labels:** `phase-2`, `productionization`, `security`
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

### P2-10 Observability: Sentry, Metrics, Alerts, Backups, Retention

**Issue type:** Task
**Labels:** `phase-2`, `productionization`
**Description:** Add the operational baseline the app now warrants: error tracking (Sentry)
in API + worker, basic metrics/alerting, automated DB backups, Celery retry/dead-letter
handling, and a **data-retention cleanup** for old audit rows, PDFs, and screenshots (none
exists today — they accumulate under `storage/`).
**Acceptance criteria:**

- Sentry captures unhandled API + worker errors with release/environment tags.
- Basic metrics + at least one alert (e.g. job failure rate / queue backlog) exist.
- Automated DB backups are configured and a restore has been tested once.
- A retention job prunes audit rows + stored reports/screenshots past a configured age.
- Celery has retry + dead-letter (or equivalent) handling beyond the soft time limit.

**Subtasks:**

- Wire Sentry into API + worker; move secrets into the platform secret store.
- Add metrics + an alert on failure rate / backlog.
- Configure DB backups; document + test restore.
- Add a retention/cleanup task (rows + storage) with a configurable TTL.
- Add Celery retry / dead-letter handling.

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

> **Composite note.** If any signal here becomes its *own scored category* (e.g. an "AI
> Visibility / AEO" sub-score), it requires the same `scoring.py` composite change described
> in P2-23 (extend the `Literal[...]` + rebalance `rubrics/composite.yaml`). If it only adds
> rules to the existing SEO/UX categories, it is **YAML-only** — no code change.

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

## Epic P2-E4: Social Media Audit

**Epic name:** `Epic P2-E4: Social Media Audit`
**Labels:** `phase-2`, `blc`, `social-audit`, `scraper-first`
**Description:** Add the third audit type from the original scope. Architecturally it is a
**clone of the website pipeline** — the same Extract → Score → Commentate → Validate pattern
— so most of the framework is reused. Bright Data scraping only: Bright Data for IG/FB,
YouTube via its free official API. **No OAuth, no IG Business Discovery** (account approvals
BLC declined). **LinkedIn excluded; TikTok deferred.** Legal sign-off ✅ given — do not start
P2-20 until **P2-3** (paid smoke test) is done.

### P2-19 Social Data Provider Adapter (Interface + YouTube Backend)

**Issue type:** Task
**Labels:** `phase-2`, `social-audit`
**Description:** Build one swappable provider-adapter interface for social data, plus the
**YouTube Data API** backend first (the one official API that is open, free, and stable —
channel stats: subs, views, video count at 1 quota unit/call). This proves the social
pipeline end-to-end before any paid scraping.
**Acceptance criteria:**

- A provider-adapter interface exists (e.g. `fetch_profile(handle)` / `fetch_recent_posts(handle)`) with a backend registry.
- A YouTube backend returns channel stats + recent uploads via the Data API.
- New worker stages live alongside the existing ones (a social **collector** module next to `crawler.py`/`psi_client.py`).
- Missing/failed social data degrades gracefully (skip, like missing PSI), never aborts the audit.

**Subtasks:**

- Add a social provider-adapter package + interface + registry.
- Implement the YouTube Data API backend.
- Add the social collector worker stage.
- Add graceful-skip handling + tests with mocked YouTube responses.

### P2-20 Bright Data Backend (Primary) for IG/FB

**Issue type:** Task
**Labels:** `phase-2`, `social-audit`, `scraper-first`
**Description:** Implement the **primary** social backend: Bright Data for Instagram and
Facebook — any public account (business **or** personal), competitors, and post-level depth,
behind the P2-19 adapter. ~$0.75/1K, pay-per-success. **Gated on P2-3 (Bright Data smoke test); legal sign-off ✅ given (P2-1).**
**Acceptance criteria:**

- A Bright Data backend returns IG profile + recent-post engagement and FB page public data through the adapter interface.
- Failures degrade gracefully (audit completes with social marked skipped/partial).
- Cost/usage is observable (log per-call success/cost); no logins to target accounts.

**Subtasks:**

- Implement the Bright Data IG + FB backend behind the adapter.
- Normalize responses toward the common social-facts schema (P2-22).
- Add graceful-skip + retry handling.
- Add tests using the P2-3 captured fixtures.

### P2-21 ~~Instagram Business Discovery Shortcut~~ — ❌ DROPPED (2026-06-05)

**Issue type:** Task · **Status: ❌ DROPPED**
**Labels:** `phase-2`, `social-audit`
**Description:** **Dropped by BLC decision.** Business Discovery would require BLC to stand
up a Facebook Login app + an IG professional account — an approval Darius explicitly
declined (*"we can just scrape the data"*). Bright Data (P2-20) already covers Instagram
for any public account, so this shortcut adds setup for ~no benefit. **Not building it.**
(LinkedIn remains excluded; TikTok deferred — the adapter supports TikTok later with no rework.)

### P2-22 Social Fact Extractors + Common Schema + Fixtures

**Issue type:** Task
**Labels:** `phase-2`, `social-audit`
**Description:** Add deterministic parsers (`extractor_social.py`, matching the
`extractor_seo.py`/`extractor_uxui.py` naming) that normalize each platform's raw data into a
**common social-facts schema** (followers, posting cadence, engagement rate, content-type
mix, bio/CTA, link-in-bio/funnel signals). Add fixtures from the P2-3 captures.
**Acceptance criteria:**

- A common social-facts schema is defined and produced identically regardless of source (YouTube / Bright Data).
- `extractor_social.py` computes follower size, posting cadence/consistency, and an engagement-rate estimate deterministically.
- Strong/weak social fixtures + extractor tests exist (mirroring the website fixtures).

**Subtasks:**

- Define the common social-facts schema.
- Implement `extractor_social.py` + per-platform normalization.
- Add strong/weak/malformed social fixtures + expected outputs.
- Add extractor unit tests.

### P2-23 Social Rubric + Scoring & Lead-Gen Update

**Issue type:** Task
**Labels:** `phase-2`, `social-audit`
**Description:** Add `rubrics/social.yaml` (same engine) and make the **composite a code
change, not just YAML**: in `apps/worker/stages/scoring.py`, `Rubric.category` and
`CompositeRubric.weights` are typed `Literal["seo", "uxui"]` and `validate_weights` requires
the set to be **exactly** `{seo, uxui}` summing to 1.0. Add `social` to those types, rebalance
`rubrics/composite.yaml` so all three weights sum to 1.0, and extend
`compose_lead_generation_score` (and `score_audit`) to fold in the social score.
**Acceptance criteria:**

- `Rubric.category` and `CompositeRubric.weights` accept `social`; `validate_weights` expects exactly `{seo, uxui, social}` summing to 1.0.
- `rubrics/composite.yaml` is rebalanced (e.g. the Plan's 0.35 SEO / 0.40 UX / 0.25 social) and validates.
- `score_audit` produces a deterministic Social Score and a Lead-Gen score that includes social; reproducible for identical facts.
- `social.yaml` is calibrated against the strong/weak accounts from P2-4; the gate holds.

**Subtasks:**

- Add `rubrics/social.yaml` with rules + weights + version.
- Extend the `Literal[...]` types + `validate_weights` + expected category set in `scoring.py`.
- Rebalance `rubrics/composite.yaml` to three categories summing to 1.0.
- Extend `compose_lead_generation_score` + `score_audit` for social.
- Calibrate against strong/weak accounts; add scoring tests.

### P2-24 Social Commentary Prompts + Grounding-Validator Extension

**Issue type:** Task
**Labels:** `phase-2`, `social-audit`
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

### P2-25 Report/PDF/Dashboard Social Section + Updated Lead-Gen Score

**Issue type:** Task
**Labels:** `phase-2`, `social-audit`
**Description:** Extend the report payload + PDF + dashboard with a **Social** section and
surface the updated three-part Lead-Gen Readiness score. Touch-points: `report_payload.py`
(`ReportSectionId`/`ScoreCard`/`SECTION_LABELS` add `social`), the WeasyPrint template
(`templates/report.html` + `report.css`), and the dashboard (P2-11).
**Acceptance criteria:**

- The report payload includes a `social` section + a social `ScoreCard`, and the Lead-Gen card reflects the new composite.
- The PDF renders a Social section (findings + tiered recommendations) with correct pagination.
- The dashboard shows the social section + updated Lead-Gen score.
- Validated end-to-end on real builder sites **and** their social accounts; reproducible for identical inputs.

**Subtasks:**

- Extend `report_payload.py` (`ReportSectionId`, `ScoreCard.id`, `SECTION_LABELS`, section composition) for social.
- Extend the WeasyPrint template + CSS with a Social section.
- Surface social in the dashboard (P2-11).
- Run end-to-end QA on real site+social pairs; add report-payload tests.

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
**Acceptance criteria:**

- A benchmarking provider is integrated and scores can be presented relative to competitor/industry baselines.
- Recurring cost is approved before enabling.

**Subtasks:**

- Select + integrate a benchmarking provider.
- Add benchmarked presentation to the report/dashboard.
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

- **P2-E1:** Social-data path, budget, and legal sign-off are locked; accounts/keys provisioned; Bright Data paid smoke test passed; `social.yaml` drafted; hosting/auth/storage chosen.
- **P2-E2:** A team member must authenticate; reports are stored in S3 and served via signed URLs; the crawler blocks internal IPs at request level; the system is deployed to managed hosting with TLS, error tracking, and backups; a dashboard shows results and history.
- **P2-E3:** The website audit produces and scores the new signals (schema, AEO, field CWV, accessibility, crawlability/link-health, local SEO, trust/security); the strong/weak calibration gate still holds; rubric versions are bumped.
- **P2-E4:** Submitting website + social handles produces a deterministic **Social Score** per platform **without the audited account logging in** (Bright Data for IG/FB; YouTube official API), grounded social commentary with tiered recommendations, and a combined **Lead-Generation Readiness score that includes social** — reproducible for identical inputs, in both PDF and dashboard.
- Validated on real builder/remodeler sites **and** their social accounts.

Enrichment (P2-E5) is **explicitly out of Phase 2 core** and remains v3 unless pulled forward.

---

## 6. Alignment Note

This Jira plan is the operational twin of [`docs/08_PHASE2_PLAN.md`](08_PHASE2_PLAN.md)
(scope/rationale) and [`docs/10_PHASE2_IMPLEMENTATION.md`](10_PHASE2_IMPLEMENTATION.md)
(build manual). Numbering is sequential like Phase 1: **5 epics (P2-E1…P2-E5), 28 tasks
(P2-1…P2-28)**. Workstreams map to epics A→P2-E2, D→P2-E3, B→P2-E4, C→P2-E5, with P2-E1 as
discovery. Internal-tool scope, scraper-first social data, no multi-tenancy, LinkedIn
excluded, TikTok deferred, enrichment deferred to v3.
