# Social Audit Enhancement — Jira Epic & Tasks (copy-paste ready)

> **Status: IN PROGRESS (2026-07-07)** — **Wave 1 (SAE-6..10) + Wave 2 (SAE-12/13 Google Places)
> + SAE-9-full (category niche-match) DONE and tested** (rubric `phase2-social-v4`, 20 rules; 381
> unit tests pass, QA 11/11, repro byte-identical). Decisions in: SAE-1 = **both** (public tool +
> opt-in connected mode); Google Places **approved**. SAE-18 (LinkedIn) **closed Won't-Do**. Still
> open: SAE-2 (Apify fill-rate spike — needs token), SAE-3 (install the Places key), SAE-4 (Elda to
> confirm the starter category taxonomy in `social/categories.py`), SAE-5 (start Meta App Review),
> Wave 3 (SAE-14..17 YouTube+Meta connected — needs a DB migration + App Review), SAE-19 (final QA
> sign-off with Elda/Braulio). Scope from a domain-expert review of the social section of a
> combined report (builderleadconverter.com, 2026-06-30). Two reviewers: **Elda Loyola** (handle
> consistency, bio, phone/contact cross-check, business category, Google Business Profile, LinkedIn)
> and **Braulio Garcia** (public scrape is limited → wants authenticated YouTube Studio + Meta
> Business Suite analytics: reach, impressions/views, demographics, watch time, retention, follower
> growth). Feasibility verified by a cited deep-research pass (2026-07-07). Task IDs below are
> `SAE-n` placeholders — Jira assigns real `SMWA-xx` keys on creation; keep the SAE id in the
> description for traceability. Each task cites the expert remark it closes (E# = Elda, B# = Braulio).
>
> **Blocking decision (SAE-1):** is the social audit a COLD tool (public, runs on any prospect) or a
> CONNECTED tool (authenticated, consenting clients only)? Wave 1–2 are cold/public and safe to start
> now; Wave 3 (authenticated analytics) is gated on this decision.

## Epic

**Title:** Social Audit Depth & Integrations (SAE)

**Description:** The current social section scores public-scrape data only (Apify IG/FB + YouTube
Data API). Domain experts flagged it as thin and partly misleading (e.g. Facebook "0.0% engagement"
is a scrape artifact — public data lacks the reach/impressions denominator). This epic (a) mines
signals we already fetch but discard (phone, address, bio text, category, handles), (b) adds Google
Business Profile public data via the Places API, and (c) adds an opt-in "Connected" mode with
authenticated YouTube/Meta analytics. Website scoring and the website report are untouched; all new
social signals are `skip_if_missing` so a profile that hides a field rescales instead of false-failing.
Feasibility research: see the 2026-07-07 deep-research report (fields/scopes/costs/ToS per integration).

## Board

| ID | Title | Wave | Size | Depends on | Type | Closes |
|---|---|---|---|---|---|---|
| SAE-1 | Product decision: cold (public) vs connected (authenticated) | 0 | S | — | Spike/Decision | B1 |
| SAE-2 | Spike: Apify FB/IG field fill-rate audit (real SMB pages) | 0 | S | — | Spike | E3, E4 |
| SAE-3 | Spike: Google Places key + exact SKU cost sign-off | 0 | S | — | Spike | E5 |
| SAE-4 | Spike: niche→category taxonomy (contractor/remodeler/…) | 0 | S | — | Spike | E4 |
| SAE-5 | Spike: Meta App Review + Business Verification scoping | 0 | M | SAE-1 | Spike | B2 |
| SAE-6 | Extract discarded social facts (phone/address/bio text) | 1 | S | SAE-2 | Feature | E1, E3 |
| SAE-7 | Handle-consistency check + rule | 1 | S | SAE-6 | Feature | E-handle |
| SAE-8 | Bio-quality evaluation + rule(s) | 1 | S | SAE-6 | Feature | E-bio |
| SAE-9 | Business-category presence + niche-match rule | 1 | M | SAE-4, SAE-6 | Feature | E4 |
| SAE-10 | NAP cross-check (website ↔ social) for combined audits | 1 | M | SAE-6 | Feature | E3 |
| SAE-11 | social.yaml → v4 + render new signals (PDF/DOCX/UI) | 1 | M | SAE-7,8,9,10 | Feature | E1,E3,E4 |
| SAE-12 | Google Places provider (public GBP data) | 2 | M | SAE-3 | Feature | E5 |
| SAE-13 | Wire Places into NAP/category/reviews + rating signals | 2 | M | SAE-12, SAE-10 | Feature | E2(part), E5 |
| SAE-14 | Per-platform OAuth token store (table + migration) | 3 | M | SAE-1 | Feature | B1 |
| SAE-15 | YouTube Analytics provider (reuse Google OAuth) | 3 | M | SAE-14 | Feature | B1 |
| SAE-16 | Meta Graph provider (IG + FB Insights) | 3 | L | SAE-5, SAE-14 | Feature | B2 |
| SAE-17 | "Connect accounts" UI + connected-mode report sections | 3 | M | SAE-15 | Feature | B1, B2 |
| SAE-18 | LinkedIn — Won't-Do unless owner-authorized (decision) | 0 | XS | — | Decision | E-linkedin |
| SAE-19 | Rubric recalibration + QA gate + docs | gate | S | all | Chore | all |

---

## Wave 0 — Spikes & decisions (research first)

### SAE-1 — Product decision: cold (public) vs connected (authenticated)
**Type:** Spike/Decision · **Wave 0 · Size S** · Closes B1

Authenticated analytics (Braulio) require each audited business to OAuth-connect its own accounts —
only possible for consenting clients, not cold prospects. This changes *when in the funnel* the audit
runs. Decide with Darius: keep social as a cold public tool (ship Wave 1–2 only), or add an opt-in
"Connected" upgrade (Wave 3) on top of the public audit.

**Acceptance:** written decision recorded in `docs/19` / the epic; if "connected", Wave 3 is greenlit
and SAE-5 (Meta review) starts immediately; if "cold-only", Wave 3 is deferred and SAE-14…17 are parked.

### SAE-2 — Spike: Apify FB/IG field fill-rate audit
**Type:** Spike · **Wave 0 · Size S** · Closes E3, E4 (de-risks SAE-6/9/10)

Research verdict: the **Facebook Pages actor returns phone/address/category/email/website/rating —
but only for business Pages and only when public**; the **official Instagram Scraper returns NO
phone/address** (bio/category/followers only). Run `scripts/check_apify_social.py` against ~15 real
home-services/contractor pages and record which fields actually populate.

**Acceptance:** a short table of fill-rates per field per platform; conclusion on whether Places
(SAE-12) is *required* as the phone/address source or merely a fallback.

### SAE-3 — Spike: Google Places key + SKU cost sign-off
**Type:** Spike · **Wave 0 · Size S** · Closes E5

Places API (New) `GET places.googleapis.com/v1/places/{id}` is public (API key, no owner consent).
The fields we want (`nationalPhoneNumber`, `rating`, `userRatingCount`, `regularOpeningHours`,
`websiteUri`) bill at the **Enterprise** SKU; `reviews[].text` (≤5, no pagination) at
**Enterprise+Atmosphere**; a call is billed at its highest field's tier. Per-SKU free monthly calls
(~1,000 Enterprise) ⇒ effectively $0 at audit volume. Provision a key, confirm the 2026 per-1,000
rate from Google's own price list, get budget sign-off.

**Acceptance:** `GOOGLE_PLACES_API_KEY` provisioned + documented in `.env.template`; a one-line cost
estimate at expected monthly audit volume; go/no-go recorded.

### SAE-4 — Spike: niche→category taxonomy
**Type:** Spike · **Wave 0 · Size S** · Closes E4

Elda checks that the business is listed under the right FB/IG category (contractor, remodeler,
interior designer, home builder…). Build the acceptable-category map keyed off the job's existing
`niche` field, reconciled against real IG `businessCategoryName` / FB `category` / Places `types[]`
values (three different taxonomies).

**Acceptance:** a reviewed data table (niche → set of acceptable category strings per source) checked
in as config; edge cases (multi-category, generic "Local business") documented.

### SAE-5 — Spike: Meta App Review + Business Verification scoping
**Type:** Spike · **Wave 0 · Size M** · Depends SAE-1 · Closes B2

Auditing IG/FB accounts you don't own needs **Advanced Access → App Review + Business Verification**
(multi-week). Permissions: `instagram_basic` + `instagram_manage_insights` + `pages_read_engagement` +
`pages_show_list` (FB-Login path) or `instagram_business_basic` + `instagram_business_manage_insights`
(IG-Login path). IG account must be Business/Creator linked to a Page. Note the 2025 deprecation:
`impressions`→`views` (reach retained). Produce the checklist and start the clock.

**Acceptance:** documented permission list, screencast/use-case draft for review submission, business
verification prerequisites, realistic timeline; App Review submission opened (runs in parallel with Wave 1).

---

## Wave 1 — Public depth (in existing seams, ~$0, start now)

### SAE-6 — Extract discarded social facts (phone/address/bio text)
**Type:** Feature · **Wave 1 · Size S** · Depends SAE-2 · Closes E1, E3

`normalize_facebook_profile` (`social/extractor.py:319`) reads `category`/`email`/`website` but
**discards the phone/address the FB Pages actor returns**; every normalizer keeps only `bio_present:
bool` and throws the bio text away.

**Scope**
- Add `phone`, `address`, `bio_text` to `SocialProfileFacts` (`social/schema.py:25`); normalizers
  populate them (`None` when absent → `skip_if_missing`).
- FB: read `phone`/`address`; IG/YouTube: `bio_text` from `biography`/`description`; carry the raw
  digits normalized (strip formatting) for later comparison.

**Acceptance:** new fields present on the fact bundle; schema-drift test (`test_social_schema.py`)
covers them; existing scores unchanged (facts are additive, unscored until SAE-7…10).

### SAE-7 — Handle-consistency check + rule
**Type:** Feature · **Wave 1 · Size S** · Depends SAE-6 · Closes E-handle

Handles are captured per profile but never compared (report shows `builderleadconverter` /
`BuilderLeadConverter` / `builderleadconverter` — never evaluated).

**Scope**
- In `summarize_profiles` (`social/extractor.py:474`), add `handles_consistent: bool|None`
  (normalize: lowercase, strip `._-`; None if <2 profiles).
- New `social.branding.handle_consistency` rule (`rubrics/social.yaml`), `skip_if_missing`.

**Acceptance:** consistent set → pass, mismatched → finding; unit test on the normalization; a
single-profile audit rescales (rule skipped).

### SAE-8 — Bio-quality evaluation + rule(s)
**Type:** Feature · **Wave 1 · Size S** · Depends SAE-6 · Closes E-bio

**Scope**
- Derive per-profile bio checks from `bio_text`: has CTA (reuse `_CTA_RE`), mentions niche/service,
  mentions location, non-thin (≥ N chars). Aggregate to summary facts.
- New `social.profile.bio_quality` rule(s); keep the existing `profiles_complete_pct` rule.

**Acceptance:** thin/empty bio → finding with remediation; strong bio → pass; fixtures cover
CTA/niche/location permutations; grounding unaffected (deterministic).

### SAE-9 — Business-category presence + niche-match rule
**Type:** Feature · **Wave 1 · Size M** · Depends SAE-4, SAE-6 · Closes E4

`category` is captured and aggregated (`profiles_with_category`, `schema.py:111`) but **no rule scores
it** and nothing checks it against the niche.

**Scope**
- Two facts/rules: (a) category set at all; (b) category ∈ acceptable set for the job `niche` (SAE-4
  map). Handle the three taxonomies (IG `businessCategoryName`, FB `category`, later Places `types`).
- Finding copy names the expected category ("listed as 'Local business' — set it to Contractor/Home
  builder so buyers and search find you").

**Acceptance:** wrong/missing category → finding; correct → pass; unknown niche → rule (b) skips;
tests per niche.

### SAE-10 — NAP cross-check (website ↔ social) for combined audits
**Type:** Feature · **Wave 1 · Size M** · Depends SAE-6 · Closes E3

Website phone already exists (`extractor_uxui.py:38` `PHONE_RE` → `pages_with_phone`; JSON-LD
`schema_phone` in `extractor_seo.py:374`). Compare it to the social-side phone (SAE-6).

**Scope**
- In the combined path (`tasks.py::_augment_with_social:405`), pass the website contact facts to the
  social summarizer (or compare in `report_payload.build_social_report_data`); compute
  `nap_phone_consistent: bool|None` (normalized digit compare; None if either side missing).
- New `social.nap.consistency` rule; **combined audits only** (standalone social has no website side →
  rule skips). Finding lists the mismatched numbers.

**Acceptance:** matching numbers → pass; mismatch → finding naming both; standalone social audit
rescales (skipped); tests for match/mismatch/missing.

### SAE-11 — social.yaml → v4 + render new signals
**Type:** Feature · **Wave 1 · Size M** · Depends SAE-7,8,9,10 · Closes E1,E3,E4

**Scope**
- Bump `rubrics/social.yaml` → `phase2-social-v4`; add the new rules with `finding_label`/
  `remediation`/`impact`/`tier`; recalibrate against strong/weak fixtures.
- Render new signals in the social section: `templates/social_report.html` (standalone PDF),
  `report_payload.build_social_report_data` + `templates/report.html` (combined PDF),
  `docx_renderer._combined_xml` (DOCX), `pages/audit/[id].tsx` + `lib/api.ts` (UI). Keep field set
  identical across PDF/DOCX/UI (existing parity invariant).

**Acceptance:** new findings appear in all three surfaces with parity; `make qa` + `qa-repro` green;
`rubric_version` records v4; rerun-enrichment stays compatible (renamed/new facts `skip_if_missing`).

---

## Wave 2 — Google Business Profile (paid-public, ~$0 at volume)

### SAE-12 — Google Places provider (public GBP data)
**Type:** Feature · **Wave 2 · Size M** · Depends SAE-3 · Closes E5

**Scope**
- New `social/places_provider.py`: `fetch_place(business, settings)` → Text Search to resolve the
  place id, then Place Details (New) with a field mask for `displayName, formattedAddress,
  nationalPhoneNumber, types, primaryType, rating, userRatingCount, regularOpeningHours, websiteUri,
  businessStatus` (+ `reviews` if approved in SAE-3). httpx, graceful `None` on miss (mirror
  `apify_provider`).
- Register a `PlacesProvider` in `social/providers.py` (registry = one class + one entry); it is **not**
  a "platform" handle — resolve from the audited business name + website domain/URL.
- Config: `GOOGLE_PLACES_API_KEY` (SecretStr|None), timeout; empty ⇒ skip (like Apify/PSI).

**Acceptance:** live probe returns normalized GBP facts; no key ⇒ graceful skip; the field mask is
minimal (cost control); unit tests against a captured fixture payload.

### SAE-13 — Wire Places into NAP/category/reviews + rating
**Type:** Feature · **Wave 2 · Size M** · Depends SAE-12, SAE-10 · Closes E2 (part), E5

**Scope**
- Feed Places phone/address/category into SAE-9/SAE-10 as an **authoritative** third source (GBP is
  the canonical NAP for local SEO); tri-way consistency (website ↔ social ↔ GBP).
- New signals: `rating`, `userRatingCount` (review volume) → a "reviews/reputation" finding (ties to
  the report's existing Local Context page which *advises* GBP — now measured, not just advised).
- `skip_if_missing` throughout; standalone + combined both benefit.

**Acceptance:** GBP present → NAP compares three sources + surfaces rating/review count; GBP absent →
rescales; tests for match/mismatch across the three sources.

---

## Wave 3 — Connected mode (authenticated analytics; gated on SAE-1)

### SAE-14 — Per-platform OAuth token store
**Type:** Feature · **Wave 3 · Size M** · Depends SAE-1 · Closes B1

**Scope**
- Generalize the GSC token pattern: either extend `google_search_console_connections` or add a
  `social_connections` table (`apps/shared/models.py` + Alembic migration; head is `20260625_0005`) —
  platform, account id/handle, access/refresh token, expiry, scopes. Mind SQLite portability (GUID/JSON).
- Token refresh + revoke; per-audit lookup of a connected token for the audited handle.

**Acceptance:** tokens persist/refresh/revoke; migration additive + auto-runs; no plaintext token in
logs; unit tests for the store + refresh.

### SAE-15 — YouTube Analytics provider (reuse Google OAuth)
**Type:** Feature · **Wave 3 · Size M** · Depends SAE-14 · Closes B1

Reuses the existing Google OAuth (`routes/google.py`, `google_search_console.py`) — add scopes
`yt-analytics.readonly` + `youtube.readonly` to `GSC_SCOPES`'s sibling. Owner-consent only
(`channel==MINE`).

**Scope**
- `social/youtube_analytics_provider.py`: query the YouTube Analytics API for `estimatedMinutesWatched`,
  `averageViewDuration`/`averageViewPercentage`, retention (`audienceWatchRatio`), traffic sources
  (`insightTrafficSourceType`), `subscribersGained/Lost`, demographics (`ageGroup`/`gender`/`country`).
- Runs only when a YouTube token exists for the channel; else the public YouTube Data API path
  (unchanged) still supplies public stats. New "YouTube performance (connected)" report block.

**Acceptance:** connected channel → private metrics render; unconnected → unchanged public path; token
scoped correctly; fixture-based unit tests (no live calls in CI).

### SAE-16 — Meta Graph provider (IG + FB Insights)
**Type:** Feature · **Wave 3 · Size L** · Depends SAE-5, SAE-14 · Closes B2

Blocked until App Review/Business Verification (SAE-5) is approved. Separate Facebook Login OAuth
(no reuse of Google).

**Scope**
- Facebook Login OAuth flow + token store (SAE-14); `social/meta_insights_provider.py` for IG account
  + media insights and FB Page insights: `reach`, `views` (post-2025 rename of impressions),
  follower/fan growth, audience demographics (age/gender/city/country), per-post insights.
- Graceful skip when unconnected or permission missing; new "Instagram/Facebook performance
  (connected)" report block using **current** 2026 metric names.

**Acceptance:** connected Business IG/Page → private metrics render; unconnected → public scrape
unchanged; metric names match the live API (no deprecated `impressions`); fixture-based tests.

### SAE-17 — "Connect accounts" UI + connected-mode sections
**Type:** Feature · **Wave 3 · Size M** · Depends SAE-15 · Closes B1, B2

**Scope**
- On the audit form / detail page (`pages/index.tsx`, `pages/audit/[id].tsx`, `lib/api.ts`): "Connect
  YouTube / Connect Meta" buttons (OAuth), connection status, and the connected-analytics sections
  (behind `status == "complete"`, mirroring the accessibility-advisory pattern).
- Clearly label public-vs-connected data so the "0.0% engagement" scrape artifact is replaced by real
  reach-based engagement when connected.

**Acceptance:** connect/disconnect works end-to-end; connected sections render only with a valid token;
public audit unchanged for non-connected users.

---

## Closeout

### SAE-18 — LinkedIn: Won't-Do unless owner-authorized (decision) — ✅ CLOSED (Won't-Do, 2026-07-07)
**Type:** Decision · **Wave 0 · Size XS** · Closes E-linkedin · **Resolution: WON'T DO** (revisit only
under connected mode if a client authorizes an official LinkedIn app; no cold-audit LinkedIn support).

Research verdict: **no public company-data API**; partner approval is gated ($10k–50k+/yr reported);
LinkedIn's User Agreement (Nov 3 2025) prohibits automated scraping; LinkedIn sued Proxycurl (Jan
2025 → shut down Jul 2025). Matches the prior "LinkedIn dropped" decision. Record as Won't-Do for
non-owned audits; revisit only under connected mode if a client authorizes an official LinkedIn app.

**Acceptance:** decision documented; Elda/Darius acknowledged; ticket closed Won't-Do.

### SAE-19 — Rubric recalibration + QA gate + docs
**Type:** Chore · **Wave gate · Size S** · Depends all · Closes all

**Scope**
- Recalibrate `social.yaml` thresholds against real niche accounts (strong/weak fixtures); ensure new
  rules don't distort the standalone Social Score or the combined Overall Readiness weighting.
- Gates: `make test`, `make qa`, `make qa-repro` green; reproducibility byte-identical; update
  CLAUDE.md §5 (social) + `docs/08–10` where they describe social scope.

**Acceptance:** all gates green; docs reconciled; before/after example audit reviewed by Elda/Braulio.
