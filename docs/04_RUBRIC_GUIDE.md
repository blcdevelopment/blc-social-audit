# Rubric Guide (P1-26)

How the deterministic scoring rubrics work, and how to tune them safely without
changing code. Scores come from these YAML files only — the LLM never scores.

Engine: `apps/worker/stages/scoring.py`. Rubrics: `rubrics/seo.yaml`,
`rubrics/uxui.yaml`, `rubrics/composite.yaml`.

---

## 1. The Three Rubrics

| File | `version` | Category | Rules |
|---|---|---|---|
| `rubrics/seo.yaml` | `phase1-seo-v1` | `seo` | 13 |
| `rubrics/uxui.yaml` | `phase1-uxui-v1` | `uxui` | 14 |
| `rubrics/composite.yaml` | `phase1-composite-v1` | (weights) | — |

The combined `rubric_version` stored on each result is
`phase1-seo-v1+phase1-uxui-v1+phase1-composite-v1`. **Bump a version whenever you
change a rubric** so historical results remain interpretable.

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
```

- **`fact_path`** is a dotted path into the fact bundle `{seo, uxui, psi}`, with
  list indexing supported (e.g. `seo.pages[0].title.is_reasonable_length`). A
  missing path scores `fail` — unless `skip_if_missing: true`, in which case the
  rule is **skipped** and excluded from the denominator.
- **`weight`** is relative within a category; categories are normalized to
  `max_score` (default 100).

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

---

## 4. How a Category Score Is Computed

`score_category` (in `scoring.py`):

1. Evaluate every rule → `pass`/`partial`/`fail`/`skipped`.
2. Drop `skipped` rules from both numerator and denominator.
3. With `normalization: rescale_to_max` (the Phase 1 default):
   `score = round( (awarded_points / evaluated_weight) × max_score )`.
4. Clamp to `[0, max_score]`.

So skipping a rule (e.g. PageSpeed rules when PSI data is missing) **does not
penalize** the site — the remaining rules are rescaled to fill the category.

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
   make qa weak_site.html   # weak site, to confirm calibration direction
   make qa-repro      # confirm reproducibility still holds
   ```

4. Confirm the calibration gate: the strong sample site scores meaningfully
   higher than the weak one for explainable, rule-level reasons. Current
   reference (no PSI):

   | Site | SEO | UX/UI | Lead Gen |
   |---|---|---|---|
   | strong | 100 | 100 | 100 |
   | weak | 21 | 4 | 12 |

---

## 7. Validation Rules (schema)

Rubrics are validated by Pydantic models on load (`Rubric`, `CompositeRubric`):

- Unknown keys are rejected (`extra="forbid"`).
- `weight > 0`, `max_score > 0`.
- `category` must be `seo` or `uxui`; `evaluator` must be one of the six above.
- `normalization` is `rescale_to_max` or `sum_of_weights`.
- Composite weights must be exactly `{seo, uxui}` and sum to 1.0.

A malformed rubric fails fast at load time rather than producing a wrong score.
