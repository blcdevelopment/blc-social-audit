from apps.worker.stages.google_search_console import match_search_console_property


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
