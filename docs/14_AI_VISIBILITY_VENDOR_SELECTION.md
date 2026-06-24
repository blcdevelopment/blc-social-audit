# 14 - AI Visibility Vendor Selection (Rank Prompt)

**Status:** Planning / vendor-decision document. Nothing here is built yet (Phase 2).
**Date:** 2026-06-22
**Scope:** Picks the data vendor for the planned **AI-visibility report section** described in
[13_AI_INSIGHTS_INTEGRATION_PLAN.md](13_AI_INSIGHTS_INTEGRATION_PLAN.md) §9.1 / §11.1.
**Supersedes:** docs/13 originally named **Surfer** for this section. This document resets the
pick to **Rank Prompt** based on 2026-06-22 vendor research.

> **PARKED (2026-06-23).** This vendor selection is **on hold**. The Rank Prompt API Starter
> subscription ($99/mo) has **not been purchased**, so live billing remains unverified and the
> §10 trial cannot run. Per operator decision, **AI Insights (docs/13 + this doc) is deferred**
> and **Phase 2 proceeds without it** — no Phase-2 task depends on AI Insights. The body below is
> retained as-is for reference; **resume this vendor pick once the subscription is sorted.**

> **Confidence convention used throughout this doc.** Read it carefully — it is the whole point.
> - **CONFIRMED** = verified against Rank Prompt's published pages/schema (still a documentation
>   claim, not a live API call).
> - **DOCUMENTED, NOT LIVE-VERIFIED** = the official docs describe it, but we have not yet run it
>   against a real account/key. Rank Prompt's own pages contradict each other on billing (see §6.4),
>   so "documented" is **not** proof it works on our account.
> - **UNCONFIRMED / OPEN RISK** = not settled even in the docs; must be checked in the trial.
>
> Do not promote anything from "documented" to "confirmed live" until the trial in §10 passes.

---

## 0. TL;DR — the decision

**Proceed with Rank Prompt API Starter ($99/mo, MONTHLY — not annual) on a 7-day trial.**
Rank Prompt is the **provisional** choice: cheapest vendor with a real, self-serve, documented
public REST API. The commitment is gated on a live **quota-delta trial** (§10) and on confirming
a couple of open items (§6).

**One-line status:**
> Tiered credit **model is documented and settled per the official report schema**; **live billing
> is NOT yet verified**. Rank Prompt is the **provisional** vendor pick, pending (a) a quota-delta
> trial confirming the −15-credit charge, and (b) confirmation of separate **Google AI Mode** support.

**Operating shape for our 5–10 internal users:**
- Four **bundled** platforms by default (ChatGPT, Perplexity, Google AI Overviews, Claude).
- **Gemini and Grok** (and the `*-Search` variants) behind an **admin-controlled** toggle.
- **One** server-side API key (staff never touch Rank Prompt creds).
- **Cached** results — opening a report never reruns a scan.
- **Queued** worker execution to respect the 10-req/min LLM-dispatch limit.

---

## 1. What needs a vendor

The Phase-2 AI-visibility section mirrors the **SEMrush "AI Visibility"** dashboard:

- A **gauge / visibility score**
- **Mentions** and **citations** (incl. citations grouped by domain)
- **Per-LLM distribution** (which AI engines mention the brand)
- A **"mentions by country"** panel
- **Trend** lines over time

**Key product reality (unchanged):** BLC produces **point-in-time AUDITS**, not continuous
monitoring. A one-shot scan yields a **SNAPSHOT** (current score / mentions / citations /
distribution). The multi-month **TREND** lines require continuous tracking over time, which **no
tool can backfill**. v1 should plan for a snapshot, not trends.

---

## 2. Vendor comparison

### 2.1 Leading choice — Rank Prompt (rankprompt.com)
Cheapest option with a real, documented, self-serve public REST API. Server-to-server only;
Bearer `rp_live_` keys. Details in §3–§6.

### 2.2 Fallback — Otterly.ai
- Public API on **Standard $189/mo** (the Lite $29 tier has **no API**).
- Daily tracking, 6 platforms, **50+ countries**, citation analysis.
- ~2–3× the cost of Rank Prompt, but **more mature** and ships the country data that Rank Prompt
  models only as per-region reports.
- **Use as fallback** if the Rank Prompt trial fails (billing not live, or AI-visibility data not
  returned as structured JSON).

### 2.3 Ruled out (budget + self-serve-API requirement)
| Vendor | Why ruled out |
|---|---|
| RadarKit | API is **Enterprise-only** |
| Peec AI | API **Enterprise-only**, beta |
| SEMrush AI Visibility Toolkit | $99/mo dashboard, but toolkit data **not cleanly self-serve via API**; integrations need Enterprise AIO |
| Surfer AI Tracker | $95–495 add-on, **no confirmed public API** (this is what docs/13 originally assumed) |
| Ahrefs free AI checker | Snapshot only, **no API** |

---

## 3. Rank Prompt pricing & API tiers (CONFIRMED)

| Plan | Price | Request units | Credits | Notes |
|---|---|---|---|---|
| API Basic | $29/mo | 10k units | — | Add-on to a dashboard plan |
| **API Starter** | **$99/mo** | 50k units | **500 credits** | + 7-day trial. **Our pick.** |
| API Pro | $299/mo | 200k units | 2000 credits | Scale-up option |

- **Cheapest API-capable combo** ≈ dashboard **Starter** ($39/mo annual, 150 credits) **+ API
  Basic** ($29) ≈ **~$68/mo**. We are choosing the cleaner **$99 API Starter** instead (more
  credits, single plan, trial included).
- Two meters exist: **request units** (general API call budget) and **credits** (consumed by
  prompt scans / report runs — see §4).

---

## 4. Credit model (MODEL settled per schema; LIVE billing unverified)

### 4.1 The documented tiered model — CONFIRMED in the official report schema
The dashboard markets "Prompt Scan = 1 credit across all 6 platforms," but **the API report
schema tiers the engines.** This is **settled per the official schema** (not the open question):

| Platforms selected per prompt | Documented credit cost |
|---|---|
| ChatGPT + Perplexity + Google AI Overviews + Claude (the **bundle**) | **1 credit total** |
| + Gemini | **+1 credit** |
| + Grok | **+1 credit** |
| + ChatGPT Search | **+1 credit** |
| + Claude Search | **+1 credit** |

So our likely **6-platform** config (4 bundled + Gemini + Grok) = **3 credits/prompt**.

> Do **not** record this as "flat 1 credit / 6 platforms." The dashboard "flat" marketing ≠ the API
> report billing. They are different surfaces.

### 4.2 Cost per audit (at 20 prompts/audit)
| Configuration | Credits |
|---|---|
| Four bundled platforms | **20** |
| Four bundled + Gemini + Grok (6 platforms) | **60** |
| Six platforms × three countries | **180** |

(Country = per-region report, so countries multiply linearly — see §6.1.)

### 4.3 Monthly capacity on the $99 Starter (500 credits)
| Audit type | Approx. audits / month |
|---|---|
| 20-prompt, four-platform | **~25** |
| 20-prompt, six-platform, single-country | **~8** |
| 20-prompt, six-platform, three-country | **~2** |

### 4.4 What is still unverified — LIVE BILLING ONLY
The **model** is settled. The open question is purely whether `/v1` **actually debits credits on
our account** right now. See the documentation contradiction in §6.4. The trial in §10 resolves it.

---

## 5. What the API documents (DOCUMENTED, NOT LIVE-VERIFIED)

An earlier round of this research wrongly recorded several of these as **missing** ("not in the
API" / "coming soon"). That was premature — the current official docs **do** document them. They
are listed here as **documented**, with the standing caveat that the trial must confirm they
return real data.

**Reports / data the API documents:**
- `visibility_score`
- **Per-prompt, per-platform results**
- **Country & location fields**
- **Competitors**
- **Citations**, plus **domain-grouped citations** via
  `GET /v1/brands/{brand_id}/citations/by-domain`
- **Scheduled reports**
- **Schedule analytics** + **per-platform-performance trends**
- **Prompt-level run history** (each completed run + its platform breakdown)

The report endpoint returns prompts with platform results, country/location info, aggregate
visibility, ranked results, and total results.

**Auth & limits (CONFIRMED):**
- Server-to-server only; Bearer `rp_live_` keys.
- **General limit: 120 requests/min.**
- **LLM-dispatching endpoints: 10 requests/min per API key** (tighter) → **must queue**.
- Credit balance is readable from `GET /v1/me/quota` (free) plus `X-RP-Quota-*` response headers.

---

## 6. Known gaps & open risks

### 6.1 "Mentions by country" — no single chart endpoint (DOCUMENTED limitation)
There is **no ready-made by-country chart endpoint**. Rank Prompt models each market as a
**separate region configuration → one report per region**. To build the SEMrush-style by-country
panel, the BLC app must **run per-region reports and aggregate them app-side**. This multiplies
credit cost per the formula in §7.

### 6.2 Google AI Mode — UNCONFIRMED (open risk)
The platform enum includes **`ai_overviews`**, but research found **no separate `ai_mode`
platform**. **Do NOT promise distinct "Google AI Overviews" vs "Google AI Mode" reporting** until
Rank Prompt confirms it. Verify in the trial.

### 6.3 No literal `mention_count` field (DOCUMENTED — design around it)
Do **not** assume a `mention_count` field exists. The report schema provides **`ranked_prompts`**,
**`total_results`**, and **`brand_appears` per result**. The BLC app must **compute** mention count
and mention rate from those.

### 6.4 Documentation contradicts itself on billing (the core open risk)
- The **developer page** says AI-visibility reports, citations, and scheduled reports are available
  **"today."**
- The **API pricing page** says **no `/v1` endpoint currently deducts credits** and refers to
  report billing **"arriving later."**

Public docs **cannot settle** which applies to our account. Possible explanations: the pricing page
is stale; report endpoints are in **staged rollout**; or endpoints are **live but not yet billed**.
**Only the live trial (§10) resolves this.**

### 6.5 Maturity
Rank Prompt is the **newest / least-proven** vendor in the comparison. That is the price of being
the cheapest with a real API — hence the monthly-not-annual commitment and the explicit trial gate.

---

## 7. Cost drivers & sizing for 5–10 internal users

**The cost driver is NOT user count.** The real formula is:

```text
credits ≈ prompts × premium platforms × countries × reruns
```

**Sizing sanity check** against the Starter's 500 credits/month, assuming **one six-platform,
single-country, 20-prompt audit per user per month (60 credits each):**

| Users | Credits/month | Fits 500? |
|---|---|---|
| 5 users | ~300 | ✅ Yes |
| 10 users | ~600 | ❌ **Exceeds 500** |

**Implication:** with the **four-bundled default (20 credits/audit)**, 10 users ≈ **200 credits** —
comfortable. The six-platform config is the expensive path, which is exactly why **Gemini/Grok are
admin-gated** (§8.3). If six-platform usage grows, size up to **API Pro** rather than relaxing the
default.

---

## 8. Architecture & integration plan

### 8.1 Account & key model
- **One Rank Prompt API account** behind the BLC backend.
- Staff log into BLC and **never touch Rank Prompt creds/keys**.
- **Confirm in writing** with Rank Prompt that 5–10 staff may view API-derived results under one
  subscription (no per-seat dashboard requirement).

### 8.2 Caching + queueing (already free with the current stack)
- Store facts in **`external_seo_facts.ai_visibility`** (the existing JSON blob seam).
- Put the Rank Prompt call **only** in an **on-demand Celery enrichment task** (docs/13 §12.4,
  `rerun-ai-seo-insights`) — never in the always-on audit path.
- Celery **prod concurrency = 1** already serializes calls, which respects the 10-req/min cap.
- The **read path must never re-scan** — opening a stored report shows cached facts.
- Display remaining credits from `GET /v1/me/quota` + `X-RP-Quota-*` headers.

### 8.3 Admin gating — NEW WORK REQUIRED
"Restrict reruns / six-platform to admins" needs new work: **there is no admin role today** (Clerk
is binary signed-in/out). Add a role check (**Clerk org role or `publicMetadata`**) or an
allowlist before exposing the premium-platform toggle and reruns.

### 8.4 Determinism boundary (unchanged architecture rule)
Tools/LLMs provide **facts**; BLC deterministic rubrics produce **scores**. Rank Prompt data is a
**fact source** for the report section; it does **not** feed scoring in v1.

---

## 9. The decision

1. **Vendor:** Rank Prompt (provisional). Otterly.ai is the fallback.
2. **Plan:** API Starter **$99/mo MONTHLY** — do **not** commit annually until the trial passes.
3. **Defaults:** four bundled platforms; Gemini/Grok (and `*-Search`) **admin-gated**.
4. **Caps:** ~20 prompts/audit; one country by default.
5. **Engineering:** cache results (no rescans on read), queue execution, single server-side key,
   on-demand Celery enrichment, add a Clerk admin role for gating.

---

## 10. Decisive trial plan (the gate before any commitment)

During the 7-day trial, run **five prompts** across **six platforms**:

```text
chatgpt, perplexity, ai_overviews, claude, gemini, grok
```

**Step 1 — check quota** (`GET /v1/me/quota`) before the run.

**Step 2 — run** the 5 prompts × 6 platforms.

**Step 3 — re-check quota and read the delta:**

| Quota delta | Interpretation |
|---|---|
| **−15 credits** | Documented tiered billing **confirmed live** (5 × 3 credits). ✅ |
| **−0 credits** | `/v1` credit billing **not active yet** (matches the stale-pricing-page theory). |
| **−5 credits** | Live behaviour **contradicts the schema** (flat 1-credit billing). |

**Step 4 — confirm these endpoints return real structured data:**
- `GET /v1/reports/{report_id}`
- `GET /v1/brands/{brand_id}/citations/by-domain`
- `GET /v1/scheduled-reports/{id}/analytics`
- `GET /v1/scheduled-reports/{id}/prompt-history/{prompt_id}`

**Step 5 — confirm platform coverage:** check whether a **separate `ai_mode` platform** exists, or
whether `ai_overviews` is the only Google surface (§6.2).

**Pass condition:** −15 credit delta **and** the four endpoints return real data. Only then is the
"available today" vs "ships later / not yet billed" contradiction resolved **for our account**, and
only then should annual billing or production integration be considered.

---

## 11. Open items checklist (must close before production commit)

- [ ] **Live billing:** quota delta is **−15** on the 5×6 trial run (§10).
- [ ] **Endpoints live:** the four §10 endpoints return real structured data.
- [ ] **Google AI Mode:** separate `ai_mode` platform confirmed (or accept `ai_overviews`-only).
- [ ] **mention_count:** confirm `ranked_prompts` / `total_results` / `brand_appears` are present and
      sufficient to compute mention count + rate (§6.3).
- [ ] **By-country:** confirm per-region report aggregation works for the by-country panel (§6.1).
- [ ] **Licensing:** written confirmation that 5–10 staff may view results under one subscription.
- [ ] **Admin role:** Clerk role/allowlist built before exposing premium-platform toggle (§8.3).

---

## 12. Terminology & references

**Bundled platforms (1 credit total):** ChatGPT, Perplexity, Google AI Overviews, Claude.
**Premium platforms (+1 credit each):** Gemini, Grok, ChatGPT Search, Claude Search.

**Related docs:**
- [13_AI_INSIGHTS_INTEGRATION_PLAN.md](13_AI_INSIGHTS_INTEGRATION_PLAN.md) — the broader AI-insights
  plan this section plugs into (originally named Surfer; superseded here for the visibility vendor).
- [08_PHASE2_PLAN.md](08_PHASE2_PLAN.md) — Phase-2 scope.

**Process note:** this document supersedes an earlier memory that recorded API "gaps" (country /
trends / citations) as fact **before** verification completed. The corrected position: those
features are **documented**, the credit **model is settled per schema**, but **live billing and a
couple of platform details remain unverified** — hence the provisional pick and the hard trial gate
above. Treat "documented" and "confirmed live" as different states until §10 passes.
