from pathlib import Path

from apps.shared.config import Settings
from apps.worker.stages.commentary import CommentaryContent
from apps.worker.stages.content_plan import build_content_plan
from apps.worker.stages.extractor_seo import extract_seo_facts
from apps.worker.stages.extractor_uxui import extract_uxui_facts
from apps.worker.stages.grounding_validator import validate_commentary_grounding
from apps.worker.stages.scoring import score_audit

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def _settings(**kwargs) -> Settings:
    return Settings(_env_file=None, openai_api_key=None, **kwargs)


def _rule(
    rule_id: str,
    result: str,
    *,
    weight: float,
    impact: str,
    tier: str,
    surface: bool = True,
    label: str | None = None,
    fact_path: str = "seo.summary.value",
    value: object = None,
) -> dict:
    return {
        "rule_id": rule_id,
        "description": f"desc {rule_id}",
        "weight": weight,
        "evaluator": "threshold",
        "fact_path": fact_path,
        "impact": impact,
        "tier": tier,
        "finding_label": label or f"Problem {rule_id}",
        "remediation": f"Fix {rule_id}.",
        "surface_as_finding": surface,
        "result": result,
        "points_awarded": 0.0,
        "points_possible": weight,
        "evidence": {"value": value, "params": {}, "reason": None},
    }


def _breakdown(seo_rules: list[dict], uxui_rules: list[dict] | None = None) -> dict:
    return {
        "scores": {"seo": 40, "uxui": 40, "lead_gen": 40},
        "categories": {"seo": {"rules": seo_rules}, "uxui": {"rules": uxui_rules or []}},
        "composite": {"score": 40},
    }


def _plan(breakdown: dict, **settings_kwargs) -> CommentaryContent:
    return build_content_plan(
        audit_context={"url": "https://x.test", "niche": None, "target_audience": None},
        seo_facts={},
        uxui_facts={},
        psi_facts={},
        score_breakdown=breakdown,
        settings=_settings(**settings_kwargs),
    )


def test_only_failing_surfaced_rules_become_findings() -> None:
    plan = _plan(
        _breakdown(
            [
                _rule("seo.a", "pass", weight=5, impact="high", tier="quick_win"),
                _rule("seo.b", "skipped", weight=5, impact="high", tier="quick_win"),
                _rule("seo.meta", "fail", weight=10, impact="high", tier="quick_win", label="Meta"),
                _rule(
                    "seo.hidden", "fail", weight=10, impact="high", tier="quick_win", surface=False
                ),
            ]
        )
    )
    assert [f.title for f in plan.seo.findings] == ["Meta"]


def test_findings_ordered_by_severity_then_weight_then_id() -> None:
    plan = _plan(
        _breakdown(
            [
                _rule("seo.low_w", "fail", weight=6, impact="high", tier="quick_win", label="A"),
                _rule("seo.high_w", "fail", weight=9, impact="high", tier="quick_win", label="B"),
                _rule(
                    "seo.medium", "fail", weight=20, impact="medium", tier="quick_win", label="C"
                ),
            ]
        )
    )
    # High severity before medium (even though C has the largest weight); within high,
    # heavier weight first.
    assert [(f.severity, f.title) for f in plan.seo.findings] == [
        ("high", "B"),
        ("high", "A"),
        ("medium", "C"),
    ]


def test_severity_matrix_partial_is_one_notch_down() -> None:
    plan = _plan(
        _breakdown(
            [
                _rule(
                    "seo.a", "fail", weight=5, impact="high", tier="quick_win", label="fail-high"
                ),
                _rule(
                    "seo.b", "partial", weight=5, impact="high", tier="quick_win", label="part-high"
                ),
                _rule(
                    "seo.c", "partial", weight=5, impact="low", tier="quick_win", label="part-low"
                ),
            ]
        )
    )
    by_title = {f.title: f.severity for f in plan.seo.findings}
    assert by_title["fail-high"] == "high"
    assert by_title["part-high"] == "medium"
    assert by_title["part-low"] == "info"


def test_tier_comes_from_rule_metadata() -> None:
    plan = _plan(
        _breakdown([_rule("seo.a", "fail", weight=5, impact="high", tier="long_term", label="A")])
    )
    assert plan.seo.recommendations[0].tier == "long_term"


def test_top_n_truncation_is_deterministic() -> None:
    rules = [
        _rule(f"seo.r{i}", "fail", weight=5, impact="high", tier="quick_win", label=f"R{i}")
        for i in range(10)
    ]
    plan = _plan(
        _breakdown(rules),
        commentary_max_findings_per_section=3,
        commentary_max_recommendations_per_section=2,
    )
    assert len(plan.seo.findings) == 3
    assert len(plan.seo.recommendations) == 2
    # Lowest rule_id wins ties deterministically.
    assert [f.title for f in plan.seo.findings] == ["R0", "R1", "R2"]


def test_no_internal_rule_ids_leak_into_prose() -> None:
    plan = _plan(
        _breakdown(
            [
                _rule(
                    "seo.meta_description.x",
                    "fail",
                    weight=9,
                    impact="high",
                    tier="quick_win",
                    label="Meta missing",
                )
            ]
        )
    )
    finding = plan.seo.findings[0]
    assert "seo.meta_description" not in finding.title
    assert "seo.meta_description" not in finding.meaning
    assert "seo.meta_description" not in finding.why


def test_external_seo_findings_include_real_locations() -> None:
    rule = _rule(
        "seo.technical_crawl.no_broken_internal_urls",
        "fail",
        weight=8,
        impact="high",
        tier="quick_win",
        label="Internal broken URLs were found",
        fact_path="external_seo.technical_crawl.summary.client_error_internal_urls",
        value=2,
    )
    plan = build_content_plan(
        audit_context={"url": "https://x.test", "niche": None, "target_audience": None},
        seo_facts={},
        uxui_facts={},
        psi_facts={},
        external_seo_facts={
            "technical_crawl": {
                "status": "complete",
                "issues": [
                    {
                        "id": "client_error_internal_urls",
                        "examples": ["https://example.com/broken"],
                    }
                ],
            }
        },
        score_breakdown=_breakdown([rule]),
        settings=_settings(),
    )

    finding = plan.seo.findings[0]
    assert "https://example.com/broken" in finding.location_urls
    assert "external_seo" not in finding.meaning
    assert "external_seo" not in finding.why


def test_plan_is_grounding_safe_on_real_fixture() -> None:
    settings = _settings()
    html = (FIXTURE_DIR / "weak_site.html").read_text(encoding="utf-8")
    pages = [
        {
            "url": "https://weak.example/",
            "final_url": "https://weak.example/",
            "status_code": 200,
            "html": html,
        }
    ]
    seo_facts = extract_seo_facts(pages)
    uxui_facts = extract_uxui_facts(pages)
    psi_facts = {"status": "skipped", "summary": {}}
    breakdown = score_audit(seo_facts, uxui_facts, psi_facts, settings)

    plan = build_content_plan(
        audit_context={"url": "https://weak.example/", "niche": None, "target_audience": None},
        seo_facts=seo_facts,
        uxui_facts=uxui_facts,
        psi_facts=psi_facts,
        score_breakdown=breakdown,
        settings=settings,
    )
    commentary = {
        "status": "deterministic",
        "provider": "deterministic",
        "model": "deterministic",
        "content": plan.model_dump(mode="json"),
    }

    sanitized, log = validate_commentary_grounding(
        commentary,
        fact_sources={
            "seo_facts": seo_facts,
            "uxui_facts": uxui_facts,
            "psi_facts": psi_facts,
            "scores": breakdown["scores"],
        },
    )

    # Every number the deterministic plan emits is a stored fact or a score, so grounding
    # strips nothing and the content survives byte-identical.
    assert log["unsupported_claim_count"] == 0
    assert sanitized["content"] == commentary["content"]
    # The weak fixture must actually produce findings, or the invariant above is vacuous.
    content = CommentaryContent.model_validate(sanitized["content"])
    assert content.seo.findings or content.uxui.findings
