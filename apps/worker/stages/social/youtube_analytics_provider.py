"""YouTube Analytics API v2 backend — PRIVATE channel-owner metrics (SAE-15, Wave 3 "connected").

Unlike the public YouTube Data API (``youtube_provider``), this returns owner-only analytics —
watch time, average view duration/percentage, subscriber gain/loss, traffic sources, and viewer
demographics — for a channel whose owner connected via Google OAuth (scope
``yt-analytics.readonly``; ``ids=channel==MINE``). The access token is obtained + refreshed by the
EXISTING Google OAuth machinery (``google_search_console.refresh_google_access_token``) — no new
token store, no migration.

``fetch_channel_analytics`` is network-only and returns raw report payloads (or ``None`` on any
failure, so the caller degrades gracefully). ``normalize_youtube_analytics`` is pure and
unit-testable from a fixture. NOTE: this only yields data once a real channel owner has connected —
it cannot run on a cold prospect (that's the public path), and the live flow needs a configured
Google OAuth app + a granted token to exercise end to end.
"""

from __future__ import annotations

from typing import Any

import httpx

from apps.shared.config import Settings

JsonDict = dict[str, Any]

_REPORTS_ENDPOINT = "https://youtubeanalytics.googleapis.com/v2/reports"

# The three reports we pull for a connected channel (owner consent, ids=channel==MINE).
_ENGAGEMENT_METRICS = (
    "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,"
    "subscribersGained,subscribersLost"
)


def _query(access_token: str, params: dict[str, str], settings: Settings) -> JsonDict | None:
    try:
        response = httpx.get(
            _REPORTS_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
            timeout=settings.youtube_timeout_seconds,
        )
        if response.status_code >= 400:
            return None
        payload = response.json()
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def fetch_channel_analytics(
    access_token: str, *, start_date: str, end_date: str, settings: Settings
) -> JsonDict | None:
    """Fetch the engagement, traffic-source, and demographics reports for the owner's channel.

    Returns ``{"engagement", "traffic", "demographics"}`` (each a raw reports.query payload), or
    ``None`` when there is no token or the engagement query fails (traffic/demographics are
    best-effort — a channel below YouTube's minimum-data threshold simply omits them).
    """
    if not access_token:
        return None
    base = {"ids": "channel==MINE", "startDate": start_date, "endDate": end_date}
    engagement = _query(access_token, {**base, "metrics": _ENGAGEMENT_METRICS}, settings)
    if engagement is None:
        return None
    traffic = _query(
        access_token,
        {**base, "metrics": "views", "dimensions": "insightTrafficSourceType", "sort": "-views"},
        settings,
    )
    demographics = _query(
        access_token,
        {**base, "metrics": "viewerPercentage", "dimensions": "ageGroup,gender"},
        settings,
    )
    return {"engagement": engagement, "traffic": traffic, "demographics": demographics}


def _rows(report: Any) -> list[list[Any]]:
    rows = report.get("rows") if isinstance(report, dict) else None
    return [r for r in rows if isinstance(r, list)] if isinstance(rows, list) else []


def _headers(report: Any) -> list[str]:
    cols = report.get("columnHeaders") if isinstance(report, dict) else None
    if not isinstance(cols, list):
        return []
    return [c.get("name", "") if isinstance(c, dict) else "" for c in cols]


def _num(value: Any) -> float | int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value) if float(value).is_integer() else round(float(value), 2)


def normalize_youtube_analytics(reports: JsonDict) -> JsonDict:
    """Pure normalization of the raw reports.query payloads into flat connected-YouTube facts."""
    reports = reports if isinstance(reports, dict) else {}
    engagement = reports.get("engagement") or {}
    eng_rows = _rows(engagement)
    named = dict(zip(_headers(engagement), eng_rows[0], strict=False)) if eng_rows else {}

    traffic = [
        {"source": str(row[0]), "views": _num(row[1])}
        for row in _rows(reports.get("traffic"))
        if len(row) >= 2
    ]
    demographics = [
        {"age_group": str(row[0]), "gender": str(row[1]), "viewer_pct": _num(row[2])}
        for row in _rows(reports.get("demographics"))
        if len(row) >= 3
    ]
    return {
        "views": _num(named.get("views")),
        "estimated_minutes_watched": _num(named.get("estimatedMinutesWatched")),
        "avg_view_duration_seconds": _num(named.get("averageViewDuration")),
        "avg_view_percentage": _num(named.get("averageViewPercentage")),
        "subscribers_gained": _num(named.get("subscribersGained")),
        "subscribers_lost": _num(named.get("subscribersLost")),
        "traffic_sources": traffic,
        "demographics": demographics,
    }
