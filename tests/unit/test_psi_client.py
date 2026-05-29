from apps.shared.config import Settings
from apps.worker.stages import psi_client
from apps.worker.stages.psi_client import collect_pagespeed_facts, normalize_pagespeed_response


def test_normalize_pagespeed_response_extracts_scores_and_lab_metrics() -> None:
    payload = {
        "id": "https://example.com/",
        "lighthouseResult": {
            "finalDisplayedUrl": "https://example.com/",
            "fetchTime": "2026-05-29T10:00:00Z",
            "categories": {
                "performance": {"score": 0.91},
                "accessibility": {"score": 0.88},
                "best-practices": {"score": 0.97},
                "seo": {"score": 1},
            },
            "audits": {
                "first-contentful-paint": {"numericValue": 1200.4},
                "largest-contentful-paint": {"numericValue": 2100},
                "speed-index": {"numericValue": 1800},
                "total-blocking-time": {"numericValue": 45},
                "cumulative-layout-shift": {"numericValue": 0.02},
                "modern-image-formats": {"score": 0.5},
                "document-title": {"score": 1},
            },
        },
    }

    facts = normalize_pagespeed_response(payload, "mobile")

    assert facts["status"] == "complete"
    assert facts["scores"] == {
        "performance": 91,
        "accessibility": 88,
        "best_practices": 97,
        "seo": 100,
    }
    assert facts["lab_metrics"]["largest_contentful_paint_ms"] == 2100.0
    assert facts["lab_metrics"]["cumulative_layout_shift"] == 0.02
    assert facts["audit_scores"]["modern_image_formats"] == 50
    assert facts["audit_scores"]["document_title"] == 100


def test_collect_pagespeed_facts_skips_without_api_key() -> None:
    settings = Settings(_env_file=None, google_psi_api_key=None)

    facts = collect_pagespeed_facts("https://example.com/", settings)

    assert facts["status"] == "skipped"
    assert facts["reason"] == "missing_google_psi_api_key"
    assert facts["scope"] == "all_crawled_pages"
    assert facts["pages_analyzed"] == 0
    assert facts["pages"] == []
    assert facts["strategies"] == {}


def test_collect_pagespeed_facts_sends_api_key_in_header(monkeypatch) -> None:
    calls = []

    class FakeResponse:
        status_code = 200

        def json(self) -> dict:
            return {
                "id": "https://example.com/",
                "lighthouseResult": {
                    "finalDisplayedUrl": "https://example.com/",
                    "categories": {},
                    "audits": {},
                },
            }

    class FakeClient:
        def __init__(self, timeout) -> None:
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            return None

        def get(self, url, params, headers):
            calls.append({"url": url, "params": params, "headers": headers})
            return FakeResponse()

    monkeypatch.setattr(psi_client.httpx, "Client", FakeClient)
    settings = Settings(
        _env_file=None,
        google_psi_api_key="psi-secret",
        psi_cache_ttl_seconds=0,
        psi_max_retries=1,
    )

    facts = collect_pagespeed_facts("https://example.com/", settings)

    assert facts["status"] == "complete"
    assert facts["pages_analyzed"] == 1
    assert facts["pages"][0]["url"] == "https://example.com/"
    assert len(calls) == 2
    for call in calls:
        assert call["headers"]["x-goog-api-key"] == "psi-secret"
        assert all(name != "key" for name, _ in call["params"])


def test_collect_pagespeed_facts_runs_all_crawled_pages_up_to_psi_max(monkeypatch) -> None:
    calls = []

    def fake_fetch(url: str, strategy: str, settings: Settings) -> dict:
        calls.append((url, strategy))
        performance_scores = {
            "https://example.com/": 95,
            "https://example.com/services": 70,
        }
        return {
            "status": "complete",
            "strategy": strategy,
            "scores": {
                "performance": performance_scores[url],
                "accessibility": None,
                "best_practices": None,
                "seo": None,
            },
        }

    monkeypatch.setattr(psi_client, "_fetch_strategy", fake_fetch)
    settings = Settings(
        _env_file=None,
        google_psi_api_key="psi-secret",
        psi_scope="all_crawled_pages",
        psi_max_pages=2,
        crawler_max_pages=5,
    )

    facts = collect_pagespeed_facts(
        [
            "https://example.com/",
            "https://example.com/services",
            "https://example.com/contact",
        ],
        settings,
    )

    assert facts["status"] == "complete"
    assert facts["scope"] == "all_crawled_pages"
    assert facts["max_pages"] == 2
    assert facts["pages_requested"] == 3
    assert facts["pages_analyzed"] == 2
    assert calls == [
        ("https://example.com/", "mobile"),
        ("https://example.com/", "desktop"),
        ("https://example.com/services", "mobile"),
        ("https://example.com/services", "desktop"),
    ]
    assert facts["summary"]["avg_mobile_performance"] == 83
    assert facts["summary"]["avg_desktop_performance"] == 83
    assert facts["summary"]["slowest_pages"][0]["url"] == "https://example.com/services"


def test_collect_pagespeed_facts_homepage_scope_only_runs_first_page(monkeypatch) -> None:
    calls = []

    def fake_fetch(url: str, strategy: str, settings: Settings) -> dict:
        calls.append((url, strategy))
        return {
            "status": "complete",
            "strategy": strategy,
            "scores": {"performance": 90},
        }

    monkeypatch.setattr(psi_client, "_fetch_strategy", fake_fetch)
    settings = Settings(
        _env_file=None,
        google_psi_api_key="psi-secret",
        psi_scope="homepage",
        psi_max_pages=10,
    )

    facts = collect_pagespeed_facts(
        ["https://example.com/", "https://example.com/contact"],
        settings,
    )

    assert facts["status"] == "complete"
    assert facts["scope"] == "homepage"
    assert facts["max_pages"] == 1
    assert facts["pages_analyzed"] == 1
    assert calls == [
        ("https://example.com/", "mobile"),
        ("https://example.com/", "desktop"),
    ]
