# Operator Guide (P1-26)

For the BLC operator running website audits through the internal UI. No coding
required — just the running stack.

---

## 1. Before You Start

Make sure the stack is running (a developer typically does this):

- API at `http://localhost:8000` (check `http://localhost:8000/health`)
- Celery worker running (it does the actual audit work)
- Operator UI at `http://localhost:3000`

If you want real performance data and AI-written commentary, the developer must
set `GOOGLE_PSI_API_KEY` and `OPENAI_API_KEY` in `.env`. Without them, audits
still complete: PageSpeed sections are marked skipped and commentary uses a
built-in fallback.

---

## 2. Submitting an Audit

On the home page (`/`):

1. **Website URL** — required. Enter the full site URL (e.g.
   `https://example-builder.com`).
2. **Niche** — optional (e.g. "custom home builder"). Helps the commentary speak
   to the right audience.
3. **Target audience** — optional (e.g. "homeowners planning a renovation").
4. Click **Submit**. You'll be taken to the progress page for that audit.

The form validates the URL and shows an error if the API is unreachable or
rejects the request.

---

## 3. Watching Progress

The progress/result page (`/audit/{id}`) auto-refreshes and shows the current
stage and percentage:

```text
queued → crawling → collecting_performance → extracting → scoring
       → commenting → validating → rendering → complete
```

A typical audit takes from under a minute to a few minutes depending on site
size and whether PageSpeed is enabled. When it reaches **complete**, the page
shows the three scores, findings/recommendations, and a **Download PDF** button.

If something goes wrong, the status becomes **failed** with an error message; the
audit can simply be re-submitted.

---

## 4. Reading the Scores

| Score | Meaning |
|---|---|
| **SEO** | Search-visibility fundamentals: titles, meta descriptions, headings, canonical, schema, image alt text, indexability, internal links, (and PageSpeed when available). |
| **UX/UI** | Conversion and usability signals: CTAs, lead forms, contact details, trust signals, navigation, etc. |
| **Lead Generation Readiness** | A weighted blend (SEO 45% + UX/UI 55%) — the headline "how ready is this site to convert visitors" number. |

Each score has a **per-rule breakdown** (pass / partial / fail / skipped) with the
evidence behind it. Skipped rules (e.g. PageSpeed without an API key) do not lower
the score. Scores are deterministic: the same site audited twice produces the same
numbers.

The **commentary** (executive summary, findings, recommendations) is written from
those facts and scores. Numeric claims are validated against the extracted facts,
so the report won't cite performance numbers it doesn't actually have.

---

## 5. Audit History

The history page (`/audits`) lists recent audits with status, created date,
scores, and quick links to the detail view and the PDF. Failed or incomplete
audits are labeled so you can spot and re-run them.

---

## 6. Downloading & Sharing the Report

From the result page or history, click the report link to download the branded
PDF (`GET /audits/{id}/report`). Files are stored locally under
`storage/reports/<audit-id>.pdf`. The PDF is the prospect-facing deliverable:
cover page, executive summary, score overview, SEO and UX/UI sections with the
rule trail, a recommendations roadmap, and an appendix.

---

## 7. Pre-Demo Smoke Test (real site, runbook)

To validate the full live path (real crawl + PageSpeed + OpenAI) before a client
demo:

1. Set `OPENAI_API_KEY` and `GOOGLE_PSI_API_KEY` in `.env`.
2. Start the stack: `make docker-up` (or run API + worker natively).
3. Submit a real builder/remodeler URL from the UI (or via the API):

   ```bash
   curl -X POST http://localhost:8000/audits \
     -H 'Content-Type: application/json' \
     -d '{"url": "https://example-builder.com", "niche": "custom home builder"}'
   ```

4. Poll status until `complete`:

   ```bash
   curl http://localhost:8000/audits/<job_id>/status
   ```

5. Download and review the PDF:

   ```bash
   curl -L -o report.pdf http://localhost:8000/audits/<job_id>/report
   ```

6. Confirm: scores look sensible, commentary is specific to the site, PageSpeed
   numbers appear, and the PDF paginates cleanly.

---

## 8. When Something Looks Off

| Symptom | What it usually means |
|---|---|
| PageSpeed sections say "skipped" | No `GOOGLE_PSI_API_KEY`, or PSI timed out — scores are unaffected |
| Commentary looks generic / `local_fallback` | No `OPENAI_API_KEY` set |
| Some internal pages listed as "failed" | Those pages timed out or errored; the audit still completes on the rest |
| Audit stuck and then "failed" | The worker hit a time limit or an unreachable site; re-submit |
| "Report not available yet" | The audit hasn't finished rendering; wait for `complete` |
