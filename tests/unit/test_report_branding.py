from apps.worker.stages.report_branding import BrandConfig, apply_brand_overrides


def _base_context() -> dict:
    return BrandConfig().template_context()


def test_overrides_apply_name_colors_and_logo_url() -> None:
    ctx = _base_context()
    merged = apply_brand_overrides(
        ctx,
        {
            "name": "Acme Builders",
            "short_name": "Acme",
            "primary_color": "#123456",
            "accent_color": "#ABCDEF",
            "logo_url": "https://cdn.example.com/logo.png",
        },
    )
    assert merged["name"] == "Acme Builders"
    assert merged["short_name"] == "Acme"
    assert merged["primary_color"] == "#123456"
    assert merged["accent_color"] == "#ABCDEF"
    assert merged["logo_uri"] == "https://cdn.example.com/logo.png"
    assert merged["logo_exists"] is True
    # The base context is not mutated.
    assert ctx["name"] == BrandConfig().name


def test_overrides_ignore_blank_and_invalid_values() -> None:
    ctx = _base_context()
    merged = apply_brand_overrides(
        ctx,
        {"name": "   ", "primary_color": "not-a-color", "logo_url": "ftp://evil/logo.png"},
    )
    assert merged["name"] == ctx["name"]
    assert merged["primary_color"] == ctx["primary_color"]
    assert merged["logo_uri"] == ctx["logo_uri"]


def test_no_overrides_returns_context_unchanged() -> None:
    ctx = _base_context()
    assert apply_brand_overrides(ctx, None) == ctx
    assert apply_brand_overrides(ctx, {}) == ctx
