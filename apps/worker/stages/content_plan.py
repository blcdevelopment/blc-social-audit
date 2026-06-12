# flake8: noqa: E501
# ruff: noqa: E501
"""Deterministic content plan for audit commentary.

This is the canonical source of truth for what a report *says*: which findings exist,
in what order, their severity and remediation tier, and the baseline prose for each.
It is a pure function of the score breakdown + extracted facts, so the same site always
produces the same findings and recommendations - with or without an LLM.

An optional LLM polish layer (Phase 2) may later rewrite the prose strings, but it can
never add, drop, reorder, or invent a finding. See docs/11_COMMENTARY_CONSISTENCY_PLAN.md.

Grounding-safety invariant: every number emitted here is either a section/composite score
or a rule's ``evidence.value`` (the resolved fact at its ``fact_path``). Both are present
in the grounding fact sources, so the deterministic baseline is never stripped. Do not
emit derived/aggregate numbers that are not stored facts.
"""

from __future__ import annotations

from typing import Any

from apps.shared.config import Settings
from apps.worker.stages.commentary import (
    CommentaryContent,
    CommentaryFinding,
    CommentaryRecommendation,
    CommentarySection,
)

JsonDict = dict[str, Any]

Severity = str  # one of: high, medium, low, info
Tier = str  # one of: quick_win, mid_term, long_term

SECTION_TITLES = {"seo": "SEO", "uxui": "UX/UI"}
SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1, "info": 0}
TIER_ORDER = {"quick_win": 0, "mid_term": 1, "long_term": 2}

# Finding severity = rule impact x evaluated result.
_SEVERITY_MATRIX: dict[tuple[str, str], Severity] = {
    ("high", "fail"): "high",
    ("high", "partial"): "medium",
    ("medium", "fail"): "medium",
    ("medium", "partial"): "low",
    ("low", "fail"): "low",
    ("low", "partial"): "info",
}

_DEFAULT_ACTION = "Address this item to improve the score."


def build_content_plan(
    *,
    audit_context: JsonDict,
    seo_facts: JsonDict,
    uxui_facts: JsonDict,
    psi_facts: JsonDict,
    external_seo_facts: JsonDict | None = None,
    score_breakdown: JsonDict,
    settings: Settings,
) -> CommentaryContent:
    """Build the deterministic commentary plan from the score breakdown.

    ``*_facts`` are accepted for symmetry with the LLM path (and future templates that
    may cite additional stored facts); the current templates draw their numbers from the
    rule ``evidence.value`` already embedded in ``score_breakdown``.
    """
    max_findings = settings.commentary_max_findings_per_section
    max_recs = settings.commentary_max_recommendations_per_section
    facts = {
        "seo": seo_facts,
        "uxui": uxui_facts,
        "psi": psi_facts,
        "external_seo": external_seo_facts or {},
    }

    seo_section = _build_section("seo", score_breakdown, facts, max_findings, max_recs)
    uxui_section = _build_section("uxui", score_breakdown, facts, max_findings, max_recs)

    scores = _dict(score_breakdown.get("scores"))
    top_label = _top_priority_label(score_breakdown)

    return CommentaryContent(
        executive_summary=_executive_summary(scores, top_label),
        seo=seo_section,
        uxui=uxui_section,
        lead_generation=_lead_section(scores),
    )


def _build_section(
    section_id: str,
    score_breakdown: JsonDict,
    facts: JsonDict,
    max_findings: int,
    max_recs: int,
) -> CommentarySection:
    surfaced = _surfaced_rules(section_id, score_breakdown)
    score = _int(_dict(score_breakdown.get("scores")).get(section_id))

    finding_order = sorted(surfaced, key=_finding_sort_key)
    findings = [_finding(rule, facts) for rule in finding_order[:max_findings]]

    rec_order = sorted(surfaced, key=_recommendation_sort_key)
    recommendations = [_recommendation(rule, facts) for rule in rec_order[:max_recs]]

    label = SECTION_TITLES.get(section_id, section_id.upper())
    return CommentarySection(
        headline=f"{label} score is {score}",
        findings=findings,
        recommendations=recommendations,
    )


def _surfaced_rules(section_id: str, score_breakdown: JsonDict) -> list[JsonDict]:
    category = _dict(_dict(score_breakdown.get("categories")).get(section_id))
    rules = category.get("rules")
    if not isinstance(rules, list):
        return []
    return [
        rule
        for rule in rules
        if isinstance(rule, dict)
        and rule.get("result") in {"fail", "partial"}
        and rule.get("surface_as_finding", True)
    ]


def _finding_sort_key(rule: JsonDict) -> tuple[int, float, str]:
    severity = _severity(rule.get("impact"), rule.get("result"))
    return (-SEVERITY_RANK[severity], -_float(rule.get("weight")), str(rule.get("rule_id") or ""))


def _recommendation_sort_key(rule: JsonDict) -> tuple[int, int, float, str]:
    tier_rank = TIER_ORDER[_tier(rule.get("tier"))]
    severity_rank, neg_weight, rule_id = _finding_sort_key(rule)
    return (tier_rank, severity_rank, neg_weight, rule_id)


def _finding(rule: JsonDict, facts: JsonDict) -> CommentaryFinding:
    return CommentaryFinding(
        severity=_severity(rule.get("impact"), rule.get("result")),
        title=_finding_title(rule),
        explanation=_explanation(rule, facts),
        evidence_refs=_evidence_refs(rule),
    )


def _recommendation(rule: JsonDict, facts: JsonDict) -> CommentaryRecommendation:
    remediation = rule.get("remediation")
    action = (
        remediation.strip()
        if isinstance(remediation, str) and remediation.strip()
        else _DEFAULT_ACTION
    )
    return CommentaryRecommendation(
        tier=_tier(rule.get("tier")),
        title=_finding_title(rule),
        rationale=_explanation(rule, facts),
        action_items=[action],
    )


def _lead_section(scores: JsonDict) -> CommentarySection:
    lead = _int(scores.get("lead_gen"))
    seo = _int(scores.get("seo"))
    uxui = _int(scores.get("uxui"))
    severity = "high" if lead < 50 else "medium" if lead < 75 else "info"
    return CommentarySection(
        headline=f"Lead Generation Readiness score is {lead}",
        findings=[
            CommentaryFinding(
                severity=severity,
                title=f"Lead Generation Readiness score is {lead}",
                explanation=(
                    f"Lead Generation Readiness is the combined score from SEO and UX/UI. "
                    f"In this audit, SEO is {seo} and UX/UI is {uxui}, so the combined "
                    f"readiness score is {lead}. Improving the lower-scoring SEO and UX/UI "
                    "items in this report is what raises this number."
                ),
                evidence_refs=["scores.lead_gen"],
            )
        ],
        # The roadmap is driven by the concrete SEO/UX-UI recommendations; the composite
        # section adds no generic filler recommendations of its own.
        recommendations=[],
    )


def _executive_summary(scores: JsonDict, top_label: str | None) -> str:
    seo = _int(scores.get("seo"))
    uxui = _int(scores.get("uxui"))
    lead = _int(scores.get("lead_gen"))
    summary = (
        f"This audit scored the site {seo} for SEO, {uxui} for UX/UI, and {lead} for "
        "Lead Generation Readiness. Lead Generation Readiness is the roll-up score that "
        "shows whether search visibility and the on-page conversion experience are working "
        "together."
    )
    if seo + 10 < uxui:
        summary += " The UX/UI experience is much stronger than the SEO foundation, so search visibility is the main reason the combined score is lower."
    elif uxui + 10 < seo:
        summary += " SEO is stronger than the on-page conversion experience, so UX/UI is the main reason the combined score is lower."
    if top_label:
        summary += f" The highest-priority opportunity is: {top_label}."
    summary += " Start with the issues that block visitors or search engines first, then move into the content and conversion improvements."
    return summary


def _top_priority_label(score_breakdown: JsonDict) -> str | None:
    surfaced = _surfaced_rules("seo", score_breakdown) + _surfaced_rules("uxui", score_breakdown)
    if not surfaced:
        return None
    top = min(surfaced, key=_finding_sort_key)
    return _finding_title(top)


# --- prose helpers (grounding-safe: numbers come only from evidence.value) ------------


def _finding_title(rule: JsonDict) -> str:
    label = rule.get("finding_label")
    if isinstance(label, str) and label.strip():
        return " ".join(label.split())
    description = rule.get("description")
    if isinstance(description, str) and description.strip():
        return " ".join(description.split())
    return "Improvement opportunity"


def _explanation(rule: JsonDict, facts: JsonDict) -> str:
    rule_id = str(rule.get("rule_id") or "")
    context = _RULE_CONTEXT.get(rule_id, _GENERIC_CONTEXT)
    parts = [
        context["meaning"],
        _evidence_sentence(rule, context),
        context["why"],
        _where_sentence(rule, facts),
    ]
    return " ".join(part for part in parts if part).strip()


def _evidence_sentence(rule: JsonDict, context: JsonDict) -> str | None:
    value = _dict(rule.get("evidence")).get("value")
    number = _format_number(value)
    if number is None:
        if value is False:
            return str(context.get("failed_check") or "")
        return None
    fact_path = str(rule.get("fact_path") or "")
    if fact_path.endswith("_pct"):
        return f"The audit measured this at {number}% across the crawled pages."
    noun = str(context.get("noun") or "item")
    # Multi-word noun phrases pluralize their head word, not the phrase end
    # ("pages missing a title tag", never "page missing a title tags").
    plural = str(context.get("noun_plural") or f"{noun}s")
    return f"The audit found {number} {noun if number == '1' else plural}."


def _evidence_refs(rule: JsonDict) -> list[str]:
    fact_path = rule.get("fact_path")
    return [str(fact_path)] if isinstance(fact_path, str) and fact_path else []


_GENERIC_CONTEXT = {
    "meaning": "This finding marks a check that did not fully pass.",
    "why": "It matters because the issue can make the page harder to understand, trust, or act on.",
    "noun": "item",
    "failed_check": "The audit check did not pass for the crawled page or pages.",
}

_RULE_CONTEXT: dict[str, JsonDict] = {
    "seo.title.present_all_pages": {
        "meaning": "A title tag is the page name Google and searchers use to understand a result.",
        "why": "Missing titles make pages harder to identify in search and can lower clicks from people who would otherwise be interested.",
        "noun": "page missing a title tag",
        "noun_plural": "pages missing a title tag",
    },
    "seo.homepage_title.reasonable_length": {
        "meaning": "The homepage title is the main search-result headline for the most important page on the site.",
        "why": "If it is too short, too long, or unclear, Google may rewrite it and searchers may not understand the offer quickly.",
        "failed_check": "The homepage title did not fall inside the useful search-result length range.",
    },
    "seo.meta_description.present_all_pages": {
        "meaning": "A meta description is the short search-result summary that helps someone decide whether to click.",
        "why": "Missing descriptions leave Google to generate its own snippet, which may be less persuasive than a message written for buyers.",
        "noun": "page missing a meta description",
        "noun_plural": "pages missing a meta description",
    },
    "seo.homepage_meta_description.reasonable_length": {
        "meaning": "The homepage meta description should summarize the offer in a short, useful search-result snippet.",
        "why": "When the description is outside the useful range, the result can look weak, truncated, or auto-written by Google.",
        "failed_check": "The homepage meta description did not fall inside the useful search-result length range.",
    },
    "seo.h1.present_once": {
        "meaning": "An H1 is the main visible heading that tells visitors and search engines what a page is about.",
        "why": "Pages with no H1 or multiple competing H1s can feel less clear and send weaker topic signals.",
        "noun": "page with one clear H1",
        "noun_plural": "pages with one clear H1",
    },
    "seo.homepage.canonical": {
        "meaning": "A canonical URL tells Google which version of a page should be treated as the preferred version.",
        "why": "Without it, duplicate URLs can split ranking signals or cause Google to choose a less useful version.",
        "failed_check": "The homepage canonical URL was not detected in the crawled HTML.",
    },
    "seo.schema.present": {
        "meaning": "Schema markup is structured data that gives search engines extra context about the business, service, or page.",
        "why": "Without it, Google has fewer explicit clues for understanding the business and showing richer search results.",
        "noun": "page with schema markup",
        "noun_plural": "pages with schema markup",
    },
    "seo.images.alt_coverage": {
        "meaning": "Alt text describes meaningful images for screen readers and gives search engines context about the page.",
        "why": "Low coverage weakens accessibility and can make image-heavy sections less understandable to search engines.",
        "noun": "percent image alt-text coverage",
    },
    "seo.indexability.no_noindex_pages": {
        "meaning": "A noindex directive tells search engines not to include a page in search results.",
        "why": "If a lead page is accidentally noindexed, it can be invisible in Google even when the content is useful.",
        "noun": "noindex page",
    },
    "seo.internal_links.depth": {
        "meaning": "Internal links help visitors and crawlers move from one useful page to the next.",
        "why": "Thin internal linking can leave good pages isolated and make next steps harder to find.",
        "noun": "internal link",
    },
    "seo.psi.mobile_performance": {
        "meaning": "Mobile PageSpeed reflects how quickly and smoothly the site loads for people on phones.",
        "why": "Slow mobile pages can frustrate visitors before they read the offer and can weaken search performance.",
        "noun": "mobile performance point",
    },
    "seo.psi.desktop_performance": {
        "meaning": "Desktop PageSpeed reflects how quickly and smoothly the site loads on larger screens.",
        "why": "Even when the design is strong, slow loading can reduce trust and make forms or calls to action feel harder to reach.",
        "noun": "desktop performance point",
    },
    "seo.technical_crawl.no_broken_internal_urls": {
        "meaning": "A broken internal URL is a link found during the crawl that returned an error instead of a usable page.",
        "why": "Visitors and search engines can hit a dead end, which hurts trust, crawl quality, and the path to conversion.",
        "noun": "broken internal URL",
        "noun_plural": "broken internal URLs",
    },
    "seo.technical_crawl.indexable_urls": {
        "meaning": "A non-indexable internal URL is a page the crawler found but Google may not be able to include in search results.",
        "why": "If these are important service, blog, or landing pages, they may not bring organic traffic.",
        "noun": "non-indexable internal URL",
        "noun_plural": "non-indexable internal URLs",
    },
    "seo.technical_crawl.missing_titles": {
        "meaning": "A missing title tag means the page does not provide a clear search-result headline.",
        "why": "That makes the page harder for Google and buyers to understand before they click.",
        "noun": "page missing a title tag",
        "noun_plural": "pages missing a title tag",
    },
    "seo.technical_crawl.duplicate_titles": {
        "meaning": "Duplicate title tags mean multiple pages are using the same search-result headline.",
        "why": "Google may treat those pages as interchangeable and the wrong page can rank or receive clicks.",
        "noun": "page with a duplicate title tag",
        "noun_plural": "pages with a duplicate title tag",
    },
    "seo.technical_crawl.missing_meta_descriptions": {
        "meaning": "A missing meta description means the page does not provide a written search-result summary.",
        "why": "Google may invent a less persuasive snippet, which can reduce clicks from searchers.",
        "noun": "page missing a meta description",
        "noun_plural": "pages missing a meta description",
    },
    "seo.technical_crawl.missing_h1": {
        "meaning": "A missing H1 means the page lacks a clear main visible heading.",
        "why": "Visitors may need more effort to understand the page, and search engines get a weaker topic signal.",
        "noun": "page missing an H1 heading",
        "noun_plural": "pages missing an H1 heading",
    },
    "seo.technical_crawl.missing_image_alt": {
        "meaning": "Missing image alt text means meaningful images do not have a text description.",
        "why": "That weakens accessibility and removes context that can help search engines understand the page.",
        "noun": "image missing alt text",
        "noun_plural": "images missing alt text",
    },
    "seo.gsc.low_ctr_pages": {
        "meaning": "Search Console shows pages that appear often in Google but are not earning enough clicks.",
        "why": "Those pages already have visibility, so better titles, descriptions, and offer framing can turn existing impressions into more visits.",
        "noun": "high-impression low-click page",
        "noun_plural": "high-impression low-click pages",
    },
    "seo.gsc.ranking_opportunities": {
        "meaning": "Search Console shows queries where the site is close enough to compete but not yet in the strongest positions.",
        "why": "Improving the matching page can lift traffic without starting from zero because Google already associates the site with the topic.",
        "noun": "ranking opportunity",
        "noun_plural": "ranking opportunities",
    },
    "seo.gsc.url_inspection_indexing": {
        "meaning": "URL Inspection checks whether priority pages are actually available in Google.",
        "why": "If an important page is not indexed, content and design improvements will not help that page earn search traffic.",
        "noun": "priority URL not on Google",
        "noun_plural": "priority URLs not on Google",
    },
    "uxui.primary_cta.present": {
        "meaning": "A primary call to action is the main next step you want a visitor to take.",
        "why": "Without a clear primary action, interested visitors can hesitate or leave instead of contacting the business.",
        "noun": "page with a primary call to action",
        "noun_plural": "pages with a primary call to action",
    },
    "uxui.cta.volume": {
        "meaning": "Conversion paths are the buttons, links, and contact prompts that move a visitor toward becoming a lead.",
        "why": "Too few paths can make the site feel informational instead of action-oriented.",
        "noun": "call to action",
        "noun_plural": "calls to action",
    },
    "uxui.cta.above_fold": {
        "meaning": "Above-the-fold calls to action are visible early, before a visitor scrolls.",
        "why": "If the first screen does not show a next step, motivated buyers may miss the fastest way to contact the business.",
        "noun": "early call to action",
        "noun_plural": "early calls to action",
    },
    "uxui.forms.present": {
        "meaning": "A lead capture form gives visitors a direct way to request contact or start a conversation.",
        "why": "Without a form, some visitors will not take the next step even if the offer is relevant.",
        "noun": "form",
    },
    "uxui.homepage_form.field_count": {
        "meaning": "The homepage form should be short enough that a serious buyer can complete it without friction.",
        "why": "If the homepage has no practical form, or the form asks for too much, lead capture depends too heavily on other contact paths.",
        "noun": "homepage form field",
    },
    "uxui.phone.visible": {
        "meaning": "A visible phone number gives ready-to-talk visitors a direct contact path.",
        "why": "If phone contact is hard to find, high-intent visitors may delay or choose a competitor.",
        "noun": "page with a visible phone number",
        "noun_plural": "pages with a visible phone number",
    },
    "uxui.email.visible": {
        "meaning": "A visible email or clear contact link gives visitors a lower-pressure way to reach out.",
        "why": "Some prospects are not ready to call, so hiding email contact can reduce inquiries.",
        "noun": "page with a visible email",
        "noun_plural": "pages with a visible email",
    },
    "uxui.trust.present": {
        "meaning": "Trust signals are proof points such as reviews, testimonials, certifications, awards, or credible case studies.",
        "why": "Without proof, visitors must take the offer on faith, which makes lead conversion harder.",
        "noun": "page with trust evidence",
        "noun_plural": "pages with trust evidence",
    },
    "uxui.trust.depth": {
        "meaning": "Trust depth means the site uses more than one type of proof.",
        "why": "A mix of proof points is more convincing than one isolated badge or testimonial.",
        "noun": "trust signal",
    },
    "uxui.navigation.present": {
        "meaning": "Primary navigation helps visitors find key pages such as services, proof, pricing context, or contact.",
        "why": "Missing or unclear navigation creates friction before a visitor reaches the information they need.",
        "failed_check": "Primary navigation was not detected on the homepage.",
    },
    "uxui.copy.substantial": {
        "meaning": "Substantial page copy explains the offer, who it is for, and what happens next.",
        "why": "Thin copy can leave visitors with unanswered questions and reduce confidence before they contact the business.",
        "failed_check": "The homepage copy was thinner than the audit expects for a lead-generation page.",
    },
    "uxui.direct_contact.present": {
        "meaning": "Direct contact means a visitor can reach the business without hunting for another page.",
        "why": "When contact details are not obvious, high-intent visitors can drop off before converting.",
        "failed_check": "The homepage did not show a direct contact path in the crawled HTML.",
    },
    "uxui.lead_capture.cta": {
        "meaning": "A homepage call to action tells visitors exactly what to do next.",
        "why": "Without it, the page can explain the business but still fail to create leads.",
        "failed_check": "The homepage did not show a clear call to action in the crawled HTML.",
    },
}


def _where_sentence(rule: JsonDict, facts: JsonDict) -> str | None:
    rule_id = str(rule.get("rule_id") or "")
    examples = _location_examples(rule_id, facts)
    if examples:
        return "Start by checking " + ", ".join(examples[:3]) + "."

    if "pages[0]" in str(rule.get("fact_path") or ""):
        homepage = _first_page_url(facts)
        if homepage:
            return f"Start by checking the homepage: {homepage}."
    return None


def _location_examples(rule_id: str, facts: JsonDict) -> list[str]:
    if rule_id.startswith("seo.technical_crawl."):
        issue_id = _TECHNICAL_CRAWL_RULE_TO_ISSUE.get(rule_id)
        external = _dict(facts.get("external_seo"))
        technical = _dict(external.get("technical_crawl") or external.get("screaming_frog"))
        issues = _list(technical.get("issues"))
        for issue in issues:
            payload = _dict(issue)
            if payload.get("id") == issue_id:
                return [str(value) for value in _list(payload.get("examples")) if value]

    if rule_id == "seo.gsc.low_ctr_pages":
        rows = _list(
            _dict(_dict(facts.get("external_seo")).get("gsc")).get("high_impression_low_ctr_pages")
        )
        return [str(_dict(row).get("page")) for row in rows if _dict(row).get("page")]

    if rule_id == "seo.gsc.ranking_opportunities":
        rows = _list(
            _dict(_dict(facts.get("external_seo")).get("gsc")).get("ranking_opportunities")
        )
        return [f"the query '{_dict(row).get('query')}'" for row in rows if _dict(row).get("query")]

    if rule_id == "seo.gsc.url_inspection_indexing":
        rows = _list(_dict(_dict(facts.get("external_seo")).get("url_inspection")).get("items"))
        return [
            str(_dict(row).get("url"))
            for row in rows
            if _dict(row).get("on_google") is False and _dict(row).get("url")
        ]

    if rule_id in {"seo.title.present_all_pages", "seo.meta_description.present_all_pages"}:
        key = "title" if rule_id == "seo.title.present_all_pages" else "meta_description"
        return [
            str(page.get("url"))
            for page in _seo_pages(facts)
            if not _dict(page.get(key)).get("present") and page.get("url")
        ]

    if rule_id == "seo.h1.present_once":
        return [
            str(page.get("url"))
            for page in _seo_pages(facts)
            if _dict(_dict(page.get("headings")).get("counts")).get("h1") != 1 and page.get("url")
        ]

    if rule_id == "seo.images.alt_coverage":
        return [
            str(page.get("url"))
            for page in _seo_pages(facts)
            if int(_dict(page.get("images")).get("missing_alt") or 0) > 0 and page.get("url")
        ]

    if rule_id == "seo.indexability.no_noindex_pages":
        return [
            str(page.get("url"))
            for page in _seo_pages(facts)
            if _dict(page.get("robots")).get("noindex") and page.get("url")
        ]

    if rule_id.startswith("seo.psi."):
        rows = _list(_dict(_dict(facts.get("psi")).get("summary")).get("slowest_pages"))
        return [str(_dict(row).get("url")) for row in rows if _dict(row).get("url")]

    if rule_id == "uxui.homepage_form.field_count":
        homepage = _first_page_url(facts, source="uxui")
        return [f"the homepage form area ({homepage})"] if homepage else ["the homepage form area"]

    if rule_id.startswith("uxui."):
        return _uxui_relevant_pages(rule_id, facts)

    return []


_TECHNICAL_CRAWL_RULE_TO_ISSUE = {
    "seo.technical_crawl.no_broken_internal_urls": "client_error_internal_urls",
    "seo.technical_crawl.indexable_urls": "non_indexable_internal_urls",
    "seo.technical_crawl.missing_titles": "missing_titles",
    "seo.technical_crawl.duplicate_titles": "duplicate_titles",
    "seo.technical_crawl.missing_meta_descriptions": "missing_meta_descriptions",
    "seo.technical_crawl.missing_h1": "missing_h1",
    "seo.technical_crawl.missing_image_alt": "images_missing_alt",
}


def _seo_pages(facts: JsonDict) -> list[JsonDict]:
    return [_dict(page) for page in _list(_dict(facts.get("seo")).get("pages"))]


def _uxui_pages(facts: JsonDict) -> list[JsonDict]:
    return [_dict(page) for page in _list(_dict(facts.get("uxui")).get("pages"))]


def _first_page_url(facts: JsonDict, *, source: str = "seo") -> str | None:
    pages = _seo_pages(facts) if source == "seo" else _uxui_pages(facts)
    return str(pages[0].get("url")) if pages and pages[0].get("url") else None


def _uxui_relevant_pages(rule_id: str, facts: JsonDict) -> list[str]:
    pages = _uxui_pages(facts)
    if rule_id in {"uxui.primary_cta.present", "uxui.lead_capture.cta", "uxui.cta.volume"}:
        return [
            str(page.get("url"))
            for page in pages
            if not _dict(page.get("lead_capture")).get("has_cta") and page.get("url")
        ] or ([str(pages[0].get("url"))] if pages and pages[0].get("url") else [])
    if rule_id == "uxui.cta.above_fold":
        return [
            str(page.get("url"))
            for page in pages
            if int(_dict(page.get("ctas")).get("above_fold_count") or 0) == 0 and page.get("url")
        ]
    if rule_id in {"uxui.forms.present", "uxui.homepage_form.field_count"}:
        return [
            str(page.get("url"))
            for page in pages
            if int(_dict(page.get("forms")).get("count") or 0) == 0 and page.get("url")
        ] or ([str(pages[0].get("url"))] if pages and pages[0].get("url") else [])
    if rule_id in {"uxui.phone.visible", "uxui.direct_contact.present"}:
        return [
            str(page.get("url"))
            for page in pages
            if not _dict(page.get("contact")).get("has_phone") and page.get("url")
        ]
    if rule_id == "uxui.email.visible":
        return [
            str(page.get("url"))
            for page in pages
            if not _dict(page.get("contact")).get("has_email") and page.get("url")
        ]
    if rule_id in {"uxui.trust.present", "uxui.trust.depth"}:
        return [
            str(page.get("url"))
            for page in pages
            if not _dict(page.get("trust_signals")).get("has_trust_signals") and page.get("url")
        ]
    return [str(pages[0].get("url"))] if pages and pages[0].get("url") else []


def _format_number(value: Any) -> str | None:
    """Render a stored numeric fact for prose, preserving its exact value.

    Returns ``None`` for booleans/non-numbers so boolean facts (present/absent) are not
    rendered as numbers. Integral floats render without a decimal point; the parsed value
    still matches the stored fact, so grounding does not strip the sentence.
    """
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else str(value)
    return None


def _severity(impact: Any, result: Any) -> Severity:
    impact_key = impact if impact in {"high", "medium", "low"} else "medium"
    result_key = result if result in {"fail", "partial"} else "fail"
    return _SEVERITY_MATRIX[(impact_key, result_key)]


def _tier(value: Any) -> Tier:
    return value if value in TIER_ORDER else "quick_win"


def _dict(value: Any) -> JsonDict:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
