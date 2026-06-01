from types import SimpleNamespace
from uuid import uuid4

from apps.worker.stages.report_payload import compose_report_payload


def test_compose_report_payload_includes_epic_4_contract() -> None:
    payload = compose_report_payload(_job(), _result())

    assert payload.version == "phase1-report-v1"
    assert payload.metadata.site_domain == "example.com"
    assert [score.id for score in payload.scores] == ["lead_gen", "seo", "uxui"]
    assert payload.sections[0].id == "seo"
    assert payload.sections[1].id == "uxui"
    assert payload.roadmap[0].tier == "quick_win"
    assert payload.validation_summary.unsupported_claim_count == 1
    assert payload.pagespeed_summary.status == "skipped"
    assert payload.pagespeed_summary.reason == "missing_google_psi_api_key"
    assert payload.crawl_summary.failed_pages == 1
    assert payload.appendix.seo_rules
    assert payload.appendix.uxui_rules


def test_compose_report_payload_falls_back_to_rubric_findings_without_commentary() -> None:
    result = _result(commentary={"status": "complete", "content": {}})

    payload = compose_report_payload(_job(), result)

    seo = next(section for section in payload.sections if section.id == "seo")
    assert seo.findings[0].source == "rubric"
    assert seo.findings[0].evidence_refs == ["seo.meta_description.present_all_pages"]


def _job() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        url="https://example.com/",
        niche="builder",
        target_audience="homeowners",
    )


def _result(**overrides) -> SimpleNamespace:
    payload = {
        "seo_score": 76,
        "uxui_score": 68,
        "lead_gen_score": 72,
        "crawled_pages": _crawled_pages(),
        "seo_facts": {},
        "uxui_facts": {},
        "psi_facts": _missing_psi(),
        "score_breakdown": _score_breakdown(),
        "commentary": _commentary(),
        "validation_log": {
            "status": "complete",
            "numeric_claims_checked": 4,
            "unsupported_claim_count": 1,
            "action": "stripped_unsupported_numeric_sentences",
        },
        "report_metadata": {},
        "pdf_path": None,
        "rubric_version": "phase1-seo-v1+phase1-uxui-v1+phase1-composite-v1",
        "llm_model": "gpt-4o",
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def _crawled_pages() -> dict:
    return {
        "status": "partial",
        "requested_url": "https://example.com/",
        "final_url": "https://example.com/",
        "summary": {
            "successful_pages": 2,
            "failed_pages": 1,
            "skipped_pages": 1,
        },
        "failed_pages": [
            {
                "url": "https://example.com/gallery",
                "reason": "Timed out rendering https://example.com/gallery",
            }
        ],
        "skipped_pages": [
            {
                "url": "https://example.com/private",
                "reason": "disallowed_by_robots_txt",
            }
        ],
    }


def _missing_psi() -> dict:
    return {
        "status": "skipped",
        "reason": "missing_google_psi_api_key",
        "scope": "all_crawled_pages",
        "pages_requested": 2,
        "pages_analyzed": 0,
        "pages": [],
        "summary": {
            "avg_mobile_performance": None,
            "avg_desktop_performance": None,
            "complete_mobile_pages": 0,
            "complete_desktop_pages": 0,
            "slowest_pages": [],
        },
    }


def _score_breakdown() -> dict:
    return {
        "scores": {"seo": 76, "uxui": 68, "lead_gen": 72},
        "categories": {
            "seo": {
                "rules": [
                    _rule("seo.title.present_all_pages", "Page titles are present.", "pass", 8, 8),
                    _rule(
                        "seo.meta_description.present_all_pages",
                        "Meta descriptions are present across crawled pages.",
                        "fail",
                        0,
                        10,
                    ),
                ]
            },
            "uxui": {
                "rules": [
                    _rule(
                        "uxui.primary_cta.present",
                        "A primary CTA is present.",
                        "partial",
                        5,
                        10,
                    ),
                    _rule("uxui.forms.present", "The site includes a lead form.", "fail", 0, 8),
                ]
            },
        },
    }


def _rule(rule_id: str, description: str, result: str, awarded: float, possible: float) -> dict:
    return {
        "rule_id": rule_id,
        "description": description,
        "result": result,
        "points_awarded": awarded,
        "points_possible": possible,
        "evidence": {
            "value": awarded,
            "reason": None,
        },
    }


def _commentary() -> dict:
    return {
        "status": "complete",
        "provider": "openai",
        "model": "gpt-4o",
        "content": {
            "executive_summary": "The site has clear opportunities to improve lead capture.",
            "seo": _section("SEO needs stronger metadata", "seo"),
            "uxui": _section("UX/UI needs clearer conversion paths", "uxui"),
            "lead_generation": _section("Lead capture needs focus", "lead_generation"),
        },
    }


def _section(headline: str, evidence_prefix: str) -> dict:
    return {
        "headline": headline,
        "findings": [
            {
                "severity": "medium",
                "title": headline,
                "explanation": "The report finding is grounded in extracted audit facts.",
                "evidence_refs": [f"{evidence_prefix}.example"],
            }
        ],
        "recommendations": [
            {
                "tier": "quick_win",
                "title": f"Improve {headline}",
                "rationale": "This is the fastest visible improvement.",
                "action_items": ["Address the highest-confidence failed rule."],
            },
            {
                "tier": "mid_term",
                "title": f"Systematize {headline}",
                "rationale": "This improves repeatable lead generation.",
                "action_items": ["Roll the change across important pages."],
            },
            {
                "tier": "long_term",
                "title": f"Measure {headline}",
                "rationale": "This supports before-and-after comparison.",
                "action_items": ["Re-run the audit after implementation."],
            },
        ],
    }
