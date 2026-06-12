"""Built-in site health sweep — the Docker-friendly technical crawl.

Produces the same ``technical_crawl`` fact shape as the optional Screaming Frog
CLI collector (see ``technical_crawl_common.py``) without any licensed desktop
tool, JVM, or GUI dependency, so the Technical SEO section of the report works
in the production Docker stack.

What it does, all deterministically given the site's state:

1. On-page checks over the pages the Playwright crawler already rendered
   (missing/duplicate titles and meta descriptions, missing H1s, missing
   canonicals, images without alt text, noindex pages) — computed from the
   stored ``seo_facts``; no new fetching.
2. A status-code sweep (plain HTTP HEAD/GET, no rendering) over every URL the
   crawl discovered — internal links, links found on all rendered pages, and
   the XML sitemap — recording 4xx/5xx/unreachable URLs with examples.

Every number in the output is a count of concrete URLs the sweep actually
checked; example URLs are stored alongside each count so the report can show
where each problem lives. SSRF guards from the crawler are applied to every
URL before it is requested.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse
from xml.etree import ElementTree

import httpx
from bs4 import BeautifulSoup
from celery.exceptions import SoftTimeLimitExceeded

from apps.shared.config import Settings
from apps.worker.stages.crawler import (
    _hostname_is_private,
    _ip_is_blocked,
    _resolve_host_ips,
    is_same_site,
    normalize_url,
)
from apps.worker.stages.technical_crawl_common import empty_summary, issues_from_summary

JsonDict = dict[str, Any]

SITE_HEALTH_SOURCE = "site_health_sweep"
_RETRY_GET_STATUSES = {403, 405, 501}
_MAX_REDIRECTS = 10


class _BlockedHost(RuntimeError):
    """Raised when a request URL or redirect target fails the SSRF host guard."""


def collect_site_health_facts(
    *,
    url: str,
    seo_facts: JsonDict,
    crawled_pages: JsonDict,
    rendered_pages: Sequence[Any] | None,
    settings: Settings,
) -> JsonDict:
    started_at = _utc_now()
    if not settings.site_health_enabled:
        return _skipped("disabled", started_at)

    try:
        return asyncio.run(
            _collect(
                url=url,
                seo_facts=seo_facts,
                crawled_pages=crawled_pages,
                rendered_pages=rendered_pages,
                settings=settings,
                started_at=started_at,
            )
        )
    except SoftTimeLimitExceeded:
        # Celery's soft limit means the whole task is out of budget — the audit
        # must fail fast, not record a "failed sweep" and keep going.
        raise
    except Exception as exc:
        return _failed(_trim(str(exc)), started_at)


async def _collect(
    *,
    url: str,
    seo_facts: JsonDict,
    crawled_pages: JsonDict,
    rendered_pages: Sequence[Any] | None,
    settings: Settings,
    started_at: str,
) -> JsonDict:
    site_url = str(crawled_pages.get("final_url") or url)
    summary = empty_summary()
    examples: dict[str, list[str]] = defaultdict(list)
    notes: list[str] = []

    pages = [page for page in _list(seo_facts.get("pages")) if isinstance(page, dict)]
    _apply_on_page_checks(pages, summary, examples)
    summary["urls_crawled"] = len(pages)
    summary["html_urls_crawled"] = len(pages)

    rendered_urls = _rendered_urls(crawled_pages, rendered_pages)
    internal_urls, external_urls, link_notes = _link_inventory(
        site_url=site_url,
        crawled_pages=crawled_pages,
        rendered_pages=rendered_pages,
        settings=settings,
    )
    notes.extend(link_notes)

    host_allowed_cache: dict[str, bool] = {}
    async with httpx.AsyncClient(
        follow_redirects=False,
        verify=False,
        headers={"User-Agent": settings.crawler_user_agent},
        timeout=settings.site_health_request_timeout_seconds,
    ) as client:
        sitemap_urls, sitemap_status = await _sitemap_urls(
            client, site_url, settings, host_allowed_cache
        )

        internal_urls = sorted(
            (set(internal_urls) | set(sitemap_urls)) - rendered_urls,
        )
        if len(internal_urls) > settings.site_health_max_internal_urls:
            notes.append(
                f"Checked the first {settings.site_health_max_internal_urls} of "
                f"{len(internal_urls)} discovered internal URLs."
            )
            internal_urls = internal_urls[: settings.site_health_max_internal_urls]

        external_urls = sorted(set(external_urls))
        if not settings.site_health_check_external_links:
            external_urls = []
        elif len(external_urls) > settings.site_health_max_external_urls:
            notes.append(
                f"Checked the first {settings.site_health_max_external_urls} of "
                f"{len(external_urls)} outbound links."
            )
            external_urls = external_urls[: settings.site_health_max_external_urls]

        checks = await _sweep(
            client,
            internal_urls=internal_urls,
            external_urls=external_urls,
            settings=settings,
            summary=summary,
            examples=examples,
            notes=notes,
            host_allowed_cache=host_allowed_cache,
        )

    summary["sitemap_url_count"] = len(sitemap_urls)
    summary["internal_urls_checked"] = checks["internal_checked"]
    summary["external_urls_checked"] = checks["external_checked"]
    summary["urls_checked"] = checks["internal_checked"] + checks["external_checked"]

    # Sweep results arrive in network-completion order; sort the example URLs so
    # the same site state renders the same report.
    for key in examples:
        examples[key].sort()

    return {
        "status": "complete",
        "source": SITE_HEALTH_SOURCE,
        "summary": summary,
        "issues": issues_from_summary(summary, examples, source=SITE_HEALTH_SOURCE),
        "checks": {
            "sitemap_status": sitemap_status,
            "internal_urls_checked": checks["internal_checked"],
            "external_urls_checked": checks["external_checked"],
            "blocked_urls": checks["blocked"],
            "rendered_pages_excluded": len(rendered_urls),
        },
        "notes": notes,
        "files": [],
        "started_at": started_at,
        "completed_at": _utc_now(),
    }


def _apply_on_page_checks(
    pages: list[JsonDict],
    summary: JsonDict,
    examples: dict[str, list[str]],
) -> None:
    """Duplicate/missing metadata checks over the rendered pages' stored facts."""
    title_counts: dict[str, int] = defaultdict(int)
    meta_counts: dict[str, int] = defaultdict(int)
    for page in pages:
        title = _clean(_dict(page.get("title")).get("text"))
        if title:
            title_counts[title.lower()] += 1
        meta = _clean(_dict(page.get("meta_description")).get("text"))
        if meta:
            meta_counts[meta.lower()] += 1

    for page in pages:
        address = str(page.get("url") or "")
        title = _clean(_dict(page.get("title")).get("text"))
        meta = _clean(_dict(page.get("meta_description")).get("text"))

        if not title:
            _count(summary, examples, "missing_titles", address)
        elif title_counts[title.lower()] > 1:
            _count(summary, examples, "duplicate_titles", address)

        if not meta:
            _count(summary, examples, "missing_meta_descriptions", address)
        elif meta_counts[meta.lower()] > 1:
            _count(summary, examples, "duplicate_meta_descriptions", address)

        h1_count = _dict(_dict(page.get("headings")).get("counts")).get("h1")
        if not h1_count:
            _count(summary, examples, "missing_h1", address)

        if not _clean(page.get("canonical")):
            _count(summary, examples, "missing_canonicals", address)

        missing_alt = int(_dict(page.get("images")).get("missing_alt") or 0)
        if missing_alt > 0:
            summary["images_missing_alt"] += missing_alt
            _example(examples, "images_missing_alt", address)

        if _dict(page.get("robots")).get("noindex"):
            _count(summary, examples, "non_indexable_internal_urls", address)


def _rendered_urls(crawled_pages: JsonDict, rendered_pages: Sequence[Any] | None) -> set[str]:
    urls: set[str] = set()
    for page in _list(crawled_pages.get("pages")):
        if isinstance(page, dict):
            for key in ("url", "final_url"):
                normalized = normalize_url(str(page.get(key) or ""))
                if normalized:
                    urls.add(normalized)
    for page in rendered_pages or []:
        for key in ("url", "final_url"):
            normalized = normalize_url(str(getattr(page, key, "") or ""))
            if normalized:
                urls.add(normalized)
    return urls


def _link_inventory(
    *,
    site_url: str,
    crawled_pages: JsonDict,
    rendered_pages: Sequence[Any] | None,
    settings: Settings,
) -> tuple[list[str], list[str], list[str]]:
    """Collect internal/external link targets from the crawl.

    On the first audit run the rendered pages (with HTML) are in memory, so links
    from every rendered page are inventoried. On enrichment reruns only the stored
    crawl JSON is available, which keeps the homepage-discovered internal links but
    no outbound links — that limitation is recorded as a note.
    """
    internal: set[str] = set()
    external: set[str] = set()
    notes: list[str] = []

    for link in _list(crawled_pages.get("discovered_links")):
        if isinstance(link, dict):
            normalized = normalize_url(str(link.get("url") or ""))
            if normalized:
                internal.add(normalized)

    if rendered_pages:
        for page in rendered_pages:
            html = str(getattr(page, "html", "") or "")
            base = str(getattr(page, "final_url", "") or getattr(page, "url", "") or site_url)
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")
            for anchor in soup.find_all("a", href=True):
                normalized = normalize_url(str(anchor.get("href", "")).strip(), base)
                if normalized is None:
                    continue
                if is_same_site(site_url, normalized):
                    internal.add(normalized)
                else:
                    external.add(normalized)
    elif settings.site_health_check_external_links:
        notes.append(
            "Outbound links were not rechecked on this enrichment rerun; run a full "
            "audit to refresh outbound link checks."
        )

    return sorted(internal), sorted(external), notes


_SITEMAP_MAX_DEPTH = 2


async def _sitemap_urls(
    client: httpx.AsyncClient,
    site_url: str,
    settings: Settings,
    host_allowed_cache: dict[str, bool],
) -> tuple[list[str], str]:
    if settings.site_health_sitemap_max_urls <= 0:
        return [], "disabled"

    parsed = urlparse(site_url)
    sitemap_url = urlunparse((parsed.scheme, parsed.netloc, "/sitemap.xml", "", "", ""))
    urls, status = await _fetch_sitemap(
        client,
        sitemap_url,
        site_url,
        settings=settings,
        host_allowed_cache=host_allowed_cache,
        depth=0,
    )
    return sorted(urls)[: settings.site_health_sitemap_max_urls], status


async def _fetch_sitemap(
    client: httpx.AsyncClient,
    sitemap_url: str,
    site_url: str,
    *,
    settings: Settings,
    host_allowed_cache: dict[str, bool],
    depth: int,
) -> tuple[set[str], str]:
    # Sitemap-index child URLs come straight from attacker-controllable XML, so
    # every fetch gets the same SSRF host guard as swept URLs, and recursion is
    # depth-capped so a self-referencing index cannot loop forever.
    if depth > _SITEMAP_MAX_DEPTH:
        return set(), "max_depth"
    if not await asyncio.to_thread(_host_allowed, sitemap_url, settings, host_allowed_cache):
        return set(), "blocked_host"
    try:
        response = await _guarded_request(client, "GET", sitemap_url, settings, host_allowed_cache)
    except _BlockedHost:
        return set(), "blocked_host"
    except httpx.HTTPError:
        return set(), "unavailable"
    if response.status_code == 404:
        return set(), "missing"
    if response.status_code >= 400:
        return set(), f"http_{response.status_code}"

    try:
        root = ElementTree.fromstring(response.content)
    except ElementTree.ParseError:
        return set(), "unparseable"

    tag = root.tag.lower()
    locations = [
        " ".join(node.text.split())
        for node in root.iter()
        if node.tag.lower().endswith("loc") and node.text and node.text.strip()
    ]

    urls: set[str] = set()
    if tag.endswith("sitemapindex"):
        for child_url in locations[:3]:
            child_urls, _ = await _fetch_sitemap(
                client,
                child_url,
                site_url,
                settings=settings,
                host_allowed_cache=host_allowed_cache,
                depth=depth + 1,
            )
            urls.update(child_urls)
        return urls, "loaded_index"

    for location in locations:
        normalized = normalize_url(location)
        if normalized and is_same_site(site_url, normalized):
            urls.add(normalized)
    return urls, "loaded"


async def _sweep(
    client: httpx.AsyncClient,
    *,
    internal_urls: list[str],
    external_urls: list[str],
    settings: Settings,
    summary: JsonDict,
    examples: dict[str, list[str]],
    notes: list[str],
    host_allowed_cache: dict[str, bool],
) -> JsonDict:
    semaphore = asyncio.Semaphore(settings.site_health_concurrency)
    deadline = time.monotonic() + settings.site_health_total_budget_seconds
    counters = {"internal_checked": 0, "external_checked": 0, "blocked": 0, "skipped_budget": 0}
    lock = asyncio.Lock()

    async def check(url: str, *, internal: bool) -> None:
        async with semaphore:
            # Budget is checked AFTER acquiring the semaphore: all coroutines are
            # scheduled up front by gather(), so a pre-semaphore check would run at
            # t~0 for every URL and the budget could never actually fire.
            if time.monotonic() > deadline:
                async with lock:
                    counters["skipped_budget"] += 1
                return
            # getaddrinfo is blocking; keep it off the event loop so one slow DNS
            # lookup cannot stall every in-flight request.
            allowed = await asyncio.to_thread(_host_allowed, url, settings, host_allowed_cache)
            if not allowed:
                async with lock:
                    counters["blocked"] += 1
                return
            try:
                status_code, x_robots, error = await _check_url(
                    client, url, settings, host_allowed_cache
                )
            except _BlockedHost:
                async with lock:
                    counters["blocked"] += 1
                return

        async with lock:
            counters["internal_checked" if internal else "external_checked"] += 1
            if error is not None:
                key = "unreachable_internal_urls" if internal else "unreachable_external_urls"
                summary[key] = int(summary.get(key) or 0) + 1
                if internal:
                    # Only internal unreachables surface as a report issue; dead
                    # outbound hosts are often bot-blocking and would over-claim.
                    _example(examples, "unreachable_internal_urls", url)
                return
            if status_code is not None and 400 <= status_code <= 499:
                key = "client_error_internal_urls" if internal else "client_error_external_urls"
                _count(summary, examples, key, url)
            elif status_code is not None and status_code >= 500:
                key = "server_error_internal_urls" if internal else "server_error_external_urls"
                _count(summary, examples, key, url)
            elif internal and x_robots and "noindex" in x_robots.lower():
                _count(summary, examples, "non_indexable_internal_urls", url)

    await asyncio.gather(
        *(check(url, internal=True) for url in internal_urls),
        *(check(url, internal=False) for url in external_urls),
    )

    if counters["skipped_budget"]:
        notes.append(
            f"{counters['skipped_budget']} discovered URLs were not checked because the "
            f"sweep reached its {settings.site_health_total_budget_seconds}s time budget."
        )
    return counters


async def _check_url(
    client: httpx.AsyncClient,
    url: str,
    settings: Settings,
    host_allowed_cache: dict[str, bool],
) -> tuple[int | None, str | None, str | None]:
    """Return (status_code, x_robots_tag_header, error).

    GET is retried only when HEAD specifically is the problem (servers that
    reject or mishandle HEAD). Timeouts and connection failures would fail a GET
    identically, so retrying them would just double the worst-case latency.
    """
    try:
        response = await _guarded_request(client, "HEAD", url, settings, host_allowed_cache)
        if response.status_code in _RETRY_GET_STATUSES:
            response = await _guarded_request(client, "GET", url, settings, host_allowed_cache)
        return response.status_code, response.headers.get("x-robots-tag"), None
    except httpx.RemoteProtocolError:
        try:
            response = await _guarded_request(client, "GET", url, settings, host_allowed_cache)
            return response.status_code, response.headers.get("x-robots-tag"), None
        except httpx.HTTPError as exc:
            return None, None, _trim(str(exc) or exc.__class__.__name__)
    except httpx.HTTPError as exc:
        return None, None, _trim(str(exc) or exc.__class__.__name__)


async def _guarded_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    settings: Settings,
    host_allowed_cache: dict[str, bool],
) -> httpx.Response:
    """Follow redirects only after each target passes the SSRF host guard."""
    current_url = normalize_url(url)
    if current_url is None:
        raise _BlockedHost

    for redirect_count in range(_MAX_REDIRECTS + 1):
        allowed = await asyncio.to_thread(
            _host_allowed,
            current_url,
            settings,
            host_allowed_cache,
        )
        if not allowed:
            raise _BlockedHost

        response = await client.request(method, current_url)
        if not response.is_redirect:
            return response

        location = response.headers.get("location")
        if not location:
            return response
        if redirect_count >= _MAX_REDIRECTS:
            raise httpx.TooManyRedirects(
                f"Exceeded {_MAX_REDIRECTS} redirects while requesting {url}",
                request=response.request,
            )

        next_url = normalize_url(urljoin(str(response.url), location))
        if next_url is None:
            raise _BlockedHost
        current_url = next_url

    raise httpx.TooManyRedirects(
        f"Exceeded {_MAX_REDIRECTS} redirects while requesting {url}",
        request=httpx.Request(method, url),
    )


def _host_allowed(url: str, settings: Settings, cache: dict[str, bool]) -> bool:
    """SSRF guard: never sweep private/loopback/reserved hosts unless explicitly allowed."""
    if settings.crawler_allow_private_hosts:
        return True
    hostname = (urlparse(url).hostname or "").lower()
    if not hostname:
        return False
    if hostname in cache:
        return cache[hostname]

    allowed = not _hostname_is_private(hostname)
    if allowed:
        try:
            resolved = _resolve_host_ips(hostname)
            allowed = bool(resolved) and not any(_ip_is_blocked(ip) for ip in resolved)
        except OSError:
            allowed = False
    cache[hostname] = allowed
    return allowed


def _count(
    summary: JsonDict,
    examples: dict[str, list[str]],
    key: str,
    address: str,
) -> None:
    summary[key] = int(summary.get(key) or 0) + 1
    _example(examples, key, address)


def _example(examples: dict[str, list[str]], key: str, address: str) -> None:
    if address and len(examples[key]) < 10 and address not in examples[key]:
        examples[key].append(address)


def _skipped(reason: str, started_at: str) -> JsonDict:
    return {
        "status": "skipped",
        "source": SITE_HEALTH_SOURCE,
        "reason": reason,
        "summary": {},
        "issues": [],
        "files": [],
        "started_at": started_at,
        "completed_at": _utc_now(),
    }


def _failed(reason: str, started_at: str) -> JsonDict:
    return {
        "status": "failed",
        "source": SITE_HEALTH_SOURCE,
        "error": reason,
        "summary": {},
        "issues": [],
        "files": [],
        "started_at": started_at,
        "completed_at": _utc_now(),
    }


def _dict(value: Any) -> JsonDict:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _clean(value: Any) -> str | None:
    cleaned = " ".join(str(value or "").split())
    return cleaned or None


def _trim(value: str) -> str:
    cleaned = " ".join(value.split())
    return cleaned[:500] or "site health sweep error"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
