# Phase 2 Plan — Social Audit, Productionization & Enrichment

**Project:** BLC Website Audit Automation → Social Media & Website Auditing Automation
**Client:** Builder Lead Converter (BLC)
**Document purpose:** A detailed Phase 2 implementation plan: what to build, the decisions to lock first, architecture, week-by-week timeline, costs, risks, and acceptance criteria.
**Status:** Draft for review — the deliverable for Epic **P1-E7 / ticket P1-32** (see [`docs/07_DEPLOYMENT_GUIDE.md`](07_DEPLOYMENT_GUIDE.md) §6).

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

> **Sources.** This plan is grounded in the original scope documents in
> `docx/starting docx/`:
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
4. **Add enrichment** (competitor benchmarking + the analytics integrations) once the
   core is validated — *Workstream C / v3*.

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
| Scoring & **benchmarking against competitors/industry** | Scores ✅ / benchmarking ❌ | Benchmarking → **Workstream C** |
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

| Platform | Open API? | Owner OAuth | Third-party scraper | Verdict for BLC |
|---|---|---|---|---|
| **YouTube** | ✅ Data API v3 (free) | n/a | rarely needed | **Build first.** Free, reliable, zero fork risk. |
| **Instagram** | ⚠️ Business Discovery (public metrics for *business* accounts, no target OAuth) | ✅ full analytics for own clients | ✅ for personal accounts / deeper post data | **Bright Data primary;** Business Discovery as an optional free shortcut for business accounts. Covers any public account either way. |
| **Facebook** | ⚠️ Page public data is thin; rich Page Insights need owner OAuth | ✅ for own clients | ✅ public page posts/engagement | Scraper or owner-OAuth. Lower priority than IG for this niche. |
| **LinkedIn** | ❌ Partner Program only (incorporated cos, opaque pricing, often declined) | limited | ⚠️ works but **highest enforcement risk** — LinkedIn ToS bans scraping and litigates (Proxycurl shut down mid-2025) | **Defer / lowest priority.** Least relevant to residential builders/remodelers anyway. |
| **TikTok** | ❌ no free public-data API (Business API = ads only; Research API gated) | n/a | ⚠️ works but hardest to maintain (most aggressive anti-bot) | **Optional v2.1.** Rising for home-services video; add only if BLC wants it. |

> **Niche note.** BLC = *Builder Lead Converter*; its prospects are builders and
> remodelers. Their lead-gen social presence is overwhelmingly **Instagram**
> (before/after photos, Reels), **Facebook** (local pages, reviews, community
> groups), and **YouTube** (project walkthroughs). LinkedIn and TikTok are secondary.
> Prioritize IG + FB + YouTube; treat LinkedIn/TikTok as optional later additions.

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

#### 3.2.4 Recommendation (given the §3.1 internal-tool decision)

**Scraper-first.** Bright Data is the **primary** data source for the social audit —
that is the whole point of choosing scraping. It works on *any* public account
(business **or** personal), returns consistent deep data, and does **not** depend on
Meta's app review or its habit of tightening official endpoints (the Basic Display API
died Dec 2024). The free official paths are kept only as **opportunistic cost-savers**,
never as load-bearing dependencies.

Build one provider-adapter; ship backends in this order:

1. **YouTube → YouTube Data API (primary for YouTube).** The one official API that is
   genuinely open, free, and stable — no reason to scrape it. (Bright Data can also do
   YouTube if BLC later wants a single provider for everything.) Build first to prove
   the pipeline end-to-end.
2. **Instagram / Facebook / (TikTok later) → Bright Data (primary).** Default engine
   for everything Meta: business *and* personal accounts, competitors, and post-level
   depth, behind one swappable adapter. $0.75/1K, pay-per-success, ~98% IG success
   rate. (Apify was the evaluated alternative; not selected — §3.2.5.)
3. **Instagram Business Discovery → optional free shortcut.** When a target is a
   *business* account, this free Meta endpoint can supply the basic metrics and save a
   few scraper calls — but it is a *nice-to-have*, not what the audit relies on. If Meta
   restricts it, nothing breaks: Bright Data already covers Instagram.
4. **Owner-OAuth → later, optional.** Only for BLC's onboarded clients who want the
   richer first-party analytics (saves, reach, demographics) a public scrape can't see.

This keeps the one external dependency (Bright Data) behind a single swappable adapter,
gives BLC the competitor/prospect audits OAuth can't serve, and keeps cost and legal
risk low.

> **Bottom line on "OAuth or scrapers like Apify?"** For an *internal prospecting/
> sales* tool, **a scraper (Bright Data) as the primary engine**, not OAuth — with
> YouTube's official API and IG Business Discovery as free extras where they happen to
> work. OAuth only audits people who opt in, which defeats the point of auditing a
> prospect you're trying to win. Keep OAuth as an optional bonus for existing clients.

#### 3.2.5 Decisions locked (June 2026)

| Decision | Choice |
|---|---|
| Access strategy | **Scraper-first** — Bright Data is the *primary* social data source; YouTube uses its official API; IG Business Discovery is an *optional* free shortcut, not a dependency (not OAuth) |
| Scraper provider | **Bright Data** ($0.75/1K, pay-per-success, no monthly commitment) |
| Monthly budget | **Pay-as-you-go, no hard cap needed** — internal/low volume keeps this to a few dollars/month (§10). Optionally set a small Bright Data spend alert (e.g. $25/mo) as a safety net. |
| TikTok | **Deferred** — not required now; revisit later (Bright Data already supports it behind the same adapter, so adding it later is small). |
| LinkedIn | **Excluded** from scraping (enforcement risk). |
| Legal sign-off | **Pending** — a quick "go ahead" from the BLC owner before enabling Bright Data (see §3.2.3; public-data-only, no logins, minimal retention). |

### 3.3 Other decisions
- **Competitor benchmarking** (scope §4): required in Phase 2 or deferred to v3? If
  required, budget SEMrush/Ahrefs/Similarweb (no free reliable source — Technical
  Assessment §2.6).
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
- **Object storage** — there is **no storage abstraction today**: `pdf_renderer.py`
  writes PDFs directly to `local_report_storage_dir`. **Introduce** a storage interface
  first, then add an S3-compatible backend; serve reports via signed URLs.
- **Complete SSRF interception** — request-level blocking of redirects/sub-resources
  that resolve to internal IPs mid-crawl (Phase 1 only validates the start URL and
  blocks private hosts by default).
- **Secrets management** — move secrets out of `.env` into the platform's secret store.
- **Observability & resilience** — error tracking (Sentry), basic metrics/alerting,
  database backups, Celery retry/dead-letter handling.
- **Data retention** — cleanup policy for old audit rows, PDFs, and screenshots.
- **Web dashboard & product surface** — an interactive dashboard view (reuses the
  existing report payload), improved audit history, re-run, shareable links, and
  white-label branding for prospect-facing reports.

### 4.2 Tickets (Epic P2-E2)
- P2-6 Add lightweight team authentication to API + UI (single internal org)
- *(A tenant/org data model & isolation ticket was considered and **dropped** — internal tool, §3.1)*
- P2-7 Introduce a storage interface + S3 report/screenshot backend (none exists yet)
- P2-8 Complete request-level SSRF interception
- P2-9 Managed hosting + CI/CD deploy (DB, workers, API, frontend, TLS)
- P2-10 Observability: Sentry, metrics, alerts, backups, retention
- P2-11 Web dashboard view + audit history/re-run/share + white-label

---

## 5. Workstream B — Social Media Audit (Epic P2-E4, the marquee feature)

Add the third audit type from the original scope. Architecturally it is a **clone of
the website pipeline** — the same four-step pattern (Technical Assessment §3.2) — so
most of the framework is reused.

### 5.1 What the social audit evaluates (original scope §3.3)
For each connected platform (Instagram, Facebook, LinkedIn, YouTube):

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
1. **Input** — accept social handles/URLs (already in the original input spec) alongside the website URL.
2. **Collect** — per-platform collectors behind one provider-adapter (§3.2), **scraper-first**:
   - **YouTube** → YouTube Data API (channel stats, uploads, views, subs, engagement) — official API stays primary here.
   - **Instagram / Facebook / (TikTok later)** → **Bright Data (primary)**; IG Business Discovery is an optional free shortcut for business accounts, not a dependency. **LinkedIn excluded** (enforcement risk, §3.2.2).
   - **Owner-OAuth** → optional, only for BLC's onboarded clients.
3. **Extract** — deterministic parsers normalize each platform's data into a common social-facts schema.
4. **Score** — a new **YAML social rubric** (same engine as `rubrics/`) produces a deterministic Social Score; weights tunable without code.
5. **Commentate** — the existing commentary pipeline writes social findings + tiered recommendations from facts + scores.
6. **Validate** — the existing grounding validator (extended to social facts) strips unsupported numeric claims.
7. **Compose** — extend the report payload + PDF/dashboard with a Social section; **fold the Social Score into the Lead-Gen Readiness score**.

### 5.3 Data model & code touch-points (verified against the repo)
- **Input:** add social-handle fields to `AuditCreateRequest`
  (`apps/api/schemas/audits.py`) and `audit_jobs` — today a job stores only `url`,
  `niche`, `target_audience`, so this is a new schema column + migration.
- **Storage:** persist normalized social facts + the social score by extending
  `audit_jobs` / `audit_results`, or add `social_*` tables.
- **New worker stages** (matching the existing `extractor_seo.py` / `extractor_uxui.py`
  naming): a social **collector** module (alongside `crawler.py` / `psi_client.py`) and
  **`extractor_social.py`**. Scoring is rubric-driven by the single `scoring.py`, so
  there is **no** per-domain score module to add.
- **Composite score is a code change, not just YAML.** Add `rubrics/social.yaml`, then
  update `apps/worker/stages/scoring.py`: `CompositeRubric.weights` is typed
  `Literal["seo", "uxui"]` and `validate_weights` requires the category set to be
  **exactly** `{seo, uxui}` summing to 1.0. Adding social means adding `social` to that
  type and the expected set, **rebalancing** `rubrics/composite.yaml` so all three
  weights sum to 1.0, and extending `compose_lead_generation_score`.
- **Provider adapter** package for social data sources (one interface, swappable backend).

### 5.4 Tickets (Epic P2-E4)
- P2-19 Social data provider adapter (interface + YouTube backend first)
- P2-20 **Bright Data backend (primary)** for IG/FB — any public account, post-level depth (§3.2.5)
- P2-21 Instagram Business Discovery as an optional free shortcut for business accounts; LinkedIn excluded, TikTok deferred
- P2-22 Social fact extractors + common schema + fixtures
- P2-23 `rubrics/social.yaml` + extend `scoring.py` (composite Literal/weights) + Lead-Gen update
- P2-24 Social commentary prompts + grounding-validator extension
- P2-25 Report/PDF/dashboard social section + updated Lead-Gen score

---

## 6. Workstream C — Enrichment (Epic P2-E5, later / v3)

Defer until the core (A + B) is validated. These materially change the architecture
(anonymous public-data audits → user-authorized data sources), so they are their own
phase, not bundled (Technical Assessment "Future phase").

### 6.1 Competitor benchmarking (scope §4)
Benchmark SEO/UX/Social scores against competitors or industry norms via SEMrush,
Ahrefs, or Similarweb APIs (higher tiers; recurring cost — no free reliable source).

### 6.2 Analytics integrations — "Future Data Collection Expansion" (scope)
User-authorized data sources for deeper UX/SEO insight:
- **Google Analytics (GA4)** — user behavior flow, bounce/exit, conversion rates, funnel drop-offs.
- **Google Search Console** — keyword performance, technical SEO diagnostics, indexing.
- **Microsoft Clarity** — heatmaps & session-recording references.
- **SEMrush** — keyword/traffic data.

### 6.3 Tickets (Epic P2-E5, v3)
- P2-26 Competitor benchmarking provider + benchmarked scoring
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

```text
Operator UI (Next.js, + team auth in Phase 2)
        |
        v
FastAPI API (+ team auth)  ──►  Celery workers + Redis
        |                              |
        |     +------------------------+-----------+----------------------+
        |     |                        |           |                      |
        v  Website (DEEPER, D)      Social (NEW, B)                  Enrichment (v3, C)
 PostgreSQL  crawler/PSI/CrUX     Bright Data (primary) ·             SEMrush/Ahrefs,
 (managed)   SEO/UX/schema/a11y   YouTube API · IG Biz Disc (opt)     GA4/GSC/Clarity
        |        \                   /        \                          /
        |         v                 v          v                        v
        |   deterministic scoring (YAML rubrics: seo, uxui, social, [aeo?], composite)
        |                                   |
        |              grounded commentary (existing pipeline) + validation
        v                                   |
   S3 report storage  ◄──────────  report payload → PDF + dashboard
```

New vs Phase 1: team auth (no multi-tenancy), S3 storage, **deeper website signals
(schema, AEO, CrUX, a11y, local SEO)**, social collectors + `social.yaml` rubric +
Social Score folded into composite, a dashboard view, and (v3) enrichment sources.

---

## 8. Tech Stack Additions

| Need | Choice | Notes |
|---|---|---|
| Auth (internal) | Clerk / Supabase Auth, or Google Workspace SSO | Single team login; no multi-tenancy (§3.1) |
| Managed DB | Supabase / Neon (or AWS RDS) | JSONB fits audit results; free tier covers internal volume |
| Object storage | S3 / S3-compatible | Introduce a storage interface first (none today); signed URLs |
| Hosting | Vercel (UI) + Railway/Render (API+workers), or AWS ECS/Fargate | Low ops overhead |
| YouTube data | YouTube Data API v3 | Free; 10k units/day, 1 unit per channel-stats call |
| Social data — **primary** | **Bright Data** ✅ selected ($0.75/1K, pay-per-success); Apify was the alternative | Primary engine for IG/FB/(TikTok later) — any public account, deep data (§3.2.4) |
| Instagram — optional free shortcut | Instagram Business Discovery (Graph API + FB Login) | Free metrics for *business* accounts; a cost-saver, **not** a dependency |
| Owner analytics (own clients) | Meta / LinkedIn OAuth | Optional; richer first-party metrics for onboarded clients only |
| Structured data | JSON-LD parse + schema validation | Workstream D; no external dep |
| Accessibility | **axe-core** via existing Playwright | Workstream D; reuses the crawler's browser |
| Field CWV | **CrUX API** (LCP/INP/CLS) | Workstream D; free, real-world ranking signal |
| Error tracking | Sentry | App now has meaningful flows |
| Benchmarking (v3) | SEMrush / Ahrefs / Similarweb API | Recurring cost |
| Analytics (v3) | GA4 Data API, Search Console API, Clarity, SEMrush | User OAuth |
| LLM commentary | Existing OpenAI pipeline (or Claude Sonnet 4.6 + Haiku 4.5 per Technical Assessment) | Provider-agnostic contract |

---

## 9. Timeline

Full-time solo; part-time scales proportionally. §3.1 (internal tool) is already
decided, so discovery is shorter and Track A is lighter (no multi-tenancy). Tracks A,
B and D can overlap once the social-data path (§3.2) is confirmed.

| Phase / Track | Focus | Duration |
|---|---|---|
| **Phase 2.0** | Discovery & scope lock — confirm §3.2 social path + budget, draft `social.yaml`, pick hosting/auth/storage, confirm volume, legal sign-off for scraper | **2–3 days** |
| **Track A** | Productionization & platform — *internal scope* (team auth, hosting, S3, SSRF, monitoring, dashboard/history) | **2–3 weeks** (no multi-tenancy) |
| **Track D** | Deepen website audit (schema, AEO, CrUX, a11y, local SEO, link health) — runs in parallel with A | **1–2 weeks** |
| **Track B** | Social media audit (collectors, extractors, rubric, commentary, validation, report + Lead-Gen update) | **3–4 weeks** (swings on §3.2) |
| **Track C** | Enrichment — benchmarking + analytics integrations | **4–5 weeks** (v3) |

### 9.1 Week-by-week (core: A + D + B)
- **Wk 0 (2–3 days):** Phase 2.0 — confirm social path (YouTube API + **Bright Data primary** + IG Business Discovery as optional shortcut) + budget + legal sign-off; **run a small paid Bright Data smoke test on real builder accounts**; draft `social.yaml`; choose hosting/auth/storage.
- **Wk 1:** A — team auth on API+UI; managed DB + hosting skeleton; CI/CD deploy. **D in parallel:** structured-data + crawlability/link-health signals + rubric rules.
- **Wk 2:** A — S3 storage; complete SSRF interception; Sentry/backups/retention. **D:** CrUX + axe-core accessibility + local-SEO signals; re-calibrate rubric.
- **Wk 3:** A — dashboard view + audit history/re-run/share. **B starts:** provider adapter + **YouTube** backend end-to-end.
- **Wk 4:** B — **Bright Data backend (primary)** for IG/FB + optional IG Business Discovery shortcut (per §3.2); social extractors + fixtures.
- **Wk 5:** B — `social.yaml` + Social Score + composite update; social commentary + grounding extension.
- **Wk 6:** B — report/PDF/dashboard social section; **fold Social into Lead-Gen score**; QA on real accounts; calibration.

- **Phase 2 core (A + D + B): ~6–8 weeks** after ~2–3 days discovery (D overlaps A, so it adds little wall-clock).
- **With enrichment (A + B + C + D): ~10–13 weeks.** (Cross-check: the Technical Assessment put the analytics "future phase" at **3–4 weeks** on its own.)

---

## 10. Recurring Costs To Budget (2026 figures)

At **internal volume** (estimate ~50–300 audits/month) almost everything sits in free
tiers; the only new variable cost is the scraper (Bright Data), and it is small.

| Item | 2026 cost | Notes |
|---|---|---|
| YouTube Data API | **Free** | 10k units/day; an audit is a few units |
| Instagram Business Discovery | **Free** | Public metrics for business accounts |
| Paid scraper — **Bright Data** | **$0.75 / 1K results**, pay-per-success, no commitment | e.g. 300 audits × ~3 calls ≈ <$1/mo; covers IG/FB/LinkedIn/TikTok |
| Paid scraper — **Apify** (alt) | **$29/mo** Starter incl. $29 usage; IG profile $1.60/1K, posts $1.00/1K | Simpler to start; per-actor pricing |
| LLM commentary (OpenAI/Claude) | usage-based | Grounded, short outputs; cents per audit |
| Google PSI / CrUX API | **Free** | Covers internal scale |
| Managed Postgres (Supabase/Neon) | **Free → ~$25/mo** | Free tier covers internal volume |
| Hosting (Vercel + Railway/Render) | **~$0–40/mo** | Hobby/free tiers may suffice internally |
| Auth (Clerk/Supabase) | **Free** | Internal team is well under free limits |
| Error tracking (Sentry) | **Free → ~$26/mo** | Free tier likely fine |
| Benchmarking API (v3 only) | **$$$** SEMrush/Ahrefs | Defer to Track C |

> **Takeaway:** the recurring cost of the *core* Phase 2 (A + B + D) for internal use
> is roughly **$0–100/month** — dominated by hosting tiers, not data. The scraper,
> the thing the original assessment worried about, is the *cheapest* line item at this
> volume. Benchmarking (Track C) is the only expensive integration; that's why it's v3.

---

## 11. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| **Social data access** (Technical Assessment §2.1) | Could block IG/FB/LinkedIn | Scraper-first (§3.2): Bright Data is the primary engine and works on any public account; YouTube API + IG Business Discovery are free extras, not dependencies — all behind one adapter |
| Scraper breakage | Some audits fail | Provider abstraction + monitoring; graceful skip (like missing PSI) so an audit degrades, never aborts |
| Legal / ToS exposure | ToS or privacy issues | Scrape **public** data logged-out only (Meta v. Bright Data, hiQ favor this); **avoid LinkedIn scraping**; minimal retention; short legal sign-off before enabling a paid provider (§3.2.3) |
| Social score miscalibration | BLC distrusts results | Tune `social.yaml` against strong/weak sample accounts (same approach as SEO/UX) |
| LLM hallucination on social facts | Credibility loss | Reuse grounding validator; all numbers come from extracted facts |
| IG Business Discovery field limits | Low — it's only an optional shortcut | Bright Data (primary) already covers personal accounts + deep data; Business Discovery is used only where it saves a call |
| Unpredictable per-audit cost | Cost overrun | Page/handle caps, caching, volume sizing from §3.3; costs are tiny at internal volume (§10) |
| Productionization distracts from features | Velocity drops | Track A + D first (contained, low-risk), then B |

---

## 12. Acceptance Criteria

Phase 2 core (A + D + B) is successful when:

- **A:** A team member must authenticate; reports are stored in S3 and served via
  signed URLs; the crawler blocks internal IPs at request level; the system is
  deployed to managed hosting with TLS, error tracking, and backups; a dashboard shows
  results and audit history.
- **D:** The website audit produces and scores the new signals (structured data,
  AEO/answer-engine readiness, field Core Web Vitals, accessibility, local SEO, link
  health), the strong/weak calibration gate still holds, and the rubric version is
  bumped.
- **B:** Submitting website + social handles produces a deterministic **Social Score**
  per platform **without requiring the audited account to log in** (Bright Data
  primary; YouTube API; IG Business Discovery optional), grounded social commentary with tiered
  recommendations, and a combined **Lead-Generation Readiness score that includes
  social** — reproducible for identical inputs, presented in the PDF and dashboard.
- Validated on real builder/remodeler sites **and** their social accounts.

---

## 13. Out Of Scope For Phase 2 Core (v3+)

- Competitor benchmarking and analytics integrations (Workstream C) unless explicitly pulled forward in §3.3.
- Anything not in the original scope document (e.g. paid ads audits, CRM integrations).

---

## 14. What's Needed To Start

1. **§3.2 confirmed (locked — §3.2.5):** scraper-first = **Bright Data primary** +
   YouTube API + IG Business Discovery (optional shortcut); pay-as-you-go (no hard cap,
   internal volume); **TikTok deferred**; **LinkedIn excluded**. Remaining item: the
   legal go-ahead in #4.
2. **Accounts & keys for the chosen path:**
   - Google Cloud project + **YouTube Data API** key.
   - A **Facebook Login app** + one **Instagram professional account** for Business
     Discovery (BLC owns these; prospects do nothing).
   - A **Bright Data** account — the primary social-data source (selected — §3.2.5).
   - Auth provider (Clerk/Supabase/Workspace SSO) + hosting accounts (Vercel,
     Railway/Render, managed Postgres) + an S3 bucket.
3. A handful of **real social accounts** (strong + weak builder/remodeler examples)
   for calibrating `social.yaml`, mirroring the website test sites.
4. A short **legal sign-off** confirming public-data, logged-out scraping with minimal
   retention is acceptable (and that LinkedIn scraping is excluded) — §3.2.3.
5. The **P1-30** internal-test feedback to finalize priority order.

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
