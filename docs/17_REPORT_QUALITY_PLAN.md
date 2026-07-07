# Report Credibility & Accuracy Plan — Post-Review Hardening

> **Status: IMPLEMENTED (2026-07-03) — see §10 for the per-remark signoff.** Originally planned the same day. Source: line-by-line expert review (Shayan, lead manager) of
> the combined audit PDF generated 2026-06-30 for `builderleadconverter.com`
> (`blc-website-audit-commented.pdf`). His bar, verbatim: *"most parts are readable and
> understandable by a normal account/sales manager. But it must be accurate enough to be
> considered by a marketing expert."* This document is the full analysis + fix plan. The
> copy-paste-ready Jira breakdown lives in
> [docs/18_REPORT_QUALITY_JIRA_PLAN.md](18_REPORT_QUALITY_JIRA_PLAN.md).

---

## 1. How this plan was built

1. **Every reviewer remark was extracted** from the commented PDF — 26 annotations across
   15 annotated pages (pages 5, 6, 8, 13, 15, 18, 22–24, 26, 27 carry none); four are the same
   concern repeated on a later page, giving 22 unique concerns. The complete
   inventory with per-remark traceability is in §4.
2. **Every remark was root-caused in the code** (read-only verification passes over
   `google_search_console.py`, `content_plan.py`, `report_payload.py`, `extractor_uxui.py`,
   `rubrics/uxui.yaml`, `crawler.py`, `site_health.py`, `templates/report.html`, `psi_client.py`,
   `pages/index.tsx`). Exact mechanisms and file:line references are cited throughout.
3. **The three hard problems were researched against industry practice** (SEO traffic
   forecasting, polite crawling / WAF avoidance, popup/lazy-iframe form detection). Findings and
   sources are in §6.

## 2. Headline discoveries (worse than the review assumed)

1. **The "monthly" numbers are 90-day sums.** GSC facts are collected over a ~90-day window
   (`google_search_console.py:245-248`) but rendered as *"searches a month"* / *"more
   visits/month"* (`content_plan.py:225-229`, `templates/report.html:408-413`). Nothing divides
   by the window length — **~3× inflation from labeling alone**, before the opportunity model's
   own optimism. This is the single most damaging accuracy bug in the report.
2. **The form findings are structurally false for popup/iframe sites — i.e. for the sites BLC
   itself builds.** The extractor counts only literal `<form>` tags in the top frame
   (`extractor_uxui.py:147-165`); Playwright's `page.content()` never serializes iframe
   documents; the crawler performs zero clicks/scrolls (`crawler.py:521-581` — grep-verified).
   A LeadConnector/GoHighLevel popup-form site scores 0 on all form facts: `uxui.forms.present`
   (weight 8) + `uxui.homepage_form.field_count` (weight 6) + `uxui.email.visible` (weight 6)
   = **20/100 UX points → −11 Lead-Gen → −7.7 Overall** on the exact pattern our own product
   produces.
3. **The "139 site URLs did not respond" carries the signature of our checker being
   WAF-throttled, not of dead links.** The sweep fires up to 8 concurrent, zero-delay,
   HEAD-first requests with a self-declared bot UA at one host — no per-host limit, no backoff,
   429/Retry-After ignored, 403/429 instantly retried with GET (`site_health.py:421,503-506,52,
   530-533`; `config.py:112-114,165`). "Did not respond" strictly means a transport-level
   exception whose detail is **discarded** (`site_health.py:463-469,543-544`). The arithmetic
   corroborates a tarpit: 139 × 10s timeouts ÷ 8 lanes ≈ 174s — precisely why the same report
   also shows the "180s time budget" coverage note.

## 3. The plan at a glance

| Phase | Item | Title | Size |
|---|---|---|---|
| **P0 — Accuracy & trust** | A | GSC time-basis fix + data windows rendered everywhere | S |
| | B | Defensible opportunity model (curve, scenarios, caps) | M |
| | C | Popup / lazy-iframe form detection (3 sub-items) | M–L |
| | D | Replace the email-visible rule with a contact-path rule | S |
| | E | Polite site-health sweep + WAF detection | M |
| **P1 — Clarity & structure** | F | Merge Findings + Recommendations into one card | M |
| | G | Guarantee every surfaced finding carries its fix (PSI gap) | S |
| | H | De-duplicate overlapping recommendations | S |
| | I | Score naming consistency + combined cover | S–M |
| | J | Client-language pass (jargon removal) | S |
| | K | TOC order fix | XS |
| | L | URL-inspection clarity (important pages, canonical column) | S |
| | M | CWV table scope labeling | XS |
| **P2 — Polish & inputs** | N | Chart label readability | XS |
| | O | N-gram topic labels (the BERTopic question) | S |
| | P | Niche/audience input guidance | S |
| **Cross-cutting** | X | Acceptance re-run + comment-by-comment signoff | S |

Suggested waves: **Wave 1** = A, D, G, H, J, K, L, M, N (small items, one PR, closes 16
annotations / 13 unique concerns). **Wave 2** = B, E, F, I (the credibility core). **Wave 3** = C, O, P, then X as the
final gate.

---

## 4. Complete remark inventory & traceability

Every remark from the commented PDF, in page order. "Root cause" cites the verified mechanism;
"Fix" maps to the plan items in §5.

| # | Page | Remark (paraphrased) | Root cause (verified) | Fix |
|---|---|---|---|---|
| 1 | 1 | Audience "home owners" — *why not Builders and Remodelers?* | Cover prints operator input verbatim (`report_payload.py:616-617`); form has placeholder-only guidance (`index.tsx:189-215`) | P |
| 2 | 2 | *Numbering issue?* — UX/UI at p9 listed after entries for p11/p13 | TOC hardcoded in an order that doesn't match the body (`report.html:89-108` vs body order SEO→UX/UI→Technical→Search) | K |
| 3 | 3 | *Missing: time span of input data (30 days? 3 months?)* | Window dates stored (`date_range`, gsc.py:283) but rendered nowhere; previous-window dates never stored | A |
| 4 | 3 | *What is "Near-miss"? I don't understand this sentence* | Jargon; defined one way in exec summary (`content_plan.py:227-229`), a different way in the callout footnote (`report.html:417-419`); they are queries, not pages | B |
| 5 | 3 | *Bold claim! 12K clicks/month?! currently it's 0.7K* | 90-day sums labeled monthly + all-queries-jump-to-P3–5 model, no dampening, no cap vs current traffic, most-optimistic published CTR curve (gsc.py:474-575) | A+B |
| 6 | 3 | Remove *"not a separate crawl"* | Hardcoded card copy (`report_payload.py:747-752`) | J |
| 7 | 3 | *"normalized to 88/100" — redundant?* | `_score_calculation_sentence` always emits the clause, even when possible points = 100 (`report_payload.py:826-831`) | J |
| 8 | 3 | *What form? Do we have any form on Homepage?* | `uxui.homepage_form.field_count` fails on 0 because iframe/popup forms are invisible to the extractor | C |
| 9 | 4 | Email finding: *site is not supposed to expose email* | `uxui.email.visible` (weight 6) requires a literal email/mailto; no credit for a contact link — though its own remediation text promises one (`uxui.yaml:99-109`) | D |
| 10 | 7 | *Remove Recommendations section — obvious from Findings* | Findings and recommendations are built from the same rules with identical meaning/why text (`content_plan.py:104-111,168-170`); text prints 3× incl. roadmap | F |
| 11 | 7 | *For Mobile PageSpeed (the complex one) there is no recommendation* | Remediation metadata EXISTS (seo.yaml:404-476; `_ACTION_TITLES` content_plan.py:343-347) but recommendations sort tier-first and all PSI/CWV rules are `long_term`, so they fall off the 5-per-section cap and out of the roadmap | G |
| 12 | 9 | Email rule: *we need to rethink this* | Same as #9 | D |
| 13 | 9 | *Forms are popups + lazy-loaded iframes; a crawler can never find forms on our sites* | Confirmed: top-frame-only capture, no interaction, no provider-signature reading (see §2.2) | C |
| 14 | 10 | *Remove UX/UI Recommendations section* | Same as #10 | F |
| 15 | 11 | *"crawl"/"crawler" are nonsense to clients; merge chapter into previous* | Internal vocabulary in client-facing copy; separate "Technical SEO" chapter | J |
| 16 | 11 | *What is "sweep"?* | Internal tool word baked into coverage-note strings (`site_health.py:508-512`), passed verbatim to the PDF (`report_payload.py:1355`, `report.html:314-315`) | J |
| 17 | 12 | *What was the crawl rate? WAF rate-limit or real 404s?* | See §2.3 — unpaced 8-concurrent bot-UA sweep, error detail discarded, no WAF detection | E |
| 18 | 14 | *Have you used topic modeling? BERTopic?* | Topics are deterministic impression-weighted **single tokens** (`gsc.py:615-667`) — hence "square", "foot" as labels; no n-grams; dead `"near me"` stopword entry (gsc.py:518) | O |
| 19 | 16 | *Time span (window) must be clear from the beginning* | Same as #3 — "the data window above" references dates that are never shown | A |
| 20 | 17 | *How do you define "important" pages?* | Copy says "important page" (`report.html:541`; `docx_renderer.py:325`) but selection is simply homepage + crawled pages, capped 20 (`gsc.py:713-726`) | L |
| 21 | 17 | *Canonical column only needed when it differs from the URL* | Column always rendered, prints the full URL twice per row (`report.html:549-557`) | L |
| 22 | 19 | *Some roadmap items can merge into previous items* | Near-duplicate rule outputs: H1 rule vs heading-outline rule; alt-coverage rule vs technical-crawl missing-alt rule — no de-duplication across rules/sources | H |
| 23 | 20 | *Where is the recommendation for Mobile PageSpeed?* | Same as #11 | G |
| 24 | 21 | *Are these (CWV) averages for the 8 analyzed pages?* | No — homepage-only lab data (`psi_client.py:398-402`), while the score uses the multi-page average; intro never says so (`report.html:766-772`) | M |
| 25 | 25 | *Not readable* (declining-pages chart) | Full absolute URLs in a 1.7in ellipsis column — every bar shows the same `https://www.…` prefix (`report.html:1000,1057`; `report.css:1153-1168`) | N |
| 26 | 28 | *Inputs/formula/definition don't match page 3* | Two similarly-named scores, two formulas (45/55 vs 70/30), ~25 pages apart, never cross-referenced; static cover always says "Website Audit Report" with the website ring (`report.html:32-84,1251-1254`; `report_payload.py:747-752`) | I |

(All 26 annotations are listed for auditability. Four are cross-page repeats of the same
concern — #12 repeats #9 (email), #14 repeats #10 (remove recommendations), #19 repeats #3
(data window), #23 repeats #11 (missing PSI recommendation) — so the 26 annotations reduce to
22 unique concerns, every one mapped to a fix item.)

---

## 5. The plan in detail

### Phase 0 — Accuracy & trust (before the next client-facing report)

#### A. Fix the GSC time basis + render the data windows — Size S
- **Problem.** All Search-Console numbers are ~90-day sums labeled "a month" (#3, #5, #19).
- **Fix.** Pick ONE presentation (decision D1, §8): (a) normalize to monthly (divide by
  `window_days / 30.44`) or (b) keep totals and label "over the last 90 days". Render the
  window prominently: exec-summary lead-in, Search Performance header ("Data window:
  {start} – {end} ({N} days), compared with the preceding {N} days"), declining-pages intro.
  Store `previous_date_range` alongside `date_range` (currently discarded, gsc.py:246-248).
- **Touch points.** `google_search_console.py`, `content_plan.py::_opportunity_lead_in`,
  `report_payload.py` (SearchPerformanceSection), `templates/report.html`, `docx_renderer.py`.
- **Acceptance.** Every GSC figure in PDF/DOCX/UI is either true-monthly or explicitly
  windowed; both window date ranges printed; grounding validator still passes (numbers change ⇒
  update stored facts so prose stays grounded).

#### B. Defensible opportunity model — Size M
- **Problem.** #4, #5: every striking query modeled at P3–P5 simultaneously; no cap vs current
  traffic; First Page Sage curve (P1 = 39.8%) is the most optimistic published dataset;
  "near-miss pages" are actually queries; "176 clicks" is the striking subset only and total
  site clicks aren't even stored (why the reviewer's ~0.7K didn't reconcile).
- **Fix (research-backed, §6.1).**
  1. Conservative blended CTR curve (Backlinko/SISTRIX/seoClarity band, P1 ≈ 20–28%),
     versioned in config like a rubric (`ctr_curve_version`), FPS demoted to optimistic bound.
  2. Three scenarios — conservative (≈50% capture), expected (≈70%), optimistic (model output);
     the headline is the conservative number.
  3. Model the top-N queries by impressions (default 25), not all striking queries.
  4. Cap the headline at a sane multiple of **current total organic clicks** (default 2–3× for
     a 12-month horizon) — requires storing `total_clicks` / `total_impressions` site facts
     from the page-dimension query before truncation.
  5. AI-Overview haircut on informational queries (decision D5: default ~30% share at ~50%
     CTR discount).
  6. One inline definition of "near-miss" used identically everywhere: "queries already ranking
     4–20 — just below the top results"; say **queries**, never pages.
  7. Fixed disclaimer block: "a projection, not a promise…" with assumptions listed.
- **Touch points.** `google_search_console.py` (model + new facts), `config.py` (curve/scenario
  knobs), `content_plan.py`, `report.html` callout, tests (`test_google_search_console.py`).
- **Acceptance.** Re-run on the same stored facts yields a conservative headline ≤ 3× current
  clicks with window-correct labeling; the three scenarios and assumptions render; exec summary
  and callout use the same numbers and the same near-miss definition.

#### C. Popup / lazy-iframe form detection — Size M–L (3 sub-items)
- **Problem.** #8, #13 — see §2.2. BLC's own form stack (LeadConnector popups, lazy iframes)
  is invisible to the audit.
- **C1 — Provider-signature scan (static, zero new network).** Regex the already-captured HTML
  for form/scheduler/chat embeds — signature table in §6.3: **LeadConnector/GoHighLevel**
  (`api.leadconnectorhq.com/widget/form|survey|booking/…`, `link.msgsndr.com/js/form_embed.js`),
  HubSpot (`js.hsforms.net`, `hbspt.forms.create`), Typeform (`embed.typeform.com`,
  `data-tf-popup|widget|live`), Jotform, Calendly, Gravity Forms (real `<form>` anyway),
  Intercom, Drift. Key research insight: the loader script / iframe src is present in the
  initial HTML even when the `<form>` element is not. New per-page facts:
  `forms.embedded_providers`, `forms.form_detected` ∈
  `{static_form, provider_embed, runtime_iframe_form, none}`.
- **C2 — Runtime frame pass in the crawler.** After the networkidle wait: incremental
  scroll-to-bottom (triggers `loading="lazy"` iframes), settle, then enumerate `page.frames`
  and count `form`/`input` elements via `frame_locator` (handles cross-origin frames); record
  render-time requests matching provider domains (`page.on("request")`). Per-frame
  try/except (isolation edge cases). **No clicking** — the guarded-CTA click (L5) is
  documented as brittle and deferred.
- **C3 — Rubric semantics (`uxui.yaml` → v3, bump version).** `uxui.forms.present` passes on
  any of `{static_form, provider_embed, runtime_iframe_form}`; `uxui.homepage_form.field_count`
  gains `skip_if_missing`-style behavior when the detected form is an embed whose fields cannot
  be counted (rescale, don't fail with "0 fields"). Report copy names the provider: "Lead
  capture detected: embedded LeadConnector popup form."
- **Touch points.** `extractor_uxui.py`, `crawler.py`, `rubrics/uxui.yaml` (v3),
  `content_plan.py` (copy), tests + a new popup-form HTML fixture for the QA harness.
- **Acceptance.** A fixture page with only a LeadConnector iframe embed passes
  `uxui.forms.present`, skips field-count, and the report names the provider; a plain
  `<form>` site behaves exactly as before; scores byte-identical for sites with no embeds.

#### D. Replace the email-visible rule with a contact-path rule — Size S
- **Problem.** #9, #12 — deliberate email hiding is penalized 6 points; evaluator contradicts
  its own remediation text.
- **Fix.** `uxui.yaml` v3: replace `uxui.email.visible` with `uxui.contact_path.low_pressure` —
  passes on ANY of: visible email / mailto / contact-page link (nav or footer anchor to
  contact-ish path) / detected form or chat embed (from C1). Keep "no visible email" as
  info-level context (`surface_as_finding: false` info entry or appendix note), never a scored
  deduction. Decision D2 (§8): weight of the new rule (recommend keeping 6).
- **Touch points.** `extractor_uxui.py` (contact-page-link fact), `rubrics/uxui.yaml`,
  `content_plan.py` `_RULE_CONTEXT`/`_ACTION_TITLES`, tests.
- **Acceptance.** A site with a contact page + popup form but no visible email passes; a site
  with none of the paths still fails with the reworded finding.

#### E. Polite sweep + WAF detection — Size M
- **Problem.** #17 — see §2.3.
- **Fix (research-backed, §6.2).**
  1. Per-host concurrency 2 (keep global 8 for future multi-host), 500–1000ms delay + 0–500ms
     jitter (≈1–2 req/s — Screaming-Frog-guidance territory); ~200-URL sweep ≈ 2–4 min, still
     inside the audit budget (raise `site_health_total_budget_seconds` default accordingly).
  2. Honor `Retry-After`/429 with exponential backoff (2–3 attempts); back off the **host**,
     not the URL. Prefer GET-with-early-close over HEAD-first (many WAFs 403 HEAD).
  3. **Circuit breaker**: ≥5 consecutive transport failures ⇒ stop, mark the source `partial`
     with reason `bot_blocked` — the existing trust vocabulary then makes technical-crawl rules
     skip/rescale instead of reporting mass false "dead links".
  4. Retain per-URL diagnostics: final status code + error class (timeout / reset / refused /
     TLS) — currently discarded.
  5. WAF-signature detection: `server: cloudflare` + `cf-ray`, `cf-mitigated: challenge`,
     "Just a moment…"/1015/1020 body markers; on first block signal, cooldown + re-test 3
     sample URLs, optionally one browser-UA recheck (decision D4).
  6. Report copy: blocked ⇒ "N URLs could not be verified — the site's firewall throttled our
     automated check; verify manually", never "did not respond"; add a coverage note stating
     the actual request rate used (directly answers "what was the crawl rate?").
- **Touch points.** `site_health.py`, `config.py` (rate knobs), `technical_crawl_common.py`
  (new issue label/status), `report_payload.py` guidance text, `test_site_health.py`.
- **Acceptance.** Simulated-WAF fixture (429s/timeouts after N requests) yields `bot_blocked`
  partial status, zero broken-link findings, and the crawl-rate note; healthy-site fixture
  output unchanged apart from pacing.

### Phase 1 — Clarity & structure

#### F. Merge Findings + Recommendations into one card — Size M
- #10, #14: identical meaning/why text prints three times (finding → recommendation →
  roadmap). New shape: one card per issue — severity chip, title, *What it means*, *Why it
  matters*, **Do this** (+ start-by-checking URLs). The Roadmap keeps tier buckets but each
  entry is title + one-line action referencing its section, not a third copy.
- Touch: `content_plan.py` (emit merged objects; keep payload back-compat), `report_payload.py`,
  `report.html`, `docx_renderer.py`, `[id].tsx`.
- Acceptance: no meaning/why sentence appears more than once per report; DOCX/UI mirror.

#### G. Guarantee every surfaced finding carries its fix — Size S
- #11, #23: tier-first sort + 5-cap silently drops PSI/CWV remediations. Fix: findings and
  recommendations are selected as **pairs** (the recommendation list = the findings list's
  rules, ordered by tier for display) — natural once F lands; interim fix independent of F is
  a one-line sort/cap change. Roadmap therefore always contains the performance item.
- Acceptance: for every rendered finding, its "Do this" exists in-section and in the roadmap;
  regression test with 6+ surfaced rules incl. a long_term PSI rule.

#### H. De-duplicate overlapping recommendations — Size S
- #22: "Give every page one clear H1" + "Clean up the heading outline" are near-duplicates
  (`seo.headings.h1_present` vs `seo.aeo.heading_hierarchy`), as are "Raise alt-text coverage"
  + "Add alt text to images that lack it" (on-page `seo.images.alt_coverage` vs technical-crawl
  `images_missing_alt`). Fix: a small merge map in `content_plan.py` — when both rules in a
  pair surface, emit ONE merged card (combined evidence: "90% of pages have a single H1; one
  page repeats/skips levels"), suppress the twin. Scores unchanged (presentation-only).
- Acceptance: fixture where both pairs fail produces one H1 card and one alt-text card; each
  alone still surfaces normally.

#### I. Score naming consistency + combined cover — Size S–M
- #26: two similarly-named scores with different formulas, never linked; static cover.
- Fix: on combined audits the cover reads "Website & Social Media Audit Report" and leads with
  the **Overall Lead-Gen Readiness** ring (decision D3: Overall ring + 3 small rings vs 4
  equal); the website composite is renamed **"Website Lead-Gen Score"** everywhere; one "How
  the scores fit together" box (exec summary + Overall section):
  `Overall 85 = 0.70 × Website 83 + 0.30 × Social 90`; `Website 83 = 0.45 × SEO 76 + 0.55 ×
  UX/UI 88`. Website-only audits unchanged.
- Touch: `report.html` cover + overall section, `report_payload.py` card copy,
  `docx_renderer.py`, `[id].tsx` labels.
- Acceptance: a combined PDF presents one headline score; both formulas cross-referenced in
  one place; website-only reports byte-identical.

#### J. Client-language pass — Size S
- #6, #7, #15, #16: remove "not a separate crawl"; suppress "normalized to X/100" when
  possible = 100 (condition in `_score_calculation_sentence`); replace "sweep"/"crawl(er)"
  in all client-facing strings with "site health check"/"checked"; retitle the chapter
  **"Site Health"** and visually nest it under the SEO part (keep separate pages — full merge
  rejected to preserve the technical evidence trail, noted for Shayan).
- Acceptance: grep of rendered PDF text for `sweep|crawl` yields no client-facing hits
  (data-source footnote "BLC site health check (built-in)" reworded too).

#### K. TOC order — Size XS
- #2: reorder hardcoded TOC entries (`report.html:89-108`) to the body order (SEO → UX/UI →
  Site Health → Search Performance → …). Page numbers are CSS `target-counter` and stay
  correct automatically.

#### L. URL-inspection clarity — Size S
- #20, #21: replace "important pages" with the honest criterion ("the homepage plus the most
  prominent pages found during the crawl, up to 20"); render the canonical column **only when
  any row differs** — matching rows show a ✓ ("matches page URL"), and if all match, replace
  the column with one summary line.

#### M. CWV table scope label — Size XS
- #24: table shows homepage-only lab data. Label "Homepage (lab test)" on both columns, one
  intro sentence distinguishing it from the multi-page average used in the score, and the CrUX
  block already says origin-wide — keep.

### Phase 2 — Polish & inputs

#### N. Chart label readability — Size XS
- #25: bar labels render full absolute URLs into a 1.7in right-ellipsis column. Fix: strip
  scheme + host (display `/blog/sales-training…`), homepage as `/`; widen label column
  slightly; same change for slowest-pages chart (`report.html:1000,1057`).

#### O. N-gram topic labels — Size S
- #18 (the BERTopic question). Answer recorded: topics are deterministic, impression-weighted
  single tokens — no BERTopic/LLM, and we should stay deterministic (identical input ⇒
  identical report is a core invariant; BERTopic is non-deterministic and heavyweight). We get
  ~80% of the benefit with **n-gram labeling**: seed clusters on top bigrams/trigrams ("cost
  per square foot") with unigram fallback, merge clusters whose label is a sub-token of
  another seed ("square", "foot" → "cost per square foot"), fix the dead `"near me"` stopword
  entry (two-word entry can never match single tokens — gsc.py:518).
- Acceptance: the sample dataset yields labels like "cost per square foot", "home builder
  marketing" instead of "square"/"foot"; deterministic across runs.

#### P. Niche/audience input guidance — Size S
- #1: cover prints whatever the operator typed ("homes"/"home owners"). Fix: form help text +
  builder-domain placeholders — Niche "e.g. custom home builder, kitchen remodeler"; Audience
  "who the audited business sells to — e.g. homeowners planning a custom build" — plus a
  "shown on the report cover" hint. Later (optional, not this pass): auto-suggest from crawled
  content.

### X. Acceptance gate (cross-cutting) — Size S
- Re-run the exact `builderleadconverter.com` combined audit after each wave; diff the new PDF
  against this document's §4 table; produce a one-page comment-by-comment signoff for Shayan.
  Rubric bumps: `uxui.yaml` → `phase2-uxui-v3` (C3+D); opportunity-model version knob (B);
  no seo.yaml rule changes planned (H/G are presentation-layer). New tests per item; new QA
  fixtures: popup-form site (C), simulated-WAF server (E).

---

## 6. Research appendix

### 6.1 SEO traffic forecasting (for item B)

CTR-by-position benchmarks compared: **Advanced Web Ranking** (GSC-derived, refreshed monthly,
device/intent segmented — best methodology), **seoClarity** (~750B impressions; P1 ≈ 19.3%
desktop / 27.7% mobile), **Backlinko** (P1 ≈ 27.6%, ~+2.8%/position), **SISTRIX** (P1 ≈ 28.5%),
vs **First Page Sage** (P1 = 39.8%, methodology undisclosed, excludes SERPs with
maps/images/shopping) — FPS is the outlier and should be the optimistic bound, not the default.
AI Overviews (~30%+ of queries) roughly halve top-position CTR where present. Practice
(SEOmonitor, Ahrefs, agency guides): ranges not points; conservative/expected/optimistic with
~50%/70%/100% capture; target P3–5 not P1; ramp 6–12 months; "projection, not a promise"
disclaimers; ideally derive the client's own curve from their GSC data with published curves as
fallback. Sources: advancedwebranking.com/free-seo-tools/google-organic-ctr ·
seoclarity.net/mobile-desktop-ctr-study-11302 · backlinko.com/google-ctr-stats ·
thestacc.com/blog/organic-ctr-by-position · firstpagesage.com/reports/google-click-through-rates-ctrs-by-ranking-position ·
ahrefs.com/blog/seo-forecasting · help.seomonitor.com (forecast scenarios) ·
agencyanalytics.com/blog/seo-forecasting.

### 6.2 Polite crawling & WAF detection (for item E)

Cloudflare rate-limit rules are commonly 10/min–50/10s (sensitive endpoints as low as
4–10/min); bot management scores fingerprints regardless of rate. Screaming Frog's own guidance:
reduce to ~2 threads / 1–2 URL/s on protected sites; practitioner consensus for polite crawlers:
per-host concurrency 1–3, 500–3000ms delay + jitter, identify yourself in the UA (with contact
URL), honor robots `Crawl-delay`, on 429 stop-the-host + honor `Retry-After` + exponential
backoff with jitter, circuit-break after ~5 consecutive failures, prefer GET (HEAD often
403/405'd — RFC 9110 `Allow` header tells you), HTTP/2 + coherent headers (TLS/JA3 and header
consistency are fingerprinted). Blocked-vs-dead checklist: 403/503/429 with `cf-ray` /
`server: cloudflare` / `cf-mitigated: challenge`; body markers "Just a moment…", `cf_chl_`,
Error 1020; CF code semantics 1015=rate-limited, 1020/1010=filtered; pattern signals (first N
succeed then uniform failures; resets mid-sweep; HEAD 403 but GET 200; bot-UA 403 but
browser-UA 200 on one recheck). Genuinely dead: 404/410 with the site's own template from the
first request, UA/rate independent. Sources: developers.cloudflare.com/waf/rate-limiting-rules/best-practices ·
screamingfrog.co.uk/seo-spider/faq · firecrawl.dev glossary (polite crawling, 429) ·
scrapfly.io/blog/posts/how-to-bypass-cloudflare-anti-scraping (used for detection signatures
only) · web.dev/articles/iframe-lazy-loading.

### 6.3 Popup / lazy-iframe form detection (for item C)

Wappalyzer/BuiltWith-style signature detection over stored HTML is the highest-ROI layer — the
loader script or iframe src is present even when the `<form>` is not. Signatures:
**LeadConnector/GoHighLevel** `api.leadconnectorhq.com/widget/form|survey|booking/{id}`,
`link.msgsndr.com/js/form_embed.js`, chat `widgets.leadconnectorhq.com` (popup/slide-in modes
have NO form in DOM until triggered); **HubSpot** `js.hs-scripts.com/{portal}.js`,
`js.hsforms.net/forms/v2.js`, `hbspt.forms.create(`, iframes `*.hsforms.com`; **Typeform**
`embed.typeform.com/next/embed.js`, `data-tf-widget|popup|live`, iframe `form.typeform.com/to/`;
**Jotform** `form.jotform.com/jsform/{id}`, iframe `id="JotFormIFrame-…"`; **Calendly**
`assets.calendly.com/assets/external/widget.js`, `.calendly-inline-widget|badge-widget`;
**Gravity Forms** `/wp-content/plugins/gravityforms/`, `.gform_wrapper` (server-rendered
`<form>` — L1 already catches); **Intercom** `widget.intercom.io/widget/{APP_ID}`; **Drift**
`js.driftt.com/include/…`. Runtime layer: Playwright `page.frames` + `frame_locator()` handles
cross-origin frames; `loading="lazy"` iframes fetch within ~1250px of viewport ⇒ scroll-to-
bottom then settle then enumerate; also sniff render-time requests to provider domains.
Click-simulation is brittle (navigation, `_blank`, side effects) — last resort only, never
fill/submit. Output semantics: `form_detected ∈ {static_form, provider_embed,
runtime_iframe_form, probable_popup, none}`. Sources: github.com/tomnomnom/wappalyzer ·
help.gohighlevel.com (form embed docs) · developers.intercom.com · devdocs.drift.com ·
playwright.dev/docs/api/class-frame · web.dev/articles/iframe-lazy-loading.

---

## 7. Invariants preserved

- **Scores stay deterministic** — every change is either presentation-layer or a versioned
  rubric/fact-semantics change (uxui v3; opportunity model versioned in config). No LLM enters
  scoring or topic labeling; BERTopic explicitly rejected for reproducibility (§5.O).
- **Graceful degradation extended, not weakened** — `bot_blocked` becomes a first-class
  non-`complete` status that rescales rules, exactly like missing PSI/GSC today.
- **Grounding** — new prose numbers (scenarios, windows, rates) must be stored as facts so the
  grounding validator keeps them.
- **Website-only reports byte-identical** where items only affect combined presentation (I).

## 8. Open decisions (need Shayan / product signoff)

| # | Decision | Recommendation |
|---|---|---|
| D1 | Monthly-normalized numbers vs "per 90 days" labels | Normalize to monthly (division), state the window |
| D2 | New contact-path rule: keep weight 6, or reduce? | Keep 6 (path still matters; email alone no longer required) |
| D3 | Combined cover: Overall ring + 3 small, or 4 equal rings | Overall large + 3 small beneath |
| D4 | Browser-UA recheck on WAF block (1 request) — allowed? | Yes, single sample recheck, documented in the report |
| D5 | AI-Overview haircut default share/discount | 30% share × 50% discount on informational queries |
| D6 | Sweep default rate | 2 concurrent + 500–1000ms jitter (≈1–2 req/s) |

## 9. Sequencing

| Wave | Items | Jira | Outcome |
|---|---|---|---|
| 1 | A, D, G, H, J, K, L, M, N | RQ-1, 6, 9, 10, 12–16 | 16 annotations (13 unique concerns) closed; one small PR |
| 2 | B, E, F, I | RQ-2, 7, 8, 11 | The credibility core (bold claims, WAF, duplication, score naming) |
| 3 | C (C1→C2→C3), O, P | RQ-3, 4, 5, 17, 18 | Crawler capability + polish |
| Gate | X | RQ-19 | Re-run BLC audit; comment-by-comment signoff vs §4 |

---

## 10. Implementation status & signoff (2026-07-03)

All 18 implementation tasks (RQ-1…RQ-18) are implemented on top of `main` (post PR #19).
Gates on the final state: full unit suite **344 passed**, `ruff check` + `ruff format` clean,
flake8 + isort clean, frontend `tsc --noEmit` clean, hermetic QA harness **11/11**,
reproducibility run **byte-for-byte identical**. The live `builderleadconverter.com` re-run
(RQ-19's last step) is an operator action — it needs the production GSC connection and
Apify/YouTube keys; regenerate the audit from the UI and check each row below against the
new PDF.

Decisions D1–D6 were implemented with the recommended defaults (D1 monthly-normalized
headline figures with windowed tables; D2 contact-path weight 6; D3 Overall ring leads the
combined cover; D4 single browser-profile recheck on bot-block; D5 15% AI-Overview discount;
D6 per-host concurrency 2 + 750 ms spacing).

**Review round (same day):** a 4-reviewer adversarial pass over the finished PR found and
fixed four majors before merge — (1) the degenerate-estimate guard tested the window-total
upside while the headline is monthly/conservative, letting "0–0 visits per month" ship (now
guarded on the headline itself); (2) the browser-profile recheck followed redirects without
per-hop SSRF vetting (now `follow_redirects=False`) and swallowed Celery soft-timeouts (now
re-raised); (3) the two renamed uxui v3 facts false-failed rerun-enrichment on pre-v3 stored
audits (both rules now `skip_if_missing`); (4) the overlapping-rule merge ran before the
severity sort/cap so an absorbed `fail` could vanish from the report (merged cards now adopt
group-max severity/weight; the exec summary's top-priority label picks from the merged list).
Plus minors: zero-click sites get **no cap** (instead of a misleading floor of 1 — the one
deviation from the D1/RQ-1 spec, which assumed a click baseline exists), "0 to 0 inquiries"
clause suppressed, dangling-pronoun copy, `final_url` captured before the frame scan, DOCX
"(None days)" on legacy facts, combined cover/title/card gates on overall
`status == "complete"`, UI roadmap de-duplicated like the PDF, topic labels trim stopword
edges and tokenize unicode. 13 regression tests pin these. Accepted (not fixed, by design):
provider-signature text mentions and third-party iframes can earn form credit (errs toward
credit), lazy-iframe variance across runs, Retry-After sleeps up to ~120 s past the sweep
deadline — recorded in docs/06 §§3/5.

**Live-report follow-up (same day, after a real prod re-run):** regenerating the actual
builderleadconverter.com combined report surfaced three residual gaps the balanced unit
fixtures had hidden; all three fixed with regression tests keyed to the live data profile:
(a) **#18 topic labels still rendered single tokens** ("square", "foot", "builder") because a
unigram collects at least the impressions of every phrase containing it, so on real
(never-tied) data the heaviest token won every seed and subsumed its own phrases —
`_topic_clusters` now **groups queries by their heaviest shared content TOKEN** (broad
coverage) but **labels each group with its cleanest phrase** (`_label_for`: heaviest, then
shortest, then most-content-chars, so "square foot" not "foot to build"), folding co-occurring
fragments into one cluster and trimming edge function words (`_CLUSTER_EDGE_FILLERS`) while
keeping meaningful short tokens like "df". (An interim phrase-FIRST seeding read well but an
adversarial review caught that it silently dropped broad token-sharing queries — "square
footage estimate" matched no exact phrase and vanished, deflating every theme; token grouping
restores 100% coverage while keeping phrase labels.) (b) **#8/#13 "0
homepage form fields" still printed** — the homepage wraps its lazy LeadConnector embed in an
empty `<form>` shell, so the static parse returned a real form with 0 inputs; the extractor
now treats a zero-input static form beside a frame/embed signal as uncountable (`None` ⇒ the
field-count rule skips) or adopts the measured frame count; (c) **#15/#17 Site Health rendered
empty** — prod runs Screaming Frog enabled but the binary isn't installed, so it failed and the
selector discarded the sweep's real `partial: bot_blocked` data; `_collect_technical_crawl` now
prefers a `partial` sweep over a failed Screaming Frog attempt, so the checked links and the
honest WAF/bot-block note (Shayan's #17 question) reach the report. These three were then run
through a 3-reviewer adversarial workflow: it verdicted the form and sweep fixes correct and
flagged the topic-clusterer coverage regression above (which drove the token-grouping rewrite)
plus a mid-filler-label leak — both since fixed. ~10 regression tests across the follow-up.
**Ops note:** set `SCREAMING_FROG_ENABLED=false` on the prod worker until the licensed binary
is actually installed, so the sweep is the primary source rather than a fallback after a
guaranteed SF failure.

| Remark(s) | Fixed by | Verify in the regenerated PDF/UI |
|---|---|---|
| #1 audience input | RQ-18 | Builder-domain placeholders + "printed on the cover" hints on the form |
| #2 TOC order | RQ-13 | Contents order matches pagination (UX/UI before Site Health) |
| #3, #19 data window | RQ-1 | "Data window: {start} to {end} ({N} days), compared with the preceding…" + declining-pages intro cites both ranges |
| #4 near-miss jargon | RQ-2 | One definition everywhere: "queries … positions 4–20, just below the top results" |
| #5 bold claim | RQ-1+RQ-2 | Conservative monthly headline (≤3× current clicks), scenario line, assumptions block naming the blended CTR curve, AI-Overview discount, window |
| #6 "not a separate crawl" | RQ-12 | Lead-gen card sentence |
| #7 redundant normalization | RQ-12 | UX/UI card drops "normalized to X/100" when earned points already read as the score |
| #8, #13 invisible forms | RQ-3/4/5 | Popup/iframe form sites credit `uxui.forms.present`; homepage field-count SKIPS (no "0 fields") |
| #9, #12 email rule | RQ-6 | `uxui.contact_path.low_pressure` (email OR contact link OR form) replaces email-visible |
| #10, #14 remove Recommendations | RQ-8 | One card per issue (What/Why/**Do this**); no per-section Recommendations list; roadmap slimmed |
| #11, #23 missing PSI fix | RQ-9 | "Speed up page loads on mobile" appears with its finding and in the roadmap |
| #15, #16 crawl/sweep jargon | RQ-12 | "Site Health" chapter, "site health check" wording; crawl-rate note answers "what was the crawl rate?" |
| #17 WAF question | RQ-7 | Polite pacing (2 lanes, ~750 ms), Retry-After honored, breaker ⇒ `partial: bot_blocked` + honest note; no mass false dead links |
| #18 BERTopic | RQ-17 | Topic labels are phrases ("cost per square foot"), deterministic (no LLM) |
| #20 "important pages" | RQ-14 | Selection criterion stated (homepage + most prominent crawled pages, up to 20) |
| #21 canonical column | RQ-14 | Rendered only when a mismatch exists; otherwise one summary line |
| #22 merge roadmap items | RQ-10 | H1/heading-outline and the two alt-text checks merge into single cards with a covered-by note |
| #24 CWV scope | RQ-15 | "Mobile/Desktop (homepage lab test)" headers + intro distinguishing the multi-page average |
| #25 unreadable chart labels | RQ-16 | Path-only labels in the slowest-pages and declining-pages charts |
| #26 formula mismatch | RQ-11 | Combined cover leads with the Overall ring + retitled report; "How the scores fit together" cross-references both formulas; website composite renamed "Website Lead-Gen Score" |
