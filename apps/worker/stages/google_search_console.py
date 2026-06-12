from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from urllib.parse import quote, urlencode, urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.shared.config import Settings
from apps.shared.models import GoogleSearchConsoleConnection

JsonDict = dict[str, Any]

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"
SITES_ENDPOINT = "https://www.googleapis.com/webmasters/v3/sites"
URL_INSPECTION_ENDPOINT = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
GSC_SCOPES = (
    "openid",
    "email",
    "https://www.googleapis.com/auth/webmasters.readonly",
)


def build_google_oauth_url(settings: Settings, state: str) -> str:
    params = {
        "client_id": settings.google_oauth_client_id,
        "redirect_uri": settings.google_oauth_redirect_uri,
        "response_type": "code",
        "scope": " ".join(GSC_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_ENDPOINT}?{urlencode(params)}"


def google_oauth_configured(settings: Settings) -> bool:
    return bool(
        settings.google_oauth_client_id
        and settings.google_oauth_client_secret
        and settings.google_oauth_client_secret.get_secret_value()
    )


def exchange_google_oauth_code(code: str, settings: Settings) -> JsonDict:
    secret = settings.google_oauth_client_secret.get_secret_value()
    response = httpx.post(
        TOKEN_ENDPOINT,
        data={
            "code": code,
            "client_id": settings.google_oauth_client_id,
            "client_secret": secret,
            "redirect_uri": settings.google_oauth_redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def refresh_google_access_token(
    connection: GoogleSearchConsoleConnection,
    settings: Settings,
    db: Session,
) -> str:
    if not connection.refresh_token:
        raise ValueError("Google connection does not have a refresh token.")
    secret = settings.google_oauth_client_secret.get_secret_value()
    response = httpx.post(
        TOKEN_ENDPOINT,
        data={
            "client_id": settings.google_oauth_client_id,
            "client_secret": secret,
            "refresh_token": connection.refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    response.raise_for_status()
    token_payload = response.json()
    access_token = str(token_payload["access_token"])
    connection.access_token = access_token
    connection.token_expires_at = _expires_at(token_payload)
    db.commit()
    db.refresh(connection)
    return access_token


def ensure_google_access_token(
    connection: GoogleSearchConsoleConnection,
    settings: Settings,
    db: Session,
) -> str:
    expires_at = connection.token_expires_at
    if (
        connection.access_token
        and isinstance(expires_at, datetime)
        and expires_at > datetime.now(UTC) + timedelta(seconds=60)
    ):
        return connection.access_token
    return refresh_google_access_token(connection, settings, db)


def google_userinfo(access_token: str) -> JsonDict:
    response = httpx.get(
        USERINFO_ENDPOINT,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def list_search_console_sites(access_token: str) -> list[JsonDict]:
    response = httpx.get(
        SITES_ENDPOINT,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    response.raise_for_status()
    return [
        {"siteUrl": str(item.get("siteUrl")), "permissionLevel": item.get("permissionLevel")}
        for item in response.json().get("siteEntry", [])
        if item.get("siteUrl")
    ]


def upsert_google_connection(
    db: Session,
    *,
    account_email: str,
    token_payload: JsonDict,
    properties: list[JsonDict],
) -> GoogleSearchConsoleConnection:
    connection = db.scalar(
        select(GoogleSearchConsoleConnection).where(
            GoogleSearchConsoleConnection.account_email == account_email
        )
    )
    if connection is None:
        connection = GoogleSearchConsoleConnection(
            account_email=account_email,
            scopes={"values": list(GSC_SCOPES)},
            properties={"siteEntry": properties},
        )
        db.add(connection)

    connection.access_token = str(token_payload.get("access_token") or "")
    refresh_token = token_payload.get("refresh_token")
    if refresh_token:
        connection.refresh_token = str(refresh_token)
    connection.token_expires_at = _expires_at(token_payload)
    connection.scopes = {"values": list(GSC_SCOPES)}
    connection.properties = {"siteEntry": properties}
    db.commit()
    db.refresh(connection)
    return connection


def latest_google_connection(db: Session) -> GoogleSearchConsoleConnection | None:
    return db.scalar(
        select(GoogleSearchConsoleConnection).order_by(
            GoogleSearchConsoleConnection.created_at.desc()
        )
    )


def collect_google_search_console_facts(
    *,
    url: str,
    page_urls: list[str],
    settings: Settings,
    db: Session,
) -> JsonDict:
    started_at = _utc_now()
    if not google_oauth_configured(settings):
        return _external_google_payload(
            gsc=_skipped("oauth_not_configured", started_at),
            url_inspection=_skipped("oauth_not_configured", started_at),
        )

    connection = latest_google_connection(db)
    if connection is None:
        return _external_google_payload(
            gsc=_skipped("no_google_connection", started_at),
            url_inspection=_skipped("no_google_connection", started_at),
        )

    try:
        access_token = ensure_google_access_token(connection, settings, db)
        properties = _connection_properties(connection)
        if not properties:
            properties = list_search_console_sites(access_token)
            connection.properties = {"siteEntry": properties}
            db.commit()
            db.refresh(connection)
        matched_property = match_search_console_property(url, properties)
        if matched_property is None:
            return _external_google_payload(
                gsc=_skipped("no_matching_search_console_property", started_at),
                url_inspection=_skipped("no_matching_search_console_property", started_at),
            )

        gsc = collect_search_analytics(
            access_token=access_token,
            site_url=str(matched_property["siteUrl"]),
            settings=settings,
            started_at=started_at,
        )
        inspected = collect_url_inspection(
            access_token=access_token,
            site_url=str(matched_property["siteUrl"]),
            urls=_priority_urls(url, page_urls, settings.url_inspection_max_urls),
            started_at=started_at,
        )
        return _external_google_payload(gsc=gsc, url_inspection=inspected)
    except Exception as exc:  # noqa: BLE001 - enrichment must not fail the audit
        return _external_google_payload(
            gsc=_failed(str(exc), started_at),
            url_inspection=_failed(str(exc), started_at),
        )


def collect_search_analytics(
    *,
    access_token: str,
    site_url: str,
    settings: Settings,
    started_at: str,
) -> JsonDict:
    end_date = date.today() - timedelta(days=3)
    start_date = end_date - timedelta(days=settings.gsc_default_date_range_days)
    previous_end = start_date - timedelta(days=1)
    previous_start = previous_end - timedelta(days=settings.gsc_default_date_range_days)

    top_queries = query_search_analytics(
        access_token,
        site_url,
        start_date=start_date,
        end_date=end_date,
        dimensions=["query"],
        row_limit=min(settings.gsc_row_limit, 500),
    )
    top_pages = query_search_analytics(
        access_token,
        site_url,
        start_date=start_date,
        end_date=end_date,
        dimensions=["page"],
        row_limit=min(settings.gsc_row_limit, 500),
    )
    previous_pages = query_search_analytics(
        access_token,
        site_url,
        start_date=previous_start,
        end_date=previous_end,
        dimensions=["page"],
        row_limit=min(settings.gsc_row_limit, 500),
    )

    opportunities = _ranking_opportunities(top_queries)
    low_ctr_pages = _low_ctr_pages(top_pages)
    declining_pages = _declining_pages(top_pages, previous_pages)
    return {
        "status": "complete",
        "source": "search_console_api",
        "site_url": site_url,
        "date_range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "summary": {
            "top_query_count": len(top_queries),
            "top_page_count": len(top_pages),
            "ranking_opportunities": len(opportunities),
            "high_impression_low_ctr_pages": len(low_ctr_pages),
            "declining_pages": len(declining_pages),
        },
        "top_queries": top_queries[:50],
        "top_pages": top_pages[:50],
        "ranking_opportunities": opportunities[:25],
        "high_impression_low_ctr_pages": low_ctr_pages[:25],
        "declining_pages": declining_pages[:25],
        "started_at": started_at,
        "completed_at": _utc_now(),
    }


def query_search_analytics(
    access_token: str,
    site_url: str,
    *,
    start_date: date,
    end_date: date,
    dimensions: list[str],
    row_limit: int,
) -> list[JsonDict]:
    encoded_site = quote(site_url, safe="")
    response = httpx.post(
        f"https://www.googleapis.com/webmasters/v3/sites/{encoded_site}/searchAnalytics/query",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "dimensions": dimensions,
            "type": "web",
            "rowLimit": row_limit,
        },
        timeout=45,
    )
    response.raise_for_status()
    return [_normalize_search_row(row, dimensions) for row in response.json().get("rows", [])]


def collect_url_inspection(
    *,
    access_token: str,
    site_url: str,
    urls: list[str],
    started_at: str,
) -> JsonDict:
    if not urls:
        return _skipped("no_urls_to_inspect", started_at)

    inspections = []
    for url in urls:
        try:
            response = httpx.post(
                URL_INSPECTION_ENDPOINT,
                headers={"Authorization": f"Bearer {access_token}"},
                json={"inspectionUrl": url, "siteUrl": site_url},
                timeout=45,
            )
            if response.status_code >= 400:
                inspections.append({"url": url, "status": "failed", "error": response.text[:300]})
                continue
            inspections.append(_normalize_inspection(url, response.json()))
        except Exception as exc:  # noqa: BLE001 - per-URL failure is data, not task failure
            inspections.append({"url": url, "status": "failed", "error": str(exc)[:300]})

    not_on_google = sum(1 for item in inspections if item.get("on_google") is False)
    return {
        "status": "complete",
        "source": "url_inspection_api",
        "site_url": site_url,
        "summary": {
            "urls_requested": len(urls),
            "urls_inspected": len(inspections),
            "not_on_google": not_on_google,
            "failed": sum(1 for item in inspections if item.get("status") == "failed"),
        },
        "items": inspections,
        "started_at": started_at,
        "completed_at": _utc_now(),
    }


def match_search_console_property(url: str, properties: list[JsonDict]) -> JsonDict | None:
    normalized_url = _normalized_url_for_match(url)
    parsed = urlparse(normalized_url)
    host = (parsed.hostname or "").lower().removeprefix("www.")

    url_prefix_matches = [
        item
        for item in properties
        if str(item.get("siteUrl") or "").startswith(("http://", "https://"))
        and normalized_url.startswith(str(item.get("siteUrl")))
    ]
    if url_prefix_matches:
        return max(url_prefix_matches, key=lambda item: len(str(item["siteUrl"])))

    domain_matches = []
    for item in properties:
        site_url = str(item.get("siteUrl") or "")
        if not site_url.startswith("sc-domain:"):
            continue
        domain = site_url.removeprefix("sc-domain:").lower().removeprefix("www.")
        if host == domain or host.endswith(f".{domain}"):
            domain_matches.append(item)
    return domain_matches[0] if domain_matches else None


def _normalize_search_row(row: JsonDict, dimensions: list[str]) -> JsonDict:
    keys = row.get("keys") if isinstance(row.get("keys"), list) else []
    values = {
        dimension: keys[index] for index, dimension in enumerate(dimensions) if index < len(keys)
    }
    return {
        **values,
        "clicks": round(float(row.get("clicks") or 0), 2),
        "impressions": round(float(row.get("impressions") or 0), 2),
        "ctr": round(float(row.get("ctr") or 0), 4),
        "position": round(float(row.get("position") or 0), 2),
    }


def _ranking_opportunities(rows: list[JsonDict]) -> list[JsonDict]:
    return [
        row
        for row in rows
        if float(row.get("impressions") or 0) >= 50 and 4 <= float(row.get("position") or 0) <= 20
    ]


def _low_ctr_pages(rows: list[JsonDict]) -> list[JsonDict]:
    return [
        row
        for row in rows
        if float(row.get("impressions") or 0) >= 100 and float(row.get("ctr") or 0) <= 0.02
    ]


def _declining_pages(current_rows: list[JsonDict], previous_rows: list[JsonDict]) -> list[JsonDict]:
    previous_by_page = {str(row.get("page")): row for row in previous_rows if row.get("page")}
    declining = []
    for current in current_rows:
        page = str(current.get("page") or "")
        previous = previous_by_page.get(page)
        if not previous:
            continue
        click_delta = float(current.get("clicks") or 0) - float(previous.get("clicks") or 0)
        if click_delta <= -5:
            declining.append(
                {
                    "page": page,
                    "current_clicks": current.get("clicks"),
                    "previous_clicks": previous.get("clicks"),
                    "click_delta": round(click_delta, 2),
                    "current_impressions": current.get("impressions"),
                    "previous_impressions": previous.get("impressions"),
                }
            )
    return sorted(declining, key=lambda row: float(row["click_delta"]))


def _normalize_inspection(url: str, payload: JsonDict) -> JsonDict:
    result = payload.get("inspectionResult") or {}
    index_status = result.get("indexStatusResult") or {}
    verdict = str(index_status.get("verdict") or "").upper()
    coverage_state = str(index_status.get("coverageState") or "")
    on_google = True if verdict == "PASS" else False if verdict == "FAIL" else None
    return {
        "url": url,
        "status": "complete",
        "on_google": on_google,
        "verdict": verdict or None,
        "coverage_state": coverage_state or None,
        "robots_txt_state": index_status.get("robotsTxtState"),
        "indexing_state": index_status.get("indexingState"),
        "google_canonical": index_status.get("googleCanonical"),
        "user_canonical": index_status.get("userCanonical"),
        "last_crawl_time": index_status.get("lastCrawlTime"),
    }


def _priority_urls(url: str, page_urls: list[str], max_urls: int) -> list[str]:
    if max_urls <= 0:
        return []
    ordered = [url, *page_urls]
    seen: set[str] = set()
    selected = []
    for value in ordered:
        cleaned = str(value or "").strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            selected.append(cleaned)
        if len(selected) >= max_urls:
            break
    return selected


def _connection_properties(connection: GoogleSearchConsoleConnection) -> list[JsonDict]:
    properties = connection.properties if isinstance(connection.properties, dict) else {}
    entries = properties.get("siteEntry")
    return [item for item in entries if isinstance(item, dict)] if isinstance(entries, list) else []


def _expires_at(token_payload: JsonDict) -> datetime | None:
    expires_in = token_payload.get("expires_in")
    if not isinstance(expires_in, int | float):
        return None
    return datetime.now(UTC) + timedelta(seconds=int(expires_in))


def _normalized_url_for_match(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return url
    path = parsed.path or "/"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def _external_google_payload(*, gsc: JsonDict, url_inspection: JsonDict) -> JsonDict:
    return {"gsc": gsc, "url_inspection": url_inspection}


def _skipped(reason: str, started_at: str) -> JsonDict:
    return {
        "status": "skipped",
        "reason": reason,
        "summary": {},
        "started_at": started_at,
        "completed_at": _utc_now(),
    }


def _failed(error: str, started_at: str) -> JsonDict:
    return {
        "status": "failed",
        "error": error[:500],
        "summary": {},
        "started_at": started_at,
        "completed_at": _utc_now(),
    }


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
