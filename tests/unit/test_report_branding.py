from pathlib import Path

from apps.worker.stages.pdf_renderer import _render_css
from apps.worker.stages.report_branding import BrandConfig, apply_brand_overrides

_REPORT_CSS = Path(__file__).resolve().parents[2] / "templates" / "report.css"


def _base_context() -> dict:
    return BrandConfig().template_context()


def test_running_header_uses_white_label_brand_name() -> None:
    # The interior-page running header must carry the (white-labeled) brand name, not a hardcode.
    ctx = apply_brand_overrides(_base_context(), {"name": "Acme Builders"})
    css = _render_css(css_path=_REPORT_CSS, brand_context=ctx)
    assert '"Acme Builders" " · Website Audit · "' in css
    assert "Builder Lead Converter" not in css  # no hardcoded leak on a white-labeled report


def test_running_header_defaults_to_blc_without_override() -> None:
    css = _render_css(css_path=_REPORT_CSS, brand_context=_base_context())
    assert '"Builder Lead Converter" " · Website Audit · "' in css


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
