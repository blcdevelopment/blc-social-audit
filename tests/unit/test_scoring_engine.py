import json
from pathlib import Path

from apps.shared.config import Settings
from apps.worker.stages.extractor_seo import extract_seo_facts
from apps.worker.stages.extractor_uxui import extract_uxui_facts
from apps.worker.stages.scoring import (
    Rubric,
    RubricRule,
    load_composite_rubric,
    load_rubric,
    score_audit,
    score_category,
)


def test_data_sufficient_distinguishes_all_skip_from_genuine_zero() -> None:
    # Every rule skips (fact absent + skip_if_missing): score is 0 only because nothing was
    # scorable, so data_sufficient must be False (not indistinguishable from a real 0).
    all_skip = Rubric(
        version="t-skip",
        category="seo",
        max_score=100,
        normalization="rescale_to_max",
        rules=[
            RubricRule(
                id="seo.absent",
                description="needs a fact that is absent",
                weight=10,
                fact_path="seo.summary.absent",
                evaluator="boolean",
                skip_if_missing=True,
            )
        ],
    )
    out = score_category({"seo": {"summary": {}}}, all_skip)
    assert out["score"] == 0
    assert out["data_sufficient"] is False

    # A scorable rule => data_sufficient True and a real score.
    scored = Rubric(
        version="t-ok",
        category="seo",
        max_score=100,
        normalization="rescale_to_max",
        rules=[
            RubricRule(
                id="seo.present",
                description="present fact",
                weight=10,
                fact_path="seo.summary.present",
                evaluator="boolean",
            )
        ],
    )
    out2 = score_category({"seo": {"summary": {"present": True}}}, scored)
    assert out2["score"] == 100
    assert out2["data_sufficient"] is True


FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def _load_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def _page(name: str, html: str) -> dict:
    return {
        "url": f"https://{name}.example/",
        "final_url": f"https://{name}.example/",
        "status_code": 200,
        "html": html,
    }


def _psi(mobile: int | None = None, desktop: int | None = None) -> dict:
    return {
        "status": "complete" if mobile is not None and desktop is not None else "skipped",
        "summary": {
            "avg_mobile_performance": mobile,
            "avg_desktop_performance": desktop,
        },
    }


def _facts_for_fixture(name: str) -> tuple[dict, dict]:
    html = _load_fixture(name)
    pages = [_page(name.removesuffix("_site.html"), html)]
    return extract_seo_facts(pages), extract_uxui_facts(pages)


def test_phase_1_rubrics_load_and_validate() -> None:
    settings = Settings(_env_file=None)

    seo = load_rubric(settings.rubric_seo_path)
    uxui = load_rubric(settings.rubric_uxui_path)
    composite = load_composite_rubric(settings.rubric_composite_path)

    assert seo.version == "phase2-seo-v11"
    assert uxui.version == "phase1-uxui-v2"
    assert sum(rule.weight for rule in seo.rules) == 261
    assert sum(rule.weight for rule in uxui.rules) == 100
    assert composite.weights == {"seo": 0.45, "uxui": 0.55}


def test_scoring_calibrates_strong_and_weak_fixture_sites() -> None:
    settings = Settings(_env_file=None)
    strong_seo, strong_uxui = _facts_for_fixture("strong_site.html")
    weak_seo, weak_uxui = _facts_for_fixture("weak_site.html")

    strong = score_audit(strong_seo, strong_uxui, _psi(92, 96), settings)
    weak = score_audit(weak_seo, weak_uxui, _psi(35, 50), settings)

    assert strong["scores"]["seo"] >= 85
    assert strong["scores"]["uxui"] >= 85
    assert strong["scores"]["lead_gen"] >= 85
    assert weak["scores"]["seo"] <= 35
    assert weak["scores"]["uxui"] <= 30
    assert weak["scores"]["lead_gen"] <= 35


def test_scoring_is_reproducible_for_same_facts() -> None:
    settings = Settings(_env_file=None)
    seo, uxui = _facts_for_fixture("strong_site.html")

    first = score_audit(seo, uxui, _psi(), settings)
    second = score_audit(seo, uxui, _psi(), settings)

    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    # The CrUX CWV rules (7+6+5) and the 2 technical-crawl rules added in P2-16 (canonicals 5 +
    # redirect_chains 5) all skip_if_missing when the fixture carries no field/external-crawl data.
    # The P2-13 AEO rules are NOT skip_if_missing (they read on-page facts always present), so they
    # are scored here. The P2-15 a11y unique_referenced_ids rule (weight 2) skips on this fixture
    # because it uses no id-referencing label/ARIA attributes, so the skipped total is 106 + 2.
    assert first["categories"]["seo"]["weights"]["skipped"] == 108
    assert first["categories"]["seo"]["score"] >= 85


def test_scoring_does_not_treat_failed_technical_crawl_zero_summary_as_clean() -> None:
    settings = Settings(_env_file=None)
    seo, uxui = _facts_for_fixture("strong_site.html")
    legacy_failed_external = {
        "technical_crawl": {
            "status": "failed",
            "summary": _technical_crawl_zero_summary(),
            "issues": [],
        },
        "gsc": {"status": "skipped", "summary": {}},
        "url_inspection": {"status": "skipped", "summary": {}},
    }

    scored = score_audit(
        seo,
        uxui,
        _psi(),
        settings,
        external_seo_facts=legacy_failed_external,
    )

    rules = {
        rule["rule_id"]: rule
        for rule in scored["categories"]["seo"]["rules"]
        if rule["rule_id"].startswith("seo.technical_crawl.")
    }
    assert rules["seo.technical_crawl.no_broken_internal_urls"]["result"] == "skipped"
    assert rules["seo.technical_crawl.missing_titles"]["result"] == "skipped"
    assert rules["seo.technical_crawl.missing_meta_descriptions"]["result"] == "skipped"


def test_scoring_uses_complete_technical_crawl_zero_summary() -> None:
    settings = Settings(_env_file=None)
    seo, uxui = _facts_for_fixture("strong_site.html")
    complete_external = {
        "technical_crawl": {
            "status": "complete",
            "summary": _technical_crawl_zero_summary(),
            "issues": [],
        },
        "gsc": {"status": "skipped", "summary": {}},
        "url_inspection": {"status": "skipped", "summary": {}},
    }

    scored = score_audit(
        seo,
        uxui,
        _psi(),
        settings,
        external_seo_facts=complete_external,
    )

    rules = {
        rule["rule_id"]: rule
        for rule in scored["categories"]["seo"]["rules"]
        if rule["rule_id"].startswith("seo.technical_crawl.")
    }
    assert rules["seo.technical_crawl.no_broken_internal_urls"]["result"] == "pass"
    assert rules["seo.technical_crawl.missing_titles"]["result"] == "pass"
    assert rules["seo.technical_crawl.missing_meta_descriptions"]["result"] == "pass"


def _technical_crawl_zero_summary() -> dict:
    return {
        "urls_crawled": 0,
        "html_urls_crawled": 0,
        "client_error_internal_urls": 0,
        "server_error_internal_urls": 0,
        "client_error_external_urls": 0,
        "server_error_external_urls": 0,
        "non_indexable_internal_urls": 0,
        "missing_titles": 0,
        "duplicate_titles": 0,
        "missing_meta_descriptions": 0,
        "duplicate_meta_descriptions": 0,
        "missing_h1": 0,
        "images_missing_alt": 0,
        "missing_canonicals": 0,
    }
