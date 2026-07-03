# Requirements Specification

**Project:** Social Media & Website Auditing Automation
**Client:** Builder Lead Converter (BLC)
**Prepared by:** Abdullah Arshed
**Document version:** 1.1
**Date:** May 2026

---

## 0. How to read this document

This standalone specification captures what the client wants and what we have committed to build. It is split into three layers:

1. **The original client scope** (what Darius sent on Apr 22) — captured in full, nothing removed or summarised.
2. **The technical assessment commitments** (what we proposed back on Apr 22) — gaps surfaced, architecture proposed, risks named.
3. **The current Phase 1 execution plan** — the local-first website audit MVP we are building now, with production/deployment preparation placed at the end.

If anything in the build is ever unclear, the order of precedence is: **current local-first Phase 1 plan > Technical Assessment > Original Scope**. Historical proposal language is context; the current execution plan is what should guide implementation.

---

> ### As-built notes (2026-06-16)
>
> This document is the **historical scope-of-record**: the sections below preserve the original
> client scope, Technical Assessment, and Phase 1 execution plan **as they were locked**. The
> bullets here only annotate where the shipped Phase 1 build diverged from those original plans —
> they do **not** rewrite the historical text. For the authoritative as-built reference, see
> [`docs/03_ARCHITECTURE.md`](03_ARCHITECTURE.md), [`DEPLOYMENT.md`](../DEPLOYMENT.md), and the
> committed `*.mmd` diagrams. Divergences:
>
> - **Frontend is plain CSS, not Tailwind/shadcn.** §6.1 names "Next.js + Tailwind + shadcn/ui";
>   the shipped UI is **Next.js 14 (Pages Router) + React 18 + TypeScript with plain CSS** (no UI
>   component library). `tsc --noEmit` is the typecheck gate.
> - **Auth shipped (Clerk), not deferred to Phase 2.** §3.3, §3.8, §4.2.6 and §6.1 say "no auth /
>   single-user / Clerk in Phase 2." As built, **Clerk auth is live and opt-in by env**: when
>   `CLERK_ISSUER` is set the whole `/audits/*` router is gated (Bearer JWT or `__session`
>   cookie); when it is empty the API is open (how local dev, the QA harness, and tests run). The
>   Clerk instance is currently a **dev instance**; open sign-up is a known gap (invitation-only
>   is a manual operator step).
> - **Managed hosting + CI/CD shipped, not deferred.** §4.5 and §6.1 treat production deployment
>   as "not front-loaded / after local end-to-end success." It is now **live in production** on a
>   single Linode VM at `https://ai.builderleadconverter.com` (Docker Compose: postgres, redis,
>   api, worker, frontend, caddy), with GitHub Actions CI/CD auto-deploying on merge to `main`.
>   See [`DEPLOYMENT.md`](../DEPLOYMENT.md).
> - **External-SEO subsystem added (site-health sweep + Google Search Console).** §2.3 / §5.2
>   list GA/GSC/Clarity/SEMrush as Phase 3-or-later. As built, Phase 1 includes a built-in
>   **site-health technical-crawl sweep** (zero extra deps; the licensed Screaming Frog CLI is an
>   optional add-on) plus **optional Google Search Console** (Search Analytics + URL Inspection
>   via OAuth). These are facts under `external_seo.technical_crawl.*` and degrade gracefully — a
>   missing/failed source never penalizes the score or aborts the audit.
> - **DOCX export added alongside the PDF.** §2.7 / §4.2.5 specify a branded PDF report only. The
>   build also renders a **branded `.docx`** on demand (`GET /audits/{id}/docx`); DOCX failure
>   never fails the audit.
> - **Re-enrichment path added.** Beyond the original one-shot pipeline, a completed audit can
>   re-run **only** its external-SEO collection → rescore → recomment → re-render via
>   `POST /audits/{id}/rerun-enrichment` (the prior report is restored if the rerun fails).
> - **Phase 1 commentary is fully deterministic — no live LLM call.** §4.1, §4.2.4 and §6.1
>   describe an OpenAI/ChatGPT commentary pipeline. As built, Phase 1 commentary is generated
>   **entirely from a deterministic content plan**; OpenAI is **not** called at all in Phase 1
>   (the LLM-polish path is dormant scaffolding retained for Phase 2). The grounding/validation
>   pass (§3.5, §6.2) is real and active. So the "ChatGPT-powered" framing reflects the original
>   intent, not the shipped Phase 1 behavior.

---

## 1. Project context

### 1.1 What the client does

Builder Lead Converter (BLC) is a US-based agency working with builders and remodelers on lead generation. Their primary value proposition revolves around helping construction-industry clients attract qualified prospects and convert them into leads.

### 1.2 Why this project exists

BLC wants an **automated audit system** that replaces the manual, agency-style auditing process they (or their clients) currently rely on. The system should:

- Take a website URL and social media handles as input
- Run independent, automated audits across SEO, UX/UI, and Social Media
- Produce numeric scores and a Lead Generation Readiness Score
- Generate a structured report with prioritized recommendations
- Be sufficiently polished to be used either internally by BLC's team or eventually as a service offering

### 1.3 Stakeholders

| Name | Role | Email | Involvement |
|---|---|---|---|
| Darius Rus | Development Manager | darius@builderleadconverter.com | Primary technical contact, owns the scope |
| Arthur Munoz | Integrator / General Manager | arthur@builderleadconverter.com | Business and process owner, runs the May 5 interview |
| Alex | (CC on thread) | alex@builderleadconverter.com | Internal stakeholder, awareness only |
| Abdullah Arshed | Engineer / Builder | abdullaharshed956@gmail.com | Solo builder for Phase 1 |

### 1.4 Engagement timeline so far

- **Apr 22:** Darius shared the project scope document and requested a technical assessment.
- **Apr 22:** Abdullah delivered the Technical Assessment (gaps, risks, architecture, tech stack, phased timeline).
- **Apr 23:** Darius confirmed receipt and team review.
- **Apr 24:** Darius proposed narrowing to a **focused Phase 1 evaluation** — a lean MVP with visible, testable, end-to-end results.
- **Apr 25:** Abdullah delivered the Phase 1 Implementation Plan, scoped to website audits only (SEO + UX/UI).
- **Apr 29:** Darius confirmed Phase 1 reviewed and accepted into evaluation; Arthur to follow up on next steps.
- **Apr 30:** Arthur scheduled an interview for **Tuesday, May 5, 10:45 AM – 11:25 AM CST**.
- **Current planning update:** Phase 1 is now planned as a local-first build. Production/staging deployment is prepared after the application works end-to-end locally, rather than being front-loaded.

---

## 2. The original scope (as delivered by Darius)

This section captures what the client originally asked for, in full. Nothing is paraphrased away or summarised. This is the long-term vision; Phase 1 covers a subset of it.

### 2.1 User input

The system shall accept the following inputs from the user:

- **Website URL** — primary input
- **Social Media Links** — Facebook, Instagram, LinkedIn, YouTube (and similar)
- **Primary Goal** — Increase lead generation (attract + capture qualified prospects)
- **Optional inputs** — Target audience, niche, or offer details

### 2.2 Data collection

The system shall automatically collect data in two main pillars:

#### 2.2.1 Website data
- On-page SEO elements
- Technical SEO signals
- Site structure & performance
- Conversion paths & CTAs

#### 2.2.2 Social media data
- Profile optimization
- Posting activity
- Engagement metrics
- Content type & positioning
- Lead capture mechanisms (bio links, forms, DM automation, etc.)

### 2.3 Future data collection expansion (UX/UI enhancement)

At a future stage, the UX/UI audit shall integrate direct data sources from:

- Google Analytics
- Google Search Console
- Microsoft Clarity
- SEMrush

These integrations shall enable deeper insights into:

- User behavior flow
- Bounce rates & exit pages
- Conversion rates
- Heatmaps & session recordings
- Keyword performance
- Technical SEO diagnostics
- Funnel drop-offs

> **Note:** This is explicitly future-phase work. Not in Phase 1, not in Phase 2 (per current understanding). Likely Phase 3 or later.

### 2.4 Analysis agents — three independent audit types

The automation must run **three distinct audit types**, each operating independently.

#### 2.4.1 SEO Audit (Website)

**Focus:** Organic visibility & traffic acquisition.

**Evaluate:**
- Keyword targeting & search intent alignment
- Meta titles / descriptions
- Heading structure
- Internal linking
- Technical issues (speed, indexing, mobile-friendliness)
- Content depth & optimization
- Local SEO (if applicable)

**Output:**
- SEO Score
- Traffic growth opportunities
- Keyword gaps
- Technical fixes
- Lead-focused SEO improvements

#### 2.4.2 UX/UI Audit (Website)

**Focus:** Conversion optimization & lead capture.

**Evaluate:**
- First impression & clarity of value proposition
- CTA visibility & placement
- Landing page structure
- Form usability
- Mobile responsiveness
- Page speed impact on conversions
- Trust signals (reviews, testimonials, badges)
- Funnel friction points

**Output:**
- UX/UI Score
- Conversion bottlenecks
- Quick wins for increasing form submissions
- Structural layout improvements
- Lead capture optimization recommendations

#### 2.4.3 Social Media Audit

**Focus:** Audience growth & lead nurturing.

**Evaluate:**
- Bio optimization & call-to-action clarity
- Content consistency & positioning
- Engagement rate
- Content types (educational, authority, promotional)
- Funnel integration (link-in-bio, landing pages, lead magnets)
- Messaging alignment with website
- Community interaction strategy

**Output:**
- Social Media Score
- Profile optimization recommendations
- Content strategy improvements
- Engagement growth tactics
- Lead capture improvements (DM flows, landing pages, offers)

### 2.5 Scoring & benchmarking

Each audit produces:

- SEO Score
- UX/UI Score
- Social Media Score
- **Overall Lead Generation Readiness Score** (composite)

Scores shall be benchmarked against industry standards or competitors where data is available.
As built, this is a presentation-only scaffold: normalized benchmark facts can be rendered in the
report, but benchmark data never changes SEO, UX/UI, Social, Lead-Gen, or Overall scores.

### 2.6 Recommendations & strategy

Recommendations must be split into three time horizons:

- **Quick Wins** — 0–30 days
- **Mid-Term Improvements** — 1–3 months
- **Long-Term Growth Strategy** — 3–12 months

All recommendations must directly support the primary goal:
- Attract more qualified traffic
- Convert traffic into leads

### 2.7 Final deliverable

A structured audit report containing:

- Executive Summary
- Detailed Findings (per audit type)
- Score Breakdown
- Lead Generation Strategy Roadmap
- Action Plan with Priority Levels

---

## 3. Identified gaps and risks (from the Technical Assessment)

Section 2 above is what Darius wrote. Section 3 is what we noticed was missing or under-specified. Each of these has architectural consequences. Some are resolved (parked into Phase 2), some are still open.

### 3.1 Social media data access — biggest risk

**Problem:** The 2026 reality of social-platform APIs makes the original scope's "collect engagement metrics, posting frequency, and profile data from Facebook, Instagram, LinkedIn, YouTube" significantly harder than it sounds.

- Meta's Instagram Graph API only returns data for accounts that have authenticated through our app via OAuth. Auditing a *prospect's* Instagram without their consent is not technically possible through official channels.
- The Instagram Basic Display API was fully deprecated in December 2024.
- LinkedIn API access requires partner program approval (multi-week, frequently denied for non-enterprise use cases).
- Third-party scraping providers (ScrapeCreators, Apify, Bright Data, etc.) work but carry legal exposure, recurring cost, and ongoing maintenance burden.
- YouTube Data API is the only genuinely open option.

**Architectural fork:**
- **Option A:** OAuth-based — only audit accounts whose owners authenticate. Tool becomes a self-audit service. Loses the competitive-audit use case.
- **Option B:** Paid scraping provider — can audit any public account. Recurring subscription cost. Reliability risk on platform updates.

**Status:** ✅ **Resolved (2026-06-05) — Option B (scraping).** BLC (Darius) chose a paid
scraping provider (**Bright Data**) for Instagram/Facebook so the tool can audit *any*
public account, including prospects and competitors. **No OAuth** (it only audits opt-in
accounts) and **no IG Business Discovery** (it needs a Facebook app / account approval BLC
declined). YouTube uses its free official API. LinkedIn excluded; TikTok deferred. See
[`docs/08_PHASE2_PLAN.md`](08_PHASE2_PLAN.md) §3.2.

### 3.2 Scoring methodology — undefined in original scope

**Problem:** Scope calls for SEO Score, UX/UI Score, Social Score, Lead Gen Readiness Score, but does not define how any of them are computed. Pure-LLM scoring is non-reproducible — running the same audit twice returns different numbers — and indefensible when a user asks "why am I a 62 not a 70?"

**Resolution:** Hybrid scoring pattern adopted (see Section 4.2).

### 3.3 Scale, volume, deployment target — under-specified

**Problem:** Scope doesn't say whether this is an internal tool doing ~10 audits/week or a SaaS doing ~10,000/month. Driver of database choice, worker infrastructure, caching, and concurrency.

**Resolution for Phase 1:** Single-user internal tool, no auth, no multi-tenancy. Volume question deferred to Phase 2.

### 3.4 Website audit page-count ceiling

**Problem:** "Audit the website" can mean one page or 500. Full-site real-browser crawls take 5–15 seconds per page. Without a cap, cost-per-audit is unpredictable.

**Resolution for Phase 1:** Hard cap of **up to 10 total crawled pages**, including the homepage and selected same-site internal pages.

### 3.5 LLM hallucination on factual claims

**Problem:** If the report says "your meta title is 75 characters" and it's actually 58, credibility is destroyed instantly.

**Resolution:** Grounded generation pattern. All numeric and factual claims come from deterministic extractors. ChatGPT only writes commentary on top of pre-extracted facts. Validation pass after generation re-verifies all numeric claims against source data.

### 3.6 Competitor benchmarking source

**Problem:** No free, reliable source for benchmark data exists. Real options are paid: SEMrush, Ahrefs, Similarweb. Recurring cost.

**Resolution:** The safe scaffold has been built: feature flag, provider registry, normalized
facts, report-section rendering, and graceful skip paths. The live SEMrush/Ahrefs/Similarweb
clients remain deferred until product-market fit and recurring cost are approved.

### 3.7 Report delivery format

**Problem:** "A structured audit report" doesn't specify PDF, web dashboard, shareable link, or white-label. Each adds meaningful effort.

**Resolution for Phase 1:** Branded PDF only, BLC-styled, professional pagination. Dashboard, sharing, white-label deferred.

### 3.8 Multi-tenancy and data storage

**Problem:** Scope doesn't address accounts, auth, audit history, tenant isolation. For a SaaS-style deployment this is 15–25% of total build effort.

**Resolution for Phase 1:** None of it. Single-user. Phase 2 concern.

---

## 4. Phase 1 — what we are actually building now

This is the current execution scope. Everything below is in scope. Anything not below is out of scope for Phase 1.

### 4.1 Phase 1 goal statement

> The BLC team can enter a website URL, trigger a complete local audit, and receive a branded PDF report with deterministic scores, AI-generated commentary, and a prioritized action roadmap. The system is built locally first; production/staging deployment is prepared after the end-to-end application flow is working.

### 4.2 Phase 1 functional scope

#### 4.2.1 User input layer

- Website URL submission
- Optional: niche / target audience metadata field
- No social media inputs in Phase 1
- No multi-user accounts in Phase 1

#### 4.2.2 Website data collection

- **Crawl coverage:** Homepage + up to top 10 internal pages.
- **Rendering:** Real-browser via Playwright (handles JavaScript-heavy sites).
- **Extracted facts:**
  - Meta tags (title, description, OG, Twitter card)
  - Heading hierarchy (H1–H6 counts and structure)
  - Image alt-text coverage
  - Internal link structure
  - Form presence (count, fields, submit destinations)
  - CTA detection (above-fold, button copy, link targets)
  - Contact information (phone, email, address)
  - Mobile-responsiveness signals
  - Schema.org structured data presence
  - Robots.txt and sitemap.xml presence
- **Performance signals:** Lighthouse and Core Web Vitals via Google PageSpeed Insights API for performance, accessibility, SEO, best-practices.

#### 4.2.3 Hybrid scoring engine

- **Deterministic, rule-based scoring** producing reproducible 0–100 numeric scores per category.
- **Categories:** SEO Score, UX/UI Score, combined Lead Generation Readiness Score.
- **Config-driven rubrics** — weights and thresholds tunable via external YAML/JSON without code changes.
- **Per-check audit trail** — every score has a visible breakdown explaining which rules contributed.
- **Reproducibility guarantee** — running the same site twice produces the same numeric score.

#### 4.2.4 ChatGPT-powered commentary pipeline

- An OpenAI ChatGPT model is the primary model; the exact model ID is configured at implementation time.
- Strict, structured system prompt.
- Inputs to ChatGPT: pre-extracted facts + computed scores.
- Outputs: structured JSON with findings, plain-language explanations, prioritized recommendations.
- **Grounded generation:** ChatGPT does not invent numeric claims. Any numeric claim must match facts or rule outputs already provided.
- **Validation pass:** secondary check verifies all factual claims in the generated commentary trace back to extracted data.
- Recommendations grouped into Quick Wins (0–30 days), Mid-Term (1–3 months), Long-Term (3–12 months).

#### 4.2.5 Branded PDF report

- Cover page (BLC-branded)
- Executive summary
- Score breakdown (per category + Lead Gen Readiness)
- Detailed findings per category (SEO + UX/UI)
- Prioritized roadmap with action items
- Professional pagination — proper page breaks, headers, footers, page numbers
- BLC brand styling — logo, color palette, typography
- Page-quality fit for sending to a prospect builder

#### 4.2.6 Internal operator interface

- Minimal web form: enter URL, trigger audit, watch progress, download PDF
- Designed for internal use by the BLC team
- Single-user — no auth, accounts, or multi-tenancy in Phase 1

### 4.3 Phase 1 deliverables

- **Running local system** — can audit real builder/remodeler websites end-to-end in the local development environment
- **Source code** — delivered via private Git repo, ownership transferred to BLC
- **Sample reports** — 5–10 fully rendered PDF audits on real builder/remodeler websites
- **Documentation** — setup guide, architecture overview
- **Walkthrough video** — 10-minute video explaining how each part works
- **Tunable rubric config** — externalized so BLC team can adjust weights and thresholds independently
- **Production-readiness package** — containerization, environment variable documentation, and storage abstraction prepared for later staging/production deployment

### 4.4 Phase 1 acceptance criteria

The Phase 1 deliverable shall be considered successful if all of the following pass:

1. The system can audit any submitted builder/remodeler website end-to-end without manual intervention.
2. The same site, audited twice, produces identical numeric scores (reproducibility).
3. Scores feel calibrated when run on five contrasting test sites — strong sites score high, weak sites score low.
4. LLM-generated recommendations are specific, actionable, and grounded in actual site data — not generic advice.
5. PDF output is professional enough that a BLC team member could send it to a prospect builder.
6. The rubric is tunable without code changes — adjusting one weight and re-running produces the expected score change.

### 4.5 Phase 1 commercial terms

| Term | Value |
|---|---|
| Commercial terms | To be confirmed separately from this technical scope |
| Included | Application development, scoring rubric design, prompt engineering, PDF template, source code handover, documentation, walkthrough video, production-readiness preparation |
| Excluded | Third-party API costs, production hosting costs, social media data providers, live benchmarking-provider subscriptions |
| Deployment note | Production/staging deployment is not front-loaded. It can be executed after the local application is working end-to-end. |

### 4.6 What we need from BLC to start

Captured for the kickoff call:

- Short kickoff call (~30 minutes) to align on priorities, walk through the scoring rubric philosophy, answer open questions
- Five to ten example builder/remodeler websites for test cases — mix of strong and weak performers
- BLC brand assets — logo, color palette, font preferences for PDF styling
- Communication channel for daily updates (Slack, email thread, or BLC's preference)

### 4.7 Working approach during Phase 1

- **Daily updates** — short written status each working day (worked on, what's next, anything blocking)
- **Milestone demos** — recorded demos when major flows become usable: crawler/extraction, scoring, PDF, full local audit
- **Async-first** — respect time zones; live calls only when they materially unblock decisions
- **Local-first delivery** — prove the full application locally before doing production or staging infrastructure work

---

## 5. Out of scope for Phase 1 (deferred to later phases)

These are tracked here so they don't get forgotten and so the boundary is unambiguous.

### 5.1 Deferred to Phase 2

- Social media audits (Instagram, Facebook, LinkedIn, YouTube)
- OAuth-vs-scraping decision and integration
- Live competitor benchmarking provider clients via SEMrush / Ahrefs / Similarweb
- User accounts, authentication, multi-tenancy
- Web dashboard with interactive charts and exploration
- Advanced audit history and re-running previous audits
- Shareable links (public report URLs)
- White-label branding for end-customer self-service reports

### 5.2 Deferred to Phase 3 or later

- Google Analytics integration
- Google Search Console integration
- Microsoft Clarity integration
- SEMrush integration (beyond benchmarking — for keyword research)
- User behavior flow analysis
- Heatmaps & session recordings
- Funnel drop-off analysis at the analytics level

---

## 6. Architectural decisions and constraints

These are the technical decisions made during scope review that the build must respect. They are documented here so they survive personnel changes and are not silently re-invented mid-build.

### 6.1 Tech stack (locked)

| Layer | Choice | Reason |
|---|---|---|
| Backend API | Python (FastAPI) | Strongest ecosystem for scraping/parsing/LLM tooling. Clean async patterns for long jobs. |
| Job Queue | Celery + Redis | Audits take minutes. Async with progress tracking and retry. |
| Website Crawler | Playwright | Real browser rendering required for JS-heavy modern sites. |
| Performance & SEO audit | Google PageSpeed Insights API, with local Lighthouse fallback considered only if needed | PSI returns Lighthouse-style performance, accessibility, SEO, and best-practices signals. |
| LLM commentary | OpenAI ChatGPT model for primary commentary; lower-cost model optional for bulk classification | Use stronger reasoning for report commentary and cheaper classification only where it is safe. |
| Scoring engine | Pure Python rules + weighted rubric config (YAML) | Deterministic, explainable, tunable without code changes. |
| Database | PostgreSQL (local Docker Compose first; managed Postgres later) | JSONB columns suit audit results. Local-first keeps startup simple. |
| Report rendering | WeasyPrint + Jinja2 + print CSS | Better fit for long structured PDF reports with headers, footers, page counters, and page-break control. |
| Frontend | Next.js + Tailwind + shadcn/ui | Fast, clean defaults, TypeScript end-to-end. |
| Auth | Not needed in Phase 1 | Single-user. Clerk or Supabase Auth in Phase 2. |
| Hosting | Deferred until after local end-to-end success | Production/staging should not slow the initial application build. |

### 6.2 Architectural patterns (non-negotiable)

- **Hybrid scoring** — deterministic rules for numbers, LLM for commentary only. Never invert this.
- **Grounded generation** — LLM cannot produce numeric or factual claims; only commentates on extracted facts.
- **Validation pass** — every LLM output goes through a second-pass checker before reaching the user.
- **Config-driven rubrics** — scoring rules live in external YAML, not in code.
- **Structured pipelines, not autonomous agents** — each audit is Extract → Score → Commentate → Validate. No free-form agent loops.

### 6.3 Quality bars

- **Reproducibility:** same input → same numeric score, every time.
- **Explainability:** every score has a per-rule breakdown visible to the user.
- **Grounding:** every numeric claim in commentary traces back to an extracted fact.
- **Polish:** PDF output is presentable to a prospect, not just a dev artifact.

---

## 7. Risk register (live)

These are the risks we are tracking through Phase 1. Each has a mitigation strategy. Re-review every Friday.

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| R1 | Rubric review by BLC delays scoring calibration | High | Draft rubrics early and request review as soon as the first scoring outputs exist |
| R2 | PDF rendering edge cases consume more than budgeted | High | Use proven tools (WeasyPrint preferred over Puppeteer for long structured docs). Test on extreme cases (5 findings, 50 findings) early. |
| R3 | BLC brand assets change after PDF styling is implemented | Medium | Keep logo and colors centralized in `assets/brand/` and `brand/blc.yaml` so updates remain low-risk |
| R4 | Test sites break the crawler in unexpected ways | Medium | Test real builder sites early. Treat broken crawls as unblockers, not bugs to defer. |
| R5 | LLM usage costs exceed expectations | Low | Use the strongest model only for report commentary, use cheaper classification only where safe, cap retries, and monitor token usage. |
| R6 | Scope creep ("can we just add social media") | Medium | Polite-firm no, with reasoning. Park requests as Phase 2 inputs. |
| R7 | Solo-builder schedule risk (sick day, outage) | Medium | Front-load risky product work: crawler, scoring, ChatGPT grounding, PDF generation |
| R8 | Calibration: scores feel "off" to BLC even though they're reproducible | Medium | Iterate weights with BLC after sample-site scoring. Bake in 5 contrasting test sites for calibration check. |

---

## 8. Coverage map — Phase 1 vs. full project

How much of the original Darius scope does Phase 1 cover? This is the honest accounting.

| Original scope item | Phase 1 | Phase 2 | Later |
|---|---|---|---|
| Website URL input | ✅ | — | — |
| Social media link input | — | ✅ | — |
| Niche/audience metadata | ✅ optional | — | — |
| Website data collection | ✅ | — | — |
| Social media data collection | — | ✅ | — |
| GA / GSC / Clarity / SEMrush | — | — | ✅ |
| SEO Audit | ✅ | — | — |
| UX/UI Audit | ✅ | — | — |
| Social Media Audit | — | ✅ | — |
| SEO Score | ✅ | — | — |
| UX/UI Score | ✅ | — | — |
| Social Media Score | — | ✅ | — |
| Lead Gen Readiness Score | ✅ partial (without social) | ✅ full | — |
| Competitor benchmarking scaffold | — | ✅ | — |
| Live benchmarking provider subscription/client | — | — | ✅ |
| Quick Wins / Mid / Long-term recommendations | ✅ | — | — |
| Executive Summary | ✅ | — | — |
| Detailed Findings | ✅ | — | — |
| Score Breakdown | ✅ | — | — |
| Action Plan with Priority Levels | ✅ | — | — |
| Multi-tenancy / accounts | — | ✅ | — |
| Web dashboard | — | ✅ | — |
| Basic internal audit history | ✅ | — | — |
| Advanced audit history and re-runs | — | ✅ | — |
| Shareable links | — | ✅ | — |
| White-label | — | ✅ | — |

**Estimated coverage by build effort:**

- Phase 1 covers **~45–55%** of the total project effort.
- The shared infrastructure built in Phase 1 (job queue, scoring engine, ChatGPT commentary pipeline pattern, PDF generator) is reused by Phase 2, so Phase 2's incremental effort is roughly **35–45%** of the total — not 55% — even though it covers the remaining feature surface.

---

## 9. Glossary

- **Rubric** — the structured rulebook of "if X is true, award Y points" entries that produces a numeric score. Lives in external YAML.
- **Grounded generation** — pattern where the LLM is constrained to only commentate on facts already extracted by deterministic code; it cannot introduce numbers or claims of its own.
- **Hybrid scoring** — deterministic rule engine produces the score; LLM produces the prose. The score is never an LLM output.
- **Lead Generation Readiness Score** — composite score combining SEO, UX/UI, (and eventually Social) into one headline number. **As-built (2026-06-26):** the website Lead-Gen composite stays `{SEO, UX/UI}`; a **combined** audit additionally produces an **Overall Lead-Gen Readiness** score = `0.70 × website Lead-Gen + 0.30 × Social Score` (`rubrics/overall.yaml`), appended to the report. See `docs/15` §1.
- **PSI** — Google PageSpeed Insights API, returns Lighthouse output for any URL.
- **Phase 0** — discovery and scope-lock. Originally proposed in the Technical Assessment; effectively folded into the Phase 1 kickoff for the lean MVP.
- **MVP** — Minimum Viable Product. In this context, the working Phase 1 deliverable.

---

## 10. Document history

| Date | Change | Author |
|---|---|---|
| 2026-04-22 | Original scope received from Darius | Darius Rus |
| 2026-04-22 | Technical Assessment delivered | Abdullah Arshed |
| 2026-04-25 | Phase 1 Implementation Plan delivered | Abdullah Arshed |
| 2026-04-29 | Phase 1 accepted into evaluation | Darius Rus |
| 2026-05-02 | Consolidated requirements specification compiled | Abdullah Arshed |
| 2026-05-26 | Updated Phase 1 execution plan to local-first and moved production/deployment preparation to the end | Abdullah Arshed |
| 2026-06-16 | Added "As-built notes" callout (§0) reconciling original locked scope with what shipped (plain-CSS frontend, Clerk auth, Linode hosting + CI/CD, external-SEO + GSC, DOCX export, re-enrichment, deterministic commentary); historical text left intact | Abdullah Arshed |
