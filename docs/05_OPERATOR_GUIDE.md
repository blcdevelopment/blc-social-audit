# Operator Guide (P1-26)

For the BLC operator running website audits through the UI. No coding required —
just the running stack.

> **Last reconciled: 2026-07-02.**

---

## 1. Before You Start

**Production** runs at **https://ai.builderleadconverter.com** (single Linode VM,
Caddy-terminated TLS). You sign in with Clerk (see §2) — there's nothing to start.

For **local development** a developer typically brings up the stack:

- API at `http://localhost:8000` (check `http://localhost:8000/health`)
- Celery worker running (it does the actual audit work)
- Operator UI at `http://localhost:3000`

If you want real PageSpeed performance data, the developer must set
`GOOGLE_PSI_API_KEY` in `.env`. Without it, audits still complete: PageSpeed
sections are simply marked skipped and do not lower the score. (Phase 1 commentary
is fully deterministic — it is generated from the extracted facts and scores, and
does **not** call any LLM, so no `OPENAI_API_KEY` is needed for the report prose.)

---

## 2. Signing In (Clerk)

Production is gated by **Clerk** authentication. Open
`https://ai.builderleadconverter.com`, and if you're signed out you'll see a
Welcome screen with a sign-in button. Sign in with your operator account; once
signed in, the full app (submit, history, results, downloads) is available.

Notes:

- **Invitation-only.** Clerk is currently a **dev instance** and open sign-up is a
  known gap, so access is granted by an operator inviting you manually — there is
  no self-serve registration to rely on.
- **Local dev / QA run unauthenticated.** When `CLERK_ISSUER` is unset (the local
  and QA-harness default), the API is open and no sign-in is required. Production
  sets `CLERK_ISSUER`, which turns auth on and gates the entire `/audits/*` API.

---

## 3. Submitting an Audit

On the home page (`/`):

1. **Website URL** — required. Enter the full site URL (e.g.
   `https://example-builder.com`).
2. **Niche** — optional (e.g. "custom home builder"). Helps the commentary speak
   to the right audience.
3. **Target audience** — optional (e.g. "homeowners planning a renovation").
4. **Social media (optional — runs a combined audit)** — expand this panel to paste
   **Instagram**, **Facebook**, and/or **YouTube** profile links or `@handles`.
   Adding **any** of these turns the submission into a **combined audit**: the
   website audit runs first, then the social audit, and you get **one report** with a
   Social Media Audit section and an Overall Lead-Gen Readiness score appended at the
   end (see §3a). Platforms you leave blank may be **auto-detected** from the site's own
   profile links (see §3a); leave them all blank for a website-first audit.
5. **White-label branding (optional)** — override the report logo, name, and colours
   for a prospect-facing PDF (see §9).
6. Click **Start audit**. You'll be taken to the progress page for that audit.

The form validates the URL and shows an error if the API is unreachable or
rejects the request.

---

## 3a. Combined Audits (website + social, one report)

There is **no separate Social Audit tab** — social media is audited from the same
**Website Audit** page (`/`). Whenever you paste at least one social link in the
**Social media** panel (§3 step 4), the submission becomes a **combined audit**:

1. The **website audit runs first**, exactly as it always has (SEO + UX/UI, same
   scores, same sections — nothing about it changes).
2. Then the **social audit runs**: Instagram + Facebook are fetched via **Apify**
   (needs `APIFY_API_TOKEN` on the server) and YouTube via the free **YouTube Data
   API** (`YOUTUBE_API_KEY`). A platform with no configured key is **skipped
   gracefully** — it never fails the audit. Profiles are normalized and scored
   against `rubrics/social.yaml` into a **Social Score (0–100)**; the social findings
   in the combined report are **deterministic** (no LLM).
3. You get **one combined report** — today's website report with a **Social Media
   Audit** section and an **Overall Lead-Gen Readiness** score (§6) **appended at the
   end**, in **both PDF and DOCX**.

**Auto-discovery (blank fields):** platforms you leave blank are auto-filled from
the site's **own** profile links found on the crawled pages (footer/header/nav icons;
third-party mentions like testimonials or agency credits are ignored). Only platforms
whose server key is configured are used, and a plain website submission is upgraded to
a combined audit **only when the social collection actually returns data** — so a
website run either gains a real Social Media Audit section or stays exactly a website
report; it never gains an empty social section. Server-side kill-switch:
`SOCIAL_AUTODISCOVERY_ENABLED=false`.

**Graceful degradation:** if the social/overall step of an explicitly-combined audit
can't run (e.g. the provider returns no data), the audit still completes as a normal
website report with an honest collection note — the social problem never fails the
whole job.

A **social-only** audit (no website URL) is **no longer offered in the UI** — every
audit from the form is either website-only or website+social. (The backend
`social`-only audit type still exists, and any social audits run before this change
still render in History and the detail view.)

---

## 4. Watching Progress

The progress/result page (`/audit/{id}`) auto-refreshes (it polls every 2.5s) and
shows the current stage and percentage:

```text
queued → crawling (15%) → collecting_performance / PSI (45%)
       → extracting / SEO + UX-UI (70%) → extracting / external SEO (76%)
       → scoring (80%) → commenting (88%) → validating (95%)
       → rendering (98%) → complete (100%)
```

The **external-SEO** step (76%) runs the built-in site-health sweep and, if
connected, pulls Google Search Console insights — see §5.

For a **combined** audit, after the website result is saved an extra
**"Auditing social profiles" (96%)** step runs the social audit and computes the
Overall Lead-Gen Readiness score before the single combined report renders (98%).

A typical audit takes from under a minute to a few minutes depending on site
size and whether PageSpeed is enabled. When it reaches **complete**, the page
shows the scores, findings/recommendations, and **Download PDF** /
**Download DOCX** buttons. A combined audit additionally shows the Social Media
Audit block and the Overall Lead-Gen Readiness block at the very end.

If something goes wrong, the status becomes **failed** with an error message; the
audit can simply be re-submitted.

---

## 5. Connecting Google Search Console (optional)

Reports can be enriched with Google Search Console (GSC) data — top ranking
opportunities and URL-inspection facts for the audited site. This is entirely
optional; audits complete fine without it.

Connection is a one-time, **shared** setup, not per-submitter:

1. On the home page (`/`) or the history page (`/audits`), find the
   **"BLC Search Console connection"** panel.
2. If it shows **Not connected**, click **Connect** — you'll be redirected through
   Google's OAuth consent screen for the shared BLC Google account.
3. After granting access, Google returns you to the app and the panel shows
   **Connected** with the connected account email and the available properties.

Notes:

- Website submitters do **not** need their own Search Console account — reports use
  the connected BLC account whenever it has access to the audited site.
- GSC data only appears in a report if the audited site is one of the connected
  account's verified properties. Otherwise the Search Console section simply shows
  that no matching data was available (the score is unaffected).
- To pull GSC into an audit that already finished, use **Rerun enrichment** (§7).

---

## 6. Reading the Scores

| Score | Meaning |
|---|---|
| **SEO** | Search-visibility fundamentals: titles, meta descriptions, headings, canonical, schema, image alt text, indexability, internal links, the site-wide technical crawl, Search Console facts (when connected), and PageSpeed (when available). |
| **UX/UI** | Conversion and usability signals: CTAs, lead forms, contact details, trust signals, navigation, etc. |
| **Lead Generation Readiness** | A weighted blend (SEO 45% + UX/UI 55%) — the headline "how ready is this site to convert visitors" number. |

On a **combined** audit two more numbers appear, appended after the website scores:

| Score | Meaning |
|---|---|
| **Social Score** | The standalone social-media score (0–100) from the Instagram / Facebook / YouTube profiles, scored against `rubrics/social.yaml`. |
| **Overall Lead-Gen Readiness** | The top-line combined number: **70% website Lead-Gen Readiness + 30% Social Score** (config-driven via `rubrics/overall.yaml`). The website dominates because it is the bottom-of-funnel lead-capture surface while social is top-of-funnel demand generation / nurture. If the social audit produced no score, this rescales to the website Lead-Gen score alone. |

Each score has a **per-rule breakdown** (pass / partial / fail / skipped) with the
evidence behind it. Skipped rules — e.g. PageSpeed without an API key, or an
external source (technical crawl / Search Console) that wasn't available — do not
lower the score; the category rescales around them. Scores are deterministic: the
same site audited twice produces the same numbers.

The **commentary** (executive summary, findings, recommendations) is generated
deterministically from those facts and scores (Phase 1 uses no LLM). Numeric
claims are validated against the extracted facts, so the report won't cite
performance numbers it doesn't actually have.

---

## 7. Rerunning External SEO Enrichment

On a **completed** audit's detail page (`/audit/{id}`), a **Rerun enrichment**
button re-runs only the external-SEO step — the technical-crawl sweep and Google
Search Console — then rescores, regenerates commentary, and re-renders the report.
The crawl, PageSpeed, and on-page extraction are **not** repeated.

Use this after you connect Google Search Console (§5), or to refresh the technical
crawl, without resubmitting the whole audit. If the rerun fails, the previous
result and report are restored automatically — the audit stays **complete** with
its prior report, and an error message is shown. (It needs a finished audit with a
stored result; the action is unavailable otherwise.)

For a **combined** audit, the rerun is combined-aware: it re-attaches the stored
social section and recomputes the Overall Lead-Gen Readiness from the freshly
re-scored website Lead-Gen plus the stored Social Score, so the social and overall
sections stay in the re-rendered report (it does **not** re-fetch the social
profiles).

---

## 8. Audit History

The history page (`/audits`) lists recent audits with status, created date,
scores, and quick links to the detail view and the report downloads. Failed or
incomplete audits are labeled so you can spot and re-run them. A combined audit is
tagged with a **"Full"** badge and shows its **Overall** Lead-Gen Readiness score in
the scores column (older standalone social audits still appear with their Social
Score).

---

## 9. Downloading & Sharing the Report

From the result page or history, download the branded report in two formats:

- **PDF** — `GET /audits/{id}/report`, stored locally under
  `storage/reports/<audit-id>.pdf`.
- **DOCX** — `GET /audits/{id}/docx`, an editable Word version rendered on demand
  (generated the first time it's requested if it doesn't already exist).

The report is the prospect-facing deliverable: cover page, executive summary,
score overview, SEO and UX/UI sections with the rule trail, the external-SEO /
Search Console findings, a recommendations roadmap, and an appendix.

For a **combined** audit, the **same** PDF and DOCX additionally carry a **Social
Media Audit** section and an **Overall Lead-Gen Readiness** section appended at the
end — there is no separate social file. A website-only report is byte-for-byte
unchanged (those sections are simply absent).

---

## 10. Pre-Demo Smoke Test (real site, runbook)

To validate the full live path (real crawl + PageSpeed + external SEO) before a
client demo:

1. Set `GOOGLE_PSI_API_KEY` in `.env` (and connect Google Search Console, §5, if
   you want GSC data). Phase 1 commentary is deterministic, so no `OPENAI_API_KEY`
   is required for the report prose.
2. Start the stack: `make docker-up` (or run API + worker natively). For a local
   API call, leave `CLERK_ISSUER` unset so the API is open; otherwise pass a Clerk
   `Authorization: Bearer <jwt>` header.
3. Submit a real builder/remodeler URL from the UI (or via the API):

   ```bash
   curl -X POST http://localhost:8000/audits \
     -H 'Content-Type: application/json' \
     -d '{"url": "https://example-builder.com", "niche": "custom home builder"}'
   ```

   For a **combined** audit, send `audit_type: "combined"` with **both** the `url`
   and at least one social handle:

   ```bash
   curl -X POST http://localhost:8000/audits \
     -H 'Content-Type: application/json' \
     -d '{"url": "https://example-builder.com", "audit_type": "combined",
          "social_handles": {"instagram": "acmebuilders"}}'
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

## 11. When Something Looks Off

| Symptom | What it usually means |
|---|---|
| Welcome screen / can't get in | You're signed out, or your Clerk account hasn't been invited yet (access is invitation-only) |
| PageSpeed sections say "skipped" | No `GOOGLE_PSI_API_KEY`, or PSI timed out — scores are unaffected |
| Search Console section says "not available" | Google isn't connected (§5), or the audited site isn't a property on the connected BLC account — scores are unaffected |
| "Rerun enrichment" unavailable / errors | The audit isn't complete or has no stored result; or the rerun failed and the prior report was restored — try again |
| Some internal pages listed as "failed" | Those pages timed out or errored; the audit still completes on the rest |
| Audit stuck and then "failed" | The worker hit a time limit or an unreachable site; re-submit |
| "Report not available yet" | The audit hasn't finished rendering; wait for `complete` |
