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
    external_seo_facts: JsonDict | None = None,
    score_breakdown: JsonDict,
    settings: Settings,
) -> JsonDict:
    # Imported lazily: content_plan imports the commentary models defined in this module,
    # so a top-level import here would be circular.
    from apps.worker.stages.content_plan import build_content_plan

    plan = build_content_plan(
        audit_context=audit_context,
        seo_facts=seo_facts,
        uxui_facts=uxui_facts,
        psi_facts=psi_facts,
        external_seo_facts=external_seo_facts,
        score_breakdown=score_breakdown,
        settings=settings,
    )

    # Phase 1: the deterministic plan IS the report - identical findings, order, severity,
    # and tier on every run, with or without an OpenAI key. The optional LLM polish layer
    # (Phase 2) will rewrite the prose strings here when a key is configured, without
    # changing the structure. See docs/11_COMMENTARY_CONSISTENCY_PLAN.md.
    return {
        "status": "deterministic",
        "provider": "deterministic",
        "model": "deterministic",
        "content": plan.model_dump(mode="json"),
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
    # Retained for Phase 2 (LLM polish): structured-output plumbing that the polish layer
    # will reuse to rewrite the deterministic plan's prose. Not called in Phase 1.
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
