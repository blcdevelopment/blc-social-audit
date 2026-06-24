# 13 - AI Insights Integration Plan

> **⛔ PARKED / DEFERRED (2026-06-23):** This entire plan is **on hold**. It is **blocked on an
> unpurchased paid vendor subscription** (Rank Prompt API Starter $99/mo; live billing
> unverified — see [14_AI_VISIBILITY_VENDOR_SELECTION.md](14_AI_VISIBILITY_VENDOR_SELECTION.md)).
> **Phase 2 is proceeding WITHOUT AI Insights.** Deferring was **verified safe**: no Phase-2 task
> depends on AI Insights (it depends only on the shipped Phase-1 spine and on its own vendor
> trial). **To be resumed once the subscription is sorted.** The body below is retained as the
> as-planned reference.

**Status:** Planning document. Nothing in here is built yet.
**Date:** 2026-06-17
**Canonical doc:** This file is the single AI insights plan. The previous separate AI SEO tooling plan has been merged here.

> **⚠️ Partially superseded (2026-06-22):** the **AI-visibility vendor pick has changed from
> Surfer to Rank Prompt** — see [14_AI_VISIBILITY_VENDOR_SELECTION.md](14_AI_VISIBILITY_VENDOR_SELECTION.md).
> This affects **only** the AI-visibility section (§6.1, §9.1, §11.1). Everything else in this plan
> — Windsor.ai analytics, Frase content research, OpenAI report intelligence, data architecture,
> the enrichment seam (§12.4), scoring, phases, and the file checklist — **remains current.**

## 0. TL;DR

BLC should treat "AI insights" as two layers:

```text
Layer 1: External AI SEO and analytics facts
  Surfer SEO -> AI visibility, prompt tracking, brand and competitor mentions
  Windsor.ai -> GSC, GA4, Ads, CRM, channel and conversion analytics
  Frase      -> content gaps, topic clusters, content briefs, SEO/GEO research

Layer 2: OpenAI (ChatGPT) report intelligence
  OpenAI -> optional prose polish, strategic narrative, and audit Q&A over stored BLC facts
```

The most important architecture rule stays the same:

```text
Tools and LLMs provide facts or prose.
BLC deterministic rubrics produce scores.
```

Best build order:

1. **Validate Surfer, Windsor, and Frase manually on 2 to 3 real sites.**
2. **Add normalized external AI SEO facts and report sections.**
3. **Add on-demand enrichment with snapshot/restore safety.**
4. **Add OpenAI (ChatGPT) polish/strategic narrative/Q&A as an optional layer over the richer facts.**
5. **Only then decide if AI SEO facts should affect scores.**

## 1. Why This Is One Plan

There were two related ideas:

1. **AI SEO tooling:** paid platforms that tell us where the brand appears in AI answers, what content is missing, what competitors are winning, and which traffic/conversion gaps matter.
2. **AI report intelligence:** OpenAI (ChatGPT) rewriting/summarizing/explaining the audit in a warmer, more strategic way, plus answering questions about the audit.

They belong together, but they are not the same thing.

| Layer | Main job | Tools |
|---|---|---|
| External AI SEO facts | Collect new facts the current audit cannot know alone | Surfer, Windsor, Frase |
| Report intelligence | Explain stored facts better, answer questions, polish prose | OpenAI (ChatGPT) |
| Deterministic scoring | Turn facts into BLC scores | BLC YAML rubrics |

This doc is now the canonical plan for all of that.

## 2. Current Architecture Fit

The current BLC system already has the right spine:

```text
Next.js UI
  -> FastAPI
  -> PostgreSQL
  -> Redis/Celery worker
  -> crawler / PSI / SEO / UX / external SEO
  -> deterministic YAML scoring
  -> deterministic commentary
  -> grounding validation
  -> PDF/DOCX rendering
```

The new integrations should extend the existing pipeline, not replace it.

Current fact storage:

```text
audit_results.crawled_pages
audit_results.seo_facts
audit_results.uxui_facts
audit_results.psi_facts
audit_results.external_seo_facts
audit_results.score_breakdown
audit_results.commentary
audit_results.validation_log
audit_results.report_metadata
```

Fastest path:

```text
Store new AI SEO facts under external_seo_facts first.
Move them into dedicated JSONB columns later after contracts stabilize.
```

## 3. Non-Negotiable Guardrails

These guardrails come from the current architecture and must not change:

1. **Scores are deterministic.** Vendors and LLMs never decide BLC scores.
2. **LLMs do not add, remove, reorder, or re-rank findings.** They may polish prose only when explicitly allowed.
3. **Missing tool data degrades gracefully.** If Surfer/Windsor/Frase is missing, failed, or skipped, the base audit still completes.
4. **Only complete external data may be scored.** Non-complete source summaries must be stripped before scoring.
5. **All numeric claims must be grounded.** Report prose can cite only stored facts/scores.
6. **No autonomous agent loop.** Keep the fixed Extract -> Score -> Commentate -> Validate pattern.
7. **Base audit stays valuable without paid tools.** Paid tools create premium enrichment, not a hard dependency.
8. **On-demand first.** Do not run expensive AI SEO enrichment automatically on every audit until cost and value are proven.

## 4. Tool Recommendation

For best overall results:

```text
Surfer + Windsor + Frase
```

But use each for a different job:

| Tool | Main BLC job | Why it matters |
|---|---|---|
| **Surfer SEO** | AI visibility and prompt tracking | Answers "Are we mentioned in ChatGPT/Claude/Gemini/Perplexity/AI Overviews, or are competitors mentioned instead?" |
| **Windsor.ai** | Analytics and conversion proof | Pulls GSC, GA4, Ads, CRM, and channel data so recommendations have business evidence |
| **Frase** | Content gaps and SEO/GEO content strategy | Finds missing topics, FAQs, clusters, and page-level content improvements |
| **OpenAI (ChatGPT)** | Report prose, strategic synthesis, Q&A | Explains BLC's stored facts in a client-ready way, without changing scores |

If budget is tight:

```text
Start with Surfer + Windsor.
Add Frase after testing whether Surfer's content workflow is enough.
```

If the only immediate question is "Where are we mentioned in GPT or Claude?":

```text
Start with Surfer, but verify Claude coverage and API/export access before purchase.
```

## 5. Tool Comparison

| Area | Surfer SEO | Windsor.ai | Frase | OpenAI (ChatGPT) |
|---|---|---|---|---|
| Main category | AI SEO / content optimization | Data connector / analytics pipeline | SEO/GEO content research | LLM prose and Q&A |
| Best BLC use | AI mentions, prompt tracking, AI visibility | GSC, GA4, Ads, CRM, leads, conversions | Content gaps, topics, briefs, SERP research | Explain and polish stored audit facts |
| Tells us if brand appears in GPT/AI | Strong fit | No | Some fit | No, unless fed external tool facts |
| Claude mention tracking | Must verify plan/API coverage | No | Must verify depth | No; the LLM writes prose, it is not a visibility tracker |
| Competitor AI visibility | Strong fit | No | Some fit | Can summarize if facts are provided |
| Prompt tracking | Strong fit | No | Some fit | Can help generate prompts, not monitor them |
| AI Overviews / AI Mode | Strong fit | No | Some fit | No direct monitoring |
| Content score | Strong fit | No | Strong fit | Can explain score, not compute vendor score |
| Topic clusters | Some fit | No | Strong fit | Can summarize clusters |
| Content gaps | Strong fit | No | Strong fit | Can explain gaps from facts |
| Keyword intent | Some fit | Indirect via GSC queries | Strong fit | Can classify only if facts are provided |
| GSC data | Not main role | Strong fit | Not main role | No |
| GA4 data | No | Strong fit | No | No |
| Google Ads data | No | Strong fit | No | No |
| CRM/lead data | No | Strong fit if connected | No | No |
| Business proof | Medium | Strong | Medium | Summarizes proof |
| API fit | Medium; confirm entitlement | Strong; public API docs | Strong-looking; pricing says API/MCP included | Direct SDK/API |
| MCP fit | No clear public MCP surface found | Clear Windsor MCP offering | Pricing says API/MCP access | Not needed for production path |
| Best first report section | AI Visibility | Traffic and Conversion | Content Gap Roadmap | Strategic Summary / Ask This Audit |
| Main risk | API and Claude coverage need confirmation | Not an AI SEO insight tool | Overlap with Surfer | Hallucination if not grounded |
| BLC priority | 1 | 2 | 3 | Optional overlay after facts |

## 6. Pricing, API, MCP, and Ease of Use

Pricing and plan features change. Treat this as a public-page snapshot checked on 2026-06-17.

### 6.1 Surfer SEO

> **⚠️ Superseded for AI visibility (2026-06-22):** Surfer is **no longer the AI-visibility
> vendor** — research found no confirmed self-serve public API for its AI tracker. The pick is now
> **Rank Prompt**; see [14_AI_VISIBILITY_VENDOR_SELECTION.md](14_AI_VISIBILITY_VENDOR_SELECTION.md)
> for pricing, the tiered credit model, API features, and the trial gate. The Surfer notes below
> are kept for historical context only.

Observed public pricing:

| Plan | Public price note | Practical BLC read |
|---|---:|---|
| Discovery | $49/month, billed yearly | Too small for serious AI visibility |
| Standard | $99/month, billed yearly | Possible starter, but prompt/model limits may be tight |
| Pro | $182/month, billed yearly | Better practical starting point for AI visibility |
| Peace of Mind | $299/month, billed yearly | Best if BLC needs more usage and API access |
| Enterprise | Starts around $999/month | Too heavy unless BLC productizes this at scale |

API:

- Surfer pricing references API access, especially around higher plans.
- Do not assume low-plan API access is enough.
- Before building, confirm:
  - which endpoints are available;
  - whether AI visibility data is API-accessible;
  - whether Claude-specific visibility is included;
  - prompt limits per engine;
  - export limits.

MCP:

- No clear public MCP contract found for Surfer.
- Treat Surfer as API/export/dashboard first.

Ease:

- Dashboard use: easy.
- Product integration: medium until API entitlement is confirmed.

### 6.2 Windsor.ai

Observed public pricing:

| Plan | Public price note | Practical BLC read |
|---|---:|---|
| Free | Free | Useful for testing only |
| Basic | $23/month monthly, $19/month annual | Small connector experiments |
| Standard | $118/month monthly, $99/month annual | Likely first useful production plan |
| Plus | $299/month monthly, $249/month annual | More sources/accounts |
| Professional | $598/month monthly, $499/month annual | Larger reporting/data needs |

API:

- Windsor has public API documentation.
- It supports database/warehouse style workflows.
- Best BLC pattern is likely:

```text
Windsor -> Postgres schema or Windsor API -> BLC normalized facts
```

MCP:

- Windsor has a public MCP offering for AI insight workflows.
- Use MCP for operator/assistant analysis, not as the production audit pipeline.

Ease:

- Dashboard use: easy.
- Postgres sync: easy to medium.
- BLC normalization: medium, because analytics rows must become stable audit facts.

### 6.3 Frase

Observed public pricing:

| Plan | Public price note | Practical BLC read |
|---|---:|---|
| Starter | $49/month | Good first API/MCP experiment |
| Professional | $129/month | Better if multiple content workflows are needed |
| Scale | $299/month | Use if audits/usage grow |

API:

- Frase pricing says API and MCP access are included.
- Before building, confirm:
  - content brief create/retrieve endpoints;
  - content score retrieve endpoint;
  - missing topics retrieve endpoint;
  - audit workflow endpoint;
  - AI visibility metrics API coverage.

MCP:

- Frase pricing advertises API/MCP access.
- MCP may be useful for internal workflows.
- For production reports, prefer deterministic API calls and persisted facts.

Ease:

- Dashboard use: easy.
- Product integration: likely easy to medium.
- Normalization still required.

### 6.4 OpenAI (ChatGPT)

This layer uses the **OpenAI API key**. The codebase's dormant `_call_openai` scaffolding is already
OpenAI-based, so this is turned on, not rebuilt (see §14.4).

Pricing:

- Usage-based by model and token volume (OpenAI billing).
- Confirm exact model IDs and per-token prices in the OpenAI dashboard at implementation time.

API:

- Direct OpenAI Python SDK integration (`openai` is already a dependency).
- Best used after deterministic facts are collected and stored.

MCP:

- Not required for the production path.
- The production path should call the model from the worker/API with compacted, grounded context.

Ease:

- Prose polish: medium.
- Strategic summary: medium.
- Q&A: medium to high risk unless clearly labeled and constrained.

## 7. Which Tool Answers Which Business Question?

| BLC report question | Best tool |
|---|---|
| Are we mentioned in ChatGPT? | Surfer |
| Are we mentioned in Claude? | Surfer, but verify coverage before purchase |
| Are competitors mentioned instead? | Surfer |
| Which AI prompts should we track? | Surfer + Frase |
| What content is missing compared with top pages? | Frase + Surfer |
| What topic clusters should we build? | Frase |
| What content should writers fix first? | Frase + Surfer |
| Which pages already get impressions? | Windsor / direct GSC |
| Which pages get clicks but no leads? | Windsor |
| Which paid keywords should become SEO content? | Windsor |
| Which traffic sources produce leads? | Windsor |
| What should the executive summary say? | BLC deterministic logic, optionally polished by OpenAI |
| Can an operator ask follow-up questions about the audit? | OpenAI over stored BLC facts |

## 8. Report Upgrade

Current BLC report:

```text
Website technical audit
  -> SEO score
  -> UX/UI score
  -> Lead Gen score
  -> deterministic findings
  -> PDF/DOCX
```

After this plan:

```text
AI search + content + analytics intelligence report
  -> current technical SEO and UX/UI findings
  -> AI visibility and prompt tracking
  -> content gaps and topic clusters
  -> traffic, conversion, and paid/organic opportunities
  -> strategic action plan
  -> optional AI-polished prose
  -> optional Q&A over the audit
  -> PDF/DOCX/UI report
```

Estimated capability uplift if implemented well:

| Capability | Current BLC | After this plan |
|---|---:|---:|
| Website technical audit | 7.5/10 | 8.5/10 |
| AI/GEO visibility | 2/10 | 8/10 to 9/10 |
| Content strategy | 3/10 | 8/10 |
| Business/conversion proof | 3/10 | 8/10 |
| Competitor insight | 3/10 | 8/10 |
| Client-ready strategy value | 6/10 | 9/10 |

## 9. New Report Sections

### 9.1 AI Visibility & Prompt Tracking

> **⚠️ Vendor updated (2026-06-22):** source is now **Rank Prompt**, not Surfer — see
> [14_AI_VISIBILITY_VENDOR_SELECTION.md](14_AI_VISIBILITY_VENDOR_SELECTION.md). The questions and
> example findings below are vendor-agnostic and still apply.

Source: ~~Surfer~~ **Rank Prompt** (provisional — pending the live-trial gate in docs/14).

Answers:

- Does the brand appear in AI answers?
- Which platforms mention the brand?
- Which prompts mention competitors but not the client?
- What citations or URLs appear?
- What content changes can improve AI visibility?

Example findings:

- "The brand appears in 6 of 50 tracked prompts."
- "Competitor A appears in 22 of 50 tracked prompts."
- "The client is missing visibility for commercial prompts around 'custom home builder near me'."
- "The most cited competitor pages are service pages, not blog posts."

### 9.2 Content Gaps & Topic Authority

Source: Frase, optionally enriched by Surfer.

Answers:

- What important topics are missing?
- What FAQs should be added?
- What pages need stronger topical coverage?
- Which topic clusters should be built?
- Which pages need a better content score?

Example findings:

- "The homepage does not answer cost, timeline, financing, or design-build process questions."
- "Top-ranking competitors cover warranty, remodeling permits, and project timeline more clearly."
- "Create a cluster around 'custom home building process' with supporting FAQ pages."

### 9.3 Traffic, Conversion & Channel Intelligence

Source: Windsor.

Answers:

- Which pages get impressions but low CTR?
- Which pages get traffic but low conversions?
- Which paid keywords convert and should become SEO pages?
- Which channels contribute to leads?
- Which campaigns or pages deserve priority?

Example findings:

- "The kitchen remodeling page gets organic traffic but produces low form submissions."
- "Paid keyword 'custom home builder Austin' converts, but the site lacks a dedicated organic landing page."
- "Organic traffic is growing, but direct conversion rate trails paid search."

### 9.4 AI SEO Action Plan

Source: BLC synthesis over Surfer + Windsor + Frase + existing audit facts.

This is deterministic. OpenAI may polish it later, but the selected actions and ordering should come from stored facts.

Example action categories:

- fix technical SEO blockers first;
- improve the pages that have traffic but weak leads;
- track the highest-value AI prompts;
- create pages for paid keywords that already convert;
- build topic clusters where competitors are stronger;
- add FAQs/schema/entity clarity where AI visibility is weak.

### 9.5 AI Strategic Summary

Source: OpenAI (ChatGPT) over stored BLC facts.

This is optional and should be hidden when OpenAI is not configured.

Purpose:

- explain the top 3 priorities in plain English;
- make the report more client-ready;
- connect technical/content/analytics facts into one narrative.

### 9.6 Ask About This Audit

Source: OpenAI (ChatGPT) over stored BLC facts.

Purpose:

- let the operator ask follow-up questions;
- answer only from the audit data;
- label output as AI-generated and require human review.

## 10. Data Architecture

### 10.1 Fastest Prototype: No Migration

For the first proof of concept, store normalized facts inside the existing `audit_results.external_seo_facts` JSONB column.

Suggested shape:

```json
{
  "technical_crawl": {},
  "gsc": {},
  "url_inspection": {},
  "ai_visibility": {
    "status": "complete",
    "provider": "surfer",
    "retrieved_at": "2026-06-17T00:00:00Z",
    "summary": {},
    "prompts": []
  },
  "marketing_analytics": {
    "status": "complete",
    "provider": "windsor",
    "date_range": {"start": "2026-03-19", "end": "2026-06-17"},
    "summary": {},
    "top_pages": [],
    "low_ctr_opportunities": [],
    "conversion_gaps": [],
    "paid_to_organic_opportunities": []
  },
  "content_research": {
    "status": "complete",
    "provider": "frase",
    "summary": {},
    "page_scores": [],
    "missing_topics": [],
    "topic_clusters": [],
    "faq_opportunities": []
  }
}
```

Required scoring guard:

`scoring._trusted_external_seo_facts()` currently strips summaries only for:

```python
("technical_crawl", "screaming_frog", "gsc", "url_inspection")
```

Before new tool facts influence scoring, extend source trust handling to:

```python
("ai_visibility", "marketing_analytics", "content_research")
```

Only score those summaries when `status == "complete"`.

### 10.2 Stable Product Schema: Migration Later

Once contracts stabilize, add explicit JSONB columns:

```text
audit_results.ai_visibility_facts JSONB NOT NULL DEFAULT '{}'
audit_results.marketing_analytics_facts JSONB NOT NULL DEFAULT '{}'
audit_results.content_research_facts JSONB NOT NULL DEFAULT '{}'
```

Cleaner long-term ownership:

- `external_seo_facts`: technical SEO, GSC, URL inspection.
- `ai_visibility_facts`: AI prompt, brand, citation visibility.
- `marketing_analytics_facts`: Windsor/GSC/GA4/Ads/CRM performance.
- `content_research_facts`: Frase content/topic/brief data.

### 10.3 Commentary Storage

OpenAI output can ride inside the existing `audit_results.commentary` JSONB:

```json
{
  "status": "polished",
  "provider": "openai",
  "model": "configured-openai-model-id",
  "content": {},
  "ai_strategic_summary": "Optional text"
}
```

No migration is needed for the first OpenAI layer.

If chat history is required later, add:

```text
audit_chat_messages
  id
  job_id
  role
  content
  created_at
```

## 11. Normalized Fact Contracts

### 11.1 Surfer AI Visibility Facts

> **⚠️ Provider changed to Rank Prompt (2026-06-22)** — see
> [14_AI_VISIBILITY_VENDOR_SELECTION.md](14_AI_VISIBILITY_VENDOR_SELECTION.md). The **normalized
> shape below stays useful as the BLC-internal contract** (set `"provider": "rank_prompt"`), but
> note Rank Prompt's raw schema differs and must be mapped onto it:
> - **No literal `mention_count`** — compute `brand_mentioned_prompts` / `brand_mention_rate_pct`
>   from Rank Prompt's `ranked_prompts` / `total_results` / `brand_appears`.
> - **Platforms** are bundle-tiered (4 bundled + premium add-ons), and **`ai_mode` is unconfirmed**
>   (only `ai_overviews` is in the enum) — don't list a separate Google AI Mode yet.
> - **By-country** comes from **per-region reports** aggregated app-side, not one fact blob.

```json
{
  "status": "complete",
  "provider": "surfer",
  "domain": "example.com",
  "brand_names": ["Example Homes"],
  "markets": ["Austin, TX"],
  "competitors": ["Competitor A", "Competitor B"],
  "platforms": ["ChatGPT", "Claude", "Gemini", "Perplexity", "Google AI Overview"],
  "summary": {
    "prompts_tracked": 50,
    "platforms_tracked": 5,
    "brand_mentioned_prompts": 8,
    "brand_mention_rate_pct": 16.0,
    "competitor_mentioned_prompts": 31,
    "citation_count": 12,
    "top_competitor": "Competitor A"
  },
  "prompts": [
    {
      "prompt": "best custom home builders in Austin",
      "platform": "ChatGPT",
      "brand_mentioned": false,
      "competitors_mentioned": ["Competitor A"],
      "citation_urls": ["https://competitor-a.example/service"],
      "sentiment": "unknown",
      "recommended_action": "Create or strengthen a service-area page for Austin custom homes."
    }
  ],
  "opportunities": [
    {
      "type": "missing_brand_visibility",
      "prompt": "best custom home builders in Austin",
      "platform": "ChatGPT",
      "competitor": "Competitor A",
      "recommended_page_type": "service-area page"
    }
  ]
}
```

### 11.2 Windsor Marketing Analytics Facts

```json
{
  "status": "complete",
  "provider": "windsor",
  "date_range": {"start": "2026-03-19", "end": "2026-06-17"},
  "sources": ["google_search_console", "ga4", "google_ads", "crm"],
  "summary": {
    "organic_clicks": 1240,
    "organic_impressions": 42000,
    "organic_ctr_pct": 2.95,
    "ga4_sessions": 5100,
    "lead_conversions": 41,
    "conversion_rate_pct": 0.8,
    "paid_converting_keywords": 12,
    "low_ctr_page_count": 6,
    "conversion_gap_page_count": 4
  },
  "low_ctr_opportunities": [
    {
      "url": "https://example.com/custom-homes",
      "impressions": 3800,
      "clicks": 42,
      "ctr_pct": 1.1,
      "avg_position": 7.8,
      "recommended_action": "Rewrite title and meta description around custom home builder intent."
    }
  ],
  "conversion_gaps": [
    {
      "url": "https://example.com/kitchen-remodeling",
      "sessions": 700,
      "conversions": 1,
      "conversion_rate_pct": 0.14,
      "recommended_action": "Add stronger CTA, proof, and a shorter form above the fold."
    }
  ],
  "paid_to_organic_opportunities": [
    {
      "keyword": "custom home builder Austin",
      "ad_conversions": 8,
      "organic_page_exists": false,
      "recommended_action": "Create a dedicated SEO landing page."
    }
  ]
}
```

### 11.3 Frase Content Research Facts

```json
{
  "status": "complete",
  "provider": "frase",
  "target_pages": [
    "https://example.com/",
    "https://example.com/custom-homes"
  ],
  "summary": {
    "pages_analyzed": 2,
    "avg_content_score": 61,
    "missing_topic_count": 18,
    "faq_opportunity_count": 12,
    "topic_cluster_count": 4
  },
  "page_scores": [
    {
      "url": "https://example.com/custom-homes",
      "content_score": 58,
      "target_score": 75,
      "competitor_avg_score": 72,
      "recommended_action": "Expand process, cost, timeline, and warranty coverage."
    }
  ],
  "missing_topics": [
    {
      "topic": "custom home building timeline",
      "importance": "high",
      "covered_on_site": false,
      "recommended_page_type": "service page section"
    }
  ],
  "faq_opportunities": [
    {
      "question": "How long does it take to build a custom home?",
      "intent": "commercial_investigation",
      "covered_on_site": false,
      "recommended_location": "Custom homes service page"
    }
  ],
  "topic_clusters": [
    {
      "cluster": "Custom home building process",
      "recommended_pages": [
        "Custom home building timeline",
        "Custom home design-build process",
        "Custom home cost guide"
      ]
    }
  ]
}
```

## 12. Integration Architecture

### 12.1 New Worker Package

Add:

```text
apps/worker/stages/ai_seo_tools/
  __init__.py
  schemas.py
  surfer.py
  windsor.py
  frase.py
  prompts.py
  normalizer.py
  collector.py
```

Responsibilities:

- `schemas.py`: Pydantic models for normalized facts.
- `surfer.py`: Surfer API/export adapter.
- `windsor.py`: Windsor Postgres/API reader.
- `frase.py`: Frase API/MCP adapter.
- `prompts.py`: deterministic prompt seed generation for AI visibility tracking.
- `normalizer.py`: convert vendor payloads into BLC fact contracts.
- `collector.py`: orchestrate enabled providers and return one normalized payload.

### 12.2 New Settings

Add to `apps/shared/config.py`:

```python
# AI SEO tooling enrichment
ai_seo_tools_enabled: bool = False
ai_seo_tools_auto_run: bool = False

surfer_api_key: SecretStr | None = None
surfer_workspace_id: str = ""
surfer_default_prompt_limit: int = Field(default=50, ge=1, le=500)

windsor_api_key: SecretStr | None = None
windsor_database_schema: str = "windsor_raw"
windsor_default_date_range_days: int = Field(default=90, ge=7, le=540)

frase_api_key: SecretStr | None = None
frase_default_page_limit: int = Field(default=5, ge=1, le=50)

ai_seo_tool_timeout_seconds: int = Field(default=120, ge=10)

# OpenAI / ChatGPT report intelligence.
# These fields ALREADY EXIST in config.py (from the dormant scaffolding) — reuse them:
#   openai_api_key, openai_model ("gpt-4o"), openai_max_tokens (4096),
#   openai_temperature (0.2), openai_timeout_seconds (60)
# Empty openai_api_key => the LLM layer is off (graceful, like the CLERK_ISSUER opt-in).
# Add only these optional per-capability overrides (fall back to openai_model when blank):
openai_polish_model: str = "gpt-4o-mini"   # cheap/fast prose rewrite
openai_insights_model: str = "gpt-4o"      # strategic summary
openai_qa_model: str = "gpt-4o"            # Q&A
openai_insights_max_tokens: int = Field(default=1500, ge=256)
openai_qa_max_tokens: int = Field(default=1024, ge=256)
```

> Use OpenAI model IDs your account has access to (the config already defaults `openai_model` to
> `gpt-4o`). A smaller/cheaper model (e.g. `gpt-4o-mini`) is fine for high-volume prose polish; use the
> stronger model for the strategic summary. Confirm exact IDs and per-token prices in the OpenAI
> dashboard. See §14.4 for the exact SDK calls.

Add matching `.env.template` entries.

Do not expose vendor/API secrets to the frontend container.

### 12.3 Input Fields Needed

The current `AuditJob` has:

```text
url
niche
target_audience
```

AI visibility works better with:

```text
brand_name
market / city / service area
competitor_names
priority_services
```

MVP:

- derive `brand_name` from site title/domain when not provided;
- use `niche` and `target_audience` as context;
- allow manual competitors later.

Full:

```text
audit_jobs.ai_context JSONB
```

Example:

```json
{
  "brand_name": "Example Homes",
  "markets": ["Austin, TX"],
  "priority_services": ["custom homes", "kitchen remodeling"],
  "competitors": ["Competitor A", "Competitor B"]
}
```

### 12.4 New API Endpoints

On-demand AI SEO tool enrichment:

```text
POST /audits/{job_id}/rerun-ai-seo-insights
```

Mirrors existing `rerun-enrichment`:

```text
load completed audit
  -> snapshot result
  -> collect Surfer/Windsor/Frase facts
  -> normalize facts
  -> optionally rescore
  -> regenerate deterministic commentary
  -> validate grounding
  -> rerender PDF/DOCX
  -> restore snapshot on failure
```

On-demand OpenAI (ChatGPT) report intelligence:

```text
POST /audits/{job_id}/ai-insights
POST /audits/{job_id}/ask
```

`/ai-insights` handles optional polish and strategic summary.

`/ask` answers questions over stored audit facts and should be clearly labeled as AI-generated.

## 13. Prompt and Query Strategy

### 13.1 Surfer Prompt Seeds

Build deterministic prompt templates from:

- `job.niche`;
- `job.target_audience`;
- brand name;
- service area;
- discovered H1/title/service page text;
- GSC top queries when available;
- paid converting keywords from Windsor when available.

Example prompt templates:

```text
best {service} companies in {market}
who are the top {service} contractors near {market}
how do I choose a {service} company
{brand} reviews
{competitor} vs {brand}
best home remodeling company in {market}
custom home builder near {market}
```

Store the prompt set:

```json
{
  "prompt_set_version": "blc-builder-prompts-v1",
  "generated_prompts": [],
  "manual_prompts": []
}
```

### 13.2 Frase Content Seeds

Use:

- homepage;
- top crawled service pages;
- GSC top pages;
- pages with low CTR;
- pages with traffic but weak conversions;
- priority service keywords.

### 13.3 Windsor Date Windows

Default:

```text
Last 90 days
```

Optional:

```text
Last 90 days vs previous 90 days
Last 28 days vs previous 28 days
```

### 13.4 OpenAI Context

OpenAI should receive compacted stored facts only:

- headline scores;
- deterministic findings and recommendations;
- normalized Surfer/Windsor/Frase facts;
- no raw HTML;
- no screenshots;
- no secrets;
- no tokens.

## 14. OpenAI (ChatGPT) Report Intelligence

OpenAI should be optional and on-demand.

### 14.1 Prose Polish

Goal:

- rewrite existing deterministic findings in warmer client-ready language.

Rules:

- do not add findings;
- do not remove findings;
- do not reorder findings;
- do not change severity/tier/evidence/action items;
- rewrite prose fields only;
- run grounding afterward;
- revert to deterministic baseline on failure.

Implementation pattern:

```text
deterministic CommentaryContent
  -> OpenAI returns prose-only replacement fields
  -> Python merges prose into original structure
  -> grounding validator strips unsupported numbers
  -> report renders
```

### 14.2 Strategic Summary

Goal:

- produce a short "top priorities and why" narrative.

Inputs:

- scores;
- deterministic findings;
- Surfer/Windsor/Frase facts;
- niche and target audience.

Failure behavior:

- hide the section when OpenAI is unavailable;
- never fake an AI section with deterministic text.

### 14.3 Q&A Over Audit

Goal:

- let the operator ask questions like:
  - "What should this client fix first?"
  - "Why is the lead-gen score weak?"
  - "Which content should we build next?"
  - "Where are competitors beating them in AI search?"

Rules:

- answer only from stored audit data;
- if not covered, say so;
- never invent numbers, competitors, or benchmarks;
- show a disclaimer in the UI;
- v1 can be stateless with no chat history.

### 14.4 OpenAI (ChatGPT) implementation detail

This is the code-grounded version of 14.1–14.3, mapped to the real seam
(`apps/worker/stages/commentary.py`, `content_plan.py`, `grounding_validator.py`). Good news: the
dormant scaffolding (`_call_openai`, `prompts/*.md`, and the `openai` dependency already in
`pyproject.toml`) is **already OpenAI-based** — we turn it **on**, not replace it. No new provider
dependency is added.

**Module:** extend `apps/worker/stages/commentary.py` (which already holds `_call_openai`,
`_read_prompt`, `_render_user_prompt`, `_compact_facts`) — or add `apps/worker/stages/ai_insights.py` —
with `polish_commentary()`, `generate_strategic_summary()`, and `answer_question()`.

**1) Structured-output prose polish (merge-by-position — structure can't drift).**
The model returns *only* prose, keyed by position; Python copies every structural field verbatim
from the deterministic baseline. The structure lock lives in the merge, not the prompt.

```python
from pydantic import BaseModel, ConfigDict

class _PolishedFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    meaning: str = ""; why: str = ""; explanation: str = ""

class _PolishedRec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rationale: str = ""

class _PolishedSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    headline: str
    findings: list[_PolishedFinding]
    recommendations: list[_PolishedRec]

class PolishResult(BaseModel):              # prose ONLY — no ids, no structural data, no numbers-as-data
    model_config = ConfigDict(extra="forbid")
    executive_summary: str
    seo: _PolishedSection; uxui: _PolishedSection; lead_generation: _PolishedSection

def _merge_polish(base: CommentaryContent, p: PolishResult) -> CommentaryContent:
    out = base.model_copy(deep=True)
    out.executive_summary = p.executive_summary or base.executive_summary
    for name in ("seo", "uxui", "lead_generation"):
        b, ps = getattr(out, name), getattr(p, name)
        if len(ps.findings) != len(b.findings) or len(ps.recommendations) != len(b.recommendations):
            continue                         # count mismatch => structural drift => keep baseline
        b.headline = ps.headline or b.headline
        for bf, pf in zip(b.findings, ps.findings):
            bf.meaning, bf.why, bf.explanation = pf.meaning or bf.meaning, pf.why or bf.why, pf.explanation or bf.explanation
            # severity, title, evidence_refs, action_items, location_* are NEVER touched
        for br, pr in zip(b.recommendations, ps.recommendations):
            br.rationale = pr.rationale or br.rationale
    return out
```

The OpenAI call reuses the dormant `_call_openai` pattern exactly — `client.responses.parse(...,
text_format=PolishResult)`. `PolishResult` is nested-but-not-recursive and string-only, so it is a
valid structured-output schema.

```python
from openai import OpenAI

def polish_commentary(base, *, facts, score_breakdown, settings) -> tuple[CommentaryContent, dict]:
    model = settings.openai_polish_model or settings.openai_model     # default gpt-4o-mini
    try:
        client = OpenAI(api_key=settings.openai_api_key.get_secret_value(),
                        timeout=settings.openai_timeout_seconds, max_retries=2)
        resp = client.responses.parse(                       # same call the dormant _call_openai uses
            model=model,
            instructions=_read_prompt(settings.commentary_system_prompt_path),
            input=_render_polish_prompt(base, facts=_compact_facts(facts),
                                        scores=score_breakdown.get("scores")),
            text_format=PolishResult,
            max_output_tokens=settings.openai_max_tokens,
            temperature=settings.openai_temperature,         # 0.2 default => low-variance prose
        )
        return _merge_polish(base, resp.output_parsed), {
            "status": "polished", "provider": "openai", "model": model}
    except Exception as exc:                                 # timeout, rate-limit, validation, anything
        log.warning("polish failed, keeping deterministic baseline: %s", exc)
        return base, {"status": "deterministic", "reason": "polish_error"}
```

**2) Grounding still runs, after polish.** Feed the merged content to the existing
`validate_commentary_grounding(commentary, fact_sources={seo, uxui, psi, external_seo, scores})`
(the same call already at `tasks.py:277–286`). Any AI-introduced number not in the facts is
stripped; an emptied field reverts to the deterministic baseline (never a placeholder).
`UNGROUNDED_KEYS = {evidence_refs, action_items, location_urls, location_label}` are never rewritten
and never grounded.

**3) Strategic summary** (`generate_strategic_summary`): one OpenAI call on `openai_insights_model`
(default `gpt-4o`) returning a short narrative string. Store it as the optional
`ai_strategic_summary` field inside `audit_results.commentary` (see §10.3 — no migration). Surface it
as an optional, nullable field on `ReportPayload`; **bump `REPORT_PAYLOAD_VERSION`** to
`phase2-report-v1` (additive — old payloads still deserialize). Hide the section when absent
(`{% if payload.ai_strategic_summary %}`); never fake it with deterministic text.

**4) Q&A** (`answer_question`): `openai_qa_model` (default `gpt-4o`); put the per-audit compacted
context in the `instructions`/system message (OpenAI automatically caches long repeated prompt
prefixes, so repeat questions on the same audit are cheaper). Strict system prompt: *answer only from
the provided audit data; if not present, say so; never invent numbers/competitors/benchmarks.*
v1 synchronous + UI disclaimer.

**5) OpenAI API notes.** Structured output via `client.responses.parse(..., text_format=Model)` →
`resp.output_parsed` (the exact pattern the dormant `_call_openai` already uses). `temperature` is
supported (keep `openai_temperature=0.2` for low-variance polish). Catch all `openai.*` errors
(timeout, rate-limit, `APIError`) and Pydantic validation errors → graceful degradation to the
deterministic baseline. The SDK retries 429/5xx automatically.

**6) Reproducibility anchor (why this is safe).** Because the LLM layer is **on-demand only**
(a separate Celery task, mirroring `rerun_external_enrichment` — never in the base pipeline), the
hermetic QA harness (`scripts/qa_reproducibility.py`, run with no key) never invokes OpenAI — the
existing harness already forces `_call_openai` onto its skip path. The deterministic baseline
therefore stays the byte-identical reproducibility anchor — untouched. Add a **new** opt-in script
(`scripts/qa_ai_insights.py`) for the LLM path; do **not** wire it into the reproducibility harness.

**7) Rough cost per "Generate AI insights" click:** a few cents — a `gpt-4o-mini` polish is the
cheapest part, the `gpt-4o` strategic summary costs more, and each Q&A question is a small `gpt-4o`
call. Confirm current per-token prices in the OpenAI dashboard and log real usage before relying on
an estimate.

## 15. Scoring Strategy

### 15.1 V1: No New Score

Do not add a new score first.

Reasons:

- vendor outputs need validation;
- contracts vary by plan;
- current scoring is type-locked to `seo` and `uxui`;
- premature scoring creates false precision.

V1 should show facts, recommendations, and sections only.

### 15.2 V2: Add Rules Under SEO/UX

Once facts stabilize, add YAML rules under existing categories:

| Rule idea | Category | Fact path |
|---|---|---|
| Brand has low AI prompt visibility | SEO | `external_seo.ai_visibility.summary.brand_mention_rate_pct` |
| Competitors dominate target prompts | SEO | `external_seo.ai_visibility.summary.competitor_mentioned_prompts` |
| Content score below competitor average | SEO | `external_seo.content_research.summary.avg_content_score` |
| Missing high-intent FAQs | SEO | `external_seo.content_research.summary.faq_opportunity_count` |
| High-traffic page has weak conversion | UX/UI or SEO | `external_seo.marketing_analytics.summary.conversion_gap_page_count` |

Every rule must:

- use `skip_if_missing: true`;
- score only complete sources;
- include `impact`, `tier`, `finding_label`, `remediation`;
- bump the rubric version.

### 15.3 V3: Add AI Search Readiness Score

If BLC wants a dedicated score later:

```text
SEO Score
UX/UI Score
AI Search Readiness Score
Lead Generation Readiness Score
```

Requires:

- new `rubrics/ai_visibility.yaml`;
- `Rubric.category` Literal update;
- `CompositeRubric.weights` update;
- `score_audit()` update;
- `AuditResult` score column or JSON score;
- `ReportPayload` score card update;
- frontend score card update;
- PDF/DOCX template update;
- calibration tests.

Possible composite:

```yaml
weights:
  seo: 0.35
  uxui: 0.35
  ai_visibility: 0.30
```

Do this only after real audit data proves the score is meaningful.

## 16. Implementation Phases

### Phase 0 - Vendor Validation

Duration: 2 to 5 days.

Tasks:

- Open trials/accounts.
- Confirm Surfer AI visibility API/export access.
- Confirm Claude coverage in Surfer for the desired plan.
- Confirm Frase API/MCP endpoint coverage.
- Confirm Windsor Postgres/API setup.
- Run 2 to 3 real BLC/prospect sites through dashboards manually.
- Save exported sample data for fixtures.

Exit criteria:

- We know which fields can be retrieved programmatically.
- We know real plan costs.
- We have sample payloads.
- We know whether Surfer or another vendor is needed for Claude tracking.

### Phase 1 - Data Contracts and Fixtures

Duration: 3 to 5 days.

Tasks:

- Add normalized Pydantic schemas.
- Create fixture JSON files.
- Add unit tests for schema validation and normalization.

Exit criteria:

- BLC can validate normalized Surfer/Windsor/Frase facts without calling vendors.

### Phase 2 - On-Demand Tool Enrichment

Duration: 1 to 2 weeks.

Tasks:

- Add provider adapters.
- Add settings/env fields.
- Add `collect_ai_seo_tool_facts()`.
- Add `rerun_ai_seo_insights_for_audit()`.
- Add Celery task.
- Add `POST /audits/{id}/rerun-ai-seo-insights`.
- Snapshot/restore previous result on failure.

Exit criteria:

- A completed audit can be enriched with mocked or real tool facts.
- Failure preserves the previous report.

### Phase 3 - Report Payload and UI

Duration: 1 to 2 weeks.

Tasks:

- Extend `ReportPayload` with optional sections:
  - `ai_visibility_section`;
  - `content_research_section`;
  - `marketing_analytics_section`.
- Add frontend cards.
- Add PDF/DOCX report sections.
- Add provider status badges.
- Add "Run AI SEO insights" button.

Exit criteria:

- Operator can generate and view enriched insights in UI and PDF.

### Phase 4 - Deterministic AI SEO Action Plan

Duration: 1 week.

Tasks:

- Add deterministic opportunity ranking:
  - high AI competitor visibility;
  - low brand mention rate;
  - high-impression low-CTR pages;
  - traffic-without-conversion pages;
  - paid-to-organic opportunities;
  - missing content topics.
- Add combined AI SEO Action Plan.
- Add grounding checks for numeric claims.

Exit criteria:

- Report explains the highest-value actions across all three tools.

### Phase 5 - OpenAI (ChatGPT) Report Intelligence

Duration: 1 to 2 weeks.

Tasks:

- Turn on the OpenAI key + prompts (reuse the dormant `_call_openai` scaffolding).
- Add prose polish with structure lock.
- Add strategic summary.
- Add Q&A endpoint.
- Add grounding and graceful degradation tests.

Exit criteria:

- OpenAI improves prose and answers questions without changing scores or structure.

### Phase 6 - Optional Scoring

Duration: 1 to 3 weeks.

Tasks:

- Add YAML rules under SEO/UX or add a new AI Search Readiness category.
- Bump rubric versions.
- Add calibration fixtures.
- Add reproducibility tests.

Exit criteria:

- Scores remain deterministic and missing vendor data does not penalize.

## 17. File-by-File Change Checklist

Backend:

- `apps/shared/config.py` - add tool and OpenAI settings.
- `.env.template` - add config blocks.
- `apps/worker/stages/ai_seo_tools/` - new package.
- `apps/worker/stages/ai_insights.py` - optional OpenAI polish, summary, Q&A helpers.
- `apps/worker/tasks.py` - add on-demand enrichment tasks.
- `apps/api/routes/audits.py` - add endpoints.
- `apps/api/schemas/audits.py` - add request/response models.
- `apps/worker/stages/scoring.py` - extend trusted source stripping before scoring new facts.
- `apps/worker/stages/report_payload.py` - add optional report sections.
- `apps/worker/stages/grounding_validator.py` - ensure new free-text summaries are scrubbed.
- `templates/report.html` / `templates/report.css` - add report sections.
- `apps/worker/stages/docx_renderer.py` - add DOCX sections.

Frontend:

- `apps/frontend/lib/api.ts` - add API calls.
- `apps/frontend/pages/audit/[id].tsx` - buttons, sections, Q&A UI.
- `apps/frontend/lib/format.ts` - provider/status formatting.
- `apps/frontend/styles/globals.css` - section/card styling.

Tests:

- `tests/unit/test_ai_seo_tool_schemas.py`
- `tests/unit/test_ai_seo_tool_normalizers.py`
- `tests/unit/test_ai_seo_tool_task.py`
- `tests/unit/test_ai_insights.py`
- `tests/unit/test_report_payload.py` updates.
- `tests/unit/test_audit_api.py` endpoint tests.
- fixture JSONs for each provider.

Docs:

- update `docs/06_KNOWN_LIMITATIONS.md` once tool limitations are confirmed;
- update `README.md` after implementation;
- update `CLAUDE.md` once code exists.

## 18. Testing Strategy

| Layer | Tests |
|---|---|
| Vendor schemas | Validate sample Surfer/Windsor/Frase payloads normalize into stable BLC facts |
| Tool failure | Vendor timeout/failure returns skipped/failed payload and does not fail audit |
| Snapshot/restore | Failed AI SEO enrichment keeps prior complete report |
| Report payload | Optional sections render only when facts exist |
| Scoring trust | Non-complete source summaries are stripped before scoring |
| OpenAI polish | Structure is unchanged; only prose fields change |
| Grounding | Hallucinated numbers are stripped or reverted |
| API | New endpoints return 409/503/200 correctly |
| QA harness | Base `make qa` and `make qa-repro` stay deterministic without paid keys |

## 19. Pros and Cons

### Surfer SEO

Pros:

- Best fit for AI visibility and prompt tracking.
- Useful for "are we mentioned in AI?" client questions.
- Strong content scoring and optimization.
- Strong client-facing story.

Cons:

- API entitlement must be confirmed before engineering.
- Claude coverage must be verified for BLC's chosen plan.
- Overlaps with Frase on content optimization.
- Can become expensive if every audit uses many prompts/platforms.

### Windsor.ai

Pros:

- Best fit for GSC, GA4, Ads, CRM, and conversion proof.
- Strong Postgres/data-pipeline fit.
- Public API and MCP offering.
- Makes reports much more business-backed.

Cons:

- Not an AI SEO insight platform.
- Requires connected accounts and clean attribution.
- Data normalization can be messy.
- Some prospects may not have GA4/CRM access connected.

### Frase

Pros:

- Strong for content gaps, topic clusters, briefs, SEO/GEO workflows.
- Pricing says API/MCP access is included.
- More automation-friendly for content workflows.
- Useful for writers and fulfillment teams after the audit.

Cons:

- AI visibility likely not as strong as a dedicated visibility tracker.
- Overlaps with Surfer.
- Need to confirm exactly which data is available by API.
- Content recommendations still need BLC normalization and ranking.

### OpenAI (ChatGPT)

Pros:

- Makes the report easier to read.
- Can synthesize tool facts into a better executive narrative.
- Lets operators ask questions about an audit.

Cons:

- Must be grounded carefully.
- Q&A is the least deterministic surface.
- Adds token cost and latency.
- Must never change scores or finding structure.

## 20. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Vendor API access is not available on expected plan | Phase 0 trial before code build |
| Surfer does not expose Claude data in API | Verify in trial; consider Otterly/Peec as fallback |
| Tool data changes report scores unpredictably | Keep v1 unscored; score only stable facts later |
| Missing vendor data penalizes clients | Use `skip_if_missing: true` and source status gating |
| Vendor output contains ungrounded claims | Store raw facts, generate BLC prose deterministically |
| Costs grow with every audit | On-demand enrichment first; add monthly caps later |
| Windsor data writes into app DB unsafely | Use separate schema/read-only views |
| Operators do not enter brand/competitors | Derive defaults, but add optional AI context fields |
| Report becomes too long | Cap top opportunities per section |
| MCP workflows are non-deterministic | Use API/database sync for production; MCP for operator assistance |
| OpenAI changes report structure | Merge prose into baseline structure in Python; reject count mismatches |
| OpenAI invents numbers | Run grounding validator and revert unsupported prose |
| Q&A hallucinates | Strict prompt, compact facts only, UI disclaimer, no score changes |

## 21. Recommended MVP Scope

Build v1 like this:

```text
One completed audit
  -> operator clicks "Run AI SEO insights"
  -> collect or import Surfer AI visibility facts
  -> read Windsor analytics facts if configured
  -> collect Frase content facts if configured
  -> normalize into external_seo_facts
  -> compose new report sections
  -> rerender PDF/DOCX
```

MVP includes:

- on-demand enrichment endpoint;
- provider status display;
- AI Visibility section;
- Content Gaps section;
- Traffic & Conversion section;
- no new score;
- no automatic run on every audit;
- no deep chat/agent workflow.

MVP does not include:

- new AI Search Readiness Score;
- full competitor benchmarking engine;
- automatic prompt purchases for every audit;
- stored chat history;
- MCP-driven production pipeline.

OpenAI MVP can follow:

```text
completed enriched audit
  -> operator clicks "Generate AI insights"
  -> OpenAI polishes prose / creates strategic summary
  -> grounding validation
  -> rerender PDF/DOCX
```

## 22. Budget Recommendation

Best-results stack:

```text
Surfer Pro or Peace of Mind
Windsor Standard
Frase Starter or Professional
OpenAI usage-based API
```

Cost-conscious stack:

```text
Surfer Pro
Windsor Standard
Frase later
OpenAI only for selected reports
```

Trial-first stack:

```text
Surfer trial/dashboard export
Windsor Standard or trial sync
Frase Starter
OpenAI with small usage cap
```

Do not buy all tools annually until:

- Surfer Claude coverage is confirmed;
- Surfer API/export access is confirmed;
- Frase API/MCP endpoint coverage is confirmed;
- Windsor source/destination setup is tested with BLC data;
- 2 to 3 real audits show enough report value.

## 23. Open Questions Before Build

1. Which brands/domains will be used for the first 3 test audits?
2. Which markets/cities should prompt tracking target?
3. Does BLC want operators to enter competitors manually?
4. Is Claude visibility mandatory, or is ChatGPT/Gemini/Perplexity/AI Overview enough for v1?
5. Will Windsor connect only GSC/GA4 first, or also Ads/CRM?
6. Should Frase generate content briefs only, or also influence audit recommendations?
7. Should enriched facts change scores in v1, or remain report-only?
8. What monthly tooling budget is acceptable?
9. Should AI SEO enrichment run on every audit or only on premium/on-demand audits?
10. Should OpenAI run automatically after AI SEO enrichment, or stay a separate button?
11. Should Q&A be stateless in v1, or should chat history be stored?
12. Who owns vendor account setup and credentials?

## 24. Source Links Checked

Official/public sources checked for the paid tooling portion:

- Surfer pricing: <https://surferseo.com/pricing/>
- Windsor pricing: <https://windsor.ai/pricing/>
- Windsor API documentation: <https://windsor.ai/api-documentation/>
- Windsor MCP destination: <https://windsor.ai/destinations/windsor-mcp-for-ai-insights/>
- Frase pricing: <https://www.frase.io/pricing/>

Pricing and plan features can change. Re-check before purchasing or coding against a paid-plan entitlement.

## 25. Final Recommendation

Use one unified AI insights roadmap:

```text
Surfer = AI visibility and prompt tracking
Windsor = analytics, traffic, conversions, and lead proof
Frase = content gaps, topic clusters, and content workflow
OpenAI (ChatGPT) = client-ready synthesis, polish, and Q&A over stored facts
```

The most practical implementation path is:

1. **Validate vendors manually on 2 to 3 sites.**
2. **Build normalized fact contracts and report sections.**
3. **Add on-demand enrichment with snapshot/restore safety.**
4. **Add OpenAI polish/summary/Q&A after the fact layer is useful.**
5. **Only then decide if AI SEO facts should affect scores.**

This turns BLC from a strong website audit generator into an AI search, content, analytics, and lead-growth intelligence platform without breaking the deterministic architecture that already works.
