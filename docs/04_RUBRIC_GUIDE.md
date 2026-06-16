# Rubric Guide (P1-26)

How the deterministic scoring rubrics work, and how to tune them safely without
changing code. Scores come from these YAML files only — the LLM never scores.

Engine: `apps/worker/stages/scoring.py`. Rubrics: `rubrics/seo.yaml`,
`rubrics/uxui.yaml`, `rubrics/composite.yaml`.

_Last reconciled: 2026-06-16._

---

## 1. The Three Rubrics

| File | `version` | Category | Rules |
|---|---|---|---|
| `rubrics/seo.yaml` | `phase1-seo-v4` | `seo` | 23 |
| `rubrics/uxui.yaml` | `phase1-uxui-v2` | `uxui` | 14 |
| `rubrics/composite.yaml` | `phase1-composite-v1` | (weights) | — |

The combined `rubric_version` stored on each result is
`phase1-seo-v4+phase1-uxui-v2+phase1-composite-v1`. **Bump a version whenever you
change a rubric** so historical results remain interpretable.

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
| UX/UI | `uxui.*` | mixed | `false` | `extractor_uxui.py` |
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

`rubrics/composite.yaml` combines the two category scores:

```yaml
version: "phase1-composite-v1"
max_score: 100
weights:
  seo: 0.45
  uxui: 0.55
```

`lead_gen = round(seo_score × 0.45 + uxui_score × 0.55)`. Weights must include
exactly `seo` and `uxui` and **sum to 1.0** (validated on load).

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

Rubrics are validated by Pydantic models on load (`Rubric`, `CompositeRubric`):

- Unknown keys are rejected (`extra="forbid"`).
- `weight > 0`, `max_score > 0`.
- `category` must be `seo` or `uxui`; `evaluator` must be one of the six above.
- `impact` ∈ `{high, medium, low}`; `tier` ∈ `{quick_win, mid_term, long_term}`
  (both default-valued, so omitting them still validates).
- `normalization` is `rescale_to_max` or `sum_of_weights`.
- Composite weights must be exactly `{seo, uxui}` and sum to 1.0.

A malformed rubric fails fast at load time rather than producing a wrong score.

> **Adding a category (e.g. `social`) is not YAML-only.** The category set is a
> typed `Literal["seo", "uxui"]` in `scoring.py` — both on `Rubric.category` and on
> the composite `weights` dict. Introducing a third category in Phase 2 therefore
> requires a typed **code** change (widen the `Literal`, extend the composite
> validation) in addition to the new `social.yaml` rubric.
