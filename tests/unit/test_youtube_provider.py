from apps.shared.config import Settings
from apps.worker.stages.social.collector import collect_social_facts
from apps.worker.stages.social.youtube_provider import _channel_lookups


def test_lookups_bare_handle() -> None:
    assert _channel_lookups("@acme") == [{"forHandle": "@acme"}, {"forUsername": "acme"}]
    assert _channel_lookups("acme") == [{"forHandle": "@acme"}, {"forUsername": "acme"}]


def test_lookups_channel_id() -> None:
    cid = "UC" + "a" * 22  # 24 chars
    assert _channel_lookups(cid) == [{"id": cid}]
    assert _channel_lookups(f"https://youtube.com/channel/{cid}") == [{"id": cid}]


def test_lookups_handle_url_with_subpath() -> None:
    # /@acme/videos must resolve the handle, not the trailing 'videos' segment.
    assert _channel_lookups("https://youtube.com/@acme/videos") == [
        {"forHandle": "@acme"},
        {"forUsername": "acme"},
    ]
    assert _channel_lookups("https://www.youtube.com/@acme") == [
        {"forHandle": "@acme"},
        {"forUsername": "acme"},
    ]


def test_lookups_legacy_custom_url() -> None:
    assert _channel_lookups("https://youtube.com/c/AcmeBuilders") == [
        {"forUsername": "AcmeBuilders"},
        {"forHandle": "@AcmeBuilders"},
    ]


def _settings(**overrides) -> Settings:
    base = {"_env_file": None, "apify_api_token": None, "youtube_api_key": None}
    base.update(overrides)
    return Settings(**base)


def test_collector_youtube_only_missing_key_skips() -> None:
    out = collect_social_facts(_settings(), {"youtube": "@acme"})
    assert out["status"] == "skipped"
    assert out["reason"] == "missing_youtube_api_key"


def test_collector_instagram_only_missing_token_skips() -> None:
    out = collect_social_facts(_settings(), {"instagram": "acme"})
    assert out["status"] == "skipped"
    assert out["reason"] == "missing_apify_api_token"


def test_collector_no_handles_skips() -> None:
    out = collect_social_facts(_settings(), {})
    assert out["status"] == "skipped"
    assert out["reason"] == "no_social_handles"
