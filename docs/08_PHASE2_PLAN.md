# Phase 2 Plan — Social Audit, Productionization & Enrichment

> **CURRENT AS-BUILT SNAPSHOT (2026-07-02).** This plan keeps historical decision notes for
> traceability, but the shipped product is: Website Audit page + optional/auto-discovered
> Instagram, Facebook, and YouTube profiles; combined audits append a Social Media Audit and an
> Overall Lead-Gen Readiness score; standalone social is still supported by the backend/report path
> for old or direct API jobs but no longer has a separate UI tab; `rubrics/social.yaml` is
> `phase2-social-v3`; Facebook uses both Pages and Posts scrapers; YouTube is supported via the
> free Data API; and the competitor-benchmarking scaffold is shipped while live paid vendor clients
> remain v3.

> **UPDATE 2026-06-24 — YouTube RE-ADDED.** The "YouTube is dropped / out of scope" notes
> throughout this doc are **superseded**. A YouTube Data API v3 backend now ships
> (`apps/worker/stages/social/youtube_provider.py` + `normalize_youtube_channel`), so the social
> audit supports **Instagram + Facebook (Apify) AND YouTube** (free `YOUTUBE_API_KEY`, no OAuth,
> ~10k units/day). **Bright Data and IG Business Discovery remain dropped.** Trust `CLAUDE.md` §5
> and `README` for as-built truth.

**Project:** BLC Website Audit Automation → Social Media & Website Auditing Automation
**Client:** Builder Lead Converter (BLC)
**Document purpose:** A detailed Phase 2 implementation plan: what to build, the decisions to lock first, architecture, week-by-week timeline, costs, risks, and acceptance criteria.
**Status:** Draft for review — the deliverable for Epic **P1-E7 / ticket P1-32** (see [`docs/07_DEPLOYMENT_GUIDE.md`](07_DEPLOYMENT_GUIDE.md) §6).

> **Operator decisions (2026-06-23, round 2) — these SUPERSEDE the round-1 banner and §3.2/§5
> wherever they conflict:**
> - **Social data provider = APIFY ([apify.com](https://apify.com)), free-tier credits — REPLACES
>   Bright Data everywhere in this plan.** Apify runs actors for **Instagram + Facebook** public
>   data behind the existing provider-adapter. (TikTok remains an optional later add via Apify.)
>   Apify is self-serve on a **free tier** — there is **no paid smoke test and no provisioning
>   gate**.
> - **YouTube is DROPPED entirely.** No YouTube Data API, no YouTube backend, no "build YouTube
>   first." **Social platforms in scope = Instagram + Facebook (via Apify).**
> - **Provisioning/paid gates removed.** **P2-3** (paid Bright Data smoke test on real builder
>   accounts) is **REMOVED** — no "gated on P2-3" dependency. **P2-2** ("Provision accounts &
>   keys") simplifies to: create a **free Apify account + API token** (self-serve, free tier) — no
>   YouTube key needed. **P2-20** becomes the **Apify** backend for IG/FB; **P2-19** becomes
>   "provider adapter + **Apify** backend (IG/FB)" (no YouTube-first).
> - **P2-7 (storage interface + S3 backend) REMOVED/descoped.** No AWS/S3 — **local filesystem
>   storage on the VM** is the intended design for this internal ~5–10-user tool. Storage retention
>   is handled by **P2-10**, not S3.
> - **Status — DONE in code (shipped 2026-06-23):**
>   - **P2-8 (request-level SSRF interception) = DONE.** The crawler now validates every
>     sub-resource/redirect host against the private/loopback/metadata-IP block-list during
>     rendering (`apps/worker/stages/crawler.py`: `_host_blocked_for_subrequest` + a Playwright
>     route guard on each context; new setting `crawler_intercept_requests`, auto-disabled when
>     `crawler_allow_private_hosts` is true; unit-tested).
>   - **P2-10 (observability + retention):** the **RETENTION part = DONE** (`apps/shared/retention.py`
>     + `scripts/cleanup_storage.py` + `storage_retention_days` setting; deletes
>     reports/screenshots/tool-exports older than N days; run from cron — no in-app scheduler;
>     unit-tested). **SENTRY = DONE** as optional env-gated error reporting
>     (`apps/shared/observability.py` + `SENTRY_DSN` setting; no-op when unset). Metrics/alerts/
>     backups remain **VM-ops tasks (not code)** — lighter scope for a 5–10-user internal tool.

> **SHIPPED (2026-06-23) — Workstream B / Social audit is now BUILT, not just planned.** The
> standalone Social Media audit is **implemented end-to-end and tested** (119 unit tests pass, ruff
> clean, live IG+FB runs verified); the website audit is **untouched** and still passes its QA
> (11/11). As built (verify in code):
> - **Provider = Apify (free tier)** via `apps/worker/stages/social/apify_provider.py`, wiring **two
>   actors**: `apify~instagram-scraper` (`_IG_ACTOR`) + `apify~facebook-pages-scraper` (`_FB_ACTOR`).
>   **YouTube and Bright Data are not used.** Config: `apify_api_token`, `apify_timeout_seconds`
>   ([`apps/shared/config.py`](../apps/shared/config.py):117–118).
> - **Social stages** live in `apps/worker/stages/social/`: `collector.py`
>   (`collect_social_facts`, graceful skip), `extractor.py` (pure IG+FB → `social.*` facts),
>   `apify_provider.py` (network), `report.py` (`compose_social_report_payload`).
> - **Scoring is standalone:** `scoring.score_social_audit()`
>   ([`apps/worker/stages/scoring.py`](../apps/worker/stages/scoring.py):143) runs
>   **`rubrics/social.yaml`** (`version: phase2-social-v1` — now `phase2-social-v3`, `category: social`) for a 0–100 Social
>   Score. `Rubric.category` `Literal` now includes `"social"` (line 47), but the website
>   `CompositeRubric.weights` stays exactly `{seo, uxui}` (line 66) — social is **not** folded into
>   the website composite; website scoring is unchanged.
> - **Findings/recommendations are DETERMINISTIC**, derived from rubric rule metadata
>   (`finding_label` / `remediation` / `impact` / `tier`) — **not an LLM** (so P2-24's "commentary
>   prompts" shipped as deterministic, rule-derived findings).
> - **Data model:** `audit_jobs.audit_type` (`"website"` default | `"social"`) +
>   `audit_jobs.social_handles` JSONB; `audit_results` gained `social_score` (nullable INT) +
>   `social_facts` JSONB, and the website scores (`seo_score`/`uxui_score`/`lead_gen_score`) are now
>   **nullable** ([`apps/shared/models.py`](../apps/shared/models.py):71–111). Alembic head is now
>   **`20260623_0004`** (chain `0001→0002→0003→0004`).
> - **Report:** separate [`templates/social_report.html`](../templates/social_report.html) rendered by
>   `pdf_renderer.render_social_pdf` (PDF only, **no DOCX** for social); `report_social_template_path`
>   config; `compose_social_report_payload` is the shared seam (API detail + renderer).
> - **Pipeline:** `tasks.run_collection_audit` **branches on `audit_type`**
>   ([`apps/worker/tasks.py`](../apps/worker/tasks.py):300) → `_run_social_pipeline` (collect → score →
>   render → store), reusing `_mark_job`/the shared spine; `social_collector` is an injectable param
>   (default `collect_social_facts`).
> - **API:** `POST /audits` accepts `audit_type` + `social_handles` (`url` optional for social);
>   `AuditCreateRequest` validates website-needs-`url` / social-needs-≥1-handle
>   ([`apps/api/schemas/audits.py`](../apps/api/schemas/audits.py):22–34); list/detail expose
>   `audit_type` + `social_score`, and detail returns `social_report` for social audits
>   ([`apps/api/routes/audits.py`](../apps/api/routes/audits.py):85–114).
> - **Frontend:** a new **Social Audit** tab + [`/social`](../apps/frontend/pages/social.tsx) submit
>   page (paste an IG/FB link or `@handle`; **no login/OAuth/account-connection**); history shows a
>   Web/Social badge + the right score; the detail page renders a social view (score + findings +
>   per-platform table) with Download PDF + Share.
> - **FB limitation:** the FB pages actor returns **page metadata, not posts**, so
>   cadence/recency/engagement **skip** for FB (rescale, never penalize) — IG has full post data
>   ([`apps/worker/stages/social/extractor.py`](../apps/worker/stages/social/extractor.py):111–112,177–179).
> - **Scripts:** `scripts/run_social_audit.py` (CLI: link → Apify → score) and
>   `scripts/check_apify_social.py` (live probe), both reusing the real code. New tests:
>   `test_extractor_social.py`, `test_social_scoring.py`, `test_worker_social.py`.
>
> The planning text below is **kept** for history; treat the round-2 banners and §5 as the *intended*
> design and this banner as the *as-built* truth. **AI Insights stays PARKED; P2-7 (S3) stays
> removed; P2-E3 (deepen the website audit / Workstream D) is the only remaining unbuilt epic.**

> **Operator decisions (2026-06-23) — read before the social sections below; they supersede them where noted:**
> - **Social Media audit is now a STANDALONE, fully-independent product.** It is *not* a section
>   bolted onto the website audit. It gets its **own UI tab**, its **own handle inputs (no website
>   URL required)**, its **own separate report (separate PDF)**, and its **own standalone Social
>   Score**. It does **NOT** fold into the website Lead-Gen Readiness composite — the website
>   audit's scoring is **UNCHANGED** (`composite.yaml` stays `seo:0.45 / uxui:0.55`; no
>   recalibration, no regression). There is **no combined website+social number** (a blended
>   dashboard view is not foreclosed for later, but it would live at the dashboard level, not in
>   any rubric). Social gets its **own `rubrics/social.yaml`** producing a standalone Social Score;
>   the scoring **engine** is reused, the website **composite** is not changed.
>   - Recommended shape: add an **`audit_type` discriminator** (`"website" | "social"`, default
>     `"website"`) to `audit_jobs`; make **`url` nullable**; add **`social_handles` JSONB**;
>     require `url` for website audits and **≥1 handle** for social audits. `run_collection_audit`
>     **branches on `audit_type`**: the social branch is a **leaner pipeline** — collect (~~Bright
>     Data IG/FB + YouTube Data API~~ **Apify IG/FB** — *round 2*) → `extractor_social` → score
>     **`social.yaml` ONLY** →
>     deterministic commentary → grounding → render a **separate social report template**. **No
>     crawl / PSI / external-SEO** in the social branch. It reuses ~80% of the shared spine (job
>     lifecycle, status polling, storage, deterministic commentary + grounding, WeasyPrint/branding,
>     Clerk auth). Status/report/detail API endpoints stay **`job_id`-keyed and type-agnostic**.
>   - **§3.3, §5.2, §5.3, §5.4, §9.1, §12 below are updated/superseded accordingly** (see the inline
>     `Update (2026-06-23)` notes). ~~Social remains **gated on provisioning** (Bright Data account +
>     YouTube API key + the paid Bright Data smoke test, P2-3) before the IG/FB backend (P2-20).~~
>     **Superseded (round 2):** no provisioning gate — a **free Apify account + API token** is the
>     only setup; **P2-3 (paid smoke test) is REMOVED**.
> - **AI Insights work is PARKED.** The AI Insights / AI-visibility plan
>   ([`docs/13_AI_INSIGHTS_INTEGRATION_PLAN.md`](13_AI_INSIGHTS_INTEGRATION_PLAN.md) +
>   [`docs/14_AI_VISIBILITY_VENDOR_SELECTION.md`](14_AI_VISIBILITY_VENDOR_SELECTION.md)) is
>   **deferred** — blocked on an unpurchased paid vendor subscription (Rank Prompt API Starter
>   $99/mo; live billing unverified). **Phase 2 proceeds WITHOUT it** (verified safe: no Phase-2
>   task depends on AI Insights; it depends only on the shipped Phase-1 spine and its own vendor
>   trial). To be resumed once the subscription is sorted.

> **Companion docs (keep all three in lockstep):**
> - **This doc** — Phase 2 scope, rationale, decisions, timeline, costs, risks.
> - [`docs/09_PHASE2_JIRA_PLAN.md`](09_PHASE2_JIRA_PLAN.md) — the Jira epics/tasks + the
>   live **tracking board** (what's done / what's not), with copy-paste-ready ticket text.
> - [`docs/10_PHASE2_IMPLEMENTATION.md`](10_PHASE2_IMPLEMENTATION.md) — the **build manual**:
>   exact code touch-points (verified against the repo) and sequencing.
> The workstreams here (A/B/C/D) are a **planning concept**; in Jira they become epics
> **A → P2-E2**, **D → P2-E3**, **B → P2-E4**, **C → P2-E5**, with discovery as **P2-E1**.
> Jira tasks use **sequential IDs (P2-1…P2-28)** like Phase 1 — the full per-task mapping is in
> [`docs/09_PHASE2_JIRA_PLAN.md`](09_PHASE2_JIRA_PLAN.md).

> **Sources.** This plan is grounded in the original scope documents (external Word
> files kept locally in `docx/starting docx/`; they are gitignored via `*.docx` and are
> **not committed** to the repo — their content is captured in full in
> [`docs/01_REQUIREMENTS.md`](01_REQUIREMENTS.md)):
> - **Social Media & Website Auditing Automation** — the full product scope (user
>   input, website + social data collection, three audit types, scoring &
>   benchmarking, recommendations, final deliverable, and the "Future Data
>   Collection Expansion").
> - **Technical Assessment** — gaps/risks, proposed architecture, tech stack, and a
>   phased timeline. Phase 2 picks up the items it flagged as deferred.
> - **Phase 1 Implementation Plan §4** — the explicit "deferred to Phase 2" list.
>
> Estimates assume full-time solo work (the Technical Assessment's own assumption);
> part-time extends them proportionally. Final prioritization should fold in the
> **P1-30** internal-test feedback.

---

## 1. Phase 2 Goal

Phase 1 delivered the **website** half of the original vision: a single submitted
URL is crawled, SEO and UX/UI facts are extracted, deterministic scores and a
Lead-Generation Readiness score are produced, grounded AI commentary is generated,
and a branded PDF is rendered — all local-first and internal-only.

Phase 2 completes the original product and makes it usable by the **internal BLC
team** (not a public SaaS — see the locked decision in §3.1). It has four goals, in
priority order:

1. **Make the working product safe and hosted** for a small internal team
   (lightweight auth, hosting, storage, security hardening) — *Workstream A*.
2. **Add the third audit type — Social Media** — the marquee feature still missing
   from the original three-audit scope — *Workstream B*.
3. **Deepen the website audit** so it produces sharper, more modern, more
   defensible findings (structured data, AI/answer-engine readiness, accessibility,
   local SEO, link health) — *Workstream D*. This is the cheapest, lowest-risk way
   to make the existing product visibly "better," because it reuses the rubric engine.
4. **Add enrichment** (live competitor-benchmarking providers + the analytics integrations)
   once the core is validated — *Workstream C / v3*.

> **Why this order.** Workstreams A and D are low-risk and reuse what already works,
> so they ship fast and immediately improve the daily-use tool. Workstream B is the
> headline feature but carries the one genuinely hard decision (§3.2). Workstream C
> changes the architecture (anonymous public-data audits → user-authorized data
> sources) and is deliberately last.

---

## 2. Alignment With The Original Scope

The original scope (Social Media & Website Auditing Automation) defined **three
independent audits** — SEO, UX/UI, and **Social Media** — feeding an **overall Lead
Generation Readiness Score**, plus benchmarking and a "Future Data Collection
Expansion." Phase 1 implemented the first two audits. Phase 2 maps to the remainder:

| Original scope item | Phase 1 | Phase 2 |
|---|---|---|
| Website SEO audit | ✅ Done (core) | Deepen: schema, AEO, CrUX, local SEO → **Workstream D** |
| Website UX/UI audit | ✅ Done (core) | Deepen: accessibility, trust/conversion signals → **Workstream D** |
| **Social media audit** | ❌ Deferred | **Workstream B** |
| Scoring & **benchmarking against competitors/industry** | Scores ✅ / benchmarking scaffold ✅ | Live provider clients → **Workstream C** |
| Final deliverable (report) | ✅ PDF | Dashboard + history + share → **Workstream A** |
| Future Data Collection Expansion (GA, GSC, Clarity, SEMrush) | ❌ | **Workstream C** |
| Accounts / multi-user / hosting | ❌ (internal, no auth) | Team auth + hosting → **Workstream A** |

---

## 3. Decisions To Lock First (Phase 2.0 Discovery — 3–5 days)

These are architectural forks; resolving them is cheaper on paper than mid-build
(Technical Assessment §2, §6). **Nothing in Workstream B should start before #2 is decided.**

### 3.1 Deployment target — ✅ DECIDED: internal tool
Internal tool vs multi-tenant **SaaS** vs **white-label**. **Decision (locked for
Phase 2): internal tool for the BLC team.** This is the single most important scope
cut and it simplifies everything downstream:

- **No multi-tenancy.** The Technical Assessment put multi-tenant SaaS at **15–25%
  of total build effort**; an internal tool removes that entirely. One shared org,
  shared audit history.
- **Auth is lightweight, not a product.** A few named operators behind a single
  login (or SSO via Google Workspace), not public sign-up, billing, or per-tenant
  isolation.
- **It reframes the §3.2 social-data decision** (below): because BLC operators audit
  **prospects and competitors who have not signed up**, the "ask the prospect to
  OAuth" model mostly does not apply. This pushes the answer decisively — see §3.2.
- **White-label / prospect-facing share links remain possible later** (Workstream A
  can still produce a clean branded PDF/dashboard to send a prospect) without making
  the system multi-tenant.

> If BLC later wants to sell this as a SaaS, multi-tenancy becomes a v3 project on top
> of the same pipeline — it is additive, not a rewrite.

### 3.2 Social data strategy — the second-biggest fork (Technical Assessment §2.1)

> **Update (2026-06-23, round 2): provider = APIFY (free tier); YouTube DROPPED.** The recommendation
> in §3.2.4 and the "Decisions locked" table in §3.2.5 below are **superseded**: the social data
> source for **Instagram + Facebook** is now **Apify** (apify.com), using its **free-tier credits**,
> behind the same swappable provider-adapter. **Bright Data is no longer used.** **YouTube is removed
> from scope entirely** (no Data API, no backend). There is **no paid smoke test and no provisioning
> gate** — Apify is self-serve on the free tier. The discussion of Bright Data / YouTube / Business
> Discovery below is kept for history.

This is *the* defining decision for Workstream B. The Technical Assessment framed it
as a binary "OAuth self-audit **or** paid scraper." **The 2026 reality is richer:
there are three access mechanisms, and the right answer for BLC is a hybrid of them.**
(Research current as of June 2026 — see Sources at the end of this doc.)

#### 3.2.1 The three access mechanisms

1. **Official open APIs (free, compliant, no target cooperation).**
   - **YouTube Data API v3** — genuinely open. 10,000 free quota units/day;
     `channels.list` (stats: subs, views, video count) costs **1 unit**, a search
     costs 100. An entire channel audit is a handful of units, so it is effectively
     free at internal volume. **This is the safe first platform.**
   - **Instagram Business Discovery** *(the path the original assessment missed)* —
     the Instagram Graph API (Facebook Login) `business_discovery` endpoint returns
     **public** data about *other* Business/Creator accounts **without the target's
     OAuth**: follower count, media count, bio, website, verified status, and recent
     media with `like_count`, `comments_count`, `view_count`. That is enough to
     compute follower size, posting cadence, and an engagement-rate estimate. Only
     **BLC's** app needs a Facebook Login app + one IG professional account; the
     prospect does nothing. Limits: target must be a **professional** (Business/Creator)
     account, age-gated accounts are excluded, and fields are limited (no audience
     demographics, no story data). Free.

2. **Owner-authorized OAuth (free, compliant, *requires the target to log in*).**
   The prospect connects their own IG/FB/LinkedIn via OAuth, granting full
   first-party analytics (audience demographics, reach, impressions, saves).
   **Limitation for BLC:** this only works for accounts that *choose* to authenticate
   — i.e. BLC's **existing/onboarding clients**, not cold prospects or competitors.

3. **Third-party providers (paid, broad, no target cooperation).**
   Apify, Bright Data, EnsembleData, ScrapeCreators, etc. cover IG, Facebook,
   LinkedIn, TikTok, X, and more behind one interface. They handle proxies/CAPTCHA
   and return public profile + post + engagement data for **any** public account,
   including competitors. Cost is per-result and modest at internal volume; they
   break when platforms change and carry the legal/ToS considerations in §3.2.3.

#### 3.2.2 Per-platform reality (2026)

> **Update (2026-06-23, round 2):** the "Verdict" column below is **superseded** — IG/FB use
> **Apify** (free tier), and **YouTube is dropped** (no longer in scope). Table kept for history.

| Platform | Open API? | Owner OAuth | Third-party scraper | Verdict for BLC |
|---|---|---|---|---|
| ~~**YouTube**~~ | ✅ Data API v3 (free) | n/a | rarely needed | ~~**Build first.** Free, reliable, zero fork risk.~~ **DROPPED (round 2) — out of scope.** |
| **Instagram** | ⚠️ Business Discovery (public metrics for *business* accounts, no target OAuth) | ✅ full analytics for own clients | ✅ for personal accounts / deeper post data | **Apify** (free tier) — covers any public account. *(was Bright Data; round 2.)* (Business Discovery dropped: account approvals declined.) |
| **Facebook** | ⚠️ Page public data is thin; rich Page Insights need owner OAuth | ✅ for own clients | ✅ public page posts/engagement | **Apify** (free tier). *(was Bright Data; round 2.)* Lower priority than IG for this niche. |
| **LinkedIn** | ❌ Partner Program only (incorporated cos, opaque pricing, often declined) | limited | ⚠️ works but **highest enforcement risk** — LinkedIn ToS bans scraping and litigates (Proxycurl shut down mid-2025) | **Defer / lowest priority.** Least relevant to residential builders/remodelers anyway. |
| **TikTok** | ❌ no free public-data API (Business API = ads only; Research API gated) | n/a | ⚠️ works but hardest to maintain (most aggressive anti-bot) | **Optional v2.1.** Rising for home-services video; add only if BLC wants it. |

> **Niche note.** BLC = *Builder Lead Converter*; its prospects are builders and
> remodelers. Their lead-gen social presence is overwhelmingly **Instagram**
> (before/after photos, Reels), **Facebook** (local pages, reviews, community
> groups), and ~~**YouTube** (project walkthroughs)~~. LinkedIn and TikTok are secondary.
> ~~Prioritize IG + FB + YouTube;~~ **Prioritize IG + FB** (round 2: YouTube dropped); treat
> LinkedIn/TikTok as optional later additions.

#### 3.2.3 Legal posture — better than the original assessment implied
The Technical Assessment flagged "legal exposure" for scraping. The 2026 U.S. case
law is **more favorable** than that framing:

- **Meta v. Bright Data (2024):** a federal judge held that **logged-out scraping of
  *public* Facebook/Instagram data does not breach Meta's ToS** (you are not a "user"
  when logged off), and Meta then **dropped** the suit.
- **hiQ v. LinkedIn:** scraping public pages while logged out is not a CFAA violation.

So scraping **public** social data while logged out is, in the U.S., largely
defensible. The live risks are narrower and manageable: **(a)** LinkedIn specifically
still enforces its contract aggressively (avoid scraping LinkedIn); **(b)** GDPR/UK
DPA apply if BLC stores EU personal data; **(c)** the AI-training frontier is
unsettled but irrelevant here (BLC audits, it does not train models on the data).
**Mitigation:** scrape public data only, never log into target accounts, store the
minimum needed for the audit with a retention policy (Workstream A), and get a short
written legal sign-off before turning on a paid provider.

#### 3.2.4 Recommendation — DECIDED: Bright Data scraping only

> **Update (2026-06-23, round 2): provider is now APIFY (free tier); YouTube dropped.** Read this
> subsection as: scraping only via **Apify** for **Instagram + Facebook**, behind one swappable
> adapter; **no YouTube**, no OAuth, no IG Business Discovery, no paid smoke test/provisioning gate.
> The Bright-Data / YouTube text below is retained for history.

**Scraping only (Bright Data) — no OAuth, no Facebook app / account approvals.**
Decided by BLC (Darius, 2026-06-05): *"we can just scrape the data."* Bright Data is
the social data source for Instagram and Facebook. It works on *any* public account
(business **or** personal), returns consistent deep data, and does **not** depend on
Meta's app review or its habit of tightening official endpoints (the Basic Display API
died Dec 2024). YouTube uses its free official API (an API key only — no app review).

Build one provider-adapter; ship backends in this order:

1. **YouTube → YouTube Data API.** The one official API that is genuinely open, free,
   and stable — just needs an API key, no app review. Build first to prove the pipeline
   end-to-end. (Bright Data can also do YouTube if BLC later wants a single provider.)
2. **Instagram / Facebook / (TikTok later) → Bright Data.** The engine for everything
   Meta: business *and* personal accounts, competitors, and post-level depth, behind one
   swappable adapter. $0.75/1K, pay-per-success, ~98% IG success rate. (Apify was the
   evaluated alternative; not selected — §3.2.5.)

**Dropped (BLC decision — no account approvals, no opt-in dependence):**

- **Instagram Business Discovery** — *not used.* It would need BLC to stand up a
  Facebook Login app + an IG professional account (an approval Darius explicitly
  rejected), and Bright Data already covers Instagram, so it adds setup for ~no benefit.
- **Owner-authorized OAuth** — *not used.* It only audits accounts whose owner logs in
  (existing clients), which defeats auditing the prospects/competitors this tool targets.

This keeps the one external dependency (Bright Data) behind a single swappable adapter
and keeps cost and legal risk low.

> **Bottom line on "OAuth or scrapers?"** For an *internal prospecting/sales* tool,
> **Bright Data scraping** — full stop. OAuth only audits people who opt in, which
> defeats the point of auditing a prospect you're trying to win, and it (plus IG
> Business Discovery) needs account approvals BLC chose to skip.

#### 3.2.5 Decisions locked (June 2026)

> **Update (2026-06-23, round 2):** the table below is **superseded** by the round-2 choices —
> provider is **Apify (free tier)** for **IG/FB**, **YouTube is dropped**, and there is **no paid
> smoke test / provisioning gate**. The current table is immediately after; the original is kept
> struck for history.

| Decision | Choice (round 2 — current) |
|---|---|
| Access strategy | **Apify scraping (free tier)** for **IG/FB**. **YouTube dropped** (out of scope). **No OAuth. No IG Business Discovery.** |
| Scraper provider | **Apify** (apify.com) — free-tier credits; self-serve; runs IG/FB actors behind the same swappable adapter |
| Monthly budget | **Free tier** — internal/low volume stays within Apify's included free credits (§10). No paid commitment, no smoke-test spend. |
| TikTok | **Deferred** — optional later add via **Apify** (same adapter). |
| LinkedIn | **Excluded** from scraping (enforcement risk). |
| Legal sign-off | **✅ Given** — BLC (Darius) approved public-data, logged-out scraping on 2026-06-05 (public-data-only, no logins, minimal retention, no LinkedIn). Applies to Apify the same way. |

> ~~Original (June 2026) — superseded by round 2:~~
> | Decision | Choice |
> |---|---|
> | ~~Access strategy~~ | ~~**Bright Data scraping only** for IG/FB; YouTube uses its free official API. **No OAuth. No IG Business Discovery** (both need account approvals BLC rejected).~~ |
> | ~~Scraper provider~~ | ~~**Bright Data** ($0.75/1K, pay-per-success, no monthly commitment)~~ |
> | ~~Monthly budget~~ | ~~**Pay-as-you-go, no hard cap needed** — internal/low volume keeps this to a few dollars/month (§10). Optionally set a small Bright Data spend alert (e.g. $25/mo) as a safety net.~~ |
> | ~~TikTok~~ | ~~**Deferred** — not required now; revisit later (Bright Data already supports it behind the same adapter, so adding it later is small).~~ |
> | ~~Legal sign-off~~ | ~~**✅ Given** — BLC (Darius) approved public-data, logged-out scraping via Bright Data on 2026-06-05 (public-data-only, no logins, minimal retention, no LinkedIn).~~ |

### 3.3 Other decisions

> **Update (2026-06-23): Social audit is STANDALONE — DECIDED.** Earlier framing across this
> doc assumed social handles are pasted alongside the website URL into one combined report with the
> Social Score folded into the website Lead-Gen Readiness composite. That is **superseded**: the
> Social audit is now a **separate, fully-independent product** (own UI tab, own handle inputs, no
> website URL, own separate PDF, own standalone Social Score). It does **not** fold into the website
> composite and there is **no combined website+social number**. The website audit's scoring is
> **unchanged**. See the top-of-doc banner for the recommended `audit_type` shape.

- **Competitor benchmarking** (scope §4): the safe presentation scaffold was pulled forward
  (feature flag, provider registry, normalized facts, report rendering, graceful no-op). Live
  SEMrush/Ahrefs/Similarweb clients remain v3 because there is no free reliable source and a
  recurring subscription must be approved first.
- **Report format** beyond PDF: dashboard, shareable link, white-label (§2.7).
- **Expected volume** (audits/month): sizes DB, workers, caching (§2.3).
- **LLM provider for social commentary:** reuse the existing pipeline (Phase 1 uses
  OpenAI/ChatGPT with a local fallback). The Technical Assessment proposed Claude
  Sonnet 4.6 (primary) + Haiku 4.5 (bulk classification) — either works; the
  extract→score→commentate→validate contract is provider-agnostic.

---

## 4. Workstream A — Productionization & Platform (Epic P2-E2, do first)

Take the proven website tool from "internal/local" to "hosted and safe for more
users." Closes the items in [`docs/06_KNOWN_LIMITATIONS.md`](06_KNOWN_LIMITATIONS.md).

### 4.1 In scope
- **Lightweight authentication** *(internal-tool scope — §3.1)* — a single login for
  the BLC team (Clerk/Supabase Auth, or Google Workspace SSO) protecting every audit
  endpoint (today there is none — anyone who can reach the API can run audits). **No
  public sign-up, billing, or per-user isolation.**
- **Multi-tenancy — OUT for Phase 2** (§3.1 locked "internal tool"). One shared org,
  shared audit history. Revisit only if BLC later productizes this as a SaaS.
- **Managed hosting** — managed Postgres (Supabase/Neon or AWS RDS), backend + workers
  on Railway/Render (or AWS ECS/Fargate), frontend on Vercel. TLS terminated at the edge.
- ~~**Object storage** — there is **no storage abstraction today**: `pdf_renderer.py`
  writes PDFs directly to `local_report_storage_dir`. **Introduce** a storage interface
  first, then add an S3-compatible backend; serve reports via signed URLs.~~
  **REMOVED (2026-06-23 round 2):** no AWS/S3 — **local filesystem storage on the VM** is the
  intended design for this internal ~5–10-user tool. Retention is handled by P2-10 (below), not S3.
- **Complete SSRF interception** — request-level blocking of redirects/sub-resources
  that resolve to internal IPs mid-crawl (Phase 1 only validates the start URL and
  blocks private hosts by default). **✅ DONE (2026-06-23):** the crawler now validates every
  sub-resource/redirect host against the private/loopback/metadata-IP block-list during rendering
  (`crawler.py`: `_host_blocked_for_subrequest` + a Playwright route guard per context; setting
  `crawler_intercept_requests`, auto-disabled when `crawler_allow_private_hosts` is true; unit-tested).
- **Secrets management** — move secrets out of `.env` into the platform's secret store.
- **Observability & resilience** — error tracking (Sentry), basic metrics/alerting,
  database backups, Celery retry/dead-letter handling. **✅ Sentry DONE (2026-06-23):** optional
  env-gated error reporting (`apps/shared/observability.py` + `SENTRY_DSN`; no-op when unset).
  Metrics/alerts/backups remain **VM-ops tasks (not code)** — lighter scope for a 5–10-user tool.
- **Data retention** — cleanup policy for old audit rows, PDFs, and screenshots. **✅ DONE
  (2026-06-23):** `apps/shared/retention.py` + `scripts/cleanup_storage.py` +
  `storage_retention_days` setting delete reports/screenshots/tool-exports older than N days; run
  from cron (no in-app scheduler); unit-tested.
- **Web dashboard & product surface** — an interactive dashboard view (reuses the
  existing report payload), improved audit history, re-run, shareable links, and
  white-label branding for prospect-facing reports.

### 4.2 Tickets (Epic P2-E2)
- P2-6 Add lightweight team authentication to API + UI (single internal org)
- *(A tenant/org data model & isolation ticket was considered and **dropped** — internal tool, §3.1)*
- ~~P2-7 Introduce a storage interface + S3 report/screenshot backend (none exists yet)~~
  **— REMOVED/descoped (2026-06-23 round 2):** no AWS/S3; local filesystem storage on the VM is the
  intended design. Retention handled by P2-10.
- ~~P2-8 Complete request-level SSRF interception~~ **— ✅ DONE (2026-06-23)** (`crawler.py`
  sub-resource/redirect guard + `crawler_intercept_requests`; unit-tested).
- P2-9 Managed hosting + CI/CD deploy (DB, workers, API, frontend, TLS)
- P2-10 Observability: Sentry, metrics, alerts, backups, retention — **✅ retention DONE** (`retention.py`
  + `cleanup_storage.py` + `storage_retention_days`, cron-run) and **✅ Sentry DONE** (`observability.py`
  + `SENTRY_DSN`, opt-in). **Metrics/alerts/backups remain VM-ops (not code).**
- P2-11 Web dashboard view + audit history/re-run/share + white-label

---

## 5. Workstream B — Social Media Audit (Epic P2-E4, the marquee feature)

> **✅ SHIPPED (2026-06-23) — this workstream is BUILT, not just planned.** The standalone social
> audit is implemented end-to-end (IG+FB via Apify, deterministic rule-derived findings, its own
> `social.yaml` Social Score, its own report/PDF, its own UI tab) and tested. The subsections below
> are kept as the design record; see the top-of-doc **SHIPPED (2026-06-23)** banner for the exact
> as-built code touch-points, and §5.4 for per-ticket status.

Add the third audit type from the original scope. Architecturally it is a **clone of
the website pipeline** — the same four-step pattern (Technical Assessment §3.2) — so
most of the framework is reused.

### 5.1 What the social audit evaluates (original scope §3.3)
For each connected platform (**Instagram, Facebook** — round 2: YouTube dropped; LinkedIn excluded; TikTok optional later):

- **Profile / bio optimization** & CTA clarity
- **Posting activity** — cadence and consistency
- **Engagement** — engagement rate and trends
- **Content type & positioning** — educational / authority / promotional mix
- **Funnel integration** — link-in-bio, landing pages, lead magnets
- **Messaging alignment** with the website
- **Community interaction** strategy
- **Lead-capture mechanisms** — bio links, forms, DM automation

**Outputs (scope §3.3):** a **Social Media Score**, profile-optimization
recommendations, content-strategy improvements, engagement-growth tactics, and
lead-capture improvements — split into Quick Wins / Mid-Term / Long-Term like the
website audit.

### 5.2 Pipeline (reuses Phase 1 pattern)

> **Update (2026-06-23): standalone social branch.** The social audit runs as its **own audit
> type** (`audit_type="social"`), not as extra steps inside the website audit. `run_collection_audit`
> **branches on `audit_type`**, and the social branch is **leaner**: it **skips crawl / PSI /
> external-SEO** entirely and runs only collect → extract → score (`social.yaml`) → commentate →
> validate → render a **separate** social report. Input is **social handles only — no website URL**.

1. **Input** — accept social handles/URLs as the **sole** input for a social audit (no website URL required).
2. **Collect** — per-platform collectors behind one provider-adapter (§3.2), **scraping only**:
   - **Instagram / Facebook** → **Apify** (free tier) actors. **TikTok** is an optional later add via Apify. **LinkedIn excluded** (enforcement risk, §3.2.2).
   - **No YouTube** — dropped from scope (round 2, 2026-06-23). **No OAuth and no IG Business Discovery** — dropped per the BLC decision (both need account approvals; §3.2.4/§3.2.5).
   - *(Superseded 2026-06-23 round 2 — was: "YouTube → YouTube Data API … ; Instagram/Facebook/(TikTok later) → Bright Data.")*
3. **Extract** — deterministic parsers normalize each platform's data into a common social-facts schema.
4. **Score** — a new **YAML social rubric** (same engine as `rubrics/`) produces a deterministic Social Score; weights tunable without code.
5. **Commentate** — the existing commentary pipeline writes social findings + tiered recommendations from facts + scores.
6. **Validate** — the existing grounding validator (extended to social facts) strips unsupported numeric claims.
7. **Compose** — render a **SEPARATE Social report** (its own report payload + PDF/dashboard) with a **standalone Social Score**. **No fold-in:** the Social Score does **not** roll into the website Lead-Gen Readiness composite, and there is no combined website+social number. *(Superseded 2026-06-23 — was: "extend the report payload + PDF/dashboard with a Social section; fold the Social Score into the Lead-Gen Readiness score.")*

### 5.3 Data model & code touch-points (verified against the repo)

> **Update (2026-06-23): standalone — `audit_type` discriminator, not a composite change.** The
> two bullets below about input fields and the composite code change are **revised** to reflect the
> standalone decision: add an **`audit_type` discriminator** instead of merging social into the
> website job, and **do not touch the website composite**.

- **Input / discriminator:** add an **`audit_type`** column (`"website" | "social"`, default
  `"website"`) to `audit_jobs`, make **`url` nullable**, and add a **`social_handles` JSONB**
  column (plus the matching fields on `AuditCreateRequest` in `apps/api/schemas/audits.py`).
  Validate: `url` required for website audits, **≥1 handle** for social audits.
  `run_collection_audit` **branches on `audit_type`** (the social branch skips crawl/PSI/external-SEO).
- **Storage:** persist normalized social facts + the standalone social score by extending
  `audit_results` (e.g. reuse the JSON blobs for the social branch) or adding `social_*` tables.
- **New worker stages** (matching the existing `extractor_seo.py` / `extractor_uxui.py`
  naming): a social **collector** module (alongside `crawler.py` / `psi_client.py`) and
  **`extractor_social.py`**. Scoring is rubric-driven by the single `scoring.py`, so
  there is **no** per-domain score module to add.
- ~~**Composite score is a code change, not just YAML.**~~ **SUPERSEDED (2026-06-23):** the
  **website composite is NOT changed.** Do **not** add `social` to `scoring.py`'s
  `CompositeRubric.weights` `Literal["seo", "uxui"]`, do **not** touch `validate_weights`'s expected
  set, and do **not** rebalance `rubrics/composite.yaml` — it stays `{seo:0.45, uxui:0.55}`.
  Instead, add **`rubrics/social.yaml`** and run it through the **same scoring engine** to produce a
  **standalone Social Score** (its own category set, summing to 1.0 on its own). The website
  `compose_lead_generation_score` is left untouched and there is no social fold-in.
- **Separate Social report template:** add a standalone social report template (its own Jinja2
  template under `templates/`) rendered via the existing WeasyPrint/branding stack — not a new
  section in the website report.
- **Provider adapter** package for social data sources (one interface, swappable backend).

### 5.4 Tickets (Epic P2-E4)

> **✅ All P2-E4 tickets below are DONE (2026-06-23)** — the social audit is built, tested, and
> runnable from the browser. Per-ticket as-built notes are inline.

- P2-19 Social data provider adapter (interface + **Apify IG/FB + YouTube** backends) *(updated
  through 2026-07-02)* — **✅ DONE:** `apps/worker/stages/social/providers.py` registry dispatches
  to Apify Instagram, Facebook Pages, Facebook Posts, and YouTube Data API providers.
- P2-20 **Apify backend** for IG/FB (free tier) — any public account, post-level depth (§3.2.5). *(Updated 2026-06-23 round 2; was: "Bright Data backend for IG/FB." May fold into P2-19.)* **No P2-3 gate** — Apify is self-serve on the free tier (the paid smoke-test gate is removed). — **✅ DONE** (folded into P2-19's provider; live IG+FB runs verified).
- ~~P2-21 Instagram Business Discovery shortcut~~ — **DROPPED** (BLC: no account approvals; Bright Data covers IG). LinkedIn excluded, TikTok deferred.
- P2-22 Social fact extractors + common schema + fixtures — **✅ DONE:**
  `apps/worker/stages/social/extractor.py` normalizes Instagram/Facebook/YouTube into
  `social.*` facts + `tests/unit/test_extractor_social.py`.
- P2-23 `rubrics/social.yaml` → **standalone Social Score** via the shared scoring engine. **NO
  website-composite change** — do not touch `scoring.py`'s composite `Literal`/weights or
  `composite.yaml`. *(Updated 2026-06-23; was: "extend `scoring.py` (composite Literal/weights) +
  Lead-Gen update.")* — **✅ DONE:** `rubrics/social.yaml` (`phase2-social-v3`, `category:
  social`) scored by `scoring.score_social_audit()`; website `CompositeRubric.weights` stays
  `{seo, uxui}` (untouched).
- P2-24 Social commentary prompts + grounding-validator extension — **✅ DONE.** Findings/recommendations are deterministic from the rubric rule metadata (`finding_label`/`remediation`/`impact`/`tier`) by default. **Update 2026-06-24:** an optional LLM polish layer was added — `commentary.generate_social_commentary` (prompts in `prompts/commentary_social_*.md`) rephrases the rule-derived findings via GPT-4o when `OPENAI_API_KEY` is set, with a grounding backstop and the deterministic baseline as the no-key fallback. Polish only — scores/findings are unchanged.
- P2-25 Social report surfaces — **✅ DONE:** the standalone `templates/social_report.html` /
  `render_social_pdf` path remains for social-only jobs; combined website+social reports now
  append the Social Media Audit and Overall Lead-Gen Readiness sections to the main PDF/DOCX/web
  report. The separate Social Audit UI tab was removed; operators enter social handles on the
  Website Audit page.

---

## 6. Workstream C — Enrichment (Epic P2-E5, later / v3)

Defer until the core (A + B) is validated. These materially change the architecture
(anonymous public-data audits → user-authorized data sources), so they are their own
phase, not bundled (Technical Assessment "Future phase").

### 6.1 Competitor benchmarking (scope §4)
Benchmark SEO/UX/Social scores against competitors or industry norms via SEMrush,
Ahrefs, or Similarweb APIs (higher tiers; recurring cost — no free reliable source).

> **Update (2026-07-02):** the benchmarking scaffold is now built: `benchmark_enabled`,
> `benchmark_provider`, and `benchmark_api_key` gate a provider registry; normalized facts are
> stored in `score_breakdown["benchmark"]`; and the PDF/DOCX/web report can render a Competitor
> Benchmarking section. All paid vendor clients are still no-op stubs, so production incurs no
> benchmarking cost and reports stay unchanged until a real provider returns baselines.

### 6.2 Analytics integrations — "Future Data Collection Expansion" (scope)
User-authorized data sources for deeper UX/SEO insight:
- **Google Analytics (GA4)** — user behavior flow, bounce/exit, conversion rates, funnel drop-offs.
- **Google Search Console** — keyword performance, technical SEO diagnostics, indexing.
- **Microsoft Clarity** — heatmaps & session-recording references.
- **SEMrush** — keyword/traffic data.

### 6.3 Tickets (Epic P2-E5, v3)
- P2-26 Competitor benchmarking scaffold + live provider client
- P2-27 GA4 + Search Console OAuth integrations & insight extraction
- P2-28 Microsoft Clarity + SEMrush integrations

---

## 6B. Workstream D — Deepen The Website Audit (Epic P2-E3, high ROI, low risk)

The website audit already works; this workstream makes it **visibly better and more
modern** without touching the architecture. Every item below is **new
extractor signals + new YAML rubric rules** — it reuses the existing crawler, rubric
engine (`scoring.py`), commentary, grounding validator, and report. That is why it is
the cheapest way to increase the product's quality and is recommended **in the core**,
in parallel with Workstream A.

These signals also map straight onto the original scope's SEO/UX outputs (keyword
gaps, technical fixes, trust signals, funnel friction) that Phase 1 only partially
covered, and onto the scope's stated goal: *attract qualified traffic → convert it to
leads.*

### 6B.1 New signals to add (2026-relevant)
- **Structured data / Schema (JSON-LD)** — detect and validate `LocalBusiness`,
  `Organization`, `Service`, `Review`/`AggregateRating`, `FAQPage`, `BreadcrumbList`.
  In 2026 this is the #1 lever for **AI-citation visibility** (Google AI Overviews,
  ChatGPT Search, Perplexity) *and* for rich results. Currently **not audited**;
  high impact for local builders.
- **AI / Answer-Engine readiness (AEO/GEO)** — `llms.txt` presence, AI-crawler access
  in `robots.txt` (GPTBot, ClaudeBot, PerplexityBot, Google-Extended), content
  structured for answer extraction (clear headings, FAQ blocks, entity clarity). New
  emerging dimension; cheap to check, increasingly decisive for discovery.
- **Real Core Web Vitals (field data)** — pull **CrUX** field data (LCP, **INP**,
  CLS) alongside the existing lab PSI numbers. Field CWV is the actual ranking signal;
  INP replaced FID in 2024. (PSI already returns some of this — surface and score it.)
- **Accessibility** — run **axe-core** (via the existing Playwright render) for
  WCAG issues: image alt text, form labels, color contrast, heading order, landmark
  structure. Accessibility doubles as conversion + legal-risk signal for SMB sites.
- **Crawlability & indexability** — `robots.txt` / `noindex` / canonical correctness,
  XML sitemap presence and validity, redirect chains. These are the **most common**
  real-world SEO failures and are currently only partially checked.
- **Link health** — broken internal/outbound links and orphan pages within the
  crawled set (reuses crawl output; no new fetching budget needed).
- **Local SEO** *(high value for this niche)* — NAP (name/address/phone) consistency,
  presence of a Google Business Profile link, service-area / location pages,
  embedded map, local schema. Builders/remodelers live and die by local search.
- **Trust & conversion signals (UX)** — testimonials/reviews presence, trust badges,
  contact/quote-request form depth and friction, phone/click-to-call above the fold,
  social-proof density. Sharpens the existing UX/UI lead-capture scoring.
- **Security hygiene (light)** — HTTPS enforcement, HSTS, basic security headers,
  mixed-content. Low effort, professional polish in the report.

### 6B.2 How it lands in the codebase
- Extend `extractor_seo.py` / `extractor_uxui.py` (or add `extractor_technical.py`)
  to emit the new facts into the existing `{seo, uxui, psi}` fact bundle.
- Add the new rules to `rubrics/seo.yaml` / `rubrics/uxui.yaml` (and optionally a new
  `rubrics/technical.yaml` if the SEO rubric gets large) — **bump the rubric version**
  per the Rubric Guide so historical scores stay interpretable.
- **Optional new scored dimension:** add an **"AI Visibility / AEO"** sub-score. If it
  becomes its own category it follows the *same* composite-weights code change
  described for Social in §5.3 (extend the `Literal[...]` and rebalance
  `composite.yaml`). If it just adds rules to the SEO category, it is **YAML-only**.
- Re-run the calibration gate (`make qa` strong vs weak site) after tuning, exactly as
  in the Rubric Guide.

### 6B.3 Tickets (Epic P2-E3)
- P2-12 Structured-data (JSON-LD) extractor + schema rubric rules
- P2-13 AEO/GEO readiness signals (`llms.txt`, AI-crawler access, answer structure)
- P2-14 CrUX field Core Web Vitals (LCP/INP/CLS) surfaced + scored
- P2-15 axe-core accessibility pass + rubric rules
- P2-16 Crawlability/indexability + link-health + redirect checks
- P2-17 Local-SEO signals (NAP, GBP, location pages, local schema)
- P2-18 Trust/conversion UX signals + security-hygiene checks

---

## 7. Architecture — How Phase 2 Extends Phase 1

Phase 2 keeps the Phase 1 spine and adds collectors/rubrics/sections; it does not
rewrite the pipeline.

> **Update (2026-06-23, round 2):** in the diagram below, read **"Bright Data (IG/FB) · YouTube API"**
> as **"Apify (IG/FB)"** (YouTube dropped), and **"S3 report storage"** as **local-filesystem report
> storage on the VM** (S3 descoped — P2-7 removed).

```text
Operator UI (Next.js, + team auth in Phase 2)
        |
        v
FastAPI API (+ team auth)  ──►  Celery workers + Redis
        |                              |
        |     +------------------------+-----------+----------------------+
        |     |                        |           |                      |
        v  Website (DEEPER, D)      Social (NEW, B)                  Enrichment (v3, C)
 PostgreSQL  crawler/PSI/CrUX     Bright Data (IG/FB) ·               SEMrush/Ahrefs,
 (managed)   SEO/UX/schema/a11y   YouTube API (official)              GA4/GSC/Clarity
        |        \                   /        \                          /
        |         v                 v          v                        v
        |   deterministic scoring (YAML rubrics: seo, uxui, social, [aeo?], composite)
        |                                   |
        |              grounded commentary (existing pipeline) + validation
        v                                   |
   S3 report storage  ◄──────────  report payload → PDF + dashboard
```

New vs Phase 1: team auth (no multi-tenancy), ~~S3 storage~~ **local-filesystem storage on the VM
(S3 descoped — round 2)**, **deeper website signals
(schema, AEO, CrUX, a11y, local SEO)**, social collectors (**Apify** for IG/FB; YouTube dropped —
round 2) + `social.yaml` rubric →
**standalone Social Score in a separate Social report** (not folded into the website composite;
the website composite is unchanged — *updated 2026-06-23*), a dashboard view, and (v3) enrichment
sources.

---

## 8. Tech Stack Additions

| Need | Choice | Notes |
|---|---|---|
| Auth (internal) | Clerk / Supabase Auth, or Google Workspace SSO | Single team login; no multi-tenancy (§3.1) |
| Managed DB | Supabase / Neon (or AWS RDS) | JSONB fits audit results; free tier covers internal volume |
| ~~Object storage~~ | ~~S3 / S3-compatible~~ **REMOVED (round 2)** | Local filesystem on the VM; retention via P2-10 (no S3) |
| Hosting | Vercel (UI) + Railway/Render (API+workers), or AWS ECS/Fargate | Low ops overhead |
| ~~YouTube data~~ | ~~YouTube Data API v3~~ **DROPPED (round 2)** | YouTube out of scope |
| Social data (IG/FB) | **Apify** ✅ selected (free tier) *(was Bright Data; round 2)* | The engine for IG/FB/(TikTok later) — any public account, deep data (§3.2.4) |
| ~~IG Business Discovery~~ | **Dropped** | Needs a Facebook app + IG account approval — BLC declined; Bright Data covers IG (§3.2.4) |
| ~~Owner OAuth (social)~~ | **Dropped** | Only audits opt-in accounts; defeats the prospecting use case (§3.2.4) |
| Structured data | JSON-LD parse + schema validation | Workstream D; no external dep |
| Accessibility | **axe-core** via existing Playwright | Workstream D; reuses the crawler's browser |
| Field CWV | **CrUX API** (LCP/INP/CLS) | Workstream D; free, real-world ranking signal |
| Error tracking | Sentry | App now has meaningful flows |
| Live benchmarking providers (v3) | SEMrush / Ahrefs / Similarweb API | Recurring cost |
| Analytics (v3) | GA4 Data API, Search Console API, Clarity, SEMrush | User OAuth |
| LLM commentary | Existing OpenAI pipeline (or Claude Sonnet 4.6 + Haiku 4.5 per Technical Assessment) | Provider-agnostic contract |

---

## 9. Timeline

Full-time solo; part-time scales proportionally. §3.1 (internal tool) is already
decided, so discovery is shorter and Track A is lighter (no multi-tenancy). Tracks A,
B and D can overlap once the social-data path (§3.2) is confirmed.

| Phase / Track | Focus | Duration |
|---|---|---|
| **Phase 2.0** | Discovery & scope lock — social path locked (**Apify free tier** for IG/FB *(was Bright Data; round 2)*; legal ✅ given), create a **free Apify account + API token**, draft `social.yaml`, confirm volume. **No paid smoke test (P2-3 removed).** | **2–3 days** |
| **Track A** | Productionization & platform — *internal scope* (team auth, hosting, ~~S3~~ **local storage + retention (S3 removed; SSRF ✅ done)**, monitoring, dashboard/history) | **2–3 weeks** (no multi-tenancy) |
| **Track D** | Deepen website audit (schema, AEO, CrUX, a11y, local SEO, link health) — runs in parallel with A | **1–2 weeks** |
| **Track B** | Social media audit — backend standalone score/report plus current combined website+social flow from the Website Audit page (`social.yaml` v3, IG/FB/YouTube, auto-discovery) | **3–4 weeks** (swings on §3.2) |
| **Track C** | Enrichment — live benchmarking providers + analytics integrations | **4–5 weeks** (v3) |

### 9.1 Week-by-week (core: A + D + B)

> **Update (2026-06-23, round 2):** Wk 0 — **Apify** (free tier) for IG/FB, **no YouTube**, **no paid
> smoke test** (P2-3 removed). Wk 2 — **S3 removed** (local storage); **SSRF interception ✅ already
> done**; Sentry + retention ✅ done. Wk 3/4 — **B starts with the Apify backend (IG/FB)**, not a
> YouTube backend / Bright Data.

- **Wk 0 (2–3 days):** Phase 2.0 — social path is **locked** (**Apify free tier** for IG/FB; no YouTube; no OAuth/Business Discovery) and **legal is ✅ given**; create a **free Apify account + API token**; draft `social.yaml`. *(Superseded round 2 — was: "YouTube API + Bright Data … run a small paid Bright Data smoke test.")*
- **Wk 1:** A — team auth on API+UI; managed DB + hosting skeleton; CI/CD deploy. **D in parallel:** structured-data + crawlability/link-health signals + rubric rules.
- **Wk 2:** A — ~~S3 storage; complete SSRF interception; Sentry/backups/retention~~ **local storage + retention (S3 removed; SSRF ✅ done; Sentry + retention ✅ done — backups remain VM-ops)**. **D:** CrUX + axe-core accessibility + local-SEO signals; re-calibrate rubric.
- **Wk 3:** A — dashboard view + audit history/re-run/share. **B starts:** provider adapter + **Apify backend (IG/FB)** end-to-end. *(Superseded round 2 — was: "+ YouTube backend.")*
- **Wk 4:** B — **Apify backend** for IG/FB (per §3.2); social extractors + fixtures. *(Superseded round 2 — was: "Bright Data backend.")*
- **Wk 5:** B — `social.yaml` + **standalone Social Score** (no website-composite change); social commentary + grounding extension.
- **Wk 6:** B — **separate Social report** (own PDF/dashboard) with the **standalone Social Score**; QA on real accounts; calibration. *(Updated 2026-06-23 — no fold into the website Lead-Gen score.)*

- **Phase 2 core (A + D + B): ~6–8 weeks** after ~2–3 days discovery (D overlaps A, so it adds little wall-clock).
- **With enrichment (A + B + C + D): ~10–13 weeks.** (Cross-check: the Technical Assessment put the analytics "future phase" at **3–4 weeks** on its own.)

---

## 10. Recurring Costs To Budget (2026 figures)

At **internal volume** (estimate ~50–300 audits/month) almost everything sits in free
tiers; the social scraper now runs on **Apify's free tier** (round 2), so it adds **~$0** at this
volume.

> **Update (2026-06-23, round 2):** social provider = **Apify (free tier)**; **YouTube dropped**;
> **Bright Data no longer used**. The YouTube/Bright-Data rows below are superseded.

| Item | 2026 cost | Notes |
|---|---|---|
| Social scraper — **Apify** (selected) | **Free tier** | Free-tier credits cover IG/FB at internal volume; TikTok optional later |
| ~~YouTube Data API~~ | ~~**Free**~~ **DROPPED (round 2)** | YouTube out of scope |
| ~~Paid scraper — **Bright Data**~~ | ~~**$0.75 / 1K results**, pay-per-success, no commitment~~ **Not used (round 2)** | ~~covers IG/FB/TikTok~~ — replaced by Apify free tier |
| LLM commentary (OpenAI/Claude) | usage-based | Grounded, short outputs; cents per audit |
| Google PSI / CrUX API | **Free** | Covers internal scale |
| Managed Postgres (Supabase/Neon) | **Free → ~$25/mo** | Free tier covers internal volume |
| Hosting (Vercel + Railway/Render) | **~$0–40/mo** | Hobby/free tiers may suffice internally |
| Auth (Clerk/Supabase) | **Free** | Internal team is well under free limits |
| Error tracking (Sentry) | **Free → ~$26/mo** | Free tier likely fine |
| Live benchmarking API (v3 only) | **$$$** SEMrush/Ahrefs | Defer to Track C |

> **Takeaway:** the recurring cost of the *core* Phase 2 (A + B + D) for internal use
> is roughly **$0–100/month** — dominated by hosting tiers, not data. The scraper,
> the thing the original assessment worried about, is now **$0** on **Apify's free tier** at this
> volume *(round 2)*. Live benchmarking providers (Track C) are the expensive integration; that's
> why they stay v3 even though the no-cost scaffold has shipped.

---

## 11. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| **Social data access** (Technical Assessment §2.1) | Could block IG/FB | **Apify** scraping (free tier, §3.2) works on any public account, behind one swappable adapter *(was Bright Data + YouTube; round 2)* |
| Scraper breakage | Some audits fail | Provider abstraction + monitoring; graceful skip (like missing PSI) so an audit degrades, never aborts |
| Legal / ToS exposure | ToS or privacy issues | Scrape **public** data logged-out only (Meta v. Bright Data, hiQ favor this); **avoid LinkedIn scraping**; minimal retention; short legal sign-off before enabling a paid provider (§3.2.3) |
| Social score miscalibration | BLC distrusts results | Tune `social.yaml` against strong/weak sample accounts (same approach as SEO/UX) |
| LLM hallucination on social facts | Credibility loss | Reuse grounding validator; all numbers come from extracted facts |
| Unpredictable per-audit cost | Cost overrun | Page/handle caps, caching, volume sizing from §3.3; costs are tiny at internal volume (§10) |
| Productionization distracts from features | Velocity drops | Track A + D first (contained, low-risk), then B |

---

## 12. Acceptance Criteria

Phase 2 core (A + D + B) is successful when:

- **A:** A team member must authenticate; reports are stored on the **VM's local filesystem**
  with a **retention policy** *(S3 descoped — round 2)*; the crawler **blocks internal IPs at
  request level (✅ done)**; the system is deployed to managed hosting with TLS and **error tracking
  (Sentry ✅ done)** (backups remain VM-ops); a dashboard shows results and audit history.
- **D:** The website audit produces and scores the new signals (structured data,
  AEO/answer-engine readiness, field Core Web Vitals, accessibility, local SEO, link
  health), the strong/weak calibration gate still holds, and the rubric version is
  bumped.
- **B: ✅ MET (2026-06-23).** Submitting **social handles only** (no website URL) produces a deterministic
  **standalone Social Score** per platform **without requiring the audited account to log in**
  (**Apify** for IG/FB — *round 2; was Bright Data + YouTube*), deterministic rule-derived social
  findings with tiered recommendations (delivered as deterministic, **not** LLM commentary),
  presented in a **SEPARATE Social report** (its own PDF + UI detail view) — reproducible for
  identical inputs. **The website audit's scoring is unchanged**; there is **no** combined
  website+social number. Verified by 119 unit tests + live IG+FB runs. *(Updated 2026-06-23 — dropped
  the "Lead-Gen score that includes social" clause per the standalone decision.)*
- Validated on real builder/remodeler sites **and** their social accounts.

---

## 13. Out Of Scope For Phase 2 Core (v3+)

- Live competitor-benchmarking provider clients and analytics integrations (Workstream C) unless
  explicitly pulled forward in §3.3. The no-cost benchmarking scaffold has already been pulled
  forward and shipped.
- Anything not in the original scope document (e.g. paid ads audits, CRM integrations).

---

## 14. What's Needed To Start

1. **§3.2 locked (§3.2.5):** **Apify scraping (free tier)** for IG/FB *(round 2; was Bright Data +
   YouTube)*; **YouTube dropped**; **no OAuth, no IG Business Discovery**; **free tier** (no paid
   commitment, no smoke test); **TikTok deferred**; **LinkedIn excluded**. **Legal go-ahead ✅ given**
   (Darius, 2026-06-05).
2. **Accounts & keys (lean — scraping only):**
   - A **free Apify account + API token** — the social-data source for IG/FB (self-serve, free
     tier; selected — §3.2.5). *(Was a Bright Data account; round 2.)*
   - *(No YouTube Data API key — YouTube dropped. No Facebook app, no IG professional account, no
     OAuth provider — dropped.)*
   - Hosting/auth accounts are **only needed if/when productionizing** (E2); not required for the
     internal MVP, which runs locally/private like Phase 1. **Storage stays on the VM's local
     filesystem** (no S3 — round 2).
3. A handful of **real social accounts** (strong + weak builder/remodeler examples)
   for calibrating `social.yaml`, mirroring the website test sites.
4. The **P1-30** internal-test feedback to finalize priority order.

---

## 15. Sources (research, June 2026)

Social data access, costs, and legal posture in this plan were checked against current
(2026) sources:

- **Instagram Business Discovery** — [Meta for Developers: Business Discovery](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/business-discovery/) (fields, no-target-OAuth, business-account requirement).
- **Apify pricing & Instagram actors** — [Apify pricing](https://apify.com/pricing), [Instagram Profile Scraper](https://apify.com/apify/instagram-profile-scraper).
- **Bright Data social scrapers** — [Social Media Scraper](https://brightdata.com/products/web-scraper/social-media-scrape), [best Instagram scrapers benchmark](https://brightdata.com/blog/web-data/best-instagram-scrapers).
- **YouTube Data API quota** — [Quota Calculator](https://developers.google.com/youtube/v3/determine_quota_cost), [YouTube API limits 2026 (Phyllo)](https://www.getphyllo.com/post/youtube-api-limits-how-to-calculate-api-usage-cost-and-fix-exceeded-api-quota).
- **LinkedIn API/scraping reality** — [Guide to the LinkedIn API & alternatives (Scrapfly)](https://scrapfly.io/blog/posts/guide-to-linkedin-api-and-alternatives), [Is the LinkedIn API free? 2026 (SociaVault)](https://sociavault.com/blog/linkedin-api-free-2026).
- **TikTok data access 2026** — [Is the TikTok API free? (SociaVault)](https://sociavault.com/blog/tiktok-api-free-2026), [How to scrape TikTok 2026 (Scrapfly)](https://scrapfly.io/blog/posts/how-to-scrape-tiktok-python-json).
- **Legal — public scraping** — [Meta v. Bright Data decision (Farella)](https://www.fbm.com/publications/major-decision-affects-law-of-scraping-and-online-data-collection-meta-platforms-v-bright-data/), [Meta drops Bright Data suit (TechCrunch)](https://techcrunch.com/2024/02/26/meta-drops-lawsuit-against-web-scraping-firm-bright-data-that-sold-millions-of-instagram-records/), [Is web scraping legal in 2026? (Coronium)](https://www.coronium.io/blog/is-web-scraping-legal-2026).
- **Website audit / AEO / CWV signals** — [Technical SEO Audit Checklist 2026 (SEO/AEO/GEO)](https://kodetimize.com/technical-seo-audit-checklist-2026/), [Technical SEO 2026: CWV, Schema, INP](https://itdgrowthlabs.com/resources/Technical_SEO_Checklist_2026_Core_Web_Vitals_Schema_JS_Rendering.php).

> Platform APIs, scraper pricing, and case law move quickly. Re-verify the §3.2 and §10
> specifics at the start of Phase 2.0 discovery before committing budget.

---

## Status reconciliation (2026-06-16)

> **Several Workstream-A productionization items have already shipped — ahead of this
> plan.** This document still describes them as unbuilt Phase-2 work; that framing is now
> partially stale. As built today:
> - **Team auth (Clerk)** is **live** — opt-in via the `CLERK_ISSUER` env var (when unset,
>   the API runs open, which is how local dev / the QA harness / tests run). This delivers
>   the §4.1 "lightweight authentication" item (currently a dev Clerk instance; open
>   sign-up is a known gap, invite-only is a manual operator step).
> - **Managed hosting** is **live** — a single Linode VM behind **Caddy** (automatic
>   Let's Encrypt TLS, single-origin reverse proxy) at `https://ai.builderleadconverter.com`.
> - **CI/CD auto-deploy on merge to `main`** is **live** — `.github/workflows/deploy.yml`
>   SSHes the box and runs `deploy/deploy.sh` (pinned to the merged SHA, sequential image
>   builds, `/health` gate).
>
> See the root **`DEPLOYMENT.md`** for the authoritative as-built deployment description.
> ~~The rest of Workstream A (S3/object storage, complete request-level SSRF interception,
> Sentry/observability, retention) and~~ **all of Workstreams B, C, and D remain unbuilt** —
> the scope, decisions, estimates, and tickets below stand. (The hosting choice that
> shipped is Linode + Caddy, not the Vercel + Railway/Render options floated in §4/§8.)
>
> **Update (2026-06-23, round 2) — more Workstream-A items now resolved:**
> - **P2-7 (S3/object storage) is REMOVED/descoped** — local-filesystem storage on the VM is the
>   intended design for this internal ~5–10-user tool (no S3).
> - **P2-8 (complete request-level SSRF interception) is ✅ DONE** (`crawler.py` sub-resource/redirect
>   guard + `crawler_intercept_requests`; unit-tested).
> - **P2-10 retention ✅ DONE** (`retention.py` + `cleanup_storage.py` + `storage_retention_days`,
>   cron-run) and **Sentry ✅ DONE** (`observability.py` + `SENTRY_DSN`, opt-in). Metrics/alerts/
>   backups remain VM-ops (not code).
> So of Workstream A, only the dashboard/history/share surface (P2-11) and remaining hardening
> (secrets store, Celery retry/DLQ, metrics/alerts/backups as ops) are left; ~~**Workstreams B, C, D
> remain unbuilt** (B now targets **Apify** for IG/FB, YouTube dropped).~~
>
> **Update (2026-06-23) — Workstream B is now ✅ BUILT.** The standalone social audit shipped
> end-to-end (Apify IG+FB, `rubrics/social.yaml` standalone Social Score, deterministic rule-derived
> findings, separate `social_report.html` PDF, `audit_type` discriminator on `audit_jobs`, Alembic
> migration `20260623_0004` (current head `20260625_0005`), and the current Website Audit
> combined-flow UI)
> and is tested (unit suite + live IG/FB runs; YouTube backend covered by fixtures). The website
> audit composite stays `{seo, uxui}`; combined reports add Overall Lead-Gen Readiness separately. See the
> top-of-doc **SHIPPED (2026-06-23)** banner and §5/§5.4 for as-built detail. **Remaining unbuilt:**
> **Workstream D** (deepen the website audit, P2-E3) and **Workstream C** (enrichment, v3). AI
> Insights stays parked; P2-7 (S3) stays removed.
