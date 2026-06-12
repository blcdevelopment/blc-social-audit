from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy.orm import Session

from apps.shared.config import Settings
from apps.worker.stages.google_search_console import collect_google_search_console_facts
from apps.worker.stages.screaming_frog import collect_screaming_frog_facts
from apps.worker.stages.site_health import collect_site_health_facts

JsonDict = dict[str, Any]


def collect_external_seo_facts(
    *,
    url: str,
    audit_id: str,
    page_urls: list[str],
    settings: Settings,
    db: Session,
    seo_facts: JsonDict | None = None,
    crawled_pages: JsonDict | None = None,
    rendered_pages: Sequence[Any] | None = None,
) -> JsonDict:
    technical_crawl = _collect_technical_crawl(
        url=url,
        audit_id=audit_id,
        settings=settings,
        seo_facts=seo_facts or {},
        crawled_pages=crawled_pages or {},
        rendered_pages=rendered_pages,
    )
    google = collect_google_search_console_facts(
        url=url,
        page_urls=page_urls,
        settings=settings,
        db=db,
    )
    return {
        "status": _combined_status(
            technical_crawl,
            google.get("gsc"),
            google.get("url_inspection"),
        ),
        "sources": {
            "technical_crawl": technical_crawl.get("status"),
            "technical_crawl_tool": technical_crawl.get("source"),
            "gsc": google.get("gsc", {}).get("status"),
            "url_inspection": google.get("url_inspection", {}).get("status"),
        },
        "technical_crawl": technical_crawl,
        "gsc": google.get("gsc", {}),
        "url_inspection": google.get("url_inspection", {}),
    }


def _collect_technical_crawl(
    *,
    url: str,
    audit_id: str,
    settings: Settings,
    seo_facts: JsonDict,
    crawled_pages: JsonDict,
    rendered_pages: Sequence[Any] | None,
) -> JsonDict:
    """Fill the technical crawl slot: Screaming Frog when licensed/enabled, else the
    built-in site health sweep. Both emit the same summary keys and issue ids."""
    screaming_frog: JsonDict | None = None
    if settings.screaming_frog_enabled:
        screaming_frog = collect_screaming_frog_facts(url, audit_id, settings)
        if screaming_frog.get("status") == "complete":
            return screaming_frog

    site_health = collect_site_health_facts(
        url=url,
        seo_facts=seo_facts,
        crawled_pages=crawled_pages,
        rendered_pages=rendered_pages,
        settings=settings,
    )
    if screaming_frog is not None and site_health.get("status") != "complete":
        # Neither tool produced usable data — report the Screaming Frog attempt,
        # which the operator explicitly enabled.
        return screaming_frog
    if screaming_frog is not None:
        site_health["screaming_frog_attempt"] = {
            "status": screaming_frog.get("status"),
            "error": screaming_frog.get("error") or screaming_frog.get("reason"),
        }
    return site_health


def empty_external_seo_facts(reason: str = "not_collected") -> JsonDict:
    skipped = {"status": "skipped", "reason": reason, "summary": {}, "issues": []}
    return {
        "status": "skipped",
        "sources": {
            "technical_crawl": "skipped",
            "technical_crawl_tool": None,
            "gsc": "skipped",
            "url_inspection": "skipped",
        },
        "technical_crawl": skipped,
        "gsc": skipped,
        "url_inspection": skipped,
    }


def _combined_status(*payloads: JsonDict | None) -> str:
    statuses = [str(payload.get("status")) for payload in payloads if isinstance(payload, dict)]
    if any(status == "complete" for status in statuses):
        if any(status in {"failed", "skipped", "partial"} for status in statuses):
            return "partial"
        return "complete"
    if any(status == "partial" for status in statuses):
        return "partial"
    if any(status == "failed" for status in statuses):
        return "failed"
    return "skipped"
