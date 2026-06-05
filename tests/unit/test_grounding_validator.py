from apps.worker.stages.grounding_validator import validate_commentary_grounding


def _commentary(summary: str) -> dict:
    return {
        "status": "complete",
        "provider": "test",
        "model": "test-model",
        "content": {
            "executive_summary": summary,
            "seo": {
                "headline": "SEO score is 80",
                "findings": [
                    {
                        "severity": "info",
                        "title": "SEO score is 80",
                        "explanation": "The SEO score is 80.",
                        "evidence_refs": ["scores.seo"],
                    }
                ],
                "recommendations": [
                    {
                        "tier": "quick_win",
                        "title": "Update meta descriptions",
                        "rationale": "The score breakdown flagged missing descriptions.",
                        "action_items": ["Add descriptions to crawled pages."],
                    }
                ],
            },
            "uxui": {
                "headline": "UX score is 70",
                "findings": [
                    {
                        "severity": "medium",
                        "title": "UX score is 70",
                        "explanation": "The UX score is 70.",
                        "evidence_refs": ["scores.uxui"],
                    }
                ],
                "recommendations": [
                    {
                        "tier": "quick_win",
                        "title": "Improve calls to action",
                        "rationale": "The score breakdown flagged CTA gaps.",
                        "action_items": ["Add a primary CTA."],
                    }
                ],
            },
            "lead_generation": {
                "headline": "Lead score is 75",
                "findings": [
                    {
                        "severity": "medium",
                        "title": "Lead score is 75",
                        "explanation": "The Lead Generation Readiness score is 75.",
                        "evidence_refs": ["composite"],
                    }
                ],
                "recommendations": [
                    {
                        "tier": "quick_win",
                        "title": "Fix failed rules",
                        "rationale": "The score breakdown shows deterministic gaps.",
                        "action_items": ["Resolve failed rules first."],
                    }
                ],
            },
        },
    }


def test_grounding_validator_keeps_supported_numeric_claims() -> None:
    sanitized, log = validate_commentary_grounding(
        _commentary("SEO score is 80. UX score is 70. Lead score is 75."),
        fact_sources={"scores": {"seo": 80, "uxui": 70, "lead_gen": 75}},
    )

    assert log["unsupported_claim_count"] == 0
    assert sanitized["content"]["executive_summary"] == (
        "SEO score is 80. UX score is 70. Lead score is 75."
    )


def test_grounding_validator_strips_unsupported_numeric_claims() -> None:
    sanitized, log = validate_commentary_grounding(
        _commentary("SEO score is 80. The site has 42 missing pages."),
        fact_sources={"scores": {"seo": 80, "uxui": 70, "lead_gen": 75}},
    )

    assert log["unsupported_claim_count"] == 1
    assert "42 missing pages" not in sanitized["content"]["executive_summary"]
    assert sanitized["content"]["executive_summary"] == "SEO score is 80."


def test_grounding_validator_keeps_timeframe_language() -> None:
    summary = "Resolve the top issues within 30 days and plan structural work over 1-3 months."
    sanitized, log = validate_commentary_grounding(
        _commentary(summary),
        fact_sources={"scores": {"seo": 80, "uxui": 70, "lead_gen": 75}},
    )

    # Timeframe numbers are rhetorical, not measured facts, so the sentence is preserved.
    assert log["unsupported_claim_count"] == 0
    assert sanitized["content"]["executive_summary"] == summary
