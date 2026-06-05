import json
from pathlib import Path

from apps.worker.stages.extractor_seo import extract_seo_facts
from apps.worker.stages.extractor_uxui import extract_uxui_facts, extract_uxui_facts_for_page

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def _load_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def _load_expected(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _page(name: str, html: str) -> dict:
    return {
        "url": f"https://{name}.example/",
        "final_url": f"https://{name}.example/",
        "status_code": 200,
        "html": html,
    }


def test_extractors_match_strong_site_fixture() -> None:
    html = _load_fixture("strong_site.html")
    expected = _load_expected("strong_site_expected.json")

    seo = extract_seo_facts([_page("strongbuilder", html)])
    uxui = extract_uxui_facts([_page("strongbuilder", html)])

    for key, value in expected["seo"]["summary"].items():
        assert seo["summary"][key] == value
    assert seo["pages"][0]["headings"]["counts"]["h1"] == expected["seo"]["page"]["h1_count"]
    assert seo["pages"][0]["headings"]["counts"]["h2"] == expected["seo"]["page"]["h2_count"]
    assert seo["pages"][0]["links"]["internal_count"] == expected["seo"]["page"]["internal_links"]
    assert (
        seo["pages"][0]["links"]["empty_or_non_http_count"]
        == expected["seo"]["page"]["empty_or_non_http_links"]
    )

    for key, value in expected["uxui"]["summary"].items():
        assert uxui["summary"][key] == value
    assert (
        uxui["pages"][0]["ctas"]["primary"]["text"] == expected["uxui"]["page"]["primary_cta_text"]
    )
    assert uxui["pages"][0]["forms"]["total_field_count"] == expected["uxui"]["page"]["form_fields"]
    assert uxui["pages"][0]["navigation"]["has_nav"] is expected["uxui"]["page"]["has_nav"]


def test_extractors_match_weak_site_fixture() -> None:
    html = _load_fixture("weak_site.html")
    expected = _load_expected("weak_site_expected.json")

    seo = extract_seo_facts([_page("weakbuilder", html)])
    uxui = extract_uxui_facts([_page("weakbuilder", html)])

    for key, value in expected["seo"]["summary"].items():
        assert seo["summary"][key] == value
    assert seo["pages"][0]["headings"]["counts"]["h1"] == expected["seo"]["page"]["h1_count"]
    assert seo["pages"][0]["links"]["internal_count"] == expected["seo"]["page"]["internal_links"]
    assert (
        seo["pages"][0]["links"]["empty_or_non_http_count"]
        == expected["seo"]["page"]["empty_or_non_http_links"]
    )
    assert seo["pages"][0]["images"]["missing_alt"] == expected["seo"]["page"]["missing_image_alts"]

    for key, value in expected["uxui"]["summary"].items():
        assert uxui["summary"][key] == value
    assert uxui["pages"][0]["lead_capture"]["has_form"] is expected["uxui"]["page"]["has_form"]
    assert (
        uxui["pages"][0]["lead_capture"]["has_direct_contact"]
        is expected["uxui"]["page"]["has_direct_contact"]
    )
    assert uxui["pages"][0]["navigation"]["has_nav"] is expected["uxui"]["page"]["has_nav"]


def test_uxui_required_field_count_ignores_aria_required_false() -> None:
    html = """
    <form>
      <input type="text" name="name" required>
      <input type="email" name="email" aria-required="true">
      <input type="text" name="company" aria-required="false">
      <button type="submit">Send</button>
    </form>
    """
    facts = extract_uxui_facts_for_page(_page("forms", html))
    form = facts["forms"]["items"][0]

    assert form["field_count"] == 3
    # name (required) + email (aria-required="true"); company (aria-required="false") excluded.
    assert form["required_field_count"] == 2


def test_extractors_handle_malformed_html_fixture() -> None:
    html = _load_fixture("malformed_site.html")
    expected = _load_expected("malformed_site_expected.json")

    seo = extract_seo_facts([_page("malformedbuilder", html)])
    uxui = extract_uxui_facts([_page("malformedbuilder", html)])

    assert seo["status"] == expected["seo"]["status"]
    assert seo["pages_analyzed"] == expected["seo"]["pages_analyzed"]
    assert uxui["status"] == expected["uxui"]["status"]
    assert uxui["pages_analyzed"] == expected["uxui"]["pages_analyzed"]
