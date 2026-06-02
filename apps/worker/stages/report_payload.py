from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

JsonDict = dict[str, Any]
ReportSectionId = Literal["seo", "uxui", "lead_generation"]
RecommendationTier = Literal["quick_win", "mid_term", "long_term"]

REPORT_PAYLOAD_VERSION = "phase1-report-v1"
TIER_LABELS: dict[RecommendationTier, str] = {
    "quick_win": "Quick Wins (0-30 days)",
    "mid_term": "Mid-Term Improvements (1-3 months)",
    "long_term": "Long-Term Growth Strategy (3-12 months)",
}
SECTION_LABELS: dict[ReportSectionId, str] = {
    "seo": "SEO",
    "uxui": "UX/UI",
    "lead_generation": "Lead Generation",
}


class ReportMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audit_id: UUID
    source_url: str
    final_url: str
    site_domain: str
    niche: str | None = None
    target_audience: str | None = None
    generated_at: datetime
    generated_date: str
    pages_crawled: int = 0
    failed_pages: int = 0
    skipped_pages: int = 0
    rubric_version: str
    llm_model: str


class ScoreCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Literal["lead_gen", "seo", "uxui"]
    label: str
    score: int = Field(ge=0, le=100)
    max_score: int = 100
    description: str


class ReportFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section: ReportSectionId
    severity: Literal["info", "low", "medium", "high"]
    title: str
    explanation: str
    evidence_refs: list[str] = Field(default_factory=list)
    source: Literal["commentary", "rubric"] = "commentary"


class ReportRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section: ReportSectionId
    tier: RecommendationTier
    title: str
    rationale: str
    action_items: list[str] = Field(default_factory=list)


class RoadmapTier(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tier: RecommendationTier
    label: str
    recommendations: list[ReportRecommendation] = Field(default_factory=list)


class RuleSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    description: str
    result: Literal["pass", "partial", "fail", "skipped"]
    points_awarded: float = 0.0
    points_possible: float = 0.0
    evidence_value: str | None = None
    reason: str | None = None


class ReportSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: ReportSectionId
    label: str
    headline: str
    score: int | None = Field(default=None, ge=0, le=100)
    findings: list[ReportFinding] = Field(default_factory=list)
    recommendations: list[ReportRecommendation] = Field(default_factory=list)
    opportunities: list[RuleSummary] = Field(default_factory=list)


class ValidationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    numeric_claims_checked: int = 0
    unsupported_claim_count: int = 0
    action: str = "none"


class PageSpeedSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    reason: str | None = None
    scope: str | None = None
    pages_requested: int = 0
    pages_analyzed: int = 0
    avg_mobile_performance: int | None = None
    avg_desktop_performance: int | None = None
    complete_mobile_pages: int = 0
    complete_desktop_pages: int = 0
    slowest_pages: list[JsonDict] = Field(default_factory=list)


class CrawlSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    successful_pages: int = 0
    failed_pages: int = 0
    skipped_pages: int = 0
    failed_page_items: list[JsonDict] = Field(default_factory=list)
    skipped_page_items: list[JsonDict] = Field(default_factory=list)


class Appendix(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scoring_note: str
    seo_rules: list[RuleSummary] = Field(default_factory=list)
    uxui_rules: list[RuleSummary] = Field(default_factory=list)


class ReportPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = REPORT_PAYLOAD_VERSION
    metadata: ReportMetadata
    scores: list[ScoreCard]
    executive_summary: str
    sections: list[ReportSection]
    roadmap: list[RoadmapTier]
    validation_summary: ValidationSummary
    pagespeed_summary: PageSpeedSummary
    crawl_summary: CrawlSummary
    appendix: Appendix


def compose_report_payload(job: Any, result: Any) -> ReportPayload:
    crawled_pages = _dict(result.crawled_pages)
    score_breakdown = _dict(result.score_breakdown)
    commentary = _dict(result.commentary)

    final_url = str(crawled_pages.get("final_url") or job.url)
    generated_at = _report_generated_at(result)
    metadata = ReportMetadata(
        audit_id=job.id,
        source_url=str(job.url),
        final_url=final_url,
        site_domain=_domain(final_url),
        niche=job.niche,
        target_audience=job.target_audience,
        generated_at=generated_at,
        generated_date=f"{generated_at.strftime('%B')} {generated_at.day}, {generated_at.year}",
        pages_crawled=int(crawled_pages.get("summary", {}).get("successful_pages") or 0),
        failed_pages=int(crawled_pages.get("summary", {}).get("failed_pages") or 0),
        skipped_pages=int(crawled_pages.get("summary", {}).get("skipped_pages") or 0),
        rubric_version=str(result.rubric_version),
        llm_model=str(result.llm_model),
    )

    sections = [
        _compose_section("seo", result.seo_score, commentary, score_breakdown),
        _compose_section("uxui", result.uxui_score, commentary, score_breakdown),
        _compose_section("lead_generation", result.lead_gen_score, commentary, score_breakdown),
    ]

    return ReportPayload(
        metadata=metadata,
        scores=_score_cards(result),
        executive_summary=_executive_summary(commentary),
        sections=sections,
        roadmap=_roadmap(sections),
        validation_summary=_validation_summary(_dict(result.validation_log)),
        pagespeed_summary=_pagespeed_summary(_dict(result.psi_facts)),
        crawl_summary=_crawl_summary(crawled_pages),
        appendix=_appendix(score_breakdown),
    )


def _compose_section(
    section_id: ReportSectionId,
    score: int,
    commentary: JsonDict,
    score_breakdown: JsonDict,
) -> ReportSection:
    section_content = _dict(_dict(commentary.get("content")).get(section_id))
    label = SECTION_LABELS[section_id]
    headline = str(section_content.get("headline") or f"{label} score is {score}")
    opportunities = _opportunities_for_section(section_id, score_breakdown)
    findings = _commentary_findings(section_id, section_content)
    if not findings:
        findings = _fallback_findings(section_id, score, opportunities)

    return ReportSection(
        id=section_id,
        label=label,
        headline=headline,
        score=score,
        findings=findings,
        recommendations=_commentary_recommendations(section_id, section_content),
        opportunities=opportunities,
    )


def _score_cards(result: Any) -> list[ScoreCard]:
    return [
        ScoreCard(
            id="lead_gen",
            label="Lead Generation Readiness",
            score=int(result.lead_gen_score),
            description="Composite score weighted from SEO and UX/UI readiness.",
        ),
        ScoreCard(
            id="seo",
            label="SEO",
            score=int(result.seo_score),
            description="Search visibility, crawlability, metadata, structure, and speed signals.",
        ),
        ScoreCard(
            id="uxui",
            label="UX/UI",
            score=int(result.uxui_score),
            description="Conversion clarity, CTAs, forms, contact paths, trust, and navigation.",
        ),
    ]


def _executive_summary(commentary: JsonDict) -> str:
    content = _dict(commentary.get("content"))
    summary = str(content.get("executive_summary") or "").strip()
    if summary:
        return summary
    return (
        "The audit produced deterministic SEO, UX/UI, and Lead Generation Readiness scores. "
        "Use the prioritized roadmap and score breakdown to address the highest-confidence "
        "lead generation opportunities first."
    )


def _commentary_findings(
    section_id: ReportSectionId,
    section_content: JsonDict,
) -> list[ReportFinding]:
    findings: list[ReportFinding] = []
    for item in _list(section_content.get("findings")):
        payload = _dict(item)
        findings.append(
            ReportFinding(
                section=section_id,
                severity=_severity(payload.get("severity")),
                title=_text(payload.get("title"), "Finding"),
                explanation=_text(payload.get("explanation"), "No explanation provided."),
                evidence_refs=[str(value) for value in _list(payload.get("evidence_refs"))],
                source="commentary",
            )
        )
    return findings


def _commentary_recommendations(
    section_id: ReportSectionId,
    section_content: JsonDict,
) -> list[ReportRecommendation]:
    recommendations: list[ReportRecommendation] = []
    for item in _list(section_content.get("recommendations")):
        payload = _dict(item)
        recommendations.append(
            ReportRecommendation(
                section=section_id,
                tier=_tier(payload.get("tier")),
                title=_text(payload.get("title"), "Recommendation"),
                rationale=_text(payload.get("rationale"), "Recommended from audit evidence."),
                action_items=[str(value) for value in _list(payload.get("action_items"))],
            )
        )
    return recommendations


def _fallback_findings(
    section_id: ReportSectionId,
    score: int,
    opportunities: list[RuleSummary],
) -> list[ReportFinding]:
    if opportunities:
        primary = opportunities[0]
        return [
            ReportFinding(
                section=section_id,
                severity="medium" if score < 70 else "info",
                title=primary.description,
                explanation=(
                    "The deterministic scoring rubric flagged this item as an opportunity "
                    f"with a {primary.result} result."
                ),
                evidence_refs=[primary.rule_id],
                source="rubric",
            )
        ]

    label = SECTION_LABELS[section_id]
    return [
        ReportFinding(
            section=section_id,
            severity="info",
            title=f"{label} score is {score}",
            explanation=(
                f"The deterministic {label} score was generated from extracted audit facts."
            ),
            evidence_refs=["score_breakdown"],
            source="rubric",
        )
    ]


def _opportunities_for_section(
    section_id: ReportSectionId,
    score_breakdown: JsonDict,
) -> list[RuleSummary]:
    if section_id == "lead_generation":
        return []
    category = _dict(_dict(score_breakdown.get("categories")).get(section_id))
    rules = [_rule_summary(rule) for rule in _list(category.get("rules"))]
    return [rule for rule in rules if rule.result in {"fail", "partial", "skipped"}]


def _appendix(score_breakdown: JsonDict) -> Appendix:
    categories = _dict(score_breakdown.get("categories"))
    return Appendix(
        scoring_note=(
            "Scores are deterministic and generated from extracted website facts using versioned "
            "YAML rubrics. Commentary explains those facts; it does not create new scores."
        ),
        seo_rules=[
            _rule_summary(rule) for rule in _list(_dict(categories.get("seo")).get("rules"))
        ],
        uxui_rules=[
            _rule_summary(rule) for rule in _list(_dict(categories.get("uxui")).get("rules"))
        ],
    )


def _rule_summary(rule: Any) -> RuleSummary:
    payload = _dict(rule)
    evidence = _dict(payload.get("evidence"))
    return RuleSummary(
        rule_id=_text(payload.get("rule_id"), "unknown_rule"),
        description=_text(payload.get("description"), "No description provided."),
        result=_rule_result(payload.get("result")),
        points_awarded=float(payload.get("points_awarded") or 0),
        points_possible=float(payload.get("points_possible") or 0),
        evidence_value=_evidence_value(evidence.get("value")),
        reason=str(evidence.get("reason")) if evidence.get("reason") else None,
    )


def _roadmap(sections: list[ReportSection]) -> list[RoadmapTier]:
    recommendations = [
        recommendation
        for section in sections
        for recommendation in section.recommendations
        if section.id in {"seo", "uxui", "lead_generation"}
    ]
    return [
        RoadmapTier(
            tier=tier,
            label=label,
            recommendations=[
                recommendation for recommendation in recommendations if recommendation.tier == tier
            ],
        )
        for tier, label in TIER_LABELS.items()
    ]


def _validation_summary(validation_log: JsonDict) -> ValidationSummary:
    return ValidationSummary(
        status=str(validation_log.get("status") or "unknown"),
        numeric_claims_checked=int(validation_log.get("numeric_claims_checked") or 0),
        unsupported_claim_count=int(validation_log.get("unsupported_claim_count") or 0),
        action=str(validation_log.get("action") or "none"),
    )


def _pagespeed_summary(psi_facts: JsonDict) -> PageSpeedSummary:
    summary = _dict(psi_facts.get("summary"))
    return PageSpeedSummary(
        status=str(psi_facts.get("status") or "unknown"),
        reason=str(psi_facts.get("reason")) if psi_facts.get("reason") else None,
        scope=str(psi_facts.get("scope")) if psi_facts.get("scope") else None,
        pages_requested=int(psi_facts.get("pages_requested") or 0),
        pages_analyzed=int(psi_facts.get("pages_analyzed") or 0),
        avg_mobile_performance=_optional_int(summary.get("avg_mobile_performance")),
        avg_desktop_performance=_optional_int(summary.get("avg_desktop_performance")),
        complete_mobile_pages=int(summary.get("complete_mobile_pages") or 0),
        complete_desktop_pages=int(summary.get("complete_desktop_pages") or 0),
        slowest_pages=[_dict(page) for page in _list(summary.get("slowest_pages"))],
    )


def _crawl_summary(crawled_pages: JsonDict) -> CrawlSummary:
    summary = _dict(crawled_pages.get("summary"))
    return CrawlSummary(
        status=str(crawled_pages.get("status") or "unknown"),
        successful_pages=int(summary.get("successful_pages") or 0),
        failed_pages=int(summary.get("failed_pages") or 0),
        skipped_pages=int(summary.get("skipped_pages") or 0),
        failed_page_items=[_dict(page) for page in _list(crawled_pages.get("failed_pages"))],
        skipped_page_items=[_dict(page) for page in _list(crawled_pages.get("skipped_pages"))],
    )


def _report_generated_at(result: Any) -> datetime:
    """Return a stable report-generation timestamp.

    Prefer the PDF renderer's recorded ``generated_at``, then the result row's
    ``created_at`` (collection completion), so the value does not drift every time
    the detail endpoint is polled. Only fall back to "now" when neither exists.
    """
    metadata = _dict(getattr(result, "report_metadata", None))
    raw = metadata.get("generated_at")
    if isinstance(raw, str):
        try:
            parsed = datetime.fromisoformat(raw)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            pass

    created = getattr(result, "created_at", None)
    if isinstance(created, datetime):
        return created if created.tzinfo else created.replace(tzinfo=UTC)

    return datetime.now(UTC)


def _domain(url: str) -> str:
    parsed = urlparse(url)
    hostname = parsed.hostname or url
    return hostname.removeprefix("www.")


def _dict(value: Any) -> JsonDict:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, fallback: str) -> str:
    cleaned = " ".join(str(value or "").split())
    return cleaned or fallback


def _severity(value: Any) -> Literal["info", "low", "medium", "high"]:
    return str(value) if value in {"info", "low", "medium", "high"} else "info"


def _tier(value: Any) -> RecommendationTier:
    return str(value) if value in TIER_LABELS else "quick_win"


def _rule_result(value: Any) -> Literal["pass", "partial", "fail", "skipped"]:
    return str(value) if value in {"pass", "partial", "fail", "skipped"} else "fail"


def _optional_int(value: Any) -> int | None:
    return int(value) if isinstance(value, int | float) else None


def _evidence_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str | int | float | bool):
        return str(value)
    if isinstance(value, list):
        return f"{len(value)} item(s)"
    if isinstance(value, dict):
        return f"{len(value)} field(s)"
    return str(value)
