import ipaddress

import pytest

from apps.worker.stages import crawler
from apps.worker.stages.crawler import (
    CrawlerError,
    assert_crawlable_url,
    discover_internal_links,
    is_failed_http_status,
    is_same_site,
    normalize_url,
)


def test_normalize_url_removes_fragments_and_default_ports() -> None:
    assert normalize_url("HTTPS://Example.com:443/about/#team") == "https://example.com/about"
    assert normalize_url("/services#top", "https://example.com/") == "https://example.com/services"
    assert normalize_url("mailto:hello@example.com", "https://example.com/") is None
    assert normalize_url("https://user:pass@example.com/") is None
    assert normalize_url("https://example.com:bad/") is None


def test_same_site_allows_www_apex_pair_but_rejects_external_hosts() -> None:
    assert is_same_site("https://example.com", "https://www.example.com/about") is True
    assert is_same_site("https://example.com", "https://other.example.com/about") is False


def test_discover_internal_links_scores_nav_links_and_excludes_external_links() -> None:
    html = """
    <header><nav>
      <a href="/services">Services</a>
      <a href="/contact">Contact</a>
    </nav></header>
    <main class="hero">
      <a href="/services">Our Services</a>
      <a href="https://external.example/">External</a>
    </main>
    <footer><a href="/privacy">Privacy</a></footer>
    """

    links = discover_internal_links(html, "https://www.example.com/")

    assert [link.url for link in links] == [
        "https://www.example.com/services",
        "https://www.example.com/contact",
        "https://www.example.com/privacy",
    ]
    assert "nav" in links[0].sources


def test_private_hosts_are_blocked_by_default() -> None:
    with pytest.raises(CrawlerError):
        assert_crawlable_url("http://127.0.0.1:8000", allow_private_hosts=False)

    assert_crawlable_url("http://127.0.0.1:8000", allow_private_hosts=True)


def test_public_hostname_resolving_to_private_ip_is_blocked(monkeypatch) -> None:
    # DNS-rebinding / metadata SSRF: a public name that resolves to a private IP.
    monkeypatch.setattr(
        crawler, "_resolve_host_ips", lambda hostname: [ipaddress.ip_address("169.254.169.254")]
    )
    with pytest.raises(CrawlerError, match="private"):
        assert_crawlable_url("https://evil.example.com/", allow_private_hosts=False)


def test_public_hostname_resolving_to_public_ip_is_allowed(monkeypatch) -> None:
    monkeypatch.setattr(
        crawler, "_resolve_host_ips", lambda hostname: [ipaddress.ip_address("93.184.216.34")]
    )
    assert_crawlable_url("https://example.com/", allow_private_hosts=False)


def test_unresolvable_host_is_blocked(monkeypatch) -> None:
    def _raise(hostname: str):
        raise OSError("Name or service not known")

    monkeypatch.setattr(crawler, "_resolve_host_ips", _raise)
    with pytest.raises(CrawlerError, match="resolve"):
        assert_crawlable_url("https://does-not-exist.example/", allow_private_hosts=False)


def test_failed_http_status_detection() -> None:
    assert is_failed_http_status(None) is False
    assert is_failed_http_status(200) is False
    assert is_failed_http_status(399) is False
    assert is_failed_http_status(400) is True
    assert is_failed_http_status(500) is True
