# 20 - Semrush AI Visibility Integration Plan

> **✅ BUILT (2026-07-16; auto-run added 2026-07-17).** Implemented as the **login-bot +
> OpenAI-vision-extraction** feed (the operator chose the bot path over CSV-first). As-built shape: a
> new `apps/worker/stages/ai_visibility/` package (`schema` / `providers` + registry / `collector` /
> `vision` / `semrush_scraper` / `report`), facts stored in `score_breakdown["ai_visibility"]` (no
> migration), and an "AI Visibility" section on PDF + DOCX + the `/audit/[id]` UI.
>
> **Runs two ways:** (1) **AUTO on every website/combined audit** via
> `tasks._augment_with_ai_visibility_safely` in the main pipeline — gated on `ai_visibility_enabled`
> (OFF by default), graceful-skip on any failure so the audit never breaks; and (2) **on-demand**
> refresh via `rerun_ai_visibility_for_audit` + `POST /audits/{id}/rerun-ai-visibility` (a "Refresh AI
> Visibility" button) to re-pull without re-running the whole audit. Presentation only — **scores are
> byte-for-byte unchanged** whether it ran or not (QA repro verified; the hermetic harness forces
> `AI_VISIBILITY_ENABLED=false`). Config block in `config.py` / `.env.template`; probe/session tool
> `scripts/check_semrush_ai_visibility.py`. Compliance note (§8) still applies (auto-run hits Semrush
> once per audit — keep volume in mind). **First-run step: establish the saved Semrush session once
> with `python scripts/check_semrush_ai_visibility.py --login`.**

**Status:** BUILT (was: planning / build plan).
**Date:** 2026-07-16
**Scope:** Add a **"AI Visibility"** section to the BLC report, fed by the **Semrush AI Visibility
Toolkit** the team already pays for ($99/mo add-on). Covers how the data gets out of Semrush (which
has no API for this toolkit), how it is normalized into BLC facts, and how it renders on PDF/DOCX/UI
— **without breaking the deterministic-scoring architecture.**

**Relationship to prior docs:**
- [13_AI_INSIGHTS_INTEGRATION_PLAN.md](13_AI_INSIGHTS_INTEGRATION_PLAN.md) §9.1/§11.1 already specs
  the *report section* and a vendor-agnostic *fact contract* for AI visibility. **That contract is
  reused here** — this doc only changes the **data source** to Semrush.
- [14_AI_VISIBILITY_VENDOR_SELECTION.md](14_AI_VISIBILITY_VENDOR_SELECTION.md) picked **Rank Prompt**
  (parked, unpurchased). This doc is the **alternative that needs no new subscription**: pull from
  the Semrush account BLC already has. If Semrush proves workable, docs/14's Rank Prompt purchase can
  stay parked indefinitely.

---

## 0. TL;DR — the recommended approach

**Build the report section once, behind a swappable data feed. Ship the zero-risk CSV feed first;
add the Playwright login-bot as a drop-in second feed afterward.**

The hard, valuable engineering is the **report section + fact plumbing** (schema → collector →
report builder → PDF/DOCX/UI), not the feed. Both feeds produce the *same* normalized facts, so the
section is built and tested once and works regardless of how the data arrived.

**Ship order:**
1. **CSV feed first** — operator exports a CSV from the Semrush AI Visibility Toolkit and drops it
   in; BLC parses → facts → report section. **Zero ToS risk, no bot, proves the whole section
   end-to-end.**
2. **Login-bot second** — a Playwright provider that logs into Semrush with a **saved session** and
   clicks the same CSV export, then hands the file to the *same* parser from step 1.

**Before turning the bot on:** email Semrush and request **written approval** for low-volume
automated export from your own account (§8). That single email flips the main risk off.

**Non-negotiable:** the report shows **extracted numbers re-rendered natively**, never a pasted
screenshot (§3). Facts only — this never feeds the score (§7).

---

## 1. The constraint that forces this design

The Semrush **AI Visibility Toolkit has no API and no PDF export** — its *only* programmatic output
is **CSV** (capped at **1,000 rows/export, 10 exports/day/user**). Verified 2026-07-16:

- Semrush's public **Standard/Trends API** and the newer **MCP server** expose domain analytics,
  keyword research, backlinks, and project data — **not** the AI Visibility Toolkit.
- The AI Visibility Toolkit is a separate **$99/mo add-on**; docs list **CSV export only**.
- This matches docs/14 §2.3, which ruled Semrush out as an API source for exactly this reason.

So a **login-bot is the only way to fully automate** Semrush AI-Visibility retrieval today. That is a
legitimate constraint — but it means the bot is a **compliance-risk decision the business owns**
(§8), and the design must minimize both that risk and the fragility that comes with UI automation.

**Why not a screenshot paste (the literal original ask):** the BLC report is deterministic
HTML→PDF via WeasyPrint, with a hard invariant that every numeric claim is grounded in stored facts
([CLAUDE.md](../CLAUDE.md) §10, rules 1/3). A pasted Semrush image would be non-reproducible,
invisible in the DOCX, un-brandable/un-white-labelable, and illegible when the PDF rescales. We want
the **values** (visibility score, mentions, citations, per-LLM distribution, topics, competitors)
lifted into structured facts and re-rendered in BLC's own styling — which is precisely what docs/13
§11.1 already defines.

---

## 2. Architecture fit — reuse the enrichment seam that already exists

This is the **third** enrichment add-on, and the repo already has a proven shape for add-ons that
(a) are optional, (b) run on-demand, (c) store facts in a JSON blob with no migration, (d) render an
optional section that is byte-identical-absent when there's no data, and (e) never touch the score.
The **social** and **competitor-benchmarking** layers are both built this way — copy that shape.

Concretely, mirror `apps/worker/stages/benchmarking/` (providers + registry + collector + typed
schema + pure report builder) and the `_augment_with_benchmark_safely` / rerun wiring:

```
apps/worker/stages/ai_visibility/
  schema.py       AiVisibilityFacts (Pydantic, extra="forbid") + as_facts()
  providers.py    AiVisibilityProvider Protocol + registry  (mirrors benchmarking/providers.py)
  csv_import.py   feed #1: parse a Semrush Toolkit CSV export -> raw payload   (SHIP FIRST)
  semrush_scraper.py  feed #2: Playwright saved-session bot -> clicks export -> same parser
  collector.py    dispatch over registry + graceful skip (skipped/partial/complete/failed/empty)
  report.py       pure build_ai_visibility_report_data(facts) -> section dict | None
```

**Storage (no migration):** stash normalized facts under
`audit_results.external_seo_facts["ai_visibility"]` — exactly the JSON seam docs/13 §10.1 prescribes,
and the same "no new column" trick the `overall_readiness` / `benchmark` keys already use.

**Render:** add an optional `ai_visibility` field to `ReportPayload`
([report_payload.py](../apps/worker/stages/report_payload.py)); guard it in both
[templates/report.html](../templates/report.html) with `{% if payload.get('ai_visibility') %}` (the
same guard the benchmark section uses at report.html:127) and in
`docx_renderer._combined_xml`. Add a frontend card in
[pages/audit/[id].tsx](../apps/frontend/pages/audit/[id].tsx) gated on `status == "complete"`.

**Run path — on-demand only, never the always-on pipeline** (cost + determinism):
- New Celery task `rerun_ai_visibility_for_audit(job_id)` + `POST /audits/{id}/rerun-ai-visibility`,
  **mirroring `rerun_external_enrichment_for_audit`** ([tasks.py:858](../apps/worker/tasks.py#L858))
  and its endpoint ([routes/audits.py:277](../apps/api/routes/audits.py#L277)).
- **Snapshot the result fields before enrichment and restore them on any failure** — the rerun task
  already demonstrates this (`previous = {...}` at tasks.py:872). A failed scrape/parse leaves the
  prior report byte-identical.
- The read path (opening a report) **never re-scrapes** — it shows the cached facts.

---

## 3. The normalized fact contract (what we store)

Reuse docs/13 §11.1's shape, mapped to what the Semrush Toolkit actually shows (visibility score,
brand mentions, citations, per-LLM distribution, topics/prompts, competitors, mentions-by-country).
`AiVisibilityFacts` (Pydantic, `extra="forbid"`, `status` in the external-source vocabulary
`complete|partial|failed|skipped|empty`) carries, at minimum:

- **provider** (`"semrush_csv"` | `"semrush_bot"`), **retrieved_at**, **domain/brand**, **status**,
  **reason** (why a non-complete run skipped — for logs/tests).
- **summary:** `visibility_score`, `mentions`, `citations`, `share_of_voice_pct`, `platforms_tracked`,
  `prompts_tracked`, `top_competitor`.
- **per_platform:** list of `{platform, mentions, share_pct}` (ChatGPT / Google AI Mode / Gemini /
  Perplexity / …) — the "Distribution by LLM" panel in your screenshots.
- **topics:** list of `{topic, visibility, your_mentions, ai_volume}` — the "Your Performing Topics"
  table.
- **competitors:** list of `{label, visibility_score, mentions}` for the comparison set.
- **by_country** (optional): list of `{country, mentions, share_pct}`.

Only `status == "complete"` (or `partial`) with real data renders a section; anything else → no
section, byte-identical report. The report builder (`report.py`) is **pure** — facts in, section
dict (or `None`) out — matching `build_benchmark_report_data`.

**Grounding:** because these are numbers rendered as-is (not LLM prose), they satisfy the grounding
invariant by construction. If OpenAI polish is ever layered on top (docs/13 §14), the existing
grounding validator already strips any number not present in these stored facts.

---

## 4. Feed #1 — CSV import (ship first, zero ToS risk)

The Toolkit exports CSV. An operator (or, later, the bot) provides that file; BLC parses it.

- **Input path:** simplest v1 = the `POST /audits/{id}/rerun-ai-visibility` request accepts an
  uploaded CSV (or a path to one dropped in a watched dir). No Semrush credentials involved.
- **Parser (`csv_import.py`):** pure, deterministic, defensive (coerce via the repo's `_dict`/`_text`
  helpers; a malformed row is dropped, never raised). Emits the raw payload `collector.normalize`
  expects. **This parser is the reusable core** — the bot feed calls the exact same function.
- **Why first:** it de-risks everything expensive. You prove the schema, collector, report builder,
  PDF/DOCX section, and UI card against **real Semrush data** with **zero** automation risk, and you
  get fixture CSVs for unit tests as a side effect. The whole section can ship and be used manually
  while the bot is still being built.

---

## 5. Feed #2 — the Semrush login-bot (add second, design for low risk)

A `semrush_scraper.py` provider using the async Playwright already vendored for the crawler
([crawler.py](../apps/worker/stages/crawler.py) imports `playwright.async_api`). Four design
decisions that cut both suspension risk and fragility:

1. **Reuse a saved session — do NOT script the email/password login each run.** Repeated headless
   logins from a server IP are the biggest bot-detection flag and will collide with 2FA/CAPTCHA. Log
   in **once** in a headed browser, save Playwright `storage_state` (cookies) to an **encrypted**
   file, and have the bot load that state. Re-auth only when the session actually expires. More
   robust *and* far less bot-like.
2. **Click the official CSV export — don't scrape rendered charts.** Navigating to the report and
   triggering **Export CSV** (respecting the 10/day cap) then parsing the file is dramatically more
   stable than reading React chart DOM nodes, and it **reuses the §4 parser** so there's no second
   extraction codebase. (Live chart-scraping is explicitly the *not-recommended* path: brittle to any
   UI change, highest detection surface.)
3. **Human-like pacing, one server-side account, secrets never exposed.** Rate-limit with jitter and
   a consecutive-failure breaker — reuse the `SITE_HEALTH_REQUEST_DELAY_MS` / breaker knobs already
   in config. One Semrush login lives only in the worker as `SecretStr`; never sent to the frontend,
   never logged.
4. **Degrade gracefully at every failure.** CAPTCHA challenge / layout change / expired session /
   export-cap hit → `status: failed` (+ `reason`), the enrichment task restores the snapshot, and the
   report renders without the section. The bot **never sinks the audit** — same contract as every
   other `_*_safely` stage.

Because feeds #1 and #2 are just two entries behind one registry, adding the bot is **one provider
class + one registry entry + config** — no change to the schema, collector, report builder, task,
endpoint, or templates.

---

## 6. Configuration (all env-driven, following config.py conventions)

Add a settings block (mirror the `benchmark_*` / `apify_*` patterns; absence ⇒ graceful skip):

- `ai_visibility_enabled: bool = False` — master switch for the section.
- `ai_visibility_provider: str = ""` — `"semrush_csv"` | `"semrush_bot"`.
- `semrush_email` / `semrush_password` (`SecretStr | None`) — **bot feed only**; empty ⇒ bot skips.
- `semrush_session_state_path: str` — encrypted `storage_state` location.
- `semrush_ai_visibility_url: str` — the Toolkit report URL to open.
- `ai_visibility_timeout_seconds`, and reuse the site-health delay/breaker knobs for pacing.

Document every field in `.env.template`. Never expose Semrush creds to the frontend container.

---

## 7. Scoring — facts only, no score (unchanged invariant)

V1 adds **no rubric and no score**. AI-visibility data is a **fact source for a report section**,
exactly like the benchmark layer — presentation only, so the SEO/UX/Lead-Gen/Social/Overall numbers
are **byte-for-byte unchanged** whether this ran or not. This preserves reproducibility (the hermetic
QA harness never logs into Semrush) and keeps the deterministic-scoring architecture intact.

If the business later wants AI visibility to influence scores, that's a **separate, deferred**
decision (docs/13 §15.2/§15.3): add `skip_if_missing` YAML rules under SEO, bump the rubric version,
add calibration fixtures. **Not in this plan.**

---

## 8. Compliance — own the decision, then de-risk it

Stated plainly so it's a conscious choice, not a surprise: Semrush's Website Terms of Use prohibit
automated access/scraping "without prior written approval," and they may suspend an account for it.
Mitigations, in order of value:

1. **Email Semrush support/account manager and request written approval** for low-volume automated
   export from your own paid account (5–10 internal users, on-demand, one report at a time). If
   granted, the ToS risk is **gone** and the bot is unambiguously fine.
2. **Ship the CSV feed regardless** — it involves no automated site access at all and is never at
   risk. It's also the fallback if approval is denied or the account is ever flagged.
3. **Keep volume human-scale** — on-demand only, saved session (not repeated logins), official export
   (not scraping), hard rate-limits. This is the difference between "an employee using their own
   login" and "a scraper," both technically and in how it reads to Semrush.

This is a business-risk call for the operator to make; engineering just makes the safe path the
default and the risky path opt-in and gated.

---

## 9. Rollout phases

| Phase | Deliverable | Exit criteria |
|---|---|---|
| **0. Manual validation** | Export a real CSV from the Toolkit for 1–2 sites; eyeball fields. | We know the exact CSV columns → the schema is grounded in real data, not guesses. Sample CSVs saved as fixtures. |
| **1. Schema + report builder** | `schema.py`, `report.py`, unit tests (pure, no network). | Fixtures normalize into stable facts; report builder returns a section (and `None` when empty). |
| **2. CSV feed end-to-end** | `csv_import.py`, `collector.py`, Celery task, `POST …/rerun-ai-visibility`, snapshot/restore, `ReportPayload` field, PDF + DOCX section, UI card. | Operator uploads a CSV → section appears in PDF/DOCX/UI; a bad CSV leaves the report byte-identical. **Section is usable in production, manually fed.** |
| **3. Login-bot feed** | `semrush_scraper.py` (saved-session, CSV-export click), config, pacing/breaker, graceful skip. Opt-in behind `ai_visibility_provider="semrush_bot"`. | Bot pulls the CSV and reuses the Phase-2 parser; CAPTCHA/expiry/UI-change degrade to a website-only report. |
| **4. (Deferred) polish/scoring** | Optional OpenAI narrative over the facts (docs/13 §14) and/or scored rules (docs/13 §15). | Only if the business wants it; separate approval. |

The value lands at **end of Phase 2** — a working AI Visibility report section — with **zero**
compliance exposure. Phase 3 is a pure convenience upgrade on top.

---

## 10. File-by-file checklist

**Backend (new):** `apps/worker/stages/ai_visibility/{schema,providers,csv_import,semrush_scraper,collector,report}.py`

**Backend (edit):**
- `apps/shared/config.py` + `.env.template` — the §6 settings block.
- `apps/worker/tasks.py` — `_augment_with_ai_visibility_safely` (best-effort, like
  `_augment_with_benchmark_safely` at tasks.py:640) + `rerun_ai_visibility_for_audit` (mirror
  tasks.py:858, incl. snapshot/restore); carry the `ai_visibility` key forward on the website-only
  rerun (the generic `setdefault` loop at tasks.py:948 already does this for any add-on key).
- `apps/worker/stages/report_payload.py` — optional `ai_visibility` field + populate from
  `external_seo_facts["ai_visibility"]` via the pure builder (mirror the `benchmark` field at
  report_payload.py:667/731).
- `apps/api/routes/audits.py` + `apps/api/schemas/audits.py` — the new rerun endpoint + response model
  (mirror `rerun-enrichment`).
- `templates/report.html` + `templates/report.css` — the section (guarded `{% if
  payload.get('ai_visibility') %}`) + TOC entry.
- `apps/worker/stages/docx_renderer.py` — the same section in `_combined_xml`.

**Frontend (edit):** `apps/frontend/lib/api.ts` (types + the rerun call),
`pages/audit/[id].tsx` (card + "Refresh AI Visibility" button), `lib/format.ts` (status/provider
labels), `styles/globals.css` (card styling).

**Tests (new):** `test_ai_visibility_schema.py`, `test_ai_visibility_csv_import.py`,
`test_ai_visibility_report.py`, `test_ai_visibility_task.py` (snapshot/restore + graceful skip),
`test_report_payload.py` updates, `test_audit_api.py` endpoint cases, and provider fixture CSV/JSON.
Keep `make qa` / `make qa-repro` untouched — the section is on-demand and never in the hermetic path.

---

## 11. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Semrush suspends the account for automation | Request written approval (§8.1); ship CSV feed as the never-at-risk baseline; saved-session + official-export + rate-limit keeps it human-scale |
| Semrush changes the Toolkit UI, breaking the bot | Export-CSV click is far more stable than chart-scraping; on break → graceful `failed`, CSV feed still works, section degrades out |
| CSV column layout changes | Defensive parser (drop unknown/missing rows, `extra` tolerated on input then normalized); Phase-0 real-CSV fixtures catch drift in tests |
| Screenshot expectation (original ask) | Extract numbers → native render (§3); explain a pasted image breaks PDF/DOCX/branding/grounding |
| Data silently drifts a score | It can't — facts only, no rubric (§7); scoring invariant proven by unchanged QA repro |
| Credentials leak | `SecretStr` in worker only, never frontend, never logged; encrypted `storage_state` |
| Export daily-cap (10/day) hit | On-demand only + cache-on-read (no re-scrape when opening a report) keeps volume well under the cap; cap-hit → graceful skip |

---

## 12. Open questions before Phase 2

1. Written approval from Semrush — will the operator request it before the bot phase, or ship CSV-only
   for now?
2. Which sites/domains seed the Phase-0 CSV validation?
3. Does the section need the **mentions-by-country** panel in v1, or is score + per-LLM + topics +
   competitors enough (country is the fiddliest CSV to normalize)?
4. Should the CSV upload be an API file-upload, or a watched drop-dir the operator copies into?
5. Any white-label concern — should the AI Visibility section honor the same brand overrides as the
   rest of the PDF? (Recommend yes; it's automatic if we render natively.)
```

---

## 13. Authentication in production — session-only bot + how to connect (added 2026-07-20)

**The account-safety rule (as-built):** the audit bot uses ONLY a saved browser session and
**never types the email/password itself** by default (`semrush_allow_headless_login=false`). A
repeated headless credential login is exactly what trips Semrush's CAPTCHA and can flag the account
for "unusual activity" / force-logout (Semrush binds a session to one IP and reacts to
repeated/anomalous logins). So with **no valid session** the bot does not attempt a login at all —
`semrush_scraper` returns `{"__blocked__": "no_session"}`, the collector marks it `failed`, and the
report shows a **"Semrush is not connected yet … connect once"** note. The session is established
**once, by a human**, and reused for weeks.

### Connecting locally (your Mac)
```bash
python scripts/check_semrush_ai_visibility.py --login   # real browser opens; log in; press Enter
```
Saves `storage/semrush_session.json`; every audit reuses it.

### Connecting on a headless server (Option B — VNC)
A headless server has no screen, and Semrush binds a session to the IP it was created on — so the
session must be minted **from the server**. The worker image ships Xvfb + x11vnc + fluxbox for this.
```bash
# On the server (in the repo dir):
make semrush-connect COMPOSE="docker compose -f docker-compose.prod.yml"
# It starts a real browser on a virtual display and a VNC server on the box's localhost:5900.

# From your laptop, tunnel the VNC port and log in:
ssh -L 5900:localhost:5900 <user>@<server>
#   open any VNC viewer at localhost:5900, log into Semrush, reach the dashboard,
#   then press Enter in the make-semrush-connect terminal.
```
The VNC port is published to the **server's localhost only** (`127.0.0.1:5900:5900`) and reached
solely through the SSH tunnel — never public. The saved session lands in the mounted `storage`
volume; the audit bot reuses it. Re-run `make semrush-connect` when the session expires.

### Simpler alternative (Option A — copy the file up)
Mint locally (`--login` on your Mac), then `scp storage/semrush_session.json <server>:.../storage/`.
Works if Semrush tolerates the IP change (don't keep Semrush open on the laptop afterward — two live
IPs force a logout). If it keeps getting logged out, use Option B (mint from the server IP).

### Escape hatch (not recommended)
`SEMRUSH_ALLOW_HEADLESS_LOGIN=true` lets the bot attempt an automatic headless credential login when
there's no session. This re-introduces the CAPTCHA/lockout risk and is only sensible paired with a
residential proxy + anti-detect browser (and even then it violates Semrush's ToS). Default is off.
