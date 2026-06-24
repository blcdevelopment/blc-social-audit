"""Compose the standalone Social report payload from a stored social audit result.

Pure function (no rendering/IO) shared by the PDF renderer and the API detail response —
mirrors how report_payload.compose_report_payload serves the website audit. Findings and
the tiered roadmap come straight from the social rubric's rule metadata (deterministic; no
LLM), so the report is reproducible.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

JsonDict = dict[str, Any]
SOCIAL_REPORT_VERSION = "phase2-social-report-v1"
_TIERS = ("quick_win", "mid_term", "long_term")


def _dict(value: Any) -> JsonDict:
    return value if isinstance(value, dict) else {}


def compose_social_report_payload(job: Any, result: Any) -> JsonDict:
    facts = _dict(getattr(result, "social_facts", None))
    breakdown = _dict(getattr(result, "score_breakdown", None))
    summary = _dict(facts.get("summary"))
    category = _dict(breakdown.get("category"))
    rules = category.get("rules") if isinstance(category.get("rules"), list) else []

    platforms = [
        p
        for p in (facts.get("platforms") or [])
        if isinstance(p, dict) and p.get("status") == "complete"
    ]

    # Optional LLM-polished prose (set by _run_social_pipeline). When present, attach the
    # executive summary and a per-finding narrative; otherwise the report is the pure
    # rule-derived deterministic output (commentary_provider == "deterministic").
    commentary = _dict(getattr(result, "commentary", None))
    content = _dict(commentary.get("content"))
    narratives = {
        f.get("id"): f.get("narrative")
        for f in (content.get("findings") or [])
        if isinstance(f, dict) and f.get("narrative")
    }

    findings: list[JsonDict] = []
    roadmap: dict[str, list[JsonDict]] = {tier: [] for tier in _TIERS}
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        if rule.get("result") not in {"fail", "partial"}:
            continue
        if not rule.get("surface_as_finding", True):
            continue
        rule_id = rule.get("rule_id")
        item = {
            "id": rule_id,
            "label": rule.get("finding_label") or rule.get("description") or rule_id,
            "remediation": rule.get("remediation"),
            "impact": rule.get("impact") or "medium",
            "tier": rule.get("tier") or "quick_win",
            "result": rule.get("result"),
            "narrative": narratives.get(rule_id) or "",
        }
        findings.append(item)
        roadmap.get(item["tier"], roadmap["quick_win"]).append(item)

    return {
        "version": SOCIAL_REPORT_VERSION,
        "score": getattr(result, "social_score", None),
        "status": facts.get("status") or "unknown",
        "handles": getattr(job, "social_handles", None) or {},
        "generated_date": datetime.now(UTC).strftime("%B %d, %Y"),
        "platforms_audited": summary.get("platforms_audited", 0),
        "summary": summary,
        "platforms": platforms,
        "executive_summary": content.get("executive_summary") or "",
        "commentary_provider": commentary.get("provider") or "deterministic",
        "findings": findings,
        "roadmap": roadmap,
    }
