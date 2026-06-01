# Implementation Plan & Architecture

**Project:** Social Media & Website Auditing Automation — Phase 1
**Client:** Builder Lead Converter (BLC)
**Builder:** Abdullah Arshed (solo)
**Execution model:** Local-first application build; production/deployment preparation at the end

---

## 0. How to read this document

This is a standalone **build manual** for the local-first Phase 1 website audit system. It answers: *given what we have to build, exactly how do we build it?*

Sections:
- **§1–3:** System architecture — components, data flow, contracts between layers
- **§4:** Repository and code organization
- **§5–9:** Component-by-component build instructions
- **§10:** Local-first execution sequence
- **§11–13:** Quality gates, production-readiness, handover
- **§14:** Pre-flight checklist before implementation starts

If you're picking this up cold, read §1, §2, and §10 first — that gives you the shape of the system and the execution sequence.

---

## 1. System architecture

### 1.1 High-level data flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                         BLC Operator UI (Next.js)                    │
│   [Submit URL form]   →   [Progress view]   →   [Download PDF]       │
└────────────────────────────────────┬─────────────────────────────────┘
                                     │ HTTPS
┌────────────────────────────────────┴─────────────────────────────────┐
│                       FastAPI backend  (Python 3.11+)                │
│   POST /audits  →  enqueue job  →  return job_id                     │
│   GET  /audits/{id}/status  →  return progress                       │
│   GET  /audits/{id}/report  →  stream PDF                            │
└────────────────────────────────────┬─────────────────────────────────┘
                                     │ Celery task
┌────────────────────────────────────┴─────────────────────────────────┐
│                         Worker (Celery + Redis)                      │
│                                                                      │
│   Stage 1: Collectors (parallel)                                     │
│     ├─ Playwright crawler (homepage + selected internal pages)       │
│     ├─ PageSpeed Insights API (per crawled page, mobile + desktop)   │
│     └─ robots.txt / sitemap.xml fetcher                              │
│                                                                      │
│   Stage 2: Extractors (deterministic Python)                         │
│     ├─ SEO fact extractor   → seo_facts.json                         │
│     └─ UX/UI fact extractor → uxui_facts.json                        │
│                                                                      │
│   Stage 3: Scoring engine (rule-based, config-driven)                │
│     ├─ SEO rubric  (rubrics/seo.yaml)   → seo_score + audit_trail    │
│     └─ UX/UI rubric (rubrics/uxui.yaml) → uxui_score + audit_trail   │
│                                                                      │
│   Stage 4: LLM commentary (OpenAI ChatGPT model)                │
│     ├─ Inputs: extracted facts + score breakdown                     │
│     ├─ Output: structured JSON (findings, recommendations by tier)   │
│     └─ Prompt enforces "no new numbers, only commentary"             │
│                                                                      │
│   Stage 5: Validator                                                 │
│     ├─ Re-checks every numeric claim in commentary                   │
│     └─ Strips or flags any claim not grounded in extracted facts     │
│                                                                      │
│   Stage 6: Composer                                                  │
│     ├─ Assembles report data structure                               │
│     └─ Computes Lead Gen Readiness Score (SEO + UX/UI weighted)      │
│                                                                      │
│   Stage 7: PDF generator                                             │
│     ├─ Renders Jinja2/HTML report template                           │
│     ├─ Writes PDF via WeasyPrint                                     │
│     ├─ Stores PDF at /storage/{audit_id}.pdf                         │
│     └─ Writes final audit_result row to Postgres                     │
└──────────────────────────────────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┴─────────────────────────────────┐
│  PostgreSQL (local first; managed later) · audit_jobs · audit_results│
│  Local report storage first; S3-compatible storage later             │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.2 Why this shape

The architecture is optimized for a local-first MVP that still has a clean path to production later.

| Decision | Rationale |
|---|---|
| FastAPI for backend | Python ecosystem is strongest for scraping, parsing, PDF rendering, and LLM tooling. |
| Celery + Redis for jobs | Audits take long enough that they need async processing, progress tracking, and retries. |
| Playwright for crawling | Modern sites are JavaScript-heavy; static HTML parsing misses too much. |
| PageSpeed Insights API for performance | Provides Lighthouse-style performance, accessibility, SEO, and best-practices signals. |
| Hybrid scoring | Deterministic rules produce reproducible scores; LLMs provide commentary only. |
| Grounded generation | ChatGPT receives extracted facts and score breakdowns, not permission to invent facts. |
| Validation pass | A second check catches unsupported factual or numeric claims before report generation. |
| Config-driven rubrics | BLC can tune weights and thresholds without code changes. |
| WeasyPrint over Puppeteer for PDF | WeasyPrint has stronger print CSS support for long structured documents. |
| Postgres + JSONB | Audit results are nested structures; JSONB fits the data shape. |
| Local-first execution | Product behavior is proven before production infrastructure work begins. |

### 1.3 Boundaries and non-goals

What this architecture explicitly does **not** try to be:

- It is **not multi-tenant.** No tenant_id on tables. Phase 2 problem.
- It is **not real-time.** Audits are jobs that take minutes; no websockets, no live updates beyond polling.
- It is **not autonomous-agent-driven.** Pipelines are explicit Extract → Score → Commentate → Validate sequences. No tool-using agent loops.
- It is **not self-service.** No signup, no billing, no email magic links. Internal BLC tool.
- It is **not horizontally scaled.** One worker is fine for Phase 1 volume. Add concurrency in Phase 2.

---

## 2. Data model

### 2.1 Tables (PostgreSQL)

```sql
-- Tracks the lifecycle of an audit request
CREATE TABLE audit_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url             TEXT NOT NULL,
    niche           TEXT,                    -- optional metadata
    target_audience TEXT,                    -- optional metadata
    status          TEXT NOT NULL,           -- 'queued' | 'crawling' | 'collecting_performance' | 'extracting' | 'scoring' | 'commenting' | 'validating' | 'rendering' | 'complete' | 'failed'
    current_stage   TEXT,
    progress_pct    INT  NOT NULL DEFAULT 0, -- 0..100
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ
);

CREATE INDEX idx_audit_jobs_status ON audit_jobs(status);
CREATE INDEX idx_audit_jobs_created ON audit_jobs(created_at DESC);

-- One row per completed audit, holding the full structured result
CREATE TABLE audit_results (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id            UUID NOT NULL REFERENCES audit_jobs(id) ON DELETE CASCADE,
    seo_score         INT  NOT NULL,         -- 0..100
    uxui_score        INT  NOT NULL,         -- 0..100
    lead_gen_score    INT  NOT NULL,         -- 0..100, composite
    crawled_pages     JSONB NOT NULL,        -- crawler artifacts and failed page log
    seo_facts         JSONB NOT NULL,        -- deterministic SEO facts
    uxui_facts        JSONB NOT NULL,        -- deterministic UX/UI facts
    psi_facts         JSONB NOT NULL,        -- normalized PSI facts or skip/failure state
    score_breakdown   JSONB NOT NULL,        -- per-rule audit trail
    commentary        JSONB NOT NULL,        -- LLM output (findings, recs by tier)
    validation_log    JSONB NOT NULL,        -- what the validator caught
    report_metadata   JSONB NOT NULL,        -- generated date, renderer version, storage metadata
    pdf_path          TEXT,                  -- local path or object storage key
    rubric_version    TEXT NOT NULL,         -- which rubric YAML was used
    llm_model         TEXT NOT NULL,         -- exact provider model ID used
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_results_job ON audit_results(job_id);
```

### 2.2 In-flight job state (the JSON contract between stages)

Every stage produces a structured artifact that the next stage consumes. The shape is fixed; this is the contract.

#### 2.2.1 Crawler output (per page)

```json
{
  "url": "https://example.com/services",
  "status_code": 200,
  "fetched_at": "2026-05-12T14:23:01Z",
  "html": "...",
  "rendered_html": "...",
  "screenshot_path": "/tmp/audit_xyz/services.png",
  "load_time_ms": 1840,
  "viewport": { "width": 1280, "height": 720 },
  "errors": []
}
```

#### 2.2.2 SEO facts (per audit)

```json
{
  "site_level": {
    "robots_txt_present": true,
    "sitemap_present": true,
    "https": true,
    "domain": "example.com"
  },
  "pages": [
    {
      "url": "https://example.com/",
      "meta_title": "Example Builders | Custom Homes in MN",
      "meta_title_length": 38,
      "meta_description": "...",
      "meta_description_length": 142,
      "h1_count": 1,
      "h1_text": "Custom Homes Built Right",
      "heading_outline": ["h1: ...", "h2: ...", "h2: ..."],
      "image_count": 12,
      "images_with_alt": 9,
      "internal_link_count": 18,
      "external_link_count": 4,
      "schema_types_present": ["Organization", "LocalBusiness"],
      "canonical_url": "https://example.com/",
      "word_count": 612
    }
  ],
  "psi_mobile": {
    "performance": 76,
    "seo": 92,
    "accessibility": 88,
    "best_practices": 95,
    "lcp_seconds": 2.8,
    "cls": 0.04,
    "tbt_ms": 210
  },
  "psi_desktop": { "...": "..." }
}
```

#### 2.2.3 UX/UI facts (per audit)

```json
{
  "homepage": {
    "value_prop_above_fold": true,
    "primary_cta_above_fold": true,
    "primary_cta_text": "Get a Free Quote",
    "phone_above_fold": true,
    "phone_number": "+1-555-...",
    "form_count": 1,
    "form_field_counts": [4],
    "trust_signals": {
      "testimonials_present": true,
      "reviews_present": false,
      "badges_present": true,
      "case_studies_present": false
    },
    "mobile_friendly": true,
    "navigation_depth": 2
  },
  "lead_capture": {
    "contact_page_exists": true,
    "form_on_homepage": true,
    "phone_clickable": true,
    "email_capture_present": false
  }
}
```

#### 2.2.4 Score breakdown (per audit, per category)

```json
{
  "category": "seo",
  "score": 72,
  "max": 100,
  "rules_evaluated": [
    {
      "rule_id": "seo.meta_title.length",
      "description": "Meta title is between 30 and 60 characters",
      "weight": 4,
      "result": "pass",
      "points_awarded": 4,
      "evidence": { "length": 38 }
    },
    {
      "rule_id": "seo.meta_description.length",
      "description": "Meta description is between 120 and 160 characters",
      "weight": 5,
      "result": "partial",
      "points_awarded": 3,
      "evidence": { "length": 142 }
    }
  ]
}
```

#### 2.2.5 Commentary (LLM output)

```json
{
  "executive_summary": "Example Builders has a technically sound site with strong on-page fundamentals, but is leaving leads on the table due to weak CTA placement on interior pages and a missing email capture mechanism on the homepage.",
  "categories": {
    "seo": {
      "headline": "Solid foundation, opportunity in long-tail keywords",
      "findings": [
        {
          "severity": "info",
          "title": "Meta tags well configured",
          "explanation": "Meta titles and descriptions are present on all crawled pages and within recommended length ranges, supporting click-through from search results."
        }
      ],
      "recommendations_quick_wins": [...],
      "recommendations_mid_term": [...],
      "recommendations_long_term": [...]
    },
    "uxui": { "..." }
  }
}
```

---

## 3. The two hardest pieces — deeper

Per the risk register (R1, R2), the rubric and the PDF are the two highest-risk components. Both deserve their own deeper architectural pass.

### 3.1 The scoring rubric — design and engineering

#### 3.1.1 Why rubrics are config, not code

Acceptance criterion #6: "rubric is tunable without code changes — adjusting one weight and re-running produces the expected score change." This forces rubrics to live in YAML, loaded at runtime.

#### 3.1.2 Rubric file structure

```yaml
# rubrics/seo.yaml
version: "1.0.0"
category: seo
max_score: 100
weight_normalization: rescale_to_max  # rules sum to anything; rescale to 0..100

rules:
  - id: seo.meta_title.length
    description: "Meta title is between 30 and 60 characters"
    weight: 4
    fact_path: "pages[0].meta_title_length"
    evaluator: range
    params:
      full_credit: [30, 60]
      partial_credit: [[20, 29], [61, 70]]
      zero: [null, 19, 71, null]

  - id: seo.meta_description.length
    description: "Meta description is between 120 and 160 characters"
    weight: 5
    fact_path: "pages[0].meta_description_length"
    evaluator: range
    params:
      full_credit: [120, 160]
      partial_credit: [[80, 119], [161, 200]]
      zero: [null, 79, 201, null]

  - id: seo.h1.exactly_one
    description: "Exactly one H1 on the homepage"
    weight: 3
    fact_path: "pages[0].h1_count"
    evaluator: exact_match
    params:
      full_credit: 1
      partial_credit: [2, 3]
      zero_otherwise: true

  - id: seo.psi.performance.mobile
    description: "Mobile performance score from PageSpeed Insights"
    weight: 12
    fact_path: "psi_mobile.performance"
    evaluator: linear_scale
    params:
      input_range: [0, 100]
      output_proportion: true   # awarded points = (value/100) * weight

  # ... 40-60 rules total for SEO
  # ... 30-50 rules total for UX/UI in rubrics/uxui.yaml
```

#### 3.1.3 Evaluator types

The rubric engine supports a small set of **evaluator primitives**. Adding a new rule means adding a YAML entry, not writing code. New evaluator types are added to code only when a genuinely new pattern emerges.

| Evaluator | Logic |
|---|---|
| `boolean` | fact is true → full credit; fact is false → zero |
| `exact_match` | fact equals param → full credit; in `partial_credit` list → half; else zero |
| `range` | fact in `full_credit` range → full; in `partial_credit` ranges → half; else zero |
| `linear_scale` | proportional points based on fact value within range |
| `count_threshold` | fact ≥ threshold → full; fact ≥ partial_threshold → half |
| `presence` | path resolves to non-null and non-empty → full credit |

#### 3.1.4 Initial SEO rubric — the 40-60 rules

This is the rubric draft that will be reviewed with BLC during scoring calibration. **Share a draft as soon as the first scoring outputs exist so review can happen in parallel with implementation.** Categories and target rule counts:

- **Meta tags (10 rules):** title length, title uniqueness across pages, description length, description presence, OG tags, Twitter card, canonical URL, etc.
- **Heading structure (6 rules):** exactly one H1, H1 contains primary keyword indicator, heading hierarchy not skipped (no H4 without H3), descriptive H2s, etc.
- **Content (6 rules):** word count thresholds per page type, content freshness signals, readability proxies.
- **Links and structure (6 rules):** internal link count thresholds, broken link rate, anchor text quality proxies, sitemap presence.
- **Images (4 rules):** alt-text coverage rate, oversized image count, image format modernity (WebP usage).
- **Technical (8 rules):** HTTPS, robots.txt valid, sitemap present, schema.org structured data, mobile-friendly Lighthouse pass, indexability of homepage.
- **Performance via PSI (6 rules):** LCP threshold, CLS threshold, TBT threshold, performance score mobile, performance score desktop, image optimization score.
- **Local SEO (4 rules):** NAP (name/address/phone) consistency, LocalBusiness schema, contact page presence, Google Business Profile mention.

**Target: 50 rules for SEO.**

#### 3.1.5 Initial UX/UI rubric

- **First impression (6 rules):** value prop above fold, primary CTA above fold, hero clarity proxies, page load speed proxy.
- **CTAs (6 rules):** primary CTA presence per page, CTA text quality (action verbs), button vs link ratio, CTA color contrast.
- **Forms (4 rules):** form on homepage, form field count ≤ 5, form labels present, form submit button copy.
- **Trust signals (5 rules):** testimonials, reviews/ratings, badges/certifications, case studies, team photos.
- **Mobile (4 rules):** mobile-friendly Lighthouse, viewport meta, tap target sizes, no horizontal scroll.
- **Lead capture (5 rules):** phone clickable, phone above fold, email capture, contact page reachable in 2 clicks, "request a quote" type CTA present.
- **Performance impact on conversion (4 rules):** LCP < 2.5s, CLS < 0.1, TBT < 200ms, no full-page redirects.

**Target: 35 rules for UX/UI.**

#### 3.1.6 Score normalization

Two normalization options to choose at rubric-design time:

- **Sum-of-weights mode:** rules sum to exactly 100; awarded points sum directly to score. Simpler, easier to reason about. Recommended.
- **Rescale mode:** rules sum to anything; final score = (sum_of_awarded / sum_of_weights) × 100. Useful if you want to add rules without rebalancing existing weights.

**Decision: sum-of-weights mode.** Easier to explain to BLC; the per-rule audit trail directly shows "this rule contributed 5 of 100 points."

#### 3.1.7 Lead Generation Readiness Score

In Phase 1 (no social):
```
lead_gen_readiness = round(0.45 * seo_score + 0.55 * uxui_score)
```

Weighting reasoning: lead generation correlates more with conversion (UX/UI) than with traffic acquisition (SEO) once a site has minimum viable SEO. **Surface this weighting choice with BLC at the kickoff and confirm.** The weights live in `rubrics/composite.yaml` and are tunable like everything else.

In Phase 2 (with social):
```
lead_gen_readiness = round(0.35 * seo_score + 0.40 * uxui_score + 0.25 * social_score)
```

#### 3.1.8 Reproducibility guarantee

The rubric engine is pure: same facts in, same scores out. No randomness, no time-dependence, no LLM. This is what makes acceptance criterion #2 ("same site, audited twice, produces identical numeric scores") trivially achievable.

The non-determinism in the system is isolated to the LLM commentary stage, where it is acceptable because users do not compare commentary text across runs the way they compare numeric scores.

### 3.2 The PDF report — design and engineering

#### 3.2.1 Why this is hard (recap)

Naive HTML-to-PDF breaks on long structured documents: page breaks land mid-content, headers don't repeat, tables get sliced, fonts disappear, layouts misalign. Reports with variable content length (5 findings vs 50) test the layout fresh every time. Acceptance criterion #5 is the bar: *"professional enough that a BLC team member could send it to a prospect builder."*

#### 3.2.2 Tool choice: WeasyPrint

The report-rendering options considered were React + Puppeteer and WeasyPrint. For Phase 1, the recommendation is **WeasyPrint** specifically, for these reasons:

- Native print-CSS support: `@page`, running headers/footers, page counters, page-break controls — all work out of the box.
- Pure Python — runs in the same process as the worker, no headless browser to manage.
- Better at long structured documents than Puppeteer; Puppeteer's strength is interactive web pages, which we don't need.
- Mature, stable, used in production by many docs-as-code pipelines.

The HTML report template is still a regular HTML+CSS file. If Phase 2 needs an interactive web dashboard, the template can be rendered to both PDF (via WeasyPrint) and live HTML (via React) — but in Phase 1 we render only to PDF.

#### 3.2.3 Report structure

Page-by-page layout:

| Page | Content | Notes |
|---|---|---|
| 1 | Cover | BLC logo, "Website Audit Report", site URL, audit date. No header/footer. |
| 2 | Table of contents | Auto-generated, page numbers from CSS counters |
| 3 | Executive summary | One-page overview: scores at a glance, top-3 findings, top-3 recommendations |
| 4 | Score breakdown | Visual: SEO, UX/UI, Lead Gen Readiness as scored bars/dials. Per-category sub-scores. |
| 5–N | SEO findings & recommendations | Findings list, then Quick Wins / Mid-Term / Long-Term |
| N+1–M | UX/UI findings & recommendations | Same structure |
| M+1 | Methodology appendix | Brief: how scoring works, per-rule transparency note |
| M+2 | Closing / contact | "Questions? Contact your BLC team." |

Header (page 2 onward): `Builder Lead Converter · Website Audit · {site_domain}` left-aligned; page number right-aligned.

Footer: `Generated {date} · Page X of Y`.

#### 3.2.4 Print CSS pattern

```css
@page {
  size: Letter;  /* US Letter for US client */
  margin: 0.75in 0.5in 0.75in 0.5in;
  @top-left {
    content: "Builder Lead Converter · Website Audit · " string(site-domain);
    font-size: 9pt;
    color: #666;
  }
  @top-right {
    content: counter(page);
    font-size: 9pt;
    color: #666;
  }
  @bottom-center {
    content: "Generated " string(audit-date) " · Page " counter(page) " of " counter(pages);
    font-size: 8pt;
    color: #999;
  }
}

@page :first {
  /* Cover page: no header, no footer */
  @top-left { content: ""; }
  @top-right { content: ""; }
  @bottom-center { content: ""; }
  margin: 0;
}

h1, h2 { page-break-after: avoid; }
.finding-card { page-break-inside: avoid; }
.score-bar { page-break-inside: avoid; }
.recommendation { page-break-inside: avoid; }
table { page-break-inside: auto; }
table thead { display: table-header-group; }  /* repeat headers */
```

#### 3.2.5 BLC brand integration

The PDF template loads brand variables from a single config file:

```yaml
# brand/blc.yaml
logo_path: "brand/blc-logo.svg"
primary_color: "#1a3a5c"     # placeholder until actual brand asset arrives
accent_color: "#f5a623"      # placeholder
font_heading: "Inter"
font_body: "Inter"
```

If brand assets arrive early, use them immediately in the PDF template. If they arrive late, develop with clearly marked placeholder branding and swap the real assets during PDF polish.

#### 3.2.6 PDF testing strategy

- **Synthetic tests:** generate reports from fixture data with 5, 25, and 50 findings each. Verify pagination doesn't break.
- **Real tests:** before final PDF QA, render reports for at least three real builder sites. Eyeball every page break.
- **Regression test:** snapshot one canonical PDF page-by-page; subsequent builds must produce identical PDFs from identical inputs (font rendering aside).

#### 3.2.7 PDF scope controls

The PDF is treated as a first-class product surface, not a last-minute export. Keep the report structure fixed, build from fixture data early, and test short, medium, and long reports before final QA.

If PDF work starts expanding beyond the agreed report sections, treat that as scope change. The required Phase 1 report is: cover, executive summary, score overview, SEO findings, UX/UI findings, recommendations roadmap, methodology appendix, headers, footers, and page numbers.

---

## 4. Repository structure

```
blc-audit/
├── README.md
├── docker-compose.yml          # local dev: api + worker + redis + postgres
├── pyproject.toml              # poetry/uv
├── .env.template
├── .gitignore
│
├── apps/
│   ├── api/                    # FastAPI service
│   │   ├── main.py
│   │   ├── routes/
│   │   │   ├── audits.py
│   │   │   └── health.py
│   │   ├── schemas/            # Pydantic models for request/response
│   │   └── deps.py
│   │
│   ├── worker/                 # Celery worker
│   │   ├── celery_app.py
│   │   ├── tasks.py            # audit pipeline orchestration
│   │   └── stages/
│   │       ├── crawler.py      # Playwright orchestration
│   │       ├── psi_client.py   # PageSpeed Insights wrapper
│   │       ├── extractor_seo.py
│   │       ├── extractor_uxui.py
│   │       ├── scoring.py      # generic rubric engine
│   │       ├── commentary.py   # ChatGPT prompt + parser
│   │       ├── validator.py    # grounding check
│   │       └── pdf_renderer.py # WeasyPrint glue
│   │
│   └── frontend/               # Next.js app (operator UI)
│       ├── package.json
│       ├── pages/
│       │   ├── index.tsx       # submit URL form
│       │   ├── audit/[id].tsx  # progress + download
│       │   └── audits.tsx      # list of past audits
│       └── components/
│
├── rubrics/
│   ├── seo.yaml
│   ├── uxui.yaml
│   └── composite.yaml          # Lead Gen Readiness weights
│
├── prompts/
│   ├── commentary_seo.md
│   ├── commentary_uxui.md
│   └── validator.md
│
├── templates/
│   ├── report.html             # WeasyPrint template (Jinja2)
│   ├── report.css              # print CSS
│   └── partials/
│       ├── cover.html
│       ├── summary.html
│       ├── score_breakdown.html
│       ├── findings.html
│       └── recommendations.html
│
├── brand/
│   ├── blc.yaml
│   ├── blc-logo.svg            # supplied by client
│   └── fonts/
│
├── migrations/                 # Alembic
│   └── versions/
│
├── tests/
│   ├── unit/
│   │   ├── test_scoring_engine.py
│   │   ├── test_extractors.py
│   │   └── test_validator.py
│   ├── fixtures/
│   │   ├── facts_strong_site.json
│   │   ├── facts_weak_site.json
│   │   └── facts_edge_case.json
│   └── integration/
│       └── test_full_pipeline.py
│
└── docs/
    ├── setup.md                # local setup guide
    ├── architecture.md         # detailed architecture diagrams
    ├── rubric_design.md        # rubric philosophy + tuning guide
    ├── operator.md             # operator usage guide
    └── walkthrough_video.md    # script for final walkthrough
```

---

## 5. Build instructions — collectors and extractors

### 5.1 Crawler

Playwright, Chromium, headless. Concurrency: 3 pages at a time per audit (politeness + speed balance).

Discovery strategy for "top 10 internal pages":
1. Fetch homepage.
2. Extract all internal links from rendered HTML.
3. Score each by: presence in main nav (+3), presence in footer nav (+1), prominence on homepage (+ count of inbound links from homepage), URL depth (deeper = lower score).
4. Take top 9 by score.
5. Crawl those 9 + the homepage = up to 10 pages total.

Per-page timeout: 30 seconds. Failed pages do not abort the audit — they are recorded with status "failed" in the crawler output and the audit proceeds with whatever pages succeeded. If the homepage itself fails, the audit fails outright.

User agent: identify ourselves as `BLC-Audit-Bot/1.0 (+https://builderleadconverter.com/audit-bot)`. This is the polite, ethical default.

Respect `robots.txt`. If a page is disallowed, skip it and log.

### 5.2 PageSpeed Insights client

Run PageSpeed Insights for each selected crawled page according to `PSI_SCOPE`. The default scope is `all_crawled_pages`, capped by `PSI_MAX_PAGES` and `CRAWLER_MAX_PAGES`; `homepage` remains available as a lower-cost mode. Each analyzed page receives two PSI calls: mobile strategy and desktop strategy. Cache results by URL+strategy for 24 hours (Phase 1 has low volume, but caching prevents waste during dev iteration).

Persist PSI as a per-page artifact:

```json
{
  "status": "complete",
  "scope": "all_crawled_pages",
  "pages_requested": 7,
  "pages_analyzed": 7,
  "pages": [
    {
      "url": "https://example.com/",
      "mobile": {},
      "desktop": {}
    }
  ],
  "summary": {
    "avg_mobile_performance": 72,
    "avg_desktop_performance": 88,
    "slowest_pages": []
  }
}
```

Failure mode: PSI occasionally returns 429 or 500. Retry with exponential backoff (3 tries). If still failing, audit proceeds without PSI data, and the rubric rules that depend on PSI output evaluate to "skipped" (zero weight contribution to the score, flagged in the audit trail).

### 5.3 SEO extractor

Pure Python, no LLM, no surprise. Uses BeautifulSoup4 for HTML parsing.

Functions are tiny and testable in isolation:

```python
def extract_meta_title(soup: BeautifulSoup) -> tuple[str | None, int]:
    tag = soup.find("title")
    if not tag or not tag.string:
        return None, 0
    text = tag.string.strip()
    return text, len(text)
```

Each extractor function has an input fixture (real HTML snippet) and an expected output. Unit tests run on every commit.

### 5.4 UX/UI extractor

Harder than SEO because some signals require visual judgment ("primary CTA above the fold"). Heuristics:

- **Above-the-fold** = within first 720px of vertical viewport at 1280×720.
- **Primary CTA** = highest-scored button/link in viewport, scored by: contains action verb (`get`, `request`, `start`, `book`, `call`, `schedule`, etc.) +5; styled as a button (background color, padding) +3; appears within hero section +2.
- **Trust signals** = pattern matching on visible text: "testimonial", "review", "rating", "trusted by", "as seen in", star emoji or icon, certification logos, etc.

Heuristics are imperfect by design. Phase 1 ships with documented heuristics, and rubric review surfaces calibration issues before final acceptance.

---

## 6. Build instructions — scoring engine

### 6.1 Rubric loader

```python
def load_rubric(path: str) -> Rubric:
    with open(path) as f:
        data = yaml.safe_load(f)
    return Rubric.model_validate(data)  # Pydantic
```

Rubric files are validated on load. Malformed rubric → loud error at startup, not silent at runtime.

### 6.2 Rule evaluation

```python
def evaluate_rule(rule: Rule, facts: dict) -> RuleResult:
    value = jsonpath(facts, rule.fact_path)
    if value is None:
        return RuleResult(
            rule_id=rule.id,
            result="skipped",
            points_awarded=0,
            evidence={"reason": "fact_not_present"}
        )
    evaluator = EVALUATORS[rule.evaluator]
    return evaluator(rule, value)
```

The `EVALUATORS` dict maps `"range"`, `"boolean"`, `"exact_match"`, etc. to their implementations. Adding a new evaluator type means writing one function and registering it.

### 6.3 Score composition

```python
def score_category(rubric: Rubric, facts: dict) -> CategoryScore:
    results = [evaluate_rule(rule, facts) for rule in rubric.rules]
    awarded = sum(r.points_awarded for r in results)
    max_points = sum(r.weight for r in rubric.rules if r.result != "skipped")
    if rubric.weight_normalization == "sum_of_weights":
        score = round(awarded)
    else:
        score = round((awarded / max_points) * 100) if max_points else 0
    return CategoryScore(category=rubric.category, score=score, rules=results)
```

### 6.4 Tests

- Unit test every evaluator with tabulated inputs/outputs.
- Snapshot-test full rubric runs against fixture facts. If a rubric change moves a fixture's score, the test fails loudly and the diff is reviewed.
- Calibration test: assert that `facts_strong_site.json` scores ≥ 75 and `facts_weak_site.json` scores ≤ 50. This protects acceptance criterion #3 (calibration).

---

## 7. Build instructions — ChatGPT commentary pipeline

### 7.1 Prompt structure

System prompt enforces five rules, in this order:

1. You are commentating on a website audit. You will be given facts and category scores. You may comment on them.
2. **You may not introduce numeric or factual claims that are not in the input data.** If a number isn't in the facts, you cannot use it.
3. Output strictly in the JSON schema provided. No prose outside the JSON.
4. Recommendations must be specific and actionable. Do not say "improve SEO." Say "add a meta description to the /services page (currently missing)."
5. Tier each recommendation as Quick Win (0–30 days), Mid-Term (1–3 months), or Long-Term (3–12 months).

User-message payload includes:
- Site URL
- Niche metadata if provided
- Category scores
- The 10 lowest-scoring rules (most material findings)
- The 5 highest-scoring rules (what's working)
- Selected raw facts that ground the commentary

Output schema is enforced via OpenAI Structured Outputs: the worker passes a Pydantic schema to the OpenAI SDK and validates the parsed response before saving it. This eliminates parser fragility.

### 7.2 Models

- Use an OpenAI ChatGPT model for the main commentary call.
- Optional cheaper model usage is allowed only for low-risk classification tasks, not for numeric scoring.
- Store the exact provider, model ID, prompt version, token usage, and completion status with each audit result.

The exact model ID should be configured through environment variables at implementation time. Do not hard-code model IDs in prompts or scoring logic.

### 7.3 Validator

Second-pass check. Inputs: the commentary JSON + the original facts. Logic:

1. Extract every numeric claim and proper-noun claim from the commentary text (regex + simple NLP).
2. For each claim, verify it appears verbatim or with trivial transformation in the facts JSON.
3. Claims that don't match get logged to `validation_log` and either flagged or stripped depending on severity.

Implementation can be either a deterministic matcher or a second OpenAI call asking "given these facts, are these claims grounded?" with structured output. **Phase 1 starts with the deterministic matcher; if false-positive rate is too high during final QA, swap to LLM-validator.**

---

## 8. Build instructions — frontend

Next.js App Router, TypeScript, Tailwind, shadcn/ui.

Three pages, that's it:

1. **`/`** — single form: URL field, optional niche dropdown, submit button. POST to `/api/audits`, redirect to `/audit/{id}`.

2. **`/audit/[id]`** — polls `/api/audits/{id}/status` every 2s. Shows progress bar with current stage label. When complete, shows scores + download button.

3. **`/audits`** — list of past audits with timestamps, URLs, scores, links to PDFs. Useful for BLC team to see history during evaluation.

No login. No fancy state management. React Query for polling.

---

## 9. Build instructions — operations

### 9.1 Local dev

`docker-compose up` brings up Postgres, Redis, the API, and a worker. The frontend runs separately via `npm run dev`. A seed command should load sample audit jobs or fixture report data for UI development.

Local development is the first-class target until the complete audit flow works. Cloud hosting, AWS, and production operations should not block the first working product loop.

### 9.2 Local storage first, cloud storage later

Phase 1 starts with local filesystem report storage so PDF generation and download can be tested without cloud infrastructure.

The storage layer must still be designed behind a small interface:

- `save_report(audit_id, bytes) -> storage_key`
- `get_report(storage_key) -> bytes`
- `get_report_url(storage_key) -> str | None`

Initial implementation: local filesystem.

Later implementation: S3-compatible object storage.

### 9.3 Production-readiness preparation

Production deployment is prepared after local end-to-end success. Preparation includes:

- Final API Dockerfile
- Final worker Dockerfile
- Environment variable documentation
- Migration command documentation
- Health check endpoint
- Storage interface ready for S3-compatible object storage
- Startup commands for API, worker, and frontend

This is readiness work, not a requirement to deploy before the application is proven locally.

### 9.4 Observability

For local-first Phase 1, keep observability lean:

- Structured application logs
- Worker logs for stage start, stage completion, and failures
- Job status stored in `audit_jobs`
- Validation logs stored with audit results
- Optional Sentry integration after meaningful flows exist

### 9.5 Paid service expectations

| Service | Phase 1 role |
|---|---|
| OpenAI API access | Required for commentary |
| Google Cloud account / PSI API access | Required for PageSpeed Insights data |
| Simple staging hosting | Optional after the app works locally |
| Sentry | Optional after meaningful flows exist |
| AWS production stack | Not needed at the start |
| SEMrush / Ahrefs / Similarweb | Not in Phase 1 |
| Social scraping providers | Not in Phase 1 |

---

## 10. Local-first execution sequence

This section defines build order by dependency, not by calendar. The rule: prove product behavior locally before production infrastructure work.

### 10.0 Pre-build alignment

- Confirm Lead Gen Readiness Score weights. Proposed default: 0.45 SEO / 0.55 UX/UI.
- Receive 5–10 example builder/remodeler test sites.
- Receive BLC brand assets, or approve placeholder branding until real assets arrive.
- Confirm communication channel for status updates and review requests.
- Confirm OpenAI and PageSpeed Insights access.

### 10.1 Foundation

**Goal:** Local services and repo structure exist.

- Repo scaffold
- Docker Compose
- FastAPI skeleton
- Postgres + Alembic migration setup
- Celery + Redis worker skeleton
- Next.js frontend skeleton
- Local `.env.template`

**Exit criteria:** API, worker, Postgres, Redis, and frontend can run locally.

### 10.2 Backend and worker pipeline

**Goal:** Audit jobs can be created, queued, processed, and tracked.

- `POST /audits`
- `GET /audits/{id}/status`
- `GET /audits/{id}/report`
- `GET /audits`
- `GET /health`
- Celery audit orchestration task
- Stage progress updates
- Failure handling

**Exit criteria:** A placeholder audit can run through the worker and update job status.

### 10.3 Crawling and data collection

**Goal:** Raw website and performance data flows into the pipeline.

- Playwright homepage render
- Internal link extraction
- Top-page selection
- Up to 10 total crawled pages, including the homepage
- robots.txt respect
- Same-domain enforcement
- Page timeouts
- PageSpeed Insights mobile + desktop calls for each selected crawled page
- Graceful PSI failure handling

**Exit criteria:** Several real builder/remodeler sites produce structured crawl and PSI artifacts.

### 10.4 Extractors

**Goal:** Deterministic SEO and UX/UI facts are extracted from crawl artifacts.

- SEO extractor
- UX/UI extractor
- Fixture HTML samples
- Expected output snapshots
- Unit tests for normal, missing-data, and malformed HTML cases

**Exit criteria:** Extractor tests pass and outputs are schema-valid.

### 10.5 Scoring and calibration

**Goal:** Reproducible scores with visible audit trails.

- YAML rubric loader
- Rule evaluators
- SEO score
- UX/UI score
- Lead Gen Readiness score
- Per-rule evidence
- Calibration on sample sites

**Exit criteria:** Same facts produce identical numeric scores and score breakdowns are explainable.

### 10.6 ChatGPT commentary and grounding

**Goal:** Specific recommendations are generated without unsupported factual claims.

- ChatGPT client
- Structured JSON output schema
- SEO prompt
- UX/UI prompt
- Quick Wins / Mid-Term / Long-Term recommendation tiers
- Grounding validator
- Validation log

**Exit criteria:** Commentary validates against schema and unsupported numeric claims are caught.

### 10.7 PDF report

**Goal:** A polished report can be generated from one report payload.

- Report composer
- WeasyPrint template
- Cover page
- Executive summary
- Score breakdown
- SEO findings
- UX/UI findings
- Recommendations roadmap
- Methodology appendix
- Brand config
- Short, medium, and long report QA

**Exit criteria:** PDFs render locally and are presentable for BLC review.

### 10.8 Operator UI

**Goal:** A BLC operator can run the audit flow through the UI.

- URL submission page
- Optional niche/audience field
- Progress page
- Failure state
- Completion state
- Audit history page
- PDF download

**Exit criteria:** An operator can submit a URL, watch progress, and download the report.

### 10.9 Local QA and production-readiness

**Goal:** Full local flow works, then production packaging is prepared.

- End-to-end local audit QA
- Same-site reproducibility QA
- ChatGPT grounding QA
- PDF pagination QA
- Final API Dockerfile
- Final worker Dockerfile
- Environment documentation
- Storage abstraction for local filesystem now and S3 later

**Exit criteria:** The app works locally end-to-end, and future staging/production deployment has clear packaging and configuration.

---

## 11. Quality gates

Before declaring Phase 1 complete, every one of these must pass:

| # | Gate | How to verify |
|---|---|---|
| Q1 | Local end-to-end audit completes without manual intervention | Submit fresh URLs via the operator UI and verify PDFs are generated |
| Q2 | Reproducibility | Audit the same site twice; compare numeric scores byte-identical |
| Q3 | Calibration | Audit contrasting sites; manually rate each strong/medium/weak; verify scores rank in the same order |
| Q4 | Grounding | Sample reports; verify numeric claims in commentary appear in facts JSON or are removed |
| Q5 | PDF presentability | Review short, medium, and long reports for layout and client-readiness |
| Q6 | Rubric tunability | Change one rule weight; re-run audit; verify score moves in the expected direction |
| Q7 | Documentation completeness | A fresh developer can follow setup docs and run a local audit |
| Q8 | Production-readiness | API and worker containers, env docs, migration command, and storage abstraction are prepared |

---

## 12. Handover artifacts

Delivered when Phase 1 is accepted:

1. **Working local system** — can audit real builder/remodeler websites end-to-end
2. **Source code** — delivered via private Git repo, ownership transferred to BLC
3. **Walkthrough video** — covers how to run an audit, where the rubric lives, how to tune weights, and how to read a score breakdown
4. **Sample reports** — 5–10 fully rendered PDFs from real builder/remodeler sites
5. **Setup guide** — clone, install, configure, run locally
6. **Architecture overview** — visual diagram + text walkthrough
7. **Rubric tuning guide** — evaluator types, adding rules, changing weights, reading audit trails
8. **Operator manual** — submitting audits, interpreting scores, downloading reports, handling failures
9. **Known limitations** — crawler limits, PSI dependency, heuristic UX/UI detection, Phase 1 exclusions
10. **Production-readiness notes** — container startup, env vars, migrations, storage options, deployment considerations

---

## 13. Phase 2 preview

Not in scope for Phase 1. Documented so later planning is easier.

Focused Phase 2 can include:

- Social media audit foundation after the OAuth-vs-paid-provider decision is made
- YouTube Data API integration
- Paid provider adapter for Instagram/Facebook/LinkedIn public data, if approved
- Social scoring rubric
- Social commentary and grounding
- Multi-user accounts and auth
- Audit history improvements
- Report detail pages
- Shareable report links
- Light competitor comparison using the same website audit pipeline

Later analytics work can include:

- Google Analytics
- Google Search Console
- Microsoft Clarity
- SEMrush
- Funnel analysis
- User behavior flow analysis
- Heatmap/session recording references

---

## 14. Pre-flight checklist

Tick these off before implementation starts:

- [ ] Current Phase 1 local-first scope confirmed
- [ ] Kickoff call held; meeting notes captured
- [ ] Lead Gen Readiness composite weighting confirmed with BLC
- [ ] BLC brand assets received or placeholder branding approved
- [ ] 5–10 test builder/remodeler URLs received from BLC
- [ ] Communication channel agreed
- [ ] Daily update format agreed
- [ ] OpenAI API access available
- [ ] Google Cloud account with PSI API enabled
- [ ] Local dev environment verified: Docker Compose can run Postgres and Redis
- [ ] Production deployment explicitly deferred until local end-to-end success

When every box is ticked, implementation can start.

---

**End of implementation plan.**

This document is designed to be self-contained. If anything in the build is unclear during execution, escalate the gap and update the implementation notes.

— Abdullah Arshed
