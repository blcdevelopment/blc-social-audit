# Phase 1 Confluence Handoff

**Project:** Social Media & Website Auditing Automation
**Client:** Builder Lead Converter (BLC)
**Document purpose:** Confluence-ready stakeholder handoff for Phase 1
**Planning principle:** Build locally first. Prepare production/deployment after the application is working.

---

## 1. Project Overview

BLC needs an automated audit system that can evaluate builder/remodeler websites and generate a useful report for lead-generation improvement.

Phase 1 focuses on the website audit portion only. The goal is to replace manual website audit work with a repeatable system that collects facts, computes deterministic scores, generates grounded AI commentary, and produces a branded PDF report.

The system is designed as a structured pipeline:

1. Submit a website URL.
2. Crawl the site with a real browser.
3. Extract SEO and UX/UI facts.
4. Compute deterministic scores.
5. Generate ChatGPT commentary from extracted facts and score breakdowns.
6. Validate commentary grounding.
7. Render a branded PDF report.
8. Let the operator download the report.

---

## 2. Decision Summary

The plan is strong and executable because it separates product risk from infrastructure risk.

Key decisions:

| Decision | Chosen approach | Reason |
|---|---|---|
| Build strategy | Local-first application build | Faster feedback and less infrastructure friction |
| Phase 1 scope | Website audit only | Keeps the first delivery focused and testable |
| Scoring | Deterministic rules in YAML | Scores must be reproducible and explainable |
| AI role | Commentary only | ChatGPT should explain facts, not invent scores |
| Report format | Branded PDF | Matches the evaluation deliverable and prospect-facing use case |
| Deployment approach | Prepare production later | Avoids AWS/production complexity before the app works |
| Social media | Later phase | Social data access needs a separate product and cost decision |

The application should be considered healthy when the local end-to-end pipeline works reliably before production hosting work begins.

---

## 3. Phase 1 Scope

### In Scope

- Website URL input
- Optional niche / target audience metadata
- Up to 10 total crawled pages, including the homepage and selected same-site internal pages
- JavaScript-capable crawling through Playwright
- PageSpeed Insights mobile and desktop performance data for selected crawled pages
- SEO audit facts
- UX/UI audit facts
- SEO score
- UX/UI score
- Lead Generation Readiness score
- Per-rule score audit trail
- ChatGPT-generated findings and recommendations
- Grounding validator for factual/numeric claims
- Branded PDF report
- Internal operator interface
- Local-first application build
- Production-readiness preparation at the end

### Out Of Scope

- Social media audits
- Instagram, Facebook, LinkedIn, or YouTube social scoring
- User accounts
- Authentication
- Multi-tenancy
- Public share links
- White-label self-service
- Competitor benchmarking through SEMrush, Ahrefs, or Similarweb
- Google Analytics integration
- Google Search Console integration
- Microsoft Clarity integration
- SEMrush keyword/traffic integration
- AWS-first production infrastructure

---

## 4. Local-First Architecture

```text
Next.js Operator UI
        |
        v
FastAPI Backend API
        |
        v
Celery Worker + Redis
        |
        +--> Playwright crawler
        +--> PageSpeed Insights client
        +--> SEO extractor
        +--> UX/UI extractor
        +--> YAML scoring engine
        +--> ChatGPT commentary
        +--> Grounding validator
        +--> WeasyPrint PDF renderer
        |
        v
PostgreSQL + local report storage
```

### Component Responsibilities

| Component | Responsibility |
|---|---|
| Next.js Operator UI | Submit URL, show audit progress, list audits, download PDF |
| FastAPI Backend | API endpoints, job creation, status reads, report retrieval |
| Celery Worker | Runs long audit pipeline asynchronously |
| Redis | Local job broker for Celery |
| PostgreSQL | Stores audit jobs, audit results, facts, scores, commentary, report metadata |
| Playwright | Renders websites with a real browser |
| PageSpeed Insights | Provides performance and Lighthouse-style metrics |
| Extractors | Turn crawled pages into deterministic SEO and UX/UI facts |
| Scoring Engine | Applies YAML rubrics to facts and produces reproducible scores |
| ChatGPT | Writes commentary and recommendations from facts and scores |
| Grounding Validator | Checks that factual and numeric claims trace back to facts |
| WeasyPrint | Renders the branded PDF report |

---

## 5. Phase 1 Data Flow

1. Operator submits website URL through the UI.
2. API validates the URL and creates an `audit_jobs` row.
3. API enqueues a Celery audit task.
4. Worker updates job status to `crawling`.
5. Playwright crawler renders homepage and selected internal pages.
6. PageSpeed Insights client collects mobile and desktop performance data for selected crawled pages according to `PSI_SCOPE` / `PSI_MAX_PAGES`.
7. SEO extractor produces SEO facts.
8. UX/UI extractor produces UX/UI facts.
9. Scoring engine applies YAML rubrics.
10. ChatGPT receives only extracted facts and deterministic score breakdowns.
11. ChatGPT returns structured commentary.
12. Grounding validator checks factual/numeric claims.
13. Report composer builds final report payload.
14. WeasyPrint renders and stores the PDF.
15. API exposes completed status and report download.

---

## 6. Tooling

| Area | Tool |
|---|---|
| Backend API | Python, FastAPI, Pydantic |
| Worker | Celery |
| Queue broker | Redis |
| Database | PostgreSQL |
| Database migrations | Alembic |
| Database access | SQLAlchemy |
| Browser crawler | Playwright |
| HTML parsing | BeautifulSoup4 |
| Structured data extraction | extruct where useful |
| Performance data | Google PageSpeed Insights API |
| Scoring | Pure Python + YAML rubrics |
| LLM commentary | OpenAI GPT-4o |
| PDF rendering | WeasyPrint + Jinja2 + print CSS |
| Frontend | Next.js, TypeScript, Tailwind, shadcn/ui |
| Frontend data fetching | TanStack Query or simple polling |
| Python package management | uv |
| Python lint/format | Ruff |
| Testing | pytest |
| Local services | Docker Compose |

---

## 7. Paid Services

### Needed During Phase 1

| Service | Why It Is Needed |
|---|---|
| OpenAI API access | AI commentary and recommendations |
| Google Cloud account / PSI API access | PageSpeed Insights performance data |

### Optional During Phase 1

| Service | Why It May Be Useful |
|---|---|
| Simple staging hosting | Client demos after the local app works |
| Sentry | Error tracking after the app has meaningful flows |

### Not Needed At The Start

| Service | Reason |
|---|---|
| AWS production stack | Production is intentionally delayed until the app works locally |
| SEMrush / Ahrefs / Similarweb | Competitor benchmarking is not in Phase 1 |
| Apify / Bright Data / social scraping providers | Social audits are not in Phase 1 |
| Clerk / Auth0 / Cognito | Auth is not in Phase 1 |
| Google Analytics / GSC / Clarity integrations | Advanced analytics are later-phase work |

---

## 8. Risks And Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Crawler breaks on real builder sites | Audit cannot complete reliably | Test real sites early, keep page cap, record failed internal pages without failing the whole audit |
| PDF pagination looks unprofessional | Report is not client-ready | Test short, medium, and long report fixtures; use print CSS and page-break controls |
| Scores feel poorly calibrated | BLC may not trust results | Use strong/weak sample sites and tune YAML weights without code changes |
| LLM invents facts | Report credibility drops | Pass only extracted facts and scores; validate numeric/factual claims |
| PSI fails or rate limits | Performance data missing | Retry, then skip PSI-dependent rules gracefully |
| Scope creep into social or benchmarking | Phase 1 slows down | Keep social, benchmarking, auth, and analytics in later phases |
| Production setup distracts from product build | Early velocity slows | Build locally first; prepare deployment only after end-to-end local flow works |

---

## 9. Jira Execution Summary

The Phase 1 execution plan is organized into six outcome-based epics. This keeps Jira manageable while still covering the full local-first website audit build.

Epic summary:

1. Local App Foundation & Backend
2. Audit Collection Pipeline
3. Scoring & AI Commentary
4. PDF Report Generation
5. Internal Operator UI
6. QA, Packaging & Handoff

Recommended ticket structure:

| Epic | Ticket examples |
|---|---|
| Local App Foundation & Backend | Set up project structure, local tooling, Docker Compose, database schema, API endpoints, and job lifecycle |
| Audit Collection Pipeline | Configure Celery, build Playwright crawler, collect PageSpeed data, build SEO extractor, build UX/UI extractor, add fixtures |
| Scoring & AI Commentary | Add YAML rubrics, build rule evaluators, compose scores, calibrate scores, add ChatGPT prompts, validate grounding |
| PDF Report Generation | Build report payload, branded WeasyPrint template, branding config, and PDF QA |
| Internal Operator UI | Add submit page, progress/result page, audit history page, and PDF download |
| QA, Packaging & Handoff | Run local end-to-end QA, run reproducibility QA, prepare container packaging, and write developer/operator documentation |

---

## 10. Phase 1 Acceptance Criteria

Phase 1 is successful when:

- A BLC operator can submit a website URL.
- The backend creates an audit job.
- The worker processes the job asynchronously.
- The crawler renders up to 10 total pages, including the homepage and selected same-site internal pages.
- SEO facts are extracted.
- UX/UI facts are extracted.
- PageSpeed Insights data is collected per selected crawled page or gracefully skipped.
- SEO score is generated deterministically.
- UX/UI score is generated deterministically.
- Lead Generation Readiness score is generated deterministically.
- Score breakdown explains each rule result.
- ChatGPT commentary is specific to the audited site.
- ChatGPT commentary is grounded in extracted facts and scores.
- Unsupported factual or numeric claims are caught or removed.
- A branded PDF report is generated.
- The UI supports submit, progress, history, and download.
- Local end-to-end QA passes.
- Documentation explains setup, architecture, rubrics, operation, and limitations.

---

## 11. Quality Gates

These gates keep the build robust and prevent the project from looking finished before the hard parts are proven.

| Gate | What must be true |
|---|---|
| Crawler gate | Real builder/remodeler sites can be crawled without one failed internal page crashing the full audit |
| Extractor gate | SEO and UX/UI extractors produce schema-valid facts from normal, missing-data, and malformed HTML fixtures |
| Scoring gate | The same extracted facts always produce identical SEO, UX/UI, and Lead Gen scores |
| Calibration gate | Stronger sample sites score higher than weaker sample sites for explainable reasons |
| OpenAI gate | Commentary validates against the expected structure and does not contain unsupported numeric claims |
| PDF gate | Short, medium, and long report examples render cleanly and look presentable |
| Operator gate | The UI supports submit, progress, failure state, history, and PDF download |
| Local QA gate | A full local audit completes without manual intervention |

---

## 12. Handoff Checklist

### Code And Local Setup

- Source code is available in the repository.
- Local setup guide is complete.
- Environment variables are documented.
- Docker Compose stack is documented.
- Database migrations are documented.
- Test commands are documented.

### Product Artifacts

- Sample audit results exist.
- Sample PDFs exist.
- Rubric files are included.
- Prompt files are included.
- PDF templates are included.
- Brand config is included.

### Documentation

- Setup instructions are available.
- Architecture notes are available.
- Rubric tuning notes are available.
- Operator usage notes are available.
- Known limitations are documented.

### Future Production Readiness

- API containerization is prepared.
- Worker containerization is prepared.
- Environment-variable based config is documented.
- Local filesystem report storage is implemented.
- S3-compatible storage can be added later.
- Production hosting is not required for local Phase 1 completion.

---

## 13. Future Phase Notes

### Later Social Audit Work

Future social audit work can add:

- Instagram profile input
- Facebook profile input
- LinkedIn profile input
- YouTube channel input
- YouTube Data API
- Paid provider adapters for public social data
- Social scoring rubric
- Social commentary
- Updated Lead Generation Readiness score including social

### Later Product Expansion

Future product work can add:

- Auth
- Roles
- Audit history improvements
- Dashboard views
- Shareable report links
- Competitor comparisons
- Production AWS deployment
- Monitoring and backups

### Later Analytics Integrations

Future analytics work can add:

- Google Analytics
- Google Search Console
- Microsoft Clarity
- SEMrush
- Funnel analysis
- User behavior flow analysis
- Heatmap/session recording references

---

## 14. Assumptions

- Phase 1 is local-first.
- Production/deployment work is prepared at the end, not front-loaded.
