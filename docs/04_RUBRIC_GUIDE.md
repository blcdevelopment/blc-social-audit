# Rubric Guide (P1-26)

How the deterministic scoring rubrics work, and how to tune them safely without
changing code. Scores come from these YAML files only — the LLM never scores.

Engine: `apps/worker/stages/scoring.py`. Rubrics: `rubrics/seo.yaml`,
`rubrics/uxui.yaml`, `rubrics/composite.yaml` (website), plus `rubrics/social.yaml`
(standalone Social Score) and `rubrics/overall.yaml` (combined-audit Overall Lead-Gen
Readiness — see §5).

_Last reconciled: 2026-07-02._

---

## 1. The Rubrics

| File | `version` | Category | Rules | Used by |
|---|---|---|---|---|
| `rubrics/seo.yaml` | `phase2-seo-v11` | `seo` | 48 | website + combined |
| `rubrics/uxui.yaml` | `phase1-uxui-v2` | `uxui` | 14 | website + combined |
| `rubrics/composite.yaml` | `phase1-composite-v1` | (weights) | — | website + combined |
| `rubrics/social.yaml` | `phase2-social-v3` | `social` | 14 | social + combined |
| `rubrics/overall.yaml` | `phase2-overall-v1` | (weights) | — | combined only |

The first three are the **website** rubrics; their combined `rubric_version` stored on a
website result is `phase2-seo-v11+phase1-uxui-v2+phase1-composite-v1`. `social.yaml` scores the
standalone **Social Score** (§5a). `overall.yaml` blends the website Lead-Gen composite with the
Social Score for a **combined** audit only (§5b). **Bump a version whenever you change a rubric**
so historical results remain interpretable.

The SEO rubric grew from the original 13 on-page rules to 23 by adding two rule
families that read facts collected by the worker's later stages: **PageSpeed
Insights** (`psi.*`) and **External SEO** (`external_seo.technical_crawl.*`,
`external_seo.gsc.*`, `external_seo.url_inspection.*`). Every one of those rules is
`skip_if_missing: true`, so a site audited without PSI/GSC/Screaming-Frog credentials
is never penalized for the absent data (see §4 and §6).

---

## 2. Anatomy of a Rule

```yaml
- id: seo.meta_description.present_all_pages   # stable, unique identifier
  description: Meta descriptions are present across crawled pages.
  weight: 10                                   # relative importance (> 0)
  fact_path: seo.summary.meta_descriptions_present_pct  # where to read the fact
  evaluator: threshold                         # how to judge the value
  params:                                      # evaluator-specific config
    min: 100
    partial_min: 70
  skip_if_missing: false                       # optional; drop rule if fact absent
  # --- content-plan metadata (optional; consumed by content_plan.py) ---
  impact: high                                 # high | medium | low (default medium)
  tier: quick_win                              # quick_win | mid_term | long_term (default quick_win)
  finding_label: Pages are missing meta descriptions   # user-facing problem (no rule IDs)
  remediation: Write a unique 120-160 char meta description for each page.
  surface_as_finding: true                     # default true; false hides meta/health rules
```

- **`fact_path`** is a dotted path into the fact bundle
  `{seo, uxui, psi, external_seo}`, with list indexing supported
  (e.g. `seo.pages[0].title.is_reasonable_length`). A missing path scores `fail` —
  unless `skip_if_missing: true`, in which case the rule is **skipped** and excluded
  from the denominator.
- **`weight`** is relative within a category; categories are normalized to
  `max_score` (default 100).
- **Content-plan metadata** (`impact`, `tier`, `finding_label`, `remediation`,
  `surface_as_finding`) does **not** affect the score. It is read by
  `content_plan.build_content_plan` to author the deterministic findings and
  recommendations in the report (see [docs/11_COMMENTARY_CONSISTENCY_PLAN.md](11_COMMENTARY_CONSISTENCY_PLAN.md)).
  All five fields are optional in the schema (`RubricRule` in `scoring.py`) — the
  defaults are `impact=medium`, `tier=quick_win`, `finding_label=None`,
  `remediation=None`, `surface_as_finding=true`. Set `surface_as_finding: false`
  for non-actionable meta/health rules (e.g. "facts were extracted successfully")
  so they score but don't appear as a user-facing finding.

---

## 3. Evaluators

| Evaluator | Passes when | Partial (ratio 0.5) | Params |
|---|---|---|---|
| `boolean` | value is `True` | — | — |
| `presence` | value is non-empty (str/list/dict/number) | — | — |
| `exact_match` | value == `full_credit` | value in `partial_credit` | `full_credit`, `partial_credit` |
| `range` | value within `full_credit` `[lo, hi]` | within any `partial_credit` range | `full_credit`, `partial_credit` |
| `threshold` | meets `min`/`max` bounds | meets `partial_min`/`partial_max` | `min`, `max`, `partial_min`, `partial_max` |
| `linear_scale` | value ≥ end of `input_range` | proportionally between start/end | `input_range: [start, end]` |

Each rule yields a result of `pass` (ratio 1.0), `partial` (0.5), `fail` (0.0),
or `skipped`. Points awarded = `weight × ratio`.

**`threshold` is overloaded by direction:**

- **Higher-is-better** — supply `min` (and optionally `partial_min`): the value
  passes when `value >= min`, partial when `value >= partial_min`. Used for
  coverage percentages (e.g. `seo.summary.image_alt_coverage_pct`).
- **Lower-is-better** — supply `max` (and optionally `partial_max`): the value
  passes when `value <= max`, partial when `value <= partial_max`. This is how
  **every external-crawl and GSC count rule** is scored — e.g.
  `external_seo.technical_crawl.summary.missing_titles` with `max: 0` /
  `partial_max: 5` (zero missing titles = pass, a few = partial, many = fail).

### Rule families and their fact sources

| Family | `fact_path` prefix | Evaluator | `skip_if_missing` | Source stage |
|---|---|---|---|---|
| On-page SEO | `seo.*` | mixed (`boolean`, `presence`, `threshold`, …) | mostly `false` | `extractor_seo.py` |
| Answer-engine readiness (AEO) | `seo.summary.*_heading_*`, `seo.summary.has_extractable_structure` | `boolean`, `threshold` | `false` | `extractor_seo.py` (`_extract_aeo`) |
| Local-SEO | `seo.summary.has_complete_nap_schema`, `…has_service_area_markup`, `…has_map_or_gbp_link`, `…has_visible_address` | `boolean` | `false` | `extractor_seo.py` (`_extract_local`) |
| Accessibility (a11y) | `seo.summary.all_pages_have_lang`, `…all_pages_have_main_landmark`, `…viewport_allows_zoom`, `…total_positive_tabindex`, `…unlabeled_form_controls`, `…empty_links`, `…empty_buttons`, `…duplicate_referenced_ids` | `boolean`, `threshold` | mixed (element-dependent rules `true`) | `extractor_seo.py` (`_extract_a11y`) |
| UX/UI | `uxui.*` | mixed | `false` | `extractor_uxui.py` |

> **Scope of the static accessibility module (P2-15).** The `seo.a11y.*` rules are a
> *static-HTML accessibility screen*: every check is computed deterministically from the
> stored, server-rendered markup with an HTML parser — no browser, no JavaScript, no computed
> CSS, no extra fetch (so **axe-core is deliberately not used**; it needs a live rendered DOM,
> which would break the deterministic-from-stored-facts invariant). It covers only the
> low-false-positive, structural checks that are also the highest-prevalence real failures
> (WebAIM Million): language declaration, zoom permission, a main landmark, programmatic labels
> for forms / links / buttons, the positive-tabindex anti-pattern, and duplicated *referenced*
> IDs. It deliberately does **not** evaluate anything render-dependent — colour/text contrast,
> computed ARIA state, whether a labelled-by target is actually visible, keyboard focus order
> and visibility, reflow/zoom behaviour, touch-target size, or JS/CSS-injected content. The
> element-dependent count rules (`form_controls_labeled`, `links_have_name`, `buttons_have_name`,
> `unique_referenced_ids`, `viewport_zoom`) are `skip_if_missing`, so a page with no
> forms/buttons/links/id-references/viewport-meta rescales rather than being vacuously credited.
> Automated tooling of any kind reliably detects only roughly **a third to a half** of WCAG
> success criteria; absence of detected issues here is **not** a proof of conformance.
| PageSpeed | `psi.summary.avg_*_performance` | `linear_scale` | **`true`** | `psi_client.py` |
| Technical crawl | `external_seo.technical_crawl.summary.*` | `threshold` (lower-is-better) | **`true`** | `external_seo.py` / `site_health.py` |
| Search Console | `external_seo.gsc.summary.*` | `threshold` (lower-is-better) | **`true`** | `google_search_console.py` |
| URL Inspection | `external_seo.url_inspection.summary.*` | `threshold` (lower-is-better) | **`true`** | `google_search_console.py` |

The PSI, technical-crawl, GSC, and URL-Inspection families are **all**
`skip_if_missing: true`. When their source degrades (no API key, source returned a
non-`complete` status, or no data), the facts are absent and the rules are skipped
rather than failed — so a missing or failed source never drags the score down (§4,
and the graceful-degradation rule in §5 of [docs/03_ARCHITECTURE.md](03_ARCHITECTURE.md)).

---

## 4. How a Category Score Is Computed

`score_category` (in `scoring.py`):

1. Evaluate every rule → `pass`/`partial`/`fail`/`skipped`.
2. Drop `skipped` rules from both numerator and denominator.
3. With `normalization: rescale_to_max` (the Phase 1 default):
   `score = round( (awarded_points / evaluated_weight) × max_score )`.
4. Clamp to `[0, max_score]`.

So skipping a rule (e.g. PageSpeed rules when PSI data is missing) **does not
penalize** the site — the remaining rules are rescaled to fill the category. A
`skip_if_missing: true` rule whose fact is absent drops out of **both** numerator
and denominator, so the category rescales around it.

This is reinforced for the External SEO families: before scoring, the engine
trusts only external sources whose `status == "complete"` — any source reporting
`partial`/`failed`/`skipped`/`empty` has its `summary` stripped
(`scoring._trusted_external_seo_facts`). The dependent rules then see a missing
fact and skip. Net effect: a degraded or unauthenticated GSC/Screaming-Frog/PSI
source neither aborts the audit nor lowers the score.

Each category breakdown records, per rule: `result`, `points_awarded`,
`points_possible`, the resolved `evidence.value`, and a `reason`. This is the
per-rule audit trail surfaced in the report and the UI.

---

## 5. Lead Generation Readiness (composite)

`rubrics/composite.yaml` combines the two website category scores:

```yaml
version: "phase1-composite-v1"
max_score: 100
weights:
  seo: 0.45
  uxui: 0.55
```

`lead_gen = round(seo_score × 0.45 + uxui_score × 0.55)`. Weights must include
exactly `seo` and `uxui` and **sum to 1.0** (validated on load). This website composite
is **untouched** by the social/combined work below — it is reused verbatim as one input
to the Overall Readiness score (§5b).

### 5a. Social Score (`rubrics/social.yaml`)

The standalone **Social audit** is scored by the same rubric engine against
`rubrics/social.yaml` (`version: phase2-social-v3`, `category: social`, 14 rules,
`normalization: rescale_to_max`, `max_score: 100`). v2 added four content-depth rules
(business/creator account, video share, posting consistency, hashtag usage); v3 is a
fact-semantics calibration in the extractor with no rule changes — video share aggregates
over non-YouTube profiles only (a channel is definitionally 100% video), Facebook post
typing no longer counts a generic reach field as video, hashtag counting requires at least
one letter ("#1" is not a hashtag), and the Instagram business-account flag is tri-state
(missing ⇒ unknown ⇒ the rule rescales instead of failing). Facts come from
`apps/worker/stages/social/extractor.py` and use `social.*` `fact_paths` (e.g.
`social.status`, `social.summary.avg_posts_per_month`). It is scored by
`scoring.score_social_audit()` into a **standalone Social Score (0–100)** and is **not** folded
into the website composite. The `social` category was added to `Rubric.category`
(`Literal["seo", "uxui", "social"]`) so the engine loads this rubric — see §7.

### 5b. Overall Lead-Gen Readiness (`rubrics/overall.yaml`) — combined audits only

A **combined** audit (one form: a website URL **plus** ≥1 social handle) runs the untouched
website pipeline first, then the social audit, and appends an **Overall Lead-Gen Readiness**
score to the end of the single report. That score blends the two pre-computed numbers via
`rubrics/overall.yaml`:

```yaml
version: phase2-overall-v1
max_score: 100
website_weight: 0.70
social_weight: 0.30
```

`overall = round(website_lead_gen × 0.70 + social_score × 0.30)`, computed by
`scoring.compose_overall_readiness_score()` (validated by the `OverallRubric` Pydantic
model: `website_weight + social_weight` must **sum to 1.0**). Both inputs are already-computed
scores — the website Lead-Gen composite (§5) and the Social Score (§5a) — so this rubric only
weights, it never re-evaluates rules. Half-up rounding, like the rest of the engine.

**Weighting rationale:** the website is the bottom-of-funnel lead-capture surface (forms, calls,
high-intent search traffic convert there) so it carries the majority weight; social media is
top-of-funnel demand generation and nurture — meaningful but secondary.

**Rescale when social is missing:** if the social audit produced no score, the readiness
**rescales to the website Lead-Gen score alone** (`status: website_only`, the social weight
drops out) — so a combined audit whose social step degraded still gets a sensible headline
number from the website alone (and a website-only result has `website_lead_gen=None` →
`status: skipped`, `score: None`). The result is stored in `score_breakdown["overall_readiness"]`
(JSON) — there is **no** new DB column.

Config knob: `RUBRIC_OVERALL_PATH` (`Settings.rubric_overall_path`, default
`./rubrics/overall.yaml`), documented in `.env.template`.

---

## 6. Tuning Workflow

1. Edit weights/params (or add/remove rules) in the relevant YAML.
2. Bump the rubric `version`.
3. Validate + re-score against the sample sites:

   ```bash
   make test          # rubric schema + scoring-engine tests
   make qa            # strong site end-to-end
   make qa fixture=weak_site.html   # weak site, to confirm calibration direction
   make qa-repro      # confirm reproducibility still holds
   ```

4. Confirm the calibration gate: the strong sample site scores meaningfully
   higher than the weak one for explainable, rule-level reasons. The committed
   gate is `test_scoring_calibrates_strong_and_weak_fixture_sites`
   (`tests/unit/test_scoring_engine.py`), which scores both fixtures **with PSI**
   (`_psi(92, 96)` strong, `_psi(35, 50)` weak) and asserts these **bounds**:

   | Site | SEO | UX/UI | Lead Gen |
   |---|---|---|---|
   | strong | ≥ 85 | ≥ 85 | ≥ 85 |
   | weak | ≤ 35 | ≤ 30 | ≤ 35 |

   > **Illustrative, pre-external-SEO snapshot.** An earlier edition of this guide
   > recorded exact scores of strong 100/100/100 and weak 21/4/12 scored *without*
   > PSI and *before* the External SEO rule family existed. Those numbers are kept
   > only as a directional illustration — they are **not** the current scores. With
   > PSI included and the external-SEO rules skipped (no GSC/crawl creds in QA), the
   > live numbers differ; trust the asserted bounds above, not the old snapshot.

---

## 7. Validation Rules (schema)

Rubrics are validated by Pydantic models on load (`Rubric`, `CompositeRubric`,
`OverallRubric`):

- Unknown keys are rejected (`extra="forbid"`).
- `weight > 0`, `max_score > 0`.
- `category` must be `seo`, `uxui`, or `social`; `evaluator` must be one of the six above.
- `impact` ∈ `{high, medium, low}`; `tier` ∈ `{quick_win, mid_term, long_term}`
  (both default-valued, so omitting them still validates).
- `normalization` is `rescale_to_max` or `sum_of_weights`.
- Composite weights must be exactly `{seo, uxui}` and sum to 1.0.
- Overall weights (`website_weight`, `social_weight`) must each be in `[0, 1]` and sum to 1.0.

A malformed rubric fails fast at load time rather than producing a wrong score.

> **`social` is now a real category, scored standalone.** `Rubric.category` is the typed
> `Literal["seo", "uxui", "social"]` in `scoring.py`, so `rubrics/social.yaml` loads and scores
> into its own Social Score (§5a) — it is **deliberately not** folded into the website composite,
> whose `weights` dict stays the typed `Literal["seo", "uxui"]`. The combined audit instead
> blends the website composite and the Social Score one level up, via `OverallRubric` /
> `rubrics/overall.yaml` (§5b). Adding a *further* website composite category would still require
> a typed code change (widen the composite `Literal`, extend the composite validation); adding a
> new social backend does not touch the rubrics.
