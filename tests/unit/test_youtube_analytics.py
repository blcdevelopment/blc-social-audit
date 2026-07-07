"""YouTube Analytics (connected/owner) normalizer + graceful fetch (SAE-15, Wave 3).

Covers the pure normalization of reports.query payloads. The live fetch path (OAuth token ->
network) is exercised only against a real connected channel and is not unit-tested here.
"""

import json
from pathlib import Path

from apps.shared.config import Settings
from apps.worker.stages.social.youtube_analytics_provider import (
    fetch_channel_analytics,
    normalize_youtube_analytics,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_normalizer_flattens_reports() -> None:
    raw = json.loads((FIXTURES / "youtube_analytics_reports.json").read_text())
    facts = normalize_youtube_analytics(raw)
    assert facts["views"] == 15234
    assert facts["estimated_minutes_watched"] == 48210
    assert facts["avg_view_duration_seconds"] == 190
    assert facts["avg_view_percentage"] == 42.7
    assert facts["subscribers_gained"] == 320
    assert facts["subscribers_lost"] == 45
    assert facts["traffic_sources"][0] == {"source": "YT_SEARCH", "views": 8200}
    assert facts["demographics"][0] == {
        "age_group": "age25-34",
        "gender": "male",
        "viewer_pct": 31.4,
    }


def test_normalizer_is_none_safe_on_empty_reports() -> None:
    facts = normalize_youtube_analytics({})
    assert facts["views"] is None
    assert facts["traffic_sources"] == []
    assert facts["demographics"] == []


def test_fetch_returns_none_without_token() -> None:
    assert (
        fetch_channel_analytics(
            "", start_date="2026-01-01", end_date="2026-03-31", settings=Settings()
        )
        is None
    )


def test_oauth_scopes_gate_youtube_analytics() -> None:
    from apps.worker.stages.google_search_console import (
        GSC_SCOPES,
        YOUTUBE_ANALYTICS_SCOPES,
        oauth_scopes,
    )

    # Default: connected-mode off -> Search Console scopes only (existing behaviour unchanged).
    # _env_file=None isolates from the local .env (which may set the toggle for live testing).
    assert oauth_scopes(Settings(_env_file=None)) == GSC_SCOPES
    # Enabled -> the YouTube Analytics scopes are appended to the same consent.
    enabled = oauth_scopes(Settings(_env_file=None, youtube_analytics_connect_enabled=True))
    assert enabled == GSC_SCOPES + YOUTUBE_ANALYTICS_SCOPES
    assert "https://www.googleapis.com/auth/yt-analytics.readonly" in enabled
