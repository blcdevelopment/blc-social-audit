import json

from apps.worker.stages.google_search_console import (
    _brand_token,
    _branded_split,
    _opportunity_estimate,
    _ranking_opportunities,
    _topic_clusters,
    match_search_console_property,
)

_STRIKING = [
    {
        "query": "custom home builder austin",
        "impressions": 3000,
        "clicks": 57,
        "ctr": 0.019,
        "position": 9,
    },
    {
        "query": "kitchen remodel cost austin",
        "impressions": 1200,
        "clicks": 48,
        "ctr": 0.04,
        "position": 6,
    },
    {
        "query": "home additions austin",
        "impressions": 800,
        "clicks": 24,
        "ctr": 0.03,
        "position": 7,
    },
    {"query": "low impression", "impressions": 10, "clicks": 1, "ctr": 0.1, "position": 5},
    {"query": "page one already", "impressions": 500, "clicks": 90, "ctr": 0.18, "position": 2},
]


def test_opportunity_estimate_math_and_grounding_shape() -> None:
    striking = _ranking_opportunities(_STRIKING)
    # only impressions>=50 AND position 4-20 qualify (drops the 10-impression and the pos-2 rows)
    assert len(striking) == 3
    opp = _opportunity_estimate(striking)

    assert opp["striking_query_count"] == 3
    assert opp["total_striking_impressions"] == 5000
    # low end models to position 5, high end to position 3 -> low <= high, both positive
    assert 0 < opp["opportunity_clicks_low"] <= opp["opportunity_clicks_high"]
    assert opp["estimated_leads_low"] <= opp["estimated_leads_high"]
    assert opp["lead_rate_low_pct"] == 5 and opp["lead_rate_high_pct"] == 10
    # Every surfaced number must be an int (clean grounding token) — no floats/derived precision.
    for key in (
        "total_striking_impressions",
        "current_clicks",
        "opportunity_clicks_low",
        "opportunity_clicks_high",
        "estimated_leads_low",
        "estimated_leads_high",
    ):
        assert isinstance(opp[key], int)
    # deterministic
    assert json.dumps(opp, sort_keys=True) == json.dumps(
        _opportunity_estimate(striking), sort_keys=True
    )


def test_opportunity_estimate_empty_is_safe() -> None:
    assert _opportunity_estimate([]) == {}


def test_opportunity_estimate_returns_empty_when_no_headroom() -> None:
    # A near-miss query that already out-performs the target CTR has no modeled upside, so the
    # estimate is suppressed rather than rendering a "0 to 0 more visits" message.
    over_performing = [
        {"query": "q", "impressions": 1000, "clicks": 500, "ctr": 0.5, "position": 4},
    ]
    assert _opportunity_estimate(over_performing) == {}


def test_branded_split_matches_spaced_brand_queries() -> None:
    rows = [
        {"query": "builder lead converter", "impressions": 500, "clicks": 200},
        {"query": "builderleadconverter reviews", "impressions": 100, "clicks": 30},
        {"query": "kitchen remodel", "impressions": 900, "clicks": 20},
    ]
    branded = _branded_split(rows, "https://www.builderleadconverter.com/")
    assert branded["brand_token"] == "builderleadconverter"
    assert branded["branded_query_count"] == 2  # spaced + exact both match
    assert branded["branded_impressions"] == 600
    assert branded["branded_impression_share_pct"] == 40
    assert _brand_token("https://www.example.co/") == "example"


def test_topic_clusters_group_deterministically() -> None:
    clusters = _topic_clusters(_STRIKING, _brand_token("https://x.example/"))
    assert clusters  # non-empty
    assert all(c["query_count"] > 0 and c["impressions"] > 0 for c in clusters)
    # sorted by impressions desc, deterministic
    impressions = [c["impressions"] for c in clusters]
    assert impressions == sorted(impressions, reverse=True)
    assert _topic_clusters([], "") == []


def test_match_search_console_property_prefers_longest_url_prefix() -> None:
    properties = [
        {"siteUrl": "sc-domain:example.com", "permissionLevel": "siteFullUser"},
        {"siteUrl": "https://example.com/", "permissionLevel": "siteFullUser"},
        {"siteUrl": "https://example.com/blog/", "permissionLevel": "siteFullUser"},
    ]

    matched = match_search_console_property("https://example.com/blog/post", properties)

    assert matched == properties[2]


def test_match_search_console_property_falls_back_to_domain_property() -> None:
    properties = [{"siteUrl": "sc-domain:example.com", "permissionLevel": "siteOwner"}]

    matched = match_search_console_property("https://www.example.com/services", properties)

    assert matched == properties[0]


def test_match_search_console_property_returns_none_without_verified_match() -> None:
    properties = [{"siteUrl": "sc-domain:other.com", "permissionLevel": "siteOwner"}]

    assert match_search_console_property("https://example.com/", properties) is None
