from types import SimpleNamespace
from uuid import uuid4

from apps.worker.stages.report_payload import compose_report_payload


def test_compose_report_payload_includes_epic_4_contract() -> None:
    payload = compose_report_payload(_job(), _result())

    assert payload.version == "phase1-report-v2"
    assert payload.metadata.site_domain == "example.com"
    assert [score.id for score in payload.scores] == ["lead_gen", "seo", "uxui"]
    score_descriptions = {score.id: score.description for score in payload.scores}
    assert (
        "Formula: round((SEO 76 * 45%) + (UX/UI 68 * 55%)) = 72/100"
        in (score_descriptions["lead_gen"])
    )
    assert (
        "It evaluated 2 checks and earned 76 of 100 available points" in (score_descriptions["seo"])
    )
    assert "1 check worth 6 points was skipped" in score_descriptions["seo"]
    assert "normalized to 68/100" in score_descriptions["uxui"]
    assert payload.sections[0].id == "seo"
    assert payload.sections[1].id == "uxui"
    assert payload.roadmap[0].tier == "quick_win"
    assert payload.validation_summary.unsupported_claim_count == 1
    assert payload.pagespeed_summary.status == "skipped"
    assert payload.pagespeed_summary.reason == "missing_google_psi_api_key"
    assert payload.external_seo_summary.status == "partial"
    assert payload.technical_seo_section.issues[0].id == "client_error_internal_urls"
    assert payload.technical_seo_section.issues[0].summary.startswith("A URL found")
    assert "Visitors" in payload.technical_seo_section.issues[0].why_it_matters
    assert "Update the link" in payload.technical_seo_section.issues[0].recommended_fix
    assert payload.technical_seo_section.issues[0].location_label == (
        "Affected URL found during crawl"
    )
    assert payload.search_performance_section.ranking_opportunities[0]["query"] == "custom homes"
    assert payload.crawl_summary.failed_pages == 1
    assert payload.appendix.seo_rules
    assert payload.appendix.uxui_rules


def test_compose_report_payload_falls_back_to_rubric_findings_without_commentary() -> None:
    result = _result(commentary={"status": "complete", "content": {}})

    payload = compose_report_payload(_job(), result)

    seo = next(section for section in payload.sections if section.id == "seo")
    assert seo.findings[0].source == "rubric"
    assert seo.findings[0].evidence_refs == ["seo.meta_description.present_all_pages"]


def test_compose_report_payload_does_not_surface_incomplete_external_zeroes() -> None:
    result = _result(
        external_seo_facts={
            "status": "partial",
            "sources": {
                "screaming_frog": "failed",
                "gsc": "skipped",
                "url_inspection": "failed",
            },
            "screaming_frog": {
                "status": "failed",
                "summary": {
                    "urls_crawled": 0,
                    "non_indexable_internal_urls": 0,
                },
                "issues": [
                    {
                        "id": "client_error_internal_urls",
                        "severity": "high",
                        "title": "Internal URLs returning 4xx errors",
                        "count": 0,
                        "examples": [],
                    }
                ],
            },
            "gsc": {
                "status": "skipped",
                "summary": {"top_query_count": 0, "top_page_count": 0},
                "ranking_opportunities": [{"query": "stale row"}],
                "high_impression_low_ctr_pages": [{"page": "https://example.com/"}],
                "declining_pages": [{"page": "https://example.com/old"}],
            },
            "url_inspection": {
                "status": "failed",
                "summary": {"not_on_google": 0},
                "items": [{"url": "https://example.com/"}],
            },
        }
    )

    payload = compose_report_payload(_job(), result)

    assert payload.external_seo_summary.technical_issue_count == 0
    assert payload.external_seo_summary.search_opportunity_count == 0
    assert payload.technical_seo_section.status == "failed"
    assert payload.technical_seo_section.summary == {}
    assert payload.technical_seo_section.issues == []
    assert payload.search_performance_section.status == "skipped"
    assert payload.search_performance_section.summary == {}
    assert payload.search_performance_section.ranking_opportunities == []
    assert payload.search_performance_section.url_inspection_items == []


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
        "external_seo_facts": _external_seo_facts(),
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


def _external_seo_facts() -> dict:
    return {
        "status": "partial",
        "sources": {
            "screaming_frog": "complete",
            "gsc": "complete",
            "url_inspection": "skipped",
        },
        "screaming_frog": {
            "status": "complete",
            "source": "screaming_frog_csv",
            "summary": {
                "urls_crawled": 12,
                "client_error_internal_urls": 1,
                "non_indexable_internal_urls": 2,
            },
            "issues": [
                {
                    "id": "client_error_internal_urls",
                    "severity": "high",
                    "title": "Internal URLs returning 4xx errors",
                    "count": 1,
                    "examples": ["https://example.com/broken"],
                }
            ],
        },
        "gsc": {
            "status": "complete",
            "site_url": "sc-domain:example.com",
            "date_range": {"start": "2026-03-01", "end": "2026-05-29"},
            "summary": {
                "top_query_count": 1,
                "top_page_count": 1,
                "ranking_opportunities": 1,
                "high_impression_low_ctr_pages": 1,
                "declining_pages": 0,
            },
            "ranking_opportunities": [
                {
                    "query": "custom homes",
                    "clicks": 12,
                    "impressions": 300,
                    "ctr": 0.04,
                    "position": 8.2,
                }
            ],
            "high_impression_low_ctr_pages": [
                {
                    "page": "https://example.com/",
                    "clicks": 2,
                    "impressions": 500,
                    "ctr": 0.004,
                    "position": 6.1,
                }
            ],
            "declining_pages": [],
            "top_queries": [],
            "top_pages": [],
        },
        "url_inspection": {"status": "skipped", "summary": {}},
    }


def _score_breakdown() -> dict:
    return {
        "scores": {"seo": 76, "uxui": 68, "lead_gen": 72},
        "composite": {"weights": {"seo": 0.45, "uxui": 0.55}},
        "categories": {
            "seo": {
                "rules": [
                    _rule(
                        "seo.title.present_all_pages",
                        "Page titles are present.",
                        "pass",
                        76,
                        76,
                    ),
                    _rule(
                        "seo.meta_description.present_all_pages",
                        "Meta descriptions are present across crawled pages.",
                        "fail",
                        0,
                        24,
                    ),
                    _rule(
                        "seo.schema.present",
                        "Structured data can be read.",
                        "skipped",
                        0,
                        0,
                        weight=6,
                    ),
                ],
                "weights": {"evaluated": 100, "skipped": 6},
            },
            "uxui": {
                "rules": [
                    _rule(
                        "uxui.primary_cta.present",
                        "A primary CTA is present.",
                        "pass",
                        68,
                        68,
                    ),
                    _rule("uxui.forms.present", "The site includes a lead form.", "fail", 0, 32),
                ],
                "weights": {"evaluated": 100, "skipped": 0},
            },
        },
    }


def _rule(
    rule_id: str,
    description: str,
    result: str,
    awarded: float,
    possible: float,
    *,
    weight: float | None = None,
) -> dict:
    return {
        "rule_id": rule_id,
        "description": description,
        "result": result,
        "weight": possible if weight is None else weight,
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
