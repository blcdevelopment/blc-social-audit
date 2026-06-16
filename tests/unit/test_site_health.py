from __future__ import annotations

import asyncio
import functools
import http.server
import ipaddress
import socketserver
import threading
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace

import httpx

from apps.worker.stages import site_health
from apps.worker.stages.external_seo import collect_external_seo_facts
from apps.worker.stages.site_health import collect_site_health_facts


def _settings(**overrides) -> SimpleNamespace:
    values = {
        "site_health_enabled": True,
        "site_health_max_internal_urls": 150,
        "site_health_max_external_urls": 50,
        "site_health_check_external_links": False,
        "site_health_concurrency": 4,
        "site_health_request_timeout_seconds": 5,
        "site_health_total_budget_seconds": 30,
        "site_health_sitemap_max_urls": 100,
        "crawler_user_agent": "test-agent",
        "crawler_allow_private_hosts": True,
        "screaming_frog_enabled": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class _Handler(http.server.BaseHTTPRequestHandler):
    routes = {
        "/ok": (200, b"ok"),
        "/missing": (404, b"not found"),
        "/error": (500, b"boom"),
        "/sitemap.xml": (
            200,
            b'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            b"<url><loc>http://{host}/from-sitemap</loc></url></urlset>",
        ),
        "/from-sitemap": (200, b"sitemap page"),
        "/noindexed": (200, b"hidden"),
    }

    def _respond(self, include_body: bool) -> None:
        status, body = self.routes.get(self.path, (404, b"unknown"))
        body = body.replace(b"{host}", self.headers.get("Host", "").encode())
        self.send_response(status)
        if self.path == "/noindexed":
            self.send_header("X-Robots-Tag", "noindex")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if include_body:
            self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        self._respond(include_body=True)

    def do_HEAD(self) -> None:  # noqa: N802 - http.server API
        self._respond(include_body=False)

    def log_message(self, *args) -> None:
        return


@contextmanager
def _serve() -> Iterator[str]:
    handler = functools.partial(_Handler)
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    port = int(httpd.server_address[1])
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def _seo_facts_with_page_problems() -> dict:
    page = {
        "url": "https://example.com/",
        "title": {"text": "Same Title"},
        "meta_description": {"text": None},
        "headings": {"counts": {"h1": 0}},
        "canonical": None,
        "images": {"missing_alt": 3},
        "robots": {"noindex": True},
    }
    twin = {
        **page,
        "url": "https://example.com/twin",
        "robots": {"noindex": False},
        "images": {"missing_alt": 0},
    }
    return {"status": "complete", "pages": [page, twin]}


def test_disabled_sweep_returns_skipped() -> None:
    facts = collect_site_health_facts(
        url="https://example.com/",
        seo_facts={},
        crawled_pages={},
        rendered_pages=None,
        settings=_settings(site_health_enabled=False),
    )
    assert facts["status"] == "skipped"
    assert facts["reason"] == "disabled"


def test_on_page_checks_count_with_examples() -> None:
    facts = collect_site_health_facts(
        url="https://example.com/",
        seo_facts=_seo_facts_with_page_problems(),
        crawled_pages={"final_url": "https://example.com/"},
        rendered_pages=None,
        settings=_settings(site_health_sitemap_max_urls=0),
    )

    assert facts["status"] == "complete"
    summary = facts["summary"]
    assert summary["duplicate_titles"] == 2
    assert summary["missing_meta_descriptions"] == 2
    assert summary["missing_h1"] == 2
    assert summary["missing_canonicals"] == 2
    assert summary["images_missing_alt"] == 3
    assert summary["non_indexable_internal_urls"] == 1
    issues = {issue["id"]: issue for issue in facts["issues"]}
    assert "https://example.com/" in issues["duplicate_titles"]["examples"]
    assert "https://example.com/" in issues["images_missing_alt"]["examples"]


def test_link_sweep_records_status_codes_and_sitemap_urls() -> None:
    with _serve() as base:
        crawled_pages = {
            "final_url": f"{base}/",
            "pages": [{"url": f"{base}/", "final_url": f"{base}/"}],
            "discovered_links": [
                {"url": f"{base}/ok"},
                {"url": f"{base}/missing"},
                {"url": f"{base}/error"},
                {"url": f"{base}/noindexed"},
            ],
        }
        facts = collect_site_health_facts(
            url=f"{base}/",
            seo_facts={"status": "complete", "pages": []},
            crawled_pages=crawled_pages,
            rendered_pages=None,
            settings=_settings(),
        )

    assert facts["status"] == "complete"
    summary = facts["summary"]
    assert summary["client_error_internal_urls"] == 1
    assert summary["server_error_internal_urls"] == 1
    assert summary["non_indexable_internal_urls"] == 1
    # /ok, /missing, /error, /noindexed and the sitemap-discovered page; the
    # rendered homepage is excluded because the browser already loaded it.
    assert summary["internal_urls_checked"] == 5
    assert summary["sitemap_url_count"] == 1
    issues = {issue["id"]: issue for issue in facts["issues"]}
    assert issues["client_error_internal_urls"]["examples"] == [f"{base}/missing"]
    assert issues["server_error_internal_urls"]["examples"] == [f"{base}/error"]


def test_private_hosts_blocked_without_allowance() -> None:
    facts = collect_site_health_facts(
        url="https://example.com/",
        seo_facts={"status": "complete", "pages": []},
        crawled_pages={
            "final_url": "https://example.com/",
            "discovered_links": [{"url": "http://127.0.0.1:9/internal"}],
        },
        rendered_pages=None,
        settings=_settings(crawler_allow_private_hosts=False, site_health_sitemap_max_urls=0),
    )

    assert facts["status"] == "complete"
    assert facts["summary"]["client_error_internal_urls"] == 0
    assert facts["summary"]["unreachable_internal_urls"] == 0
    assert facts["checks"]["blocked_urls"] == 1


def test_link_sweep_blocks_redirects_to_private_hosts(monkeypatch) -> None:
    monkeypatch.setattr(
        site_health,
        "_resolve_host_ips",
        lambda hostname: [ipaddress.ip_address("93.184.216.34")],
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "http://public.example/redirect"
        return httpx.Response(
            302,
            headers={"Location": "http://127.0.0.1/internal"},
            request=request,
        )

    async def run() -> tuple[dict, dict]:
        summary: dict = {"unreachable_internal_urls": 0}
        examples: dict = defaultdict(list)
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            follow_redirects=False,
        ) as client:
            counters = await site_health._sweep(
                client,
                internal_urls=["http://public.example/redirect"],
                external_urls=[],
                settings=_settings(crawler_allow_private_hosts=False),
                summary=summary,
                examples=examples,
                notes=[],
                host_allowed_cache={},
            )
        return counters, summary

    counters, summary = asyncio.run(run())

    assert counters["blocked"] == 1
    assert counters["internal_checked"] == 0
    assert summary["unreachable_internal_urls"] == 0


def test_sitemap_fetch_blocks_redirects_to_private_hosts(monkeypatch) -> None:
    monkeypatch.setattr(
        site_health,
        "_resolve_host_ips",
        lambda hostname: [ipaddress.ip_address("93.184.216.34")],
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "http://public.example/sitemap.xml"
        return httpx.Response(
            302,
            headers={"Location": "http://127.0.0.1/sitemap.xml"},
            request=request,
        )

    async def run() -> tuple[set[str], str]:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            follow_redirects=False,
        ) as client:
            return await site_health._fetch_sitemap(
                client,
                "http://public.example/sitemap.xml",
                "http://public.example/",
                settings=_settings(crawler_allow_private_hosts=False),
                host_allowed_cache={},
                depth=0,
            )

    urls, status = asyncio.run(run())

    assert urls == set()
    assert status == "blocked_host"


def test_external_seo_uses_site_health_when_screaming_frog_disabled() -> None:
    facts = collect_external_seo_facts(
        url="https://example.com/",
        audit_id="audit-1",
        page_urls=["https://example.com/"],
        settings=_settings(
            screaming_frog_enabled=False,
            site_health_sitemap_max_urls=0,
            google_oauth_client_id="",
            google_oauth_client_secret=None,
        ),
        db=None,
        seo_facts=_seo_facts_with_page_problems(),
        crawled_pages={"final_url": "https://example.com/"},
        rendered_pages=None,
    )

    assert facts["sources"]["technical_crawl"] == "complete"
    assert facts["sources"]["technical_crawl_tool"] == "site_health_sweep"
    assert facts["technical_crawl"]["summary"]["duplicate_titles"] == 2
    assert facts["gsc"]["status"] == "skipped"
