"""Adapter interface + registry + collector dispatch (P2-19 / SMWA-71)."""

from apps.shared.config import Settings
from apps.worker.stages.social import collector as collector_mod
from apps.worker.stages.social import providers as providers_mod
from apps.worker.stages.social.providers import (
    FacebookProvider,
    InstagramProvider,
    SocialProvider,
    YouTubeProvider,
    get_provider,
    supported_platforms,
)


def _settings(**overrides) -> Settings:
    base = {"_env_file": None}
    base.update(overrides)
    return Settings(**base)


def test_registry_covers_supported_platforms() -> None:
    assert set(supported_platforms()) == {"instagram", "facebook", "youtube"}
    for platform in supported_platforms():
        provider = get_provider(platform)
        assert provider is not None
        assert provider.platform == platform
        # Each registry entry honours the runtime-checkable adapter contract.
        assert isinstance(provider, SocialProvider)


def test_get_provider_unknown_platform_is_none() -> None:
    assert get_provider("tiktok") is None


def test_credential_available_reflects_settings() -> None:
    none = _settings()
    assert InstagramProvider().credential_available(none) is False
    assert FacebookProvider().credential_available(none) is False
    assert YouTubeProvider().credential_available(none) is False

    apify = _settings(apify_api_token="tok")
    assert InstagramProvider().credential_available(apify) is True
    assert FacebookProvider().credential_available(apify) is True
    assert YouTubeProvider().credential_available(apify) is False  # needs its own key

    youtube = _settings(youtube_api_key="key")
    assert YouTubeProvider().credential_available(youtube) is True
    assert InstagramProvider().credential_available(youtube) is False


def test_collect_skips_with_no_handles() -> None:
    facts = collector_mod.collect_social_facts(_settings(apify_api_token="t"), {})
    assert facts["status"] == "skipped"
    assert facts["reason"] == "no_social_handles"


def test_collect_skips_when_apify_token_missing() -> None:
    facts = collector_mod.collect_social_facts(_settings(), {"instagram": "acme"})
    assert facts["status"] == "skipped"
    assert facts["reason"] == "missing_apify_api_token"


def test_collect_skips_youtube_only_when_key_missing() -> None:
    facts = collector_mod.collect_social_facts(_settings(), {"youtube": "acme"})
    assert facts["status"] == "skipped"
    assert facts["reason"] == "missing_youtube_api_key"


def test_collect_dispatches_through_registry(monkeypatch) -> None:
    # No hardcoded platform branch: the collector fetches whatever provider the registry holds.
    monkeypatch.setattr(
        providers_mod,
        "fetch_instagram_profile",
        lambda handle, settings: {"followersCount": 100, "biography": "Call us"},
    )
    facts = collector_mod.collect_social_facts(
        _settings(apify_api_token="t"), {"instagram": "acme"}
    )
    assert facts["status"] == "complete"
    assert facts["platforms"][0]["platform"] == "instagram"
    assert facts["platforms"][0]["followers"] == 100


def test_facebook_provider_merges_posts_actor(monkeypatch) -> None:
    monkeypatch.setattr(
        providers_mod, "fetch_facebook_page", lambda handle, settings: {"pageName": "Acme"}
    )
    monkeypatch.setattr(
        providers_mod,
        "fetch_facebook_posts",
        lambda handle, settings: [{"time": "2026-06-01T00:00:00Z", "likes": 5}],
    )
    raw = FacebookProvider().fetch("acme", _settings(apify_api_token="t"))
    assert raw["pageName"] == "Acme"
    assert raw["posts"] == [{"time": "2026-06-01T00:00:00Z", "likes": 5}]


def test_facebook_provider_returns_none_when_page_missing(monkeypatch) -> None:
    monkeypatch.setattr(providers_mod, "fetch_facebook_page", lambda handle, settings: None)
    assert FacebookProvider().fetch("acme", _settings(apify_api_token="t")) is None
