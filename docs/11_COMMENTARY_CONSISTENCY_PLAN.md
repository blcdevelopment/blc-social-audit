# 11 — Commentary Consistency Plan (deterministic findings, optional LLM polish)

> **Status:** Phase 1 **implemented — verified 2026-06-16** (deterministic content plan
> [content_plan.py](../apps/worker/stages/content_plan.py); `generate_commentary` returns
> `status/provider/model == "deterministic"`; `RubricRule` carries
> `impact`/`tier`/`finding_label`/`remediation`/`surface_as_finding`;
> `commentary_max_findings_per_section` / `commentary_max_recommendations_per_section`
> (defaults 5) in config; grounding reverts emptied fields to baseline rather than leaking a
> placeholder). Phases 2–3 are designed so they drop in without rework.
> This does **not** touch crawling, extraction, or the deterministic scoring engine — only
> how findings/recommendations are *authored*.
> **Approval recorded:** build Phase 1 now structured so Phase 2 (LLM polish) drops in
> cleanly; per-rule severity/tier live in the **rubric YAML** (config-driven, versioned).
>
> **As-built note (grounding scoping):** grounding validates factual *claims* about the
> site only. `evidence_refs` (machine fact-paths, e.g. `seo.pages[0]....`) and `action_items`
> (prescriptive advice that legitimately carries target numbers like "70–160 characters")
> are passed through untouched — see `UNGROUNDED_KEYS` in
> [grounding_validator.py](../apps/worker/stages/grounding_validator.py). A full-field strip
> reverts to the baseline and is recorded honestly (`action="reverted_unsupported_to_baseline"`),
> never a placeholder string.

---

## 1. The problem (in one sentence)

Across re-runs of the same site, the **findings, severities, tiers, and counts** drift,
because the LLM *authors the report structure* when a key is present and a completely
different code path authors it when no key is present. Score wobble of a point is fine and
expected (PSI varies); structural drift is not.

What the user explicitly does **not** want fixed: byte-identical re-runs across different
days. That is gold-plating (Phase 3, deferred).

---

## 2. The problem this plan solved — pre-Phase-1 "before" snapshot

> **Historical note (2026-06-16):** the issues and line anchors below describe the
> **pre-Phase-1** state this plan set out to fix. Phase 1 has since shipped (see the status
> banner above), so this table is a "before" snapshot, not current behavior — issues #1–#6 are
> all resolved (the LLM-authoring fallback path was deleted, grounding reverts to baseline, and
> the rubric now carries `impact`/`tier`/`finding_label`/`remediation`/`surface_as_finding`).
> The referenced line numbers point at code as it was *before* the fix and no longer match.

| # | Issue | Evidence in code |
|---|---|---|
| 1 | **Two divergent prose generators.** With a key, the LLM authors *everything* — which findings exist, how many, their severity, the recommendations, their tier. Without a key, a different, thinner structure is built from `score_breakdown`. | [generate_commentary](../apps/worker/stages/commentary.py#L50) → [_call_openai](../apps/worker/stages/commentary.py#L101) vs [_fallback_commentary](../apps/worker/stages/commentary.py#L163) |
| 2 | **Fallback leaks internal rule IDs** into user-facing titles/rationale. | [_recommendation_from_rule](../apps/worker/stages/commentary.py#L285) emits `f"Address {rule['rule_id']}"` |
| 3 | **Grounding placeholder leaks into the report** when every sentence in a field is stripped. | [grounding_validator.py:123](../apps/worker/stages/grounding_validator.py#L123) returns the literal `"Unsupported numeric claim removed by grounding validator."` |
| 4 | **Severity is a crude heuristic** (`"medium" if score < 70 else "info"`). | [commentary.py:236](../apps/worker/stages/commentary.py#L236), repeated [report_payload.py:317](../apps/worker/stages/report_payload.py#L317) |
| 5 | **Tier is positional**, not principled — failed rule [0]→quick_win, [1]→mid_term, [2]→long_term. | [commentary.py:228-230](../apps/worker/stages/commentary.py#L228-L230) |
| 6 | **No data-driven impact/tier.** Rubric YAML has no such fields. | [seo.yaml](../rubrics/seo.yaml), [RubricRule](../apps/worker/stages/scoring.py#L20) |

**What already works in our favor:**

- Every scored rule already carries `evidence.value` (the *real* measured fact at its
  `fact_path`) — [scoring.py:210-214](../apps/worker/stages/scoring.py#L210-L214). That is
  enough to write specific, grounded prose with no rule-ID leakage.
- The report payload already consumes the **typed `CommentaryContent` model**
  ([commentary.py:41](../apps/worker/stages/commentary.py#L41)) via
  [_compose_section](../apps/worker/stages/report_payload.py#L208). If the deterministic
  builder emits that *same* model, **report_payload, the PDF templates, and the frontend
  need no changes.**
- The QA harness already runs the real pipeline deterministically with no keys
  ([qa_common.py](../scripts/qa_common.py)) — the perfect place to assert structural
  reproducibility.

---

## 3. Target architecture

**One deterministic content plan is the source of truth. The LLM, when present, is an
optional, non-substantive polish layer that can only rewrite prose — never add, drop,
reorder, or invent a finding.**

```
score_breakdown + facts
        │
        ▼
build_content_plan()  ──►  CommentaryContent     ← canonical: selection, order,
   (deterministic)          (existing model)         severity, tier, evidence_refs,
        │                                             baseline prose (cites evidence.value)
        │
        ├── no key ───────────────────────────────►  use plan as-is  (status: "deterministic")
        │
        └── key present ─► polish(plan)  ──► merge by id, structure-locked
                              (LLM)            │
                                               ▼
                                       ground ONLY the polished diff;
                                       any sentence that fails → revert to baseline
                                               │
                                               ▼
                                       CommentaryContent (same structure, nicer voice)
```

Key property: OpenAI being down, rate-limited, or hallucinating can now only change **how
polished the report reads**, never **what it says**. "Fallback" stops being a different
report — it is just "skip the polish step."

This is the standard data-to-text NLG split: **deterministic content planning** (what to
say, in what order, how severe) + optional **surface realization** (how to phrase it).

---

## 4. Phase 1 — deterministic content plan (do now)

Fixes issues #1–#6 end to end. After Phase 1, the same site produces **identical findings,
order, severity, and tier on every run**, with or without an OpenAI key (because the LLM
authoring path is removed — polish arrives in Phase 2).

### 4.1 New module: `apps/worker/stages/content_plan.py`

```python
def build_content_plan(
    *,
    audit_context: JsonDict,
    seo_facts: JsonDict,
    uxui_facts: JsonDict,
    psi_facts: JsonDict,
    score_breakdown: JsonDict,
    settings: Settings,
) -> CommentaryContent:        # the EXISTING model from commentary.py
    ...
```

> **As-built (2026-06-16):** the shipped signature also takes an
> `external_seo_facts: JsonDict | None = None` keyword (added for the external-SEO/GSC rules);
> `generate_commentary` forwards it through. The sketch above predates that parameter.

Responsibilities, all deterministic:

1. **Selection.** For each category (`seo`, `uxui`), read
   `score_breakdown.categories.<cat>.rules`. A rule becomes a finding iff
   `result in {"fail", "partial"}` **and** `surface_as_finding` is not false.
   `skipped` (e.g. PSI with no key) and `pass` are not findings (pass may become an
   optional positive note later — off by default).
2. **Severity** = `impact × result` (see mapping in §4.3), where `impact` comes from the
   rubric rule.
3. **Tier** = the rule's `tier` (rubric field) — the remediation horizon, independent of
   result.
4. **Ordering** (stable, deterministic): sort findings by
   `(severity_rank desc, weight desc, rule_id asc)`. Recommendations are grouped by tier in
   fixed order `quick_win → mid_term → long_term`, then the same secondary sort.
5. **Top-N** per section: `COMMENTARY_MAX_FINDINGS_PER_SECTION` (default 5) and
   `COMMENTARY_MAX_RECS_PER_SECTION` (default 5). Deterministic truncation after sorting.
6. **Baseline prose** (see §4.4) — cites only `evidence.value` + the section score, so it is
   grounding-safe by construction.
7. **`lead_generation` section.** Composite has no rules of its own, so its finding is a
   deterministic summary of the composite score plus the single highest-severity finding
   drawn from SEO/UX-UI; its recommendations are the top quick-win(s) rolled up. Cites only
   the composite score (grounded).
8. **`executive_summary`** — deterministic template over the three scores + the single
   highest-severity finding. Cites only scores (grounded).

The builder returns the existing `CommentaryContent`, so nothing downstream changes shape.

### 4.2 `generate_commentary` becomes a thin wrapper

`apps/worker/stages/commentary.py`:

```python
def generate_commentary(...) -> JsonDict:
    plan = build_content_plan(...)            # always
    # Phase 1: no LLM authoring. Phase 2 inserts polish() here behind the key check.
    return {
        "status": "deterministic",
        "provider": "deterministic",
        "model": "deterministic",             # llm_model column records this
        "content": plan.model_dump(mode="json"),
    }
```

- **Delete** `_fallback_commentary`, `_fallback_section`, `_fallback_lead_section`,
  `_recommendation_from_rule`, `_rules_with_results` (the rule-ID-leaking path, issue #2).
- **Keep but stop calling** `_call_openai`, `_render_user_prompt`, `_compact_*` — these get
  repurposed for the Phase 2 polish call. (Leave them in place to minimize churn, or move to
  a `commentary_polish.py` in Phase 2.)
- Keep `CommentaryContent`/`CommentaryFinding`/`CommentaryRecommendation`/`CommentarySection`
  and `validate_commentary_content` exactly as-is — they remain the contract.

### 4.3 Severity = impact × result

`impact` is the rubric-authored importance of the rule *when it fails*. The plan combines it
with the actual result to get the finding severity:

| rule `impact` | result `fail` | result `partial` |
|---|---|---|
| `high` | **high** | medium |
| `medium` | **medium** | low |
| `low` | **low** | info |

`skipped` / `pass` → not a finding. Severity ranks for ordering: `high=3, medium=2, low=1,
info=0`.

### 4.4 Baseline prose templates (grounding-safe)

Generic, evaluator-aware formatter — **no hand-written paragraph per rule**, and critically
**only `evidence.value` and the section score are ever emitted as numbers**:

- **percentage facts** (`*_pct`): `"{label}: {value}% of pages."`
- **count facts** (thresholds on counts): `"{label}: {value}."`
- **boolean facts**: `"{label}: {present|absent}."`

Each rule supplies two short authored strings in YAML (so prose is specific, not robotic, and
never leaks IDs):

- `finding_label` — e.g. `"Meta descriptions missing"`
- `remediation` — e.g. `"Add a unique 70–160 character meta description to every page."`

A finding is assembled as:

```
title       = finding_label
explanation = "<evidence phrasing>. <why-it-matters clause from impact>."
evidence_refs = [fact_path]            # not rule_id — fact_path is meaningful, not internal
recommendation.title        = finding_label
recommendation.rationale    = explanation
recommendation.action_items = [remediation]
```

**Worked example (alt-text, the case from the reports):**

```
Templated baseline (Phase 1, no LLM):
  title:        "Image alt-text coverage is low"
  explanation:  "Image alt-text coverage: 10.8% of images. Low coverage weakens
                 accessibility and SEO discoverability."
  action_items: ["Add descriptive alt text to all meaningful images."]
  severity:     medium     (impact=medium, result=fail)
  tier:         quick_win
```

`10.8` is `seo.summary.image_alt_coverage_pct` — a stored fact, so it survives grounding.

### 4.5 Rubric schema additions (the chosen approach)

Add to `RubricRule` in [scoring.py](../apps/worker/stages/scoring.py#L20) (all optional so
unrelated rubrics don't all need every field; the builder derives defaults if absent):

```python
class RubricRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # ...existing fields...
    impact: Literal["high", "medium", "low"] = "medium"
    tier: Literal["quick_win", "mid_term", "long_term"] = "quick_win"
    finding_label: str | None = None       # falls back to a cleaned description
    remediation: str | None = None         # falls back to a generic action
    surface_as_finding: bool = True         # False for non-actionable meta rules
```

Then populate every rule in [seo.yaml](../rubrics/seo.yaml) /
[uxui.yaml](../rubrics/uxui.yaml) and **bump `version:`** on both (invariant #4). Composite is
unchanged.

> **Order of operations matters:** because `RubricRule` is `extra="forbid"`, the Pydantic
> field additions must land in the **same change** as the YAML edits, or `load_rubric`
> hard-errors. Add the model fields first.

**Proposed initial `impact` / `tier` / `surface_as_finding` (tunable; the point is they are
explicit and versioned):**

SEO:

| rule | weight | impact | tier | surface |
|---|---|---|---|---|
| `seo.collection.complete` | 4 | high | quick_win | **false** (meta) |
| `seo.title.present_all_pages` | 8 | high | quick_win | true |
| `seo.homepage_title.reasonable_length` | 7 | medium | quick_win | true |
| `seo.meta_description.present_all_pages` | 10 | high | quick_win | true |
| `seo.homepage_meta_description.reasonable_length` | 8 | medium | quick_win | true |
| `seo.h1.present_once` | 9 | high | quick_win | true |
| `seo.homepage.canonical` | 6 | medium | mid_term | true |
| `seo.schema.present` | 9 | medium | mid_term | true |
| `seo.images.alt_coverage` | 8 | medium | quick_win | true |
| `seo.indexability.no_noindex_pages` | 5 | high | quick_win | true |
| `seo.internal_links.depth` | 6 | low | mid_term | true |
| `seo.psi.mobile_performance` | 10 | high | long_term | true |
| `seo.psi.desktop_performance` | 10 | medium | long_term | true |

UX/UI:

| rule | weight | impact | tier | surface |
|---|---|---|---|---|
| `uxui.collection.complete` | 4 | high | quick_win | **false** (meta) |
| `uxui.primary_cta.present` | 10 | high | quick_win | true |
| `uxui.cta.volume` | 8 | medium | quick_win | true |
| `uxui.cta.above_fold` | 8 | medium | quick_win | true |
| `uxui.forms.present` | 8 | high | mid_term | true |
| `uxui.homepage_form.field_count` | 6 | low | mid_term | true |
| `uxui.phone.visible` | 8 | high | quick_win | true |
| `uxui.email.visible` | 6 | medium | quick_win | true |
| `uxui.trust.present` | 9 | high | mid_term | true |
| `uxui.trust.depth` | 5 | low | mid_term | true |
| `uxui.navigation.present` | 8 | medium | mid_term | true |
| `uxui.copy.substantial` | 6 | low | long_term | true |
| `uxui.direct_contact.present` | 7 | high | quick_win | true |
| `uxui.lead_capture.cta` | 7 | medium | quick_win | true |

### 4.6 Grounding placeholder-leak fix (issue #3)

In Phase 1 the baseline cites only stored facts, so grounding is effectively a no-op — but
the leak is still latent and must be removed:

- Change `_sanitize_text` so the empty-result branch no longer returns the placeholder
  string. Pass the **baseline text** for that field into the sanitizer (or the merge step)
  so an emptied field reverts to its deterministic baseline, which is grounded by
  construction.
- This is the seam Phase 2 relies on: grounding polices *only* the LLM-polished diff, and any
  failed sentence falls back to the trusted baseline.

### 4.7 report_payload cleanup (light)

No structural change (same `CommentaryContent`). With the plan always populated:

- `_fallback_findings` / the `score < 70` severity heuristic at
  [report_payload.py:850-860](../apps/worker/stages/report_payload.py#L850-L860) become
  dead-but-harmless. Keep as defense-in-depth in Phase 1; consider deleting in a follow-up.
  (As-built 2026-06-16: still present and unused, exactly as planned.)

---

## 5. Phase 2 — optional LLM polish (designed now, built next)

- New `polish(plan, *, facts, settings) -> CommentaryContent`. Sends the LLM a flat list of
  `{id, text}` strings (each finding/rec's `explanation`/`rationale`/`headline` +
  `executive_summary`) and asks **only for fluent rewrites**. Returns `{id, text}`; the merge
  replaces text by id and **keeps the original for any missing/extra/renamed id** — structure
  is impossible to change.
- Determinism knobs: pinned model snapshot, `temperature=0`.
- `generate_commentary` gains the key check back: `if key: plan = polish(plan)`; on any
  error, keep the deterministic plan (`status: "deterministic"`), exactly as today's graceful
  degradation but now structurally identical.
- Grounding runs on the polished result; any sentence that fails reverts to baseline (§4.6).
- **Invariant that closes the grounding-scoping caveat:** the polish layer rewrites only the
  narrative claim fields (`headline`, `explanation`, `rationale`, `executive_summary`). It must
  **not** touch `action_items` or `evidence_refs` — those stay verbatim from the deterministic
  plan. Because they are never LLM-generated, excluding them from grounding (§4.6 /
  `UNGROUNDED_KEYS`) carries no risk: there is no path by which an unsupported number can enter
  them. (The site metric a user might fabricate lives in `explanation`, which *is* grounded.)
- Rewrite `prompts/commentary_system.md` + `commentary_user.md` to the "rewrite these
  sentences; do not change facts, numbers, count, or order" contract.
- Result: substance identical to Phase 1; only wording varies, and only cosmetically.

## 6. Phase 3 — cache (deferred; only if byte-identical archives are ever needed)

Content-address the polish input (facts + plan hash) → cache the polished strings so an
unchanged site yields byte-identical prose across days. Not requested; build only if a
real need (legal/audit diffing) appears.

---

## 7. Tests & QA

**Will break and must be updated (take care):**

- [test_commentary.py](../tests/unit/test_commentary.py)
  - `test_generate_commentary_uses_valid_local_fallback_without_api_key` — asserts
    `status == "fallback_missing_api_key"` / `provider == "local_fallback"`. Update to the
    new `status/provider == "deterministic"` and assert the **plan is populated from rules**
    (e.g. a known failing rule appears as a finding with the expected severity/tier).
  - `test_generate_commentary_uses_openai_provider_when_api_key_is_set` — currently asserts
    the LLM-authored content passes through verbatim. In Phase 1 there is no authoring path;
    rewrite/relocate it to the Phase 2 polish merge (assert structure preserved, only text
    changed).

**New tests:**

- `tests/unit/test_content_plan.py` — feed a fixed `score_breakdown` + facts and assert:
  selection (only fail/partial, surfaced), ordering (severity→weight→rule_id),
  severity mapping (§4.3), tier from rubric, top-N truncation, and that **every emitted
  number appears in the facts** (grounding-safety invariant).
- Grounding: add a case where a field's only sentence is unsupported and assert it reverts to
  **baseline text**, not the placeholder string.

**Extend reproducibility QA** ([qa_reproducibility.py](../scripts/qa_reproducibility.py),
which already runs the no-key deterministic path): in addition to scores + per-rule results,
assert the two runs produce identical **findings and recommendations** — compare
`(section, title, severity, tier, evidence_refs)` tuples and counts across `id1`/`id2`.
`snapshot_audit` already persists `commentary`; add a `commentary` field to the snapshot if
needed and a `_commentary_diff` helper mirroring `_rule_diff`.

**Gates to run after each change:** `make test`, `make qa`, `make qa-repro`, `make lint`.
(Per the project hard rule, the **user** runs any git commands; I only edit files.)

---

## 8. Compatibility / data notes

- **`rubric_version` changes** (seo/uxui `version:` bump) — intended and recorded in
  `audit_results.rubric_version`; reproducibility compares within a single code version, so
  unaffected.
- **`llm_model`** column now records `"deterministic"` when no polish runs (was
  `"not_configured"`). Cosmetic; verify the PDF/report metadata copy still reads sensibly.
- **No DB migration** — no schema change. `commentary` JSON shape is unchanged
  (`CommentaryContent`).
- **Frontend / PDF templates** — untouched (same payload).

---

## 9. File-touch checklist (Phase 1)

| File | Change |
|---|---|
| `apps/worker/stages/scoring.py` | Add `impact`/`tier`/`finding_label`/`remediation`/`surface_as_finding` to `RubricRule`. |
| `rubrics/seo.yaml`, `rubrics/uxui.yaml` | Populate new fields per §4.5; **bump `version:`**. |
| `apps/worker/stages/content_plan.py` | **New.** `build_content_plan()` → `CommentaryContent`. |
| `apps/worker/stages/commentary.py` | `generate_commentary` calls `build_content_plan`; delete `_fallback_*` / `_recommendation_from_rule`. |
| `apps/worker/stages/grounding_validator.py` | Remove placeholder leak; revert emptied fields to baseline. |
| `apps/shared/config.py` | Add `COMMENTARY_MAX_FINDINGS_PER_SECTION` / `..._RECS_...` (defaults 5). |
| `tests/unit/test_commentary.py` | Update the two assertions above. |
| `tests/unit/test_content_plan.py` | **New.** Deterministic selection/order/severity/tier + grounding-safety. |
| `tests/unit/test_grounding_validator.py` | Add baseline-revert (no placeholder) case. |
| `scripts/qa_reproducibility.py` | Assert identical findings/recommendations across two runs. |
| `apps/worker/stages/report_payload.py` | (Optional follow-up) retire dead fallback/severity heuristic. |

**Suggested sequencing:** model fields + YAML (one change, or scoring breaks) → `content_plan`
+ unit test → wire `generate_commentary` → grounding fix → repro QA extension → run all gates.

---

## 10. Risks / "take care" callouts

1. **Grounding-safety is a hard invariant of the baseline.** Templates cite only
   `evidence.value` + scores. Any future template that derives a new aggregate number must
   either (a) cite a stored fact, or (b) add that aggregate to the extractor summary so it is
   grounded. A `test_content_plan` assertion enforces "every emitted number is in the facts."
2. **`extra="forbid"` ordering trap** — model fields and YAML fields must change together.
3. **Two existing commentary tests change meaning** — update, don't delete blindly; they
   encode the old two-path behavior we are intentionally removing.
4. **Don't widen grounding's trusted set.** The deliberate choice to exclude rule
   weights/ratios from "known numbers" ([tasks.py:282-285](../apps/worker/tasks.py#L282-L285))
   stays; baseline prose respects it by construction.
5. **PSI skip stays graceful** — `skipped` rules are not findings, so a missing PSI key never
   manufactures a finding (matches today's behavior).

---

## 11. Decisions locked

- **A/B/C:** build **B**, but only **Phase 1 now**, structured so the polish layer drops in.
- **Severity/tier source:** **rubric YAML** (`impact` + `tier`), versioned.
- **Cache (Phase 3):** deferred until a concrete need.
```
