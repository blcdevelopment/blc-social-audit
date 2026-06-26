from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta
from typing import Any
from urllib.parse import quote, urlencode, urlparse

import httpx
from celery.exceptions import SoftTimeLimitExceeded
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
    # SQLite (QA harness/tests) returns naive datetimes; Postgres returns aware ones.
    if isinstance(expires_at, datetime) and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
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
    except SoftTimeLimitExceeded:
        # The whole Celery task is out of budget; fail fast instead of recording
        # a "failed enrichment" and letting the hard limit kill the job mid-write.
        raise
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
        row_limit=min(settings.gsc_row_limit, 25000),
    )
    top_pages = query_search_analytics(
        access_token,
        site_url,
        start_date=start_date,
        end_date=end_date,
        dimensions=["page"],
        row_limit=min(settings.gsc_row_limit, 25000),
    )
    previous_pages = query_search_analytics(
        access_token,
        site_url,
        start_date=previous_start,
        end_date=previous_end,
        dimensions=["page"],
        row_limit=min(settings.gsc_row_limit, 25000),
    )

    opportunities = _ranking_opportunities(top_queries)
    low_ctr_pages = _low_ctr_pages(top_pages)
    declining_pages = _declining_pages(top_pages, previous_pages)
    brand_token = _brand_token(site_url)
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
        # Business-opportunity framing (P1-P4); see helpers above. Stored as facts so the grounding
        # validator keeps any executive-summary prose that cites these numbers.
        "opportunity": _opportunity_estimate(opportunities),
        "branded": _branded_split(top_queries, site_url),
        "topic_clusters": _topic_clusters(top_queries, brand_token)[:8],
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
        except SoftTimeLimitExceeded:
            raise
        except Exception as exc:  # noqa: BLE001 - per-URL failure is data, not task failure
            inspections.append({"url": url, "status": "failed", "error": str(exc)[:300]})

    not_on_google = sum(1 for item in inspections if item.get("on_google") is False)
    failed = sum(1 for item in inspections if item.get("status") == "failed")
    succeeded = len(inspections) - failed
    # Honest status: a run where some/all per-URL inspections errored must not
    # present itself as a clean "complete" — the not_on_google count would be an
    # undercount, and the scoring layer only trusts complete sources.
    if succeeded == 0:
        status = "failed"
    elif failed > 0:
        status = "partial"
    else:
        status = "complete"
    return {
        "status": status,
        "source": "url_inspection_api",
        "site_url": site_url,
        "summary": {
            "urls_requested": len(urls),
            "urls_inspected": succeeded,
            "not_on_google": not_on_google,
            "failed": failed,
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

    # Next preference: a domain property. It aggregates every scheme/subdomain,
    # so it beats a scheme- or www-mismatched url-prefix property that may hold
    # only a stale slice of the site's data.
    domain_matches = []
    for item in properties:
        site_url = str(item.get("siteUrl") or "")
        if not site_url.startswith("sc-domain:"):
            continue
        domain = site_url.removeprefix("sc-domain:").lower().removeprefix("www.")
        if host == domain or host.endswith(f".{domain}"):
            domain_matches.append(item)
    if domain_matches:
        return domain_matches[0]

    # Last resort: relaxed url-prefix match tolerating www./scheme variants so
    # auditing https://www.example.com still finds the https://example.com/
    # property. Prefer https, then the longest (most specific) path prefix.
    relaxed_matches = []
    for item in properties:
        site_url = str(item.get("siteUrl") or "")
        if not site_url.startswith(("http://", "https://")):
            continue
        site_parsed = urlparse(site_url)
        site_host = (site_parsed.hostname or "").lower().removeprefix("www.")
        site_path = site_parsed.path or "/"
        if site_host == host and (parsed.path or "/").startswith(site_path):
            relaxed_matches.append((site_parsed.scheme == "https", len(site_path), item))
    if relaxed_matches:
        return max(relaxed_matches, key=lambda entry: (entry[0], entry[1]))[2]
    return None


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


# --- Business-opportunity framing (P1-P4) ------------------------------------------------------
# These helpers translate the site's OWN Search Console data into business-shaped, leading-indicator
# facts (clicks/leads left on the table, branded demand, topic-cluster visibility). Every number is
# a transparent function of real GSC impressions/CTR + published benchmarks, stored as a FACT so the
# grounding validator keeps any prose that cites it. They are estimates/ranges, never guarantees,
# and never a revenue/CAC figure (out of scope without CRM data). Half-up rounding (int(x + 0.5))
# matches the project convention.

# Published organic CTR-by-position meta-analysis (First Page Sage, 2025). Used only to model the
# opportunity range from real impressions; positions past 10 fall back to the position-10 CTR.
_CTR_CURVE: dict[int, float] = {
    1: 0.398,
    2: 0.187,
    3: 0.102,
    4: 0.072,
    5: 0.051,
    6: 0.044,
    7: 0.030,
    8: 0.021,
    9: 0.019,
    10: 0.016,
}
_CTR_CURVE_SOURCE = "First Page Sage organic CTR-by-position meta-analysis (2025)"
# Conservative target band: model near-miss pages reaching the top of page 1 (position 5 = low end,
# position 3 = high end). Never position 1 — that would overstate the opportunity.
_OPPORTUNITY_TARGET_LOW, _OPPORTUNITY_TARGET_HIGH = 5, 3
# Published home-services service-page contact (call/form) conversion benchmark RANGE — an industry
# figure, NOT measured on the audited site; only ever applied as a labeled range, never x job value.
_LEAD_RATE_LOW_PCT, _LEAD_RATE_HIGH_PCT = 5, 10

_CLUSTER_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "your",
        "you",
        "our",
        "best",
        "near",
        "are",
        "can",
        "does",
        "how",
        "what",
        "when",
        "where",
        "why",
        "who",
        "cost",
        "costs",
        "price",
        "prices",
        "near me",
        "company",
        "companies",
        "service",
        "services",
        "contractor",
        "contractors",
        "home",
        "homes",
    }
)


def _ctr_at(position: int) -> float:
    return _CTR_CURVE.get(max(1, min(position, 10)), _CTR_CURVE[10])


def _opportunity_for_target(rows: list[JsonDict], target_position: int) -> float:
    target_ctr = _ctr_at(target_position)
    total = 0.0
    for row in rows:
        impressions = float(row.get("impressions") or 0)
        current_ctr = float(row.get("ctr") or 0)
        # Never model a query BELOW its current real CTR; only the upside delta counts.
        total += max(0.0, impressions * (max(target_ctr, current_ctr) - current_ctr))
    return total


def _opportunity_estimate(striking_rows: list[JsonDict]) -> JsonDict:
    """P1+P2: deterministic 'clicks/leads left on the table' from the striking-distance set."""
    if not striking_rows:
        return {}
    total_impressions = sum(float(row.get("impressions") or 0) for row in striking_rows)
    current_clicks = sum(
        float(row.get("impressions") or 0) * float(row.get("ctr") or 0) for row in striking_rows
    )
    opp_low = _opportunity_for_target(striking_rows, _OPPORTUNITY_TARGET_LOW)
    opp_high = _opportunity_for_target(striking_rows, _OPPORTUNITY_TARGET_HIGH)
    opp_clicks_low, opp_clicks_high = int(opp_low + 0.5), int(opp_high + 0.5)
    # No modeled headroom (every near-miss query already out-performs the target CTR) => emit
    # nothing rather than a degenerate "0 to 0 more visits" estimate; the callout simply won't show.
    if opp_clicks_high <= 0:
        return {}
    return {
        "is_estimate": True,
        "striking_query_count": len(striking_rows),
        "total_striking_impressions": int(total_impressions + 0.5),
        "current_clicks": int(current_clicks + 0.5),
        "opportunity_clicks_low": opp_clicks_low,
        "opportunity_clicks_high": opp_clicks_high,
        "estimated_leads_low": int(opp_clicks_low * _LEAD_RATE_LOW_PCT / 100 + 0.5),
        "estimated_leads_high": int(opp_clicks_high * _LEAD_RATE_HIGH_PCT / 100 + 0.5),
        "lead_rate_low_pct": _LEAD_RATE_LOW_PCT,
        "lead_rate_high_pct": _LEAD_RATE_HIGH_PCT,
        "target_position_low": _OPPORTUNITY_TARGET_LOW,
        "target_position_high": _OPPORTUNITY_TARGET_HIGH,
        "ctr_curve_source": _CTR_CURVE_SOURCE,
    }


def _brand_token(site_url: str) -> str:
    host = (urlparse(site_url).hostname or "").lower().removeprefix("www.")
    labels = [label for label in host.split(".") if label]
    name = labels[-2] if len(labels) >= 2 else (labels[0] if labels else "")
    return re.sub(r"[^a-z0-9]", "", name)


def _branded_split(rows: list[JsonDict], site_url: str) -> JsonDict:
    """P3: branded vs non-branded demand split. A query is branded if the site's registrable name
    appears in its alphanumerics (so 'builder lead converter' matches builderleadconverter.com)."""
    token = _brand_token(site_url)
    if len(token) < 3:
        return {}
    branded_impr = branded_clicks = total_impr = total_clicks = 0.0
    branded_count = 0
    for row in rows:
        impressions = float(row.get("impressions") or 0)
        clicks = float(row.get("clicks") or 0)
        total_impr += impressions
        total_clicks += clicks
        if token in re.sub(r"[^a-z0-9]", "", str(row.get("query") or "").lower()):
            branded_impr += impressions
            branded_clicks += clicks
            branded_count += 1
    if total_impr <= 0:
        return {}
    return {
        "brand_token": token,
        "branded_query_count": branded_count,
        "branded_impressions": int(branded_impr + 0.5),
        "branded_clicks": int(branded_clicks + 0.5),
        "nonbranded_impressions": int(total_impr - branded_impr + 0.5),
        "nonbranded_clicks": int(total_clicks - branded_clicks + 0.5),
        "branded_impression_share_pct": int((branded_impr / total_impr) * 100 + 0.5),
    }


def _query_tokens(query: str, brand_token: str) -> list[str]:
    tokens = re.split(r"[^a-z0-9]+", query.lower())
    return [
        token
        for token in tokens
        if len(token) >= 4 and token not in _CLUSTER_STOPWORDS and token != brand_token
    ]


def _topic_clusters(
    rows: list[JsonDict], brand_token: str, *, max_clusters: int = 6
) -> list[JsonDict]:
    """P4: deterministic topic-cluster visibility. Seeds are the highest-impression content tokens
    across the query set; each query joins the first seed it contains. No LLM, no external
    taxonomy."""
    weights: dict[str, float] = {}
    for row in rows:
        impressions = float(row.get("impressions") or 0)
        for token in _query_tokens(str(row.get("query") or ""), brand_token):
            weights[token] = weights.get(token, 0.0) + impressions
    if not weights:
        return []
    seeds = [token for token, _ in sorted(weights.items(), key=lambda kv: (-kv[1], kv[0]))][
        :max_clusters
    ]
    buckets: dict[str, dict[str, float]] = {
        seed: {"impressions": 0.0, "position_weight": 0.0, "count": 0.0} for seed in seeds
    }
    for row in rows:
        impressions = float(row.get("impressions") or 0)
        position = float(row.get("position") or 0)
        tokens = set(_query_tokens(str(row.get("query") or ""), brand_token))
        seed = next((candidate for candidate in seeds if candidate in tokens), None)
        if seed is None:
            continue
        bucket = buckets[seed]
        bucket["impressions"] += impressions
        bucket["position_weight"] += position * impressions
        bucket["count"] += 1
    clusters = [
        {
            "cluster": seed,
            "query_count": int(bucket["count"]),
            "impressions": int(bucket["impressions"] + 0.5),
            "avg_position": round(bucket["position_weight"] / bucket["impressions"], 1)
            if bucket["impressions"] > 0
            else 0.0,
        }
        for seed, bucket in buckets.items()
        if bucket["count"] > 0 and bucket["impressions"] > 0
    ]
    clusters.sort(key=lambda item: (-item["impressions"], item["cluster"]))
    return clusters


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
