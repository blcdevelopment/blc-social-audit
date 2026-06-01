from apps.shared.config import Settings
from apps.worker.stages.commentary import (
    CommentaryContent,
    CommentaryFinding,
    CommentaryRecommendation,
    CommentarySection,
    commentary_json_schema,
    generate_commentary,
)


def _score_breakdown() -> dict:
    return {
        "status": "complete",
        "rubric_version": "phase1-seo-v1+phase1-uxui-v1+phase1-composite-v1",
        "scores": {"seo": 81, "uxui": 72, "lead_gen": 76},
        "categories": {
            "seo": {
                "rules": [
                    {
                        "rule_id": "seo.meta_description.present_all_pages",
                        "description": "Meta descriptions are present across crawled pages.",
                        "result": "fail",
                    }
                ]
            },
            "uxui": {
                "rules": [
                    {
                        "rule_id": "uxui.trust.present",
                        "description": "Trust signals are visible on at least one crawled page.",
                        "result": "partial",
                    }
                ]
            },
        },
        "composite": {"score": 76},
    }


def test_commentary_schema_is_json_object() -> None:
    schema = commentary_json_schema()

    assert schema["type"] == "object"
    assert "executive_summary" in schema["properties"]


def test_generate_commentary_uses_valid_local_fallback_without_api_key() -> None:
    commentary = generate_commentary(
        audit_context={
            "url": "https://example.com/",
            "niche": "builder",
            "target_audience": "homeowners",
        },
        seo_facts={},
        uxui_facts={},
        psi_facts={},
        score_breakdown=_score_breakdown(),
        settings=Settings(_env_file=None, openai_api_key=None),
    )

    assert commentary["status"] == "fallback_missing_api_key"
    assert commentary["provider"] == "local_fallback"
    CommentaryContent.model_validate(commentary["content"])
    assert commentary["content"]["seo"]["recommendations"][0]["tier"] == "quick_win"


def test_generate_commentary_uses_openai_provider_when_api_key_is_set(monkeypatch) -> None:
    expected = CommentaryContent(
        executive_summary="SEO score is 81. UX/UI score is 72. Lead score is 76.",
        seo=_section("SEO score is 81"),
        uxui=_section("UX/UI score is 72"),
        lead_generation=_section("Lead score is 76"),
    )

    def fake_call_openai(**kwargs):
        assert kwargs["settings"].openai_model == "gpt-4o"
        return expected

    monkeypatch.setattr("apps.worker.stages.commentary._call_openai", fake_call_openai)

    commentary = generate_commentary(
        audit_context={
            "url": "https://example.com/",
            "niche": "builder",
            "target_audience": "homeowners",
        },
        seo_facts={},
        uxui_facts={},
        psi_facts={},
        score_breakdown=_score_breakdown(),
        settings=Settings(_env_file=None, openai_api_key="test-key"),
    )

    assert commentary["status"] == "complete"
    assert commentary["provider"] == "openai"
    assert commentary["model"] == "gpt-4o"
    assert commentary["content"] == expected.model_dump(mode="json")


def _section(headline: str) -> CommentarySection:
    return CommentarySection(
        headline=headline,
        findings=[
            CommentaryFinding(
                severity="info",
                title=headline,
                explanation=headline,
                evidence_refs=["score_breakdown"],
            )
        ],
        recommendations=[
            CommentaryRecommendation(
                tier="quick_win",
                title="Review score breakdown",
                rationale="The score breakdown shows deterministic opportunities.",
                action_items=["Review failed and partial rules."],
            )
        ],
    )
