# Report Quality — Jira Epic & Tasks (copy-paste ready)

> **Status: IMPLEMENTED (2026-07-03)** — all RQ-1…RQ-18 done, plus a same-day adversarial
> review round that fixed 4 majors + minors before merge (details docs/17 §10; accepted
> tradeoffs docs/06 §§3/5). Gates: 344 unit tests, QA 11/11, repro byte-identical. RQ-19's
> live re-run remains an operator step. Signoff table: docs/17 §10. Companion to
> [docs/17_REPORT_QUALITY_PLAN.md](17_REPORT_QUALITY_PLAN.md) (full analysis, root causes with
> file:line references, research appendix, decisions D1–D6). Task IDs below are `RQ-n`
> placeholders — Jira will assign real `SMWA-xx` keys on creation; keep the RQ id in the
> description for traceability. Every task cites the reviewer remarks (`#n`, per the plan's §4
> inventory) it closes.

## Epic

**Title:** Report Credibility & Accuracy — expert-review hardening (RQ)

**Description:** A line-by-line expert review of a client-facing combined report (2026-06-30,
builderleadconverter.com) surfaced 26 annotations (22 unique concerns): inflated Search-Console projections (90-day sums
labeled monthly), findings that are structurally false for popup/iframe-form sites (the pattern
BLC itself builds), a site-health checker that gets WAF-throttled and reports the fallout as
139 "dead links", triplicated findings text, inconsistent score naming (83 vs 85), and a set of
jargon/clarity issues. Goal: the report stays readable for an account manager AND survives a
marketing expert's scrutiny. Root-cause analysis, research, and acceptance criteria:
docs/17_REPORT_QUALITY_PLAN.md. Exit gate: RQ-19 re-run signoff against all 26 annotations.

## Board

| ID | Title | Wave | Size | Depends on | Plan item | Remarks closed |
|---|---|---|---|---|---|---|
| RQ-1 | GSC time-basis fix + render data windows | 1 | S | — | A | #3, #5(part), #19 |
| RQ-2 | Defensible search-opportunity model | 2 | M | RQ-1 | B | #4, #5 |
| RQ-3 | Provider-embed form detection (static signatures) | 3 | S | — | C1 | #8(part), #13(part) |
| RQ-4 | Runtime iframe/lazy-form detection in the crawler | 3 | M | RQ-3 | C2 | #8(part), #13(part) |
| RQ-5 | UX rubric v3 — form-detection semantics | 3 | S | RQ-3, RQ-4 | C3 | #8, #13 |
| RQ-6 | Replace email-visible rule with contact-path rule | 1 | S | — | D | #9, #12 |
| RQ-7 | Polite site-health checks + WAF/bot-block detection | 2 | M | — | E | #17 |
| RQ-8 | Merge Findings + Recommendations into one card | 2 | M | RQ-9 | F | #10, #14 |
| RQ-9 | Pair every finding with its fix (PSI/CWV gap) | 1 | S | — | G | #11, #23 |
| RQ-10 | De-duplicate overlapping recommendations | 1 | S | — | H | #22 |
| RQ-11 | Score naming consistency + combined cover | 2 | S–M | — | I | #26 |
| RQ-12 | Client-language pass (jargon removal) | 1 | S | — | J | #6, #7, #15, #16 |
| RQ-13 | Fix TOC order | 1 | XS | — | K | #2 |
| RQ-14 | URL-inspection clarity (selection + canonical column) | 1 | S | — | L | #20, #21 |
| RQ-15 | Label the CWV table scope | 1 | XS | — | M | #24 |
| RQ-16 | Readable chart labels (path-only URLs) | 1 | XS | — | N | #25 |
| RQ-17 | N-gram topic labels | 3 | S | — | O | #18 |
| RQ-18 | Niche/audience input guidance on the form | 3 | S | — | P | #1 |
| RQ-19 | Acceptance re-run + comment-by-comment signoff | gate | S | all | X | all |

---

## Tasks

### RQ-1 — GSC time-basis fix + render data windows
**Type:** Bug (accuracy) · **Wave 1 · Size S** · Plan item A · Closes #3, #19, part of #5

All Search-Console figures are sums over a ~90-day window (`google_search_console.py:245-248`)
but are rendered as "searches a month" / "more visits/month" (`content_plan.py:225-229`,
`templates/report.html:408-413`) — ~3× inflation from labeling alone. The window dates are
already collected (`date_range` fact) but rendered nowhere, and the previous-comparison window
dates are never stored.

**Scope**
- Per decision D1: normalize GSC-derived figures to true monthly (÷ `window_days / 30.44`) —
  or, if D1 lands the other way, keep totals and label every figure "over the last N days".
- Store `previous_date_range`; render both windows in: exec-summary lead-in, Search Performance
  header ("Data window: {start} – {end} ({N} days), compared with the preceding {N} days"),
  declining-pages intro. PDF + DOCX + UI.
- Update stored facts so the grounding validator keeps the new numbers.

**Acceptance**
- No GSC figure in PDF/DOCX/UI is presented as monthly unless actually normalized; both window
  date ranges appear; declining-pages copy references dates that are visible; tests cover the
  normalization and the rendered window strings; grounding validation passes.

---

### RQ-2 — Defensible search-opportunity model
**Type:** Improvement (accuracy) · **Wave 2 · Size M** · Depends RQ-1 · Plan item B · Closes #4, #5

The current model sends every striking query (impressions ≥ 50, positions 4–20) to positions
3–5 simultaneously with no dampening, no cap vs current traffic, using the most optimistic
published CTR curve (First Page Sage P1=39.8% vs 20–28% in GSC-derived studies). "Near-miss
pages" are actually queries, defined two different ways in the same report; "captures only 176
clicks" is the striking subset while total site clicks aren't stored (reviewer's ~0.7K could
not be reconciled). Research: plan §6.1.

**Scope**
- Conservative blended CTR curve, versioned in config (`ctr_curve_version`); FPS demoted to the
  optimistic bound.
- Three scenarios (conservative ≈50% capture / expected ≈70% / optimistic); conservative is the
  headline.
- Model top-N striking queries (default 25); cap headline at ≤3× current total organic clicks;
  store `total_clicks`/`total_impressions` facts (page-dimension, pre-truncation).
- AI-Overview haircut per D5; ramp phrasing (6–12 months); single inline near-miss definition
  ("queries already ranking 4–20 — just below the top results"); say queries, never pages.
- Fixed disclaimer block with stated assumptions.

**Acceptance**
- Rerun on stored facts: conservative headline ≤ 3× current clicks, correctly windowed (RQ-1);
  three scenarios + assumptions render in PDF; exec summary and callout show identical numbers
  and the same definition; calibration test asserts the cap and scenario math; grounding intact.

---

### RQ-3 — Provider-embed form detection (static signatures)
**Type:** Feature · **Wave 3 · Size S** · Plan item C1 · Part of #8, #13

Popup/iframe form builders leave their loader script or iframe src in the initial HTML even when
no `<form>` exists. Add a Wappalyzer-style signature scan over the already-captured page HTML —
zero new network. Signatures (plan §6.3): LeadConnector/GoHighLevel
(`api.leadconnectorhq.com/widget/form|survey|booking/`, `link.msgsndr.com/js/form_embed.js`),
HubSpot (`js.hs-scripts.com`, `js.hsforms.net`, `hbspt.forms.create(`), Typeform
(`embed.typeform.com`, `data-tf-*`), Jotform, Calendly, Gravity Forms, Intercom, Drift.

**Scope**
- `extractor_uxui.py`: new per-page facts `forms.embedded_providers: [str]` and
  `forms.form_detected ∈ {static_form, provider_embed, none}` (runtime value added by RQ-4);
  summary rollups.
- Signature table as data (module-level, easy to extend); unit tests per provider fixture
  snippet; a full popup-form HTML fixture for the QA harness.

**Acceptance**
- A fixture page containing only a LeadConnector iframe yields `provider_embed` +
  `embedded_providers=["leadconnector"]`; pages with no embeds are unchanged (facts byte-equal
  except the new keys defaulting empty/none).

---

### RQ-4 — Runtime iframe/lazy-form detection in the crawler
**Type:** Feature · **Wave 3 · Size M** · Depends RQ-3 · Plan item C2 · Part of #8, #13

`page.content()` serializes the top frame only; the crawler never scrolls or enumerates frames,
so lazy iframes never load and iframe-hosted forms are invisible (`crawler.py:521-581`).

**Scope**
- In `_render_page` after the networkidle wait: incremental scroll-to-bottom (triggers
  `loading="lazy"` iframes), brief settle, then enumerate `page.frames`; per-frame (try/except)
  count `form`/`input` via `frame_locator`; record render-time request URLs matching the RQ-3
  provider domains (`page.on("request")`). No clicking; never fill/submit anything.
- Attach results to `CrawledPage` (in-memory, like axe_results) → extractor merges into
  `forms.form_detected = runtime_iframe_form` when applicable.
- Keep it budget-safe: hard per-page cap (~2–3s extra), skip silently on failure (graceful).

**Acceptance**
- Fixture site with a lazy-loaded iframe form (QA harness server) yields
  `runtime_iframe_form` with a field count; crawl time increase ≤3s/page; failures degrade to
  RQ-3's static result; no interaction side effects (no navigation, no submissions).

---

### RQ-5 — UX rubric v3: form-detection semantics
**Type:** Improvement (scoring) · **Wave 3 · Size S** · Depends RQ-3, RQ-4 · Plan item C3 · Closes #8, #13

**Scope**
- `rubrics/uxui.yaml` → `phase2-uxui-v3` (with RQ-6's change; bump once):
  `uxui.forms.present` passes on `form_detected ∈ {static_form, provider_embed,
  runtime_iframe_form}`; `uxui.homepage_form.field_count` skips/rescales when the detected form
  is an embed whose fields can't be counted — never again "0 homepage form fields" for a popup
  site.
- Finding/remediation copy names the provider ("Lead capture detected: embedded LeadConnector
  popup form"); `content_plan.py` rule context updated.

**Acceptance**
- Popup-form fixture: `uxui.forms.present` passes, field-count skipped, provider named in the
  report; plain `<form>` sites score exactly as before (calibration test); rubric version
  recorded on results.

---

### RQ-6 — Replace email-visible rule with contact-path rule
**Type:** Improvement (scoring) · **Wave 1 · Size S** · Plan item D · Closes #9, #12

`uxui.email.visible` (weight 6) penalizes deliberately-hidden emails; its own remediation text
already promises credit for "a clear contact link" the evaluator never gives
(`uxui.yaml:99-109`).

**Scope**
- `uxui.yaml` (v3 bump shared with RQ-5): replace with `uxui.contact_path.low_pressure` — pass
  on ANY of visible email / mailto / contact-page link (nav/footer anchor to contact-like path)
  / detected form or chat embed. Weight per D2 (recommend 6).
- `extractor_uxui.py`: new `contact.has_contact_page_link` fact. "No visible email" becomes
  info-level context only.

**Acceptance**
- Site with contact page + popup form but no visible email passes; site with no path at all
  fails with the reworded finding; email-only site still passes; calibration tests updated.

---

### RQ-7 — Polite site-health checks + WAF/bot-block detection
**Type:** Bug (accuracy) + Improvement · **Wave 2 · Size M** · Plan item E · Closes #17

The sweep runs up to 8 concurrent zero-delay bot-UA requests against one host, ignores
429/Retry-After, instantly GET-retries 403/429, discards per-URL error detail, and reports mass
transport failures as "Site URLs that did not respond" (139 on the reviewed report — the math
matches a WAF tarpit). Research settings + detection checklist: plan §6.2.

**Scope**
- Pacing: per-host concurrency 2, 500–1000ms delay + jitter (D6); prefer GET-with-early-close
  over HEAD-first; honor `Retry-After`/429 with exponential backoff (host-level, 2–3 tries).
- Circuit breaker: ≥5 consecutive transport failures ⇒ stop, mark technical-crawl source
  `partial` with reason `bot_blocked` (rules then rescale via the existing trust gate — no
  false broken-link findings).
- Diagnostics: retain per-URL final status + error class (timeout/reset/refused/TLS); detect
  WAF signatures (`cf-ray`, `cf-mitigated`, challenge-page markers, CF 1015/1020); optional
  single browser-UA recheck of 3 sample URLs (D4).
- Report copy: blocked ⇒ "N URLs could not be verified — the site's firewall throttled our
  automated check; verify manually"; add a coverage note stating the request rate used.
- Revisit `site_health_total_budget_seconds` default for the slower pace.

**Acceptance**
- Simulated-WAF fixture (429/timeouts after N requests): status `partial:bot_blocked`, zero
  broken-link findings, crawl-rate note rendered; healthy fixture: identical findings to today;
  429 fixture: Retry-After honored (test with a fake clock).

---

### RQ-8 — Merge Findings + Recommendations into one card
**Type:** Improvement (report UX) · **Wave 2 · Size M** · Depends RQ-9 · Plan item F · Closes #10, #14

The same meaning/why text renders three times per issue — finding card, recommendation card,
roadmap card (`content_plan.py:104-111,168-170`; `report.html:222-252,710`).

**Scope**
- One card per issue: severity chip, title, What it means / Why it matters / **Do this**
  (+ start-by-checking URLs). Roadmap keeps tier buckets but entries become title + one-line
  action + section reference (no third copy).
- `content_plan.py` emits merged objects (keep payload fields back-compatible for stored
  results); update `report.html`, `docx_renderer.py`, `pages/audit/[id].tsx`.

**Acceptance**
- No meaning/why sentence appears more than once in a rendered report; PDF/DOCX/UI mirror; old
  stored results still render (compat test); reproducibility harness passes.

---

### RQ-9 — Pair every finding with its fix (PSI/CWV recommendation gap)
**Type:** Bug (report logic) · **Wave 1 · Size S** · Plan item G · Closes #11, #23

Remediation metadata for PSI/CWV rules exists (`seo.yaml:404-476`; `_ACTION_TITLES`
content_plan.py:343-347) but recommendations sort tier-first and all PSI/CWV rules are
`long_term`, so with ≥5 quick/mid-term rules they fall past the per-section cap
(`content_plan.py:140-143`, cap `config.py:80-81`) — and out of the roadmap, which is built
solely from section recommendations.

**Scope**
- Select findings and recommendations as pairs: the recommendation set = the surfaced findings'
  rules (display-ordered by tier). Interim standalone fix if RQ-8 hasn't landed; folds into
  RQ-8's merged card naturally.

**Acceptance**
- Regression test: 6+ surfaced rules including a `long_term` PSI rule ⇒ the PSI fix appears in
  the section and in the roadmap; every rendered finding has a rendered "Do this".

---

### RQ-10 — De-duplicate overlapping recommendations
**Type:** Improvement (report UX) · **Wave 1 · Size S** · Plan item H · Closes #22

Reviewer: "Some items here can merge into previous items." Confirmed near-duplicates: "Give
every page one clear H1" (`seo.headings.h1_present`) vs "Clean up the heading outline"
(`seo.aeo.heading_hierarchy`); "Raise alt-text coverage" (`seo.images.alt_coverage`) vs "Add
alt text to images that lack it" (technical-crawl `images_missing_alt`).

**Scope**
- Merge map in `content_plan.py`: when both rules of a pair surface, emit one merged card with
  combined evidence; suppress the twin. Presentation-only — scores unchanged.

**Acceptance**
- Fixture where both pairs fail: one H1 card, one alt-text card (merged evidence lines); each
  rule alone still surfaces; scores byte-identical.

---

### RQ-11 — Score naming consistency + combined cover
**Type:** Improvement (report UX) · **Wave 2 · Size S–M** · Plan item I · Closes #26

Two similarly-named scores with different formulas ("Lead Generation Readiness" 83 = 45/55
SEO/UX blend on page 3; "Overall Lead-Gen Readiness" 85 = 70/30 website/social on page 28)
appear ~25 pages apart with no cross-reference; the cover of a combined audit still says
"Website Audit Report" and leads with the website ring.

**Scope**
- Combined audits: cover retitled "Website & Social Media Audit Report"; leads with the
  Overall ring (layout per D3); website composite renamed "Website Lead-Gen Score" everywhere
  (PDF/DOCX/UI).
- One "How the scores fit together" box (exec summary + Overall section):
  `Overall = 0.70 × Website + 0.30 × Social`; `Website = 0.45 × SEO + 0.55 × UX/UI`, with the
  audited numbers filled in.
- Website-only audits: byte-identical output (guarded by test).

**Acceptance**
- Combined PDF presents one headline score with both formulas cross-referenced; list/detail UI
  labels match; website-only regression test passes byte-identical.

---

### RQ-12 — Client-language pass
**Type:** Improvement (copy) · **Wave 1 · Size S** · Plan item J · Closes #6, #7, #15, #16

**Scope**
- Remove "not a separate crawl" from the Lead-Gen card (`report_payload.py:747-752`).
- Suppress "…normalized to X/100" when possible points = 100
  (`_score_calculation_sentence`, `report_payload.py:826-831`).
- Replace "sweep"/"crawl(er)" in all client-facing strings with "site health check"/"checked"
  (coverage notes `site_health.py:508-512`, data-source label `report_payload.py:286`, guidance
  strings); retitle the chapter "Site Health" and nest it visually under the SEO part (full
  chapter merge deliberately declined to keep the evidence trail — noted for the reviewer).

**Acceptance**
- Text extraction of a rendered PDF contains no client-facing "sweep"/"crawl"/"crawler"
  tokens; card sentences read correctly for the possible=100 case; existing tests updated.

---

### RQ-13 — Fix TOC order
**Type:** Bug (template) · **Wave 1 · Size XS** · Plan item K · Closes #2

TOC entries are hardcoded in an order that doesn't match the body (`report.html:89-108`): body
is SEO → UX/UI → Site Health → Search Performance; TOC lists Site Health and Search Performance
between SEO and UX/UI, so printed page numbers appear out of sequence.

**Scope/Acceptance** — reorder the `<li>` entries to body order (page numbers are CSS
`target-counter`, self-correcting); PDF pagination test asserts monotonic TOC page numbers.

---

### RQ-14 — URL-inspection clarity
**Type:** Improvement (copy/template) · **Wave 1 · Size S** · Plan item L · Closes #20, #21

**Scope**
- Replace "each important page" (`report.html:541`, `docx_renderer.py:325`) with the honest
  criterion: "the homepage plus the most prominent pages found during the crawl (up to 20)".
- Canonical column: render only when at least one row differs from its URL; matching rows show
  "✓ matches"; if all match, replace the column with a single summary line.

**Acceptance** — fixture with all-matching canonicals shows the summary line and no duplicated
URLs; fixture with one mismatch shows the column with the mismatch highlighted.

---

### RQ-15 — Label the CWV table scope
**Type:** Bug (copy) · **Wave 1 · Size XS** · Plan item M · Closes #24

The lab CWV table is homepage-only (`psi_client.py:398-402` builds `strategies` from
`pages[0]`), while the performance score uses the multi-page average — the intro implies
otherwise (`report.html:766-772`).

**Scope/Acceptance** — column headers become "Mobile (homepage lab test)" / "Desktop (homepage
lab test)"; intro sentence distinguishes homepage lab data from the multi-page average used in
scoring; CrUX block already labeled origin-wide (unchanged).

---

### RQ-16 — Readable chart labels
**Type:** Bug (template) · **Wave 1 · Size XS** · Plan item N · Closes #25

Bar labels render full absolute URLs into a 1.7in right-ellipsis column — every row displays
the same `https://www.…` prefix (`report.html:1000,1057`; `report.css:1153-1168`).

**Scope/Acceptance** — display path-only labels (`/blog/sales-training…`, homepage as `/`) in
the slowest-pages and declining-pages charts; widen the label column modestly; visual check in
the PDF pagination test fixtures.

---

### RQ-17 — N-gram topic labels
**Type:** Improvement · **Wave 3 · Size S** · Plan item O · Closes #18

Reviewer asked "BERTopic?" — topics are deterministic impression-weighted single tokens
(`gsc.py:615-667`), hence labels like "square" and "foot". Decision: stay deterministic
(reproducibility invariant; no LLM/BERTopic) but label with n-grams.

**Scope**
- Seed clusters on top bigrams/trigrams ("cost per square foot") with unigram fallback; merge
  clusters whose seed is a sub-token of another seed; fix the dead `"near me"` stopword entry
  (two-word entry can never match single tokens — gsc.py:518).

**Acceptance** — sample dataset yields "cost per square foot", "home builder marketing" instead
of "square"/"foot"; output deterministic across runs (repro test).

---

### RQ-18 — Niche/audience input guidance
**Type:** Improvement (frontend) · **Wave 3 · Size S** · Plan item P · Closes #1

The cover prints operator input verbatim; the reviewed report shipped "homes" / "home owners"
because the form gives placeholder-only guidance (`index.tsx:189-215`).

**Scope**
- Builder-domain placeholders + help text: Niche "e.g. custom home builder, kitchen remodeler";
  Audience "who the audited business sells to — e.g. homeowners planning a custom build";
  add "shown on the report cover" hint. (Auto-suggest from crawled content: separate future
  ticket, out of scope.)

**Acceptance** — form shows the guidance; cover unchanged mechanically; screenshot reviewed.

---

### RQ-19 — Acceptance re-run + comment-by-comment signoff
**Type:** Task (QA gate) · **After each wave; final gate · Size S** · Plan item X · Closes: verification of all

**Scope**
- Re-run the exact builderleadconverter.com combined audit after each wave; generate the PDF;
  diff against docs/17 §4's 26-annotation inventory; produce a one-page signoff table
  (remark → fixed-in → evidence page) for the reviewer.
- Verify cross-cutting invariants: determinism (repro harness), website-only byte-identity
  where promised, grounding validation, rubric versions recorded (`phase2-uxui-v3`,
  `ctr_curve_version`).

**Acceptance** — all 26 annotations (22 unique concerns) marked resolved-or-consciously-deferred
with reviewer signoff;
`make test` + `make qa` + `make qa-repro` green.
