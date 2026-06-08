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

    seo_section = _build_section("seo", score_breakdown, max_findings, max_recs)
    uxui_section = _build_section("uxui", score_breakdown, max_findings, max_recs)

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
    max_findings: int,
    max_recs: int,
) -> CommentarySection:
    surfaced = _surfaced_rules(section_id, score_breakdown)
    score = _int(_dict(score_breakdown.get("scores")).get(section_id))

    finding_order = sorted(surfaced, key=_finding_sort_key)
    findings = [_finding(rule) for rule in finding_order[:max_findings]]

    rec_order = sorted(surfaced, key=_recommendation_sort_key)
    recommendations = [_recommendation(rule) for rule in rec_order[:max_recs]]

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


def _finding(rule: JsonDict) -> CommentaryFinding:
    return CommentaryFinding(
        severity=_severity(rule.get("impact"), rule.get("result")),
        title=_finding_title(rule),
        explanation=_explanation(rule),
        evidence_refs=_evidence_refs(rule),
    )


def _recommendation(rule: JsonDict) -> CommentaryRecommendation:
    remediation = rule.get("remediation")
    action = (
        remediation.strip()
        if isinstance(remediation, str) and remediation.strip()
        else _DEFAULT_ACTION
    )
    return CommentaryRecommendation(
        tier=_tier(rule.get("tier")),
        title=_finding_title(rule),
        rationale=_explanation(rule),
        action_items=[action],
    )


def _lead_section(scores: JsonDict) -> CommentarySection:
    lead = _int(scores.get("lead_gen"))
    severity = "high" if lead < 50 else "medium" if lead < 75 else "info"
    return CommentarySection(
        headline=f"Lead Generation Readiness score is {lead}",
        findings=[
            CommentaryFinding(
                severity=severity,
                title=f"Lead Generation Readiness score is {lead}",
                explanation=(
                    "This composite score is weighted from the deterministic SEO and UX/UI "
                    "scores. Improving the SEO and UX/UI items in this report raises it."
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
        "Lead Generation Readiness."
    )
    if top_label:
        summary += f" The highest-priority opportunity is: {top_label}."
    summary += " Start with the quick wins, then work through the mid-term and long-term items."
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


def _explanation(rule: JsonDict) -> str:
    base = _finding_title(rule).rstrip(".") + "."
    evidence = _evidence_sentence(rule)
    return f"{base} {evidence}" if evidence else base


def _evidence_sentence(rule: JsonDict) -> str | None:
    value = _dict(rule.get("evidence")).get("value")
    number = _format_number(value)
    if number is None:
        return None
    fact_path = str(rule.get("fact_path") or "")
    if fact_path.endswith("_pct"):
        return f"Measured at {number}% across crawled pages."
    return f"Measured value: {number}."


def _evidence_refs(rule: JsonDict) -> list[str]:
    fact_path = rule.get("fact_path")
    return [str(fact_path)] if isinstance(fact_path, str) and fact_path else []


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
