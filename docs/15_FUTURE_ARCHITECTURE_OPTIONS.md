# Phase 2 — Future Architecture Options (design reference)

**Status:** Forward-looking design reference. **Created 2026-06-24.**

> **Why this doc exists.** It preserves the *still-useful* forward-looking designs from the
> original pre-pivot plan (which lived in a since-removed `docs/old/` archive) so that archive
> could be deleted without losing anything. The current build deliberately diverges from the old plan on **three**
> reversible decisions; this doc captures, against the **current** code, exactly how to make each
> of those moves if/when the team wants them. **None of this is built — it is a map, not a record.**
> For as-built truth use `CLAUDE.md` §5, `README`, and `docs/08–10`.

## The three reversible decisions (old plan → current build)
| Decision | Current build | Old plan | This doc covers |
|---|---|---|---|
| Social scoring | **standalone** Social Score (separate audit) | folded into one combined Lead-Gen score | **§1** (attach to website) |
| IG/FB data vendor | **Apify** (free, sync) | Bright Data (paid, async) | **§2** (vendor swap) |
| Report storage | **local FS** + cron retention | S3 object storage | **§3** (storage — decided against) |

Everything else from the old plan is already built and matching: **YouTube** (YouTube Data API),
**Facebook posts** (Apify Facebook Posts scraper → cadence/engagement), **optional LLM social
commentary**, IG Business Discovery dropped in both.

---

## §0. Current as-built baseline (the starting point for everything below)
- **Two independent audit types** on one `audit_jobs` row, discriminated by `audit_type`
  (`"website"` | `"social"`). Website → `run_collection_audit` website branch; social →
  `_run_social_pipeline` ([tasks.py](../apps/worker/tasks.py)).
- **Website score:** `score_audit()` → `{seo, uxui, lead_gen}` where
  `lead_gen = compose_lead_generation_score(seo, uxui, composite)` weighted **0.45/0.55** by
  [rubrics/composite.yaml](../rubrics/composite.yaml) (`phase1-composite-v1`).
  `CompositeRubric.weights` is a typed `dict[Literal["seo","uxui"], float]` whose validator
  **hard-requires exactly `{seo,uxui}` summing to 1.0** ([scoring.py](../apps/worker/stages/scoring.py)).
- **Social score:** standalone `score_social_audit()` against
  [rubrics/social.yaml](../rubrics/social.yaml) (`phase2-social-v1`, 10 rules, `rescale_to_max`)
  → `social_score`; own report (`compose_social_report_payload`) + own PDF (`render_social_pdf`).
- **Social data layer (reusable):** `collect_social_facts` (graceful-skip, injectable as
  `social_collector=`) → `apify_provider` (IG + FB pages + FB posts) + `youtube_provider`
  (YouTube Data API) → `extractor` (per-platform normalize → shared `social.*` facts).
- **Data model:** migration head **`20260623_0004`**. `audit_results.seo/uxui/lead_gen_score`
  are **nullable**; `social_score` + `social_facts` columns exist; `audit_jobs.social_handles` exists.

---

## §1. Attach social to the website audit (combined Lead-Generation score)
**Goal:** one job → one combined Lead-Gen Readiness score (SEO + UX/UI + **Social**) + one report.
**Effort: SIGNIFICANT. Highest risk — it edits the shipped website score.**

### 1.1 Recommended approach — Sub-option (a): one merged job
The website audit grows an **optional social leg**; a website job may carry `social_handles`.
The social term only contributes when social data is collected — when absent, the website score
is **byte-identical to today** (this is the whole safety property).

1. **Scoring** — widen `CompositeRubric.weights` Literal to include `"social"`; relax
   `validate_weights` to accept `{seo,uxui}` (back-compat) **or** `{seo,uxui,social}`. Add an
   optional `social_score` param to `compose_lead_generation_score` that **re-normalizes the
   weights over the categories actually present** (so a missing social term never penalizes —
   same "rescale around missing" invariant `skip_if_missing` already uses). `score_audit` accepts
   `social_facts`, scores it via the existing `score_category({"social": …}, social_rubric)` seam
   when present+complete, and folds the result into the composite + `rubric_version` string.
2. **composite.yaml** — bump `version` (`phase1-composite-v1` → `phase2-composite-v2`) and add a
   `social` weight (e.g. **0.40 seo / 0.40 uxui / 0.20 social**). ⚠️ **This version bump is the
   reproducibility boundary** (see risks).
3. **Pipeline** ([tasks.py](../apps/worker/tasks.py)) — in the website branch, if
   `job.social_handles`, call the existing `social_collector(settings, job.social_handles)`, pass
   `social_facts` into `score_audit`, and persist via an extended `_upsert_audit_result` (also
   write `social_score`/`social_facts`). Keep `_run_social_pipeline` for standalone back-compat or retire it.
4. **Report** ([report_payload.py](../apps/worker/stages/report_payload.py)) — add a 4th
   ScoreCard id `"social"` + a `social` ReportSection (reuse `compose_social_report_payload`'s
   rule-derived findings/roadmap); regenerate the lead_gen card's printed formula to include the social term.
5. **Template** ([report.html](../templates/report.html)) — add the Social section + 4th score card (lift markup from `social_report.html`).
6. **API/UI** — relax `AuditCreateRequest._validate_inputs` to allow optional `social_handles` on a
   website audit; `index.tsx` gains the optional IG/FB/YT inputs (port `extractHandle` from
   `social.tsx`); detail page + `lib/api.ts` `ReportPayload` gain the social card/section.

### 1.2 Alternative — Sub-option (b): keep separate jobs + a link FK
Add `audit_jobs.linked_social_job_id` (nullable self-FK; **one additive Alembic migration**). The
website report reads the linked social job's `social_score`/`social_facts` at compose time. Lighter
on the pipeline, but adds **cross-job race risk** (the social job may still be running when the
website report renders) + more UX. The composite changes (steps 1–2) are identical. **Sub-option (a)
is recommended** — matches the single-result/single-PDF model, no races.

### 1.3 Touch-points (sub-option a)
| File | Change |
|---|---|
| `apps/worker/stages/scoring.py` | widen weights Literal + validator; `social_score` param w/ re-normalize; `score_audit` folds social; guard no-social path byte-identical |
| `rubrics/composite.yaml` | bump version + add social weight (**reproducibility boundary**) |
| `apps/worker/tasks.py` | website branch collects+scores social; extend `_upsert_audit_result` |
| `apps/worker/stages/report_payload.py` | 4th `social` ScoreCard + section; regenerate lead_gen formula |
| `templates/report.html` | Social section + 4th card |
| `apps/api/schemas/audits.py` + `routes/audits.py` | allow `social_handles` on website audit; surface `social_score` |
| `apps/frontend/pages/index.tsx`, `audit/[id].tsx`, `lib/api.ts` | optional handle inputs; render social inline; extend `ReportPayload` types |

### 1.4 Migration
**Sub-option (a): no migration needed** — `social_score`/`social_facts`/`social_handles` already
exist (0004) and the website scores are already nullable; a website job just starts populating them.
**Sub-option (b):** one additive migration adding `audit_jobs.linked_social_job_id` (self-FK; mind
SQLite portability via the `GUID` TypeDecorator).

### 1.5 How the recent additions fit
- **YouTube** + **FB posts** already flow through `collect_social_facts` → `summarize_profiles`, so
  the combined report's social section gets them with zero extra plumbing.
- **LLM social commentary** (`generate_social_commentary`) is deterministic-by-default; in a combined
  report keep it OFF by default so the merged report stays reproducible. If on, it only rewrites
  prose, never the `social_score`.
- The composite **must treat the social term as `skip_if_missing`-equivalent** so all three degrade
  gracefully exactly as they do standalone.

### 1.6 ⚠️ Risks (this is the dangerous one)
- **Reproducibility boundary:** bumping `composite.yaml` changes `rubric_version`, so **every existing
  website audit re-scored under the new composite yields a different lead_gen number.** Must be a
  deliberate, documented version bump (design rule #4).
- **Don't-disturb-shipped-website:** `compose_lead_generation_score` + `report_payload._score_cards`
  hard-code the 0.45/0.55 formula, the printed formula string, the card order
  `['lead_gen','seo','uxui']`, and `int(result.seo_score)` (assumes non-null). The **no-social path
  must be proven byte-identical** before bumping the composite. `test_scoring_engine.py`
  (strong≥85/weak≤35) and `test_report_payload.py` (card order + formula sentence) both need updating.
- **New runtime cost/dependency inside the website pipeline** (Apify can now fail mid-website-audit) —
  must stay on the graceful-skip path so an Apify outage can't fail a website audit.
- **Pre-flight regression test:** assert a handle-less website audit produces the **exact pre-change
  scores** BEFORE bumping the composite version.

### 1.7 What stays the same
The whole rubric engine (`score_category`, the six evaluators, `skip_if_missing` rescaling,
half-up `_round_score`), the entire social data layer (`collect_social_facts`, `apify_provider`,
`youtube_provider`, `extractor`, `score_social_audit`, `compose_social_report_payload`,
`generate_social_commentary`), and `rubrics/social.yaml` (no change). The data model already has
every column needed for sub-option (a).

---

## §2. Swap the IG/FB vendor: Apify → Bright Data
**Goal:** fetch Instagram/Facebook via Bright Data instead of Apify (YouTube stays on the YouTube
Data API). **Effort: MODERATE. No website-audit impact** (social is standalone).
**Requires a paid Bright Data account** (per-record billing, no free verification path).

### 2.1 Recommended approach
1. **Formalize the provider seam.** Today the "seam" is just `collector.py` importing concrete
   `apify_provider` functions and dispatching by platform string. Add a small `SocialProvider`
   Protocol (or a dataclass of callables) exposing `fetch_instagram_profile` /
   `fetch_facebook_page` / `fetch_facebook_posts`, implemented by both `apify_provider` and a new
   `brightdata_provider`. Add `get_social_provider(settings)` keyed off a new `social_provider`
   setting (default `"apify"` → nothing changes until flipped). **YouTube is NOT in this registry** —
   it stays a direct `fetch_youtube_channel` call.
2. **`brightdata_provider.py` (new) — the async flow.** Bright Data Dataset API:
   `POST /datasets/v3/trigger?dataset_id=<id>` (Bearer token, input rows) → `{snapshot_id}` →
   poll `GET /datasets/v3/progress/<snapshot_id>` until `status == "ready"` (handle
   `running`/`building`) → `GET /datasets/v3/snapshot/<snapshot_id>?format=json`. **Wrap so ANY
   failure / timeout / non-ready terminal state returns `None`** (mirrors `_run_actor`). Poll loop
   bounded by `brightdata_timeout_seconds`, sleeping `brightdata_poll_interval_seconds`, **must stay
   under the Celery soft limit (1740s) and never raise.**
3. **Per-provider normalization.** Bright Data's IG/FB payload keys differ from Apify's
   (IG: `account`, `followers`, `posts_count`, `is_business_account`, `profile_image_link`;
   FB: `page_name`, `likes`, `about`/`page_intro`). **Extend the existing `_first(payload, (…))`
   multi-key idiom** (already used for FB posts) so each field tries both vendors' key names — one
   vendor-agnostic normalizer per platform. **Leave the shared post-shape helpers
   (`_posts_per_month`, `_avg_engagement`, `_has_video`, `_parse_ts`) and `normalize_youtube_channel`
   untouched.**
4. **Config/env.** Add `social_provider: Literal["apify","brightdata"]="apify"`,
   `brightdata_api_token: SecretStr|None`, `brightdata_instagram_dataset_id`,
   `brightdata_facebook_dataset_id` (+posts dataset if separate), `brightdata_timeout_seconds`
   (default 180), `brightdata_poll_interval_seconds` (default 5). Document in `.env.template`.
   Update `collector._usable()` for IG/FB to check the **selected** vendor's credential.
5. **Scripts.** Add `check_brightdata_social.py` (probe that triggers+polls one IG profile and
   prints the raw shape — **calibrate the key-mapping against this before trusting scores**).
   `run_social_audit.py` works unchanged (it routes through `collect_social_facts`).

### 2.2 Touch-points
| File | Change |
|---|---|
| `apps/worker/stages/social/brightdata_provider.py` (**new**) | IG/FB trigger→poll→download, None-on-failure, bounded poll loop |
| `apps/worker/stages/social/collector.py` | select IG/FB provider via `social_provider`; keep YouTube direct; update `_usable()` + skip-reason |
| `apps/worker/stages/social/extractor.py` | widen IG/FB normalizers to `_first(…)` multi-key (Apify + Bright Data keys) |
| `apps/shared/config.py` + `.env.template` | `social_provider` + `brightdata_*` settings |
| `scripts/check_brightdata_social.py` (**new**) | live probe to calibrate key-mapping |
| `tests/fixtures/social_brightdata_*.json` (**new**) | Bright Data-shaped fixtures |
| `tests/unit/test_extractor_social.py` / `test_social_scoring.py` | assert Bright Data fixtures normalize to the **same** facts/scores as Apify (calibration invariant) |
| `tests/unit/test_youtube_provider.py` | extend collector skip-reason tests for the brightdata branch |

### 2.3 Migration
**None.** Entirely in the worker provider/collector/extractor + config + fixtures/tests.
`social_facts` stores the already-normalized vendor-agnostic bundle, so the stored shape is identical
regardless of vendor.

### 2.4 Risks
- **Paid account; live testing costs money** (no free tier like Apify).
- **Async flow is materially more complex** than Apify's one-shot call — bound the poll loop under
  the soft limit; guarantee None-on-failure (a raised exception would fail the whole job).
- **Key-mapping is the highest-risk piece** — mis-mapped Bright Data keys silently produce wrong/None
  facts. Calibrate against a real probe before trusting scores. Bright Data fixtures must reproduce
  the same normalized facts or the strong≥85/weak≤45 calibration asserts drift.
- **No website-audit impact;** reproducibility preserved (extractor/scoring stay pure; only the
  network source changes, and tests run off fixtures).

### 2.5 What stays the same
`collector.py`'s dispatch + graceful None→failed contract; all shared post-shape helpers +
`summarize_profiles` + `extract_social_facts`; the FB normalizer's `_first(…)` idiom (extend it);
`rubrics/social.yaml` + `score_social_audit` (**no version bump** — facts contract unchanged);
`_run_social_pipeline`, `_upsert_social_result`, `compose_social_report_payload`, `render_social_pdf`,
`generate_social_commentary`; the API, the social UI tab, the data model, the **entire website
pipeline**, and the **YouTube** provider/config/tests.

---

## §3. Object storage (S3) — decided against; revival sketch
The old plan's P2-7 added an S3 report/screenshot backend; the current build **removed it** in favor
of local filesystem + the cron retention job (`cleanup_storage`), since there is one internal VM and
no multi-node need. **Recommendation: do not revive unless you scale to multiple nodes or need
off-box durability.** If ever needed, it's a self-contained add (no scoring/website-audit impact):
- New `apps/shared/storage.py`: a `ReportStorage` protocol (`save`/`get`/`url`) + `LocalReportStorage`
  (today's behavior) + `S3ReportStorage`, selected by a `storage_backend: local|s3` setting; add `boto3`.
- Route all **writes** through it (`pdf_renderer`, `docx_renderer`, crawler screenshots); store a
  storage **key** instead of a path (no migration — `pdf_path` is a free-form string).
- Teach the three **download** paths (`/audits/{id}/report`, `/docx`, public `/shared/{token}/report`)
  to stream-local vs 307-redirect-to-signed-URL; teach `retention.py` an S3 prune mode.
- Keep `LocalReportStorage` the default so the shipped local path stays the live code path.

---

## §4. Invariants to preserve (apply to all options)
1. **Deterministic, rule-based scores** — the LLM never produces or changes a score.
2. **Graceful degradation** — a missing key / failed source never aborts or penalizes an audit.
3. **Versioned rubrics** — bump `version:` on any rubric/composite change (it's recorded in
   `rubric_version` for reproducibility). The §1 composite bump is the one place this is unavoidable.
4. **Don't disturb the shipped website audit** unless §1 is explicitly chosen — and even then, prove
   the no-social path is byte-identical first.
