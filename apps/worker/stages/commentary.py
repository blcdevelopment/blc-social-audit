from __future__ import annotations

import json
from pathlib import Path
from string import Template
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from apps.shared.config import Settings

JsonDict = dict[str, Any]


class CommentaryFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: Literal["info", "low", "medium", "high"]
    title: str
    explanation: str
    evidence_refs: list[str]


class CommentaryRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tier: Literal["quick_win", "mid_term", "long_term"]
    title: str
    rationale: str
    action_items: list[str]


class CommentarySection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: str
    findings: list[CommentaryFinding]
    recommendations: list[CommentaryRecommendation]


class CommentaryContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    executive_summary: str
    seo: CommentarySection
    uxui: CommentarySection
    lead_generation: CommentarySection


def generate_commentary(
    *,
    audit_context: JsonDict,
    seo_facts: JsonDict,
    uxui_facts: JsonDict,
    psi_facts: JsonDict,
    score_breakdown: JsonDict,
    settings: Settings,
) -> JsonDict:
    api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else ""
    if not api_key:
        return _fallback_commentary(
            score_breakdown=score_breakdown,
            model="not_configured",
            status="fallback_missing_api_key",
        )

    try:
        content = _call_openai(
            api_key=api_key,
            audit_context=audit_context,
            seo_facts=seo_facts,
            uxui_facts=uxui_facts,
            psi_facts=psi_facts,
            score_breakdown=score_breakdown,
            settings=settings,
        )
    except Exception as exc:  # pragma: no cover - network/provider failure path
        return _fallback_commentary(
            score_breakdown=score_breakdown,
            model=settings.openai_model,
            status="fallback_provider_error",
            error_type=exc.__class__.__name__,
        )

    return {
        "status": "complete",
        "provider": "openai",
        "model": settings.openai_model,
        "content": content.model_dump(mode="json"),
    }


def validate_commentary_content(payload: JsonDict) -> CommentaryContent:
    return CommentaryContent.model_validate(payload)


def commentary_json_schema() -> JsonDict:
    return CommentaryContent.model_json_schema()


def _call_openai(
    *,
    api_key: str,
    audit_context: JsonDict,
    seo_facts: JsonDict,
    uxui_facts: JsonDict,
    psi_facts: JsonDict,
    score_breakdown: JsonDict,
    settings: Settings,
) -> CommentaryContent:
    from openai import OpenAI

    client = OpenAI(api_key=api_key, timeout=settings.openai_timeout_seconds)
    system_prompt = _read_prompt(settings.commentary_system_prompt_path)
    user_prompt = _render_user_prompt(
        settings.commentary_user_prompt_path,
        audit_context=audit_context,
        facts={
            "seo": _compact_facts(seo_facts),
            "uxui": _compact_facts(uxui_facts),
            "psi": _compact_facts(psi_facts),
        },
        score_breakdown=score_breakdown,
    )
    response = client.responses.parse(
        model=settings.openai_model,
        instructions=system_prompt,
        input=user_prompt,
        text_format=CommentaryContent,
        max_output_tokens=settings.openai_max_tokens,
        temperature=settings.openai_temperature,
    )
    parsed = getattr(response, "output_parsed", None)
    if isinstance(parsed, CommentaryContent):
        return parsed

    raise ValueError("OpenAI response did not include parsed structured commentary output.")


def _render_user_prompt(
    path: Path,
    *,
    audit_context: JsonDict,
    facts: JsonDict,
    score_breakdown: JsonDict,
) -> str:
    template = Template(_read_prompt(path))
    score_summary = score_breakdown.get("scores", {})
    return template.safe_substitute(
        url=audit_context.get("url") or "not provided",
        niche=audit_context.get("niche") or "not provided",
        target_audience=audit_context.get("target_audience") or "not provided",
        score_summary_json=_to_json(score_summary),
        facts_json=_to_json(facts),
        score_breakdown_json=_to_json(_compact_score_breakdown(score_breakdown)),
    )


def _read_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _fallback_commentary(
    *,
    score_breakdown: JsonDict,
    model: str,
    status: Literal["fallback_missing_api_key", "fallback_provider_error"],
    error_type: str | None = None,
) -> JsonDict:
    scores = score_breakdown.get("scores", {})
    seo_score = int(scores.get("seo") or 0)
    uxui_score = int(scores.get("uxui") or 0)
    lead_score = int(scores.get("lead_gen") or 0)
    content = CommentaryContent(
        executive_summary=(
            f"The audited site has an SEO score of {seo_score}, a UX/UI score of {uxui_score}, "
            f"and a Lead Generation Readiness score of {lead_score}. Review the failed "
            "and partial rules first because those are the highest-confidence improvement areas."
        ),
        seo=_fallback_section(
            "SEO",
            seo_score,
            score_breakdown.get("categories", {}).get("seo", {}),
            "Improve search visibility with clearer page metadata and crawlable structure.",
        ),
        uxui=_fallback_section(
            "UX/UI",
            uxui_score,
            score_breakdown.get("categories", {}).get("uxui", {}),
            "Improve conversion clarity with stronger calls to action and trust signals.",
        ),
        lead_generation=_fallback_lead_section(lead_score),
    )
    artifact = {
        "status": status,
        "provider": "local_fallback",
        "model": model,
        "content": content.model_dump(mode="json"),
    }
    if error_type:
        artifact["error_type"] = error_type
    return artifact


def _fallback_section(
    category_label: str,
    score: int,
    category_breakdown: JsonDict,
    default_recommendation: str,
) -> CommentarySection:
    failed_rules = _rules_with_results(category_breakdown, {"fail", "partial"})
    primary_rule = failed_rules[0] if failed_rules else None
    title = (
        f"{category_label} score is {score}"
        if primary_rule is None
        else f"{category_label} opportunity: {primary_rule['description']}"
    )
    explanation = (
        f"The deterministic {category_label} rubric produced a score of {score}."
        if primary_rule is None
        else (
            "The scoring rubric flagged this item from extracted site facts: "
            f"{primary_rule['description']}"
        )
    )

    recommendations = [
        _recommendation_from_rule("quick_win", failed_rules, default_recommendation, 0),
        _recommendation_from_rule("mid_term", failed_rules, default_recommendation, 1),
        _recommendation_from_rule("long_term", failed_rules, default_recommendation, 2),
    ]
    return CommentarySection(
        headline=title,
        findings=[
            CommentaryFinding(
                severity="medium" if score < 70 else "info",
                title=title,
                explanation=explanation,
                evidence_refs=[primary_rule["rule_id"] if primary_rule else "score_breakdown"],
            )
        ],
        recommendations=recommendations,
    )


def _fallback_lead_section(score: int) -> CommentarySection:
    return CommentarySection(
        headline=f"Lead Generation Readiness score is {score}",
        findings=[
            CommentaryFinding(
                severity="medium" if score < 70 else "info",
                title=f"Lead Generation Readiness score is {score}",
                explanation=(
                    f"The composite rubric produced a Lead Generation Readiness score of {score} "
                    "from the deterministic SEO and UX/UI scores."
                ),
                evidence_refs=["composite"],
            )
        ],
        recommendations=[
            CommentaryRecommendation(
                tier="quick_win",
                title="Fix the clearest failed rubric items first",
                rationale="The fastest improvements are the issues already flagged by rules.",
                action_items=[
                    "Review failed rules in the score breakdown and resolve visible gaps.",
                ],
            ),
            CommentaryRecommendation(
                tier="mid_term",
                title="Improve conversion paths across key pages",
                rationale="Lead generation improves when visitors can quickly find a next step.",
                action_items=["Add or refine calls to action on important service pages."],
            ),
            CommentaryRecommendation(
                tier="long_term",
                title="Re-audit after site improvements",
                rationale="Reproducible scoring makes before-and-after comparison straightforward.",
                action_items=["Run the same URL again after changes and compare score breakdowns."],
            ),
        ],
    )


def _recommendation_from_rule(
    tier: Literal["quick_win", "mid_term", "long_term"],
    failed_rules: list[JsonDict],
    default_recommendation: str,
    index: int,
) -> CommentaryRecommendation:
    rule = failed_rules[index] if index < len(failed_rules) else None
    title = f"Address {rule['rule_id']}" if rule else default_recommendation
    rationale = (
        f"The rubric flagged this item: {rule['description']}"
        if rule
        else "This recommendation follows the current Phase 1 scoring rubric."
    )
    return CommentaryRecommendation(
        tier=tier,
        title=title[:120],
        rationale=rationale,
        action_items=[
            rule["description"] if rule else default_recommendation,
        ],
    )


def _rules_with_results(category_breakdown: JsonDict, results: set[str]) -> list[JsonDict]:
    rules = category_breakdown.get("rules", [])
    if not isinstance(rules, list):
        return []
    return [rule for rule in rules if isinstance(rule, dict) and str(rule.get("result")) in results]


def _compact_facts(payload: JsonDict) -> JsonDict:
    return {
        key: value
        for key, value in payload.items()
        if key not in {"html", "rendered_html", "text"} and key != "pages"
    } | {"pages": _compact_pages(payload.get("pages", []))}


def _compact_pages(pages: Any) -> list[JsonDict]:
    if not isinstance(pages, list):
        return []
    compacted: list[JsonDict] = []
    for page in pages[:10]:
        if not isinstance(page, dict):
            continue
        compacted.append(
            {
                key: value
                for key, value in page.items()
                if key not in {"html", "rendered_html", "text"}
            }
        )
    return compacted


def _compact_score_breakdown(score_breakdown: JsonDict) -> JsonDict:
    compacted = dict(score_breakdown)
    categories = compacted.get("categories", {})
    if isinstance(categories, dict):
        compacted["categories"] = {
            name: _compact_category_breakdown(category)
            for name, category in categories.items()
            if isinstance(category, dict)
        }
    return compacted


def _compact_category_breakdown(category: JsonDict) -> JsonDict:
    compacted = dict(category)
    rules = compacted.get("rules", [])
    if isinstance(rules, list):
        compacted["rules"] = [
            rule
            for rule in rules
            if isinstance(rule, dict) and rule.get("result") in {"fail", "partial", "skipped"}
        ]
    return compacted


def _to_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, default=str)
