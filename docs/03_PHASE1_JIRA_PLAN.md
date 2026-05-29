# Phase 1 Jira Plan

**Project:** BLC Website Audit Automation
**Client:** Builder Lead Converter (BLC)
**Fix Version:** Phase 1
**Document purpose:** Jira-ready Phase 1 plan aligned to the Phase 1 DOCX
**Planning principle:** Build locally first. Production preparation happens only at the end.

---

## 1. Jira Settings

Use these defaults for all Phase 1 Jira issues.

| Field | Value |
|---|---|
| Project | BLC Website Audit Automation |
| Fix Version | Phase 1 |
| Labels | `phase-1`, `website-audit`, `local-first`, `blc` |
| Issue Types | Epic -> Task/Story -> Sub-task |
| Due Dates | Leave blank for now |
| Deployment | Local-first, production prep only at end |
| Out of Scope Labels | `no-social`, `no-auth`, `no-analytics-integrations` |

Out-of-scope labels should be used wherever a Jira issue, comment, or decision needs to explicitly confirm that social media audits, authentication, and analytics integrations are not part of Phase 1.

---

## 2. Phase 1 Scope Lock

Phase 1 is the local-first website audit MVP.

In scope:

- Website URL input.
- Optional niche and target audience metadata.
- Homepage plus up to 10 internal page crawl.
- SEO fact extraction.
- UX/UI fact extraction.
- PageSpeed Insights performance collection.
- Deterministic SEO score.
- Deterministic UX/UI score.
- Deterministic Lead Generation Readiness score.
- OpenAI-generated commentary grounded in extracted facts.
- Branded PDF report.
- Internal operator UI for submit, progress, history, and download.

Out of scope:

- Social media audits.
- User accounts and authentication.
- Multi-tenancy.
- Competitor benchmarking.
- Public share links.
- White-label self-service.
- Google Analytics, Google Search Console, Microsoft Clarity, SEMrush, or similar analytics integrations.
- AWS-first or production-first infrastructure work.

---

## 3. Epic Summary

| Epic | Name | Description |
|---|---|---|
| P1-E1 | Local App Foundation & Backend | Set up the local-first application foundation: repo structure, tooling, Docker Compose, database schema, API endpoints, and audit job lifecycle. |
| P1-E2 | Audit Collection Pipeline | Build the worker-driven audit pipeline that crawls websites, collects PageSpeed data, and extracts structured SEO/UX facts. |
| P1-E3 | Scoring & AI Commentary | Build deterministic scoring and grounded OpenAI commentary. Scores come from rules only; ChatGPT writes commentary from extracted facts. |
| P1-E4 | PDF Report Generation | Generate the branded PDF report from audit metadata, scores, facts, commentary, and recommendations. |
| P1-E5 | Internal Operator UI | Build the internal UI so a BLC operator can submit audits, track progress, view results, and download PDFs. |
| P1-E6 | QA, Packaging & Handoff | Prove the local system works end-to-end, prepare future deployment packaging, and write handoff documentation. |

Recommended delivery order:

1. P1-E1: Local App Foundation & Backend.
2. P1-E2: Audit Collection Pipeline.
3. P1-E3: Scoring & AI Commentary.
4. P1-E4: PDF Report Generation.
5. P1-E5: Internal Operator UI.
6. P1-E6: QA, Packaging & Handoff.

---

## 4. Jira Epics And Tasks

## Epic P1-E1: Local App Foundation & Backend

**Description:** Set up the local-first application foundation: repo structure, tooling, Docker Compose, database schema, API endpoints, and audit job lifecycle.

### P1-1 Set Up Local Project Structure

**Issue type:** Task
**Subtasks:**

- Create backend folder.
- Create worker folder.
- Create frontend folder.
- Create `rubrics/`.
- Create `prompts/`.
- Create `templates/`.
- Create `tests/fixtures/`.
- Add README.

### P1-2 Add Local Development Tooling

**Issue type:** Task
**Subtasks:**

- Add `uv`.
- Add Ruff.
- Add pytest.
- Add TypeScript tooling.
- Add `.env.example`.
- Add setup commands.

### P1-3 Add Local Docker Compose Stack

**Issue type:** Task
**Subtasks:**

- Add PostgreSQL.
- Add Redis.
- Add API service.
- Add worker service.
- Add local report storage.

### P1-4 Create Database Models And Migrations

**Issue type:** Task
**Subtasks:**

- Add `audit_jobs`.
- Add `audit_results`.
- Add timestamps.
- Add status.
- Add progress.
- Add JSON result fields.

### P1-5 Build Audit API And Job Lifecycle

**Issue type:** Task
**Subtasks:**

- Add `POST /audits`.
- Add status endpoint.
- Add report endpoint.
- Add audit list.
- Add health check.
- Add job states.

## Epic P1-E2: Audit Collection Pipeline

**Description:** Build the worker-driven audit pipeline that crawls websites, collects PageSpeed data, and extracts structured SEO/UX facts.

### P1-6 Configure Worker And Pipeline Orchestration

**Issue type:** Task
**Subtasks:**

- Add Celery setup.
- Add Redis connection.
- Add enqueue audit flow.
- Add stage progress.
- Add failure handling.

### P1-7 Build Safe Playwright Website Crawler

**Issue type:** Task
**Subtasks:**

- Render homepage.
- Collect selected internal pages up to the crawler max page cap.
- Add same-domain rules.
- Respect `robots.txt`.
- Add timeouts.
- Add failed-page logs.

### P1-8 Add PageSpeed Insights Collection

**Issue type:** Task
**Subtasks:**

- Add mobile call.
- Add desktop call.
- Run PSI for crawled pages according to `PSI_SCOPE`.
- Cap multi-page PSI with `PSI_MAX_PAGES`.
- Add per-page PSI summary averages and slowest pages.
- Add retries.
- Add timeouts.
- Add normalized PSI facts.
- Add graceful failure.

### P1-9 Build SEO And UX/UI Extractors

**Issue type:** Task
**Subtasks:**

- Extract meta tags.
- Extract headings.
- Extract links.
- Calculate image alt coverage.
- Detect schema.
- Detect CTAs.
- Detect forms.
- Detect phone/email.
- Detect trust signals.

### P1-10 Add Extractor Fixtures

**Issue type:** Task
**Subtasks:**

- Add strong site fixture.
- Add weak site fixture.
- Add malformed HTML fixture.
- Add expected outputs.
- Add fixture tests.

## Epic P1-E3: Scoring & AI Commentary

**Description:** Build deterministic scoring and grounded OpenAI commentary. Scores come from rules only; ChatGPT writes commentary from extracted facts.

### P1-11 Add YAML Scoring Rubrics

**Issue type:** Task
**Subtasks:**

- Add SEO rubric.
- Add UX/UI rubric.
- Add composite rubric.
- Add rubric versioning.
- Add schema validation.

### P1-12 Build Rule Evaluators And Score Composer

**Issue type:** Task
**Subtasks:**

- Add boolean evaluator.
- Add presence evaluator.
- Add range evaluator.
- Add exact match evaluator.
- Add threshold evaluator.
- Add linear scale evaluator.
- Add skipped rules.
- Add score breakdown.

### P1-13 Calibrate Phase 1 Scores

**Issue type:** Task
**Subtasks:**

- Run sample sites.
- Review strong/weak examples.
- Tune weights.
- Save rubric version.

### P1-14 Build ChatGPT Commentary And Prompts

**Issue type:** Task
**Subtasks:**

- Add OpenAI client.
- Add prompt templates.
- Add JSON schema.
- Add recommendations tiers.
- Add Pydantic validation.

### P1-15 Add Grounding Validator

**Issue type:** Task
**Subtasks:**

- Extract numeric claims.
- Compare against facts.
- Log unsupported claims.
- Strip or flag bad claims.
- Add tests.

## Epic P1-E4: PDF Report Generation

**Description:** Generate the branded PDF report from audit metadata, scores, facts, commentary, and recommendations.

### P1-16 Build Report Payload Composer

**Issue type:** Task
**Subtasks:**

- Add report schema.
- Add metadata.
- Add scores.
- Add findings.
- Add recommendations.
- Add validation summary.
- Add PageSpeed summary.

### P1-17 Build Branded PDF Template

**Issue type:** Task
**Subtasks:**

- Add cover page.
- Add executive summary.
- Add score overview.
- Add SEO section.
- Add UX/UI section.
- Add roadmap.
- Add appendix.
- Add headers/footers.

### P1-18 Add Branding Configuration

**Issue type:** Task
**Subtasks:**

- Add logo path.
- Add primary color.
- Add accent color.
- Add fonts.
- Add placeholder fallback.

### P1-19 Run PDF QA

**Issue type:** Task
**Subtasks:**

- Test short report.
- Test medium report.
- Test long report.
- Test missing PSI data.
- Test failed internal pages.
- Fix page breaks.

## Epic P1-E5: Internal Operator UI

**Description:** Build the internal UI so a BLC operator can submit audits, track progress, view results, and download PDFs.

### P1-20 Build Audit Submission Page

**Issue type:** Story
**Subtasks:**

- Add URL input.
- Add optional niche.
- Add optional target audience.
- Add validation.
- Add loading state.
- Add API error state.

### P1-21 Build Audit Progress And Result Page

**Issue type:** Story
**Subtasks:**

- Poll status.
- Show stage.
- Show percentage.
- Show failure.
- Show scores.
- Show PDF download.

### P1-22 Build Audit History Page

**Issue type:** Story
**Subtasks:**

- List recent audits.
- Show status.
- Show created date.
- Show scores.
- Add detail link.
- Add PDF link.
- Add failed/incomplete labels.

## Epic P1-E6: QA, Packaging & Handoff

**Description:** Prove the local system works end-to-end, prepare future deployment packaging, and write handoff documentation.

### P1-23 Run Local End-To-End QA

**Issue type:** Task
**Subtasks:**

- Submit audit.
- Verify API.
- Verify worker.
- Verify crawler.
- Verify extractors.
- Verify scoring.
- Verify OpenAI commentary.
- Verify validation.
- Verify PDF.
- Verify database result.

### P1-24 Run Reproducibility QA

**Issue type:** Task
**Subtasks:**

- Run same site twice.
- Compare SEO score.
- Compare UX/UI score.
- Compare Lead Gen score.
- Compare rule breakdowns.

### P1-25 Prepare Production Packaging

**Issue type:** Task
**Subtasks:**

- Add API Dockerfile.
- Add worker Dockerfile.
- Add migration command.
- Add startup commands.
- Add local storage default.
- Add S3-ready interface later.

### P1-26 Write Developer And Operator Documentation

**Issue type:** Task
**Subtasks:**

- Add setup guide.
- Add architecture overview.
- Add rubric guide.
- Add operator guide.
- Add known limitations.

---

## 5. Phase 1 Done Criteria

Phase 1 is complete when:

- The local application can run end-to-end.
- A BLC operator can submit a website audit from the UI.
- The API creates and tracks an audit job.
- The worker runs the audit pipeline asynchronously.
- The crawler collects up to 10 total pages, including the homepage and selected same-site internal pages.
- PageSpeed data is collected or gracefully skipped.
- SEO and UX/UI facts are extracted.
- Rule-based scores are generated reproducibly.
- OpenAI commentary is validated against extracted facts.
- A branded PDF report is generated and downloadable.
- Audit history and result views work for recent audits.
- Local end-to-end QA and reproducibility QA are complete.
- Production packaging is prepared only after the local system works.
- Developer and operator documentation are written.

---

## 6. Alignment Note

This is the clean Phase 1 Jira plan: 6 epics, 26 implementation tasks, production work at the end, and no social media, authentication, or analytics integrations.
