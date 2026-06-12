from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from apps.shared.config import Settings
from apps.worker.stages.google_search_console import collect_google_search_console_facts
from apps.worker.stages.screaming_frog import collect_screaming_frog_facts

JsonDict = dict[str, Any]


def collect_external_seo_facts(
    *,
    url: str,
    audit_id: str,
    page_urls: list[str],
    settings: Settings,
    db: Session,
) -> JsonDict:
    screaming_frog = collect_screaming_frog_facts(url, audit_id, settings)
    google = collect_google_search_console_facts(
        url=url,
        page_urls=page_urls,
        settings=settings,
        db=db,
    )
    return {
        "status": _combined_status(screaming_frog, google.get("gsc"), google.get("url_inspection")),
        "sources": {
            "screaming_frog": screaming_frog.get("status"),
            "gsc": google.get("gsc", {}).get("status"),
            "url_inspection": google.get("url_inspection", {}).get("status"),
        },
        "screaming_frog": screaming_frog,
        "gsc": google.get("gsc", {}),
        "url_inspection": google.get("url_inspection", {}),
    }


def empty_external_seo_facts(reason: str = "not_collected") -> JsonDict:
    skipped = {"status": "skipped", "reason": reason, "summary": {}, "issues": []}
    return {
        "status": "skipped",
        "sources": {
            "screaming_frog": "skipped",
            "gsc": "skipped",
            "url_inspection": "skipped",
        },
        "screaming_frog": skipped,
        "gsc": skipped,
        "url_inspection": skipped,
    }


def _combined_status(*payloads: JsonDict | None) -> str:
    statuses = [str(payload.get("status")) for payload in payloads if isinstance(payload, dict)]
    if any(status == "complete" for status in statuses):
        if any(status in {"failed", "skipped"} for status in statuses):
            return "partial"
        return "complete"
    if any(status == "failed" for status in statuses):
        return "failed"
    return "skipped"
