import json
from pathlib import Path

from apps.shared.config import Settings
from apps.worker.stages.extractor_seo import extract_seo_facts
from apps.worker.stages.extractor_uxui import extract_uxui_facts
from apps.worker.stages.scoring import load_composite_rubric, load_rubric, score_audit

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

    assert seo.version == "phase1-seo-v1"
    assert uxui.version == "phase1-uxui-v1"
    assert sum(rule.weight for rule in seo.rules) == 100
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
    assert first["categories"]["seo"]["weights"]["skipped"] == 20
    assert first["categories"]["seo"]["score"] >= 85
