"""Auto-discovery of a site's own social profile links from already-crawled HTML, plus the
explicit-wins / fill-the-blanks merge used by the combined audit (tasks._resolve_social_handles).

The extractor is pure over stored HTML (no network), so these tests build small HTML snippets and
lightweight page stand-ins. The merge tests prove the operator's typed handles always win per
platform while discovery fills only the platforms left blank, and that the kill-switch turns it off.
"""

from __future__ import annotations

from types import SimpleNamespace

from apps.shared.config import Settings
from apps.shared.models import AuditJob
from apps.worker.stages.social.discovery import discover_social_links
from apps.worker.tasks import _resolve_social_handles


def _page(html: str) -> SimpleNamespace:
    return SimpleNamespace(html=html)


def _crawl(*html: str) -> SimpleNamespace:
    return SimpleNamespace(pages=[_page(h) for h in html])


def _footer(href: str) -> SimpleNamespace:
    """A page whose only link is a footer-placed anchor (so it clears the placement floor)."""
    return _page(f'<footer><a href="{href}">x</a></footer>')


# --------------------------------------------------------------------------- extractor
def test_discovers_footer_profile_links_for_all_platforms() -> None:
    html = """
    <html><body>
      <main><p>Body</p></main>
      <footer class="site-footer">
        <a href="https://www.instagram.com/acmebuilders/">IG</a>
        <a href="https://facebook.com/AcmeBuilders">FB</a>
        <a href="https://www.youtube.com/@acmebuilders">YT</a>
      </footer>
    </body></html>
    """
    assert discover_social_links([_page(html)]) == {
        "instagram": "https://www.instagram.com/acmebuilders/",
        # Facebook vanity URLs are case-insensitive -> canonicalised to lowercase.
        "facebook": "https://www.facebook.com/acmebuilders/",
        "youtube": "https://www.youtube.com/@acmebuilders",
    }


def test_no_social_links_returns_empty() -> None:
    html = (
        "<html><body><a href='/about'>About</a><a href='https://example.com'>Home</a></body></html>"
    )
    assert discover_social_links([_page(html)]) == {}


def test_excludes_share_intent_and_post_permalinks() -> None:
    html = """
    <footer>
      <a href="https://facebook.com/sharer/sharer.php?u=x">share</a>
      <a href="https://www.youtube.com/watch?v=abc123">video</a>
      <a href="https://instagram.com/p/Cabcdef/">post</a>
      <a href="https://instagram.com/explore/tags/homes/">tag</a>
      <a href="https://twitter.com/acme">unsupported</a>
    </footer>
    """
    assert discover_social_links([_page(html)]) == {}


def test_footer_link_beats_inline_body_mention() -> None:
    html = """
    <html><body>
      <main><p>We post on <a href="https://instagram.com/inline_mention">our feed</a></p></main>
      <footer><a href="https://www.instagram.com/real_handle/">IG</a></footer>
    </body></html>
    """
    assert discover_social_links([_page(html)]) == {
        "instagram": "https://www.instagram.com/real_handle/"
    }


def test_youtube_channel_and_legacy_url_forms() -> None:
    # A real channel id is exactly "UC" + 22 chars. (Footer-placed so the link clears the
    # placement floor — a bare body link is intentionally not trusted; see the floor test below.)
    assert discover_social_links(
        [_footer("https://www.youtube.com/channel/UCBJycsmduvYEL83R_U4JriQ")]
    ) == {"youtube": "https://www.youtube.com/channel/UCBJycsmduvYEL83R_U4JriQ"}
    assert discover_social_links([_footer("https://youtube.com/c/AcmeBuilders")]) == {
        "youtube": "https://www.youtube.com/c/AcmeBuilders"
    }
    assert discover_social_links([_footer("https://youtube.com/user/AcmeTV")]) == {
        "youtube": "https://www.youtube.com/user/AcmeTV"
    }


def test_rejects_too_short_youtube_channel_id() -> None:
    # "UCabc" is not a valid 24-char channel id — must not become a bogus profile URL.
    assert discover_social_links([_page('<a href="https://youtube.com/channel/UCabc">x</a>')]) == {}


def test_rejects_handles_with_leading_or_trailing_punctuation() -> None:
    # Instagram never allows a leading/trailing dot; Facebook slugs start/end alphanumeric.
    for href in (
        "https://instagram.com/.acmebuilders",
        "https://instagram.com/acmebuilders.",
        "https://facebook.com/-acmebuilders",
        "https://facebook.com/acmebuilders-",
    ):
        assert discover_social_links([_page(f'<a href="{href}">x</a>')]) == {}


def test_rejects_known_non_profile_first_segments() -> None:
    for href in (
        "https://instagram.com/business",
        "https://instagram.com/developer",
        "https://www.facebook.com/business/",
        "https://www.facebook.com/ads/",
    ):
        assert discover_social_links([_page(f'<a href="{href}">x</a>')]) == {}


def test_facebook_pg_prefix_form() -> None:
    assert discover_social_links([_footer("https://www.facebook.com/pg/AcmeBuilders/about")]) == {
        "facebook": "https://www.facebook.com/acmebuilders/"
    }


def test_facebook_profile_id_and_pages_forms() -> None:
    assert discover_social_links(
        [_footer("https://www.facebook.com/profile.php?id=100012345")]
    ) == {"facebook": "https://www.facebook.com/profile.php?id=100012345"}
    assert discover_social_links(
        [_footer("https://www.facebook.com/pages/Acme-Builders/123456789")]
    ) == {"facebook": "https://www.facebook.com/pages/Acme-Builders/123456789"}


def test_strips_www_and_m_subdomains_and_query() -> None:
    page = _footer("https://m.facebook.com/AcmeBuilders/?ref=page_internal")
    assert discover_social_links([page]) == {"facebook": "https://www.facebook.com/acmebuilders/"}


def test_rejects_facebook_pages_category_directory() -> None:
    # /pages/category/... is Facebook's directory listing, and bare /pages or /pages/Name (no
    # numeric id) is not a page profile — none should be mistaken for a profile.
    for href in (
        "https://www.facebook.com/pages/category/Local-Business/Acme-123",
        "https://www.facebook.com/pages",
        "https://www.facebook.com/pages/Acme",
    ):
        assert discover_social_links([_page(f"<footer><a href='{href}'>x</a></footer>")]) == {}


def test_rejects_youtube_reserved_words_in_c_and_user_forms() -> None:
    # /c/<name> and /user/<name> must reject reserved words in the name position too.
    for href in ("https://youtube.com/c/watch", "https://youtube.com/user/feed"):
        assert discover_social_links([_page(f"<footer><a href='{href}'>x</a></footer>")]) == {}


def test_resolves_protocol_relative_links() -> None:
    # Protocol-relative icon links (href="//host/...") are resolved against the page, not dropped.
    html = '<footer><a href="//www.instagram.com/acmebuilders/">IG</a></footer>'
    assert discover_social_links([_page(html)], site_url="https://acme.com/") == {
        "instagram": "https://www.instagram.com/acmebuilders/"
    }


def test_case_insensitive_handles_dedupe() -> None:
    # /AcmeBuilders/ and /acmebuilders/ are the same profile — they must not split the vote.
    html = """
    <footer>
      <a href="https://instagram.com/AcmeBuilders/">IG</a>
      <a href="https://instagram.com/acmebuilders/">IG2</a>
    </footer>
    """
    assert discover_social_links([_page(html)]) == {
        "instagram": "https://www.instagram.com/acmebuilders/"
    }


# --------------------------------------------------------------------------- ownership guards
def test_bare_body_mention_below_floor_is_ignored() -> None:
    # A single inline body mention (no footer/header/nav placement, no brand match) is too weak to
    # be trusted as the site's own profile, so it must not promote a website audit to combined.
    html = '<main><p>see <a href="https://instagram.com/somebody">our feed</a></p></main>'
    assert discover_social_links([_page(html)], site_url="https://example.com/") == {}


def test_ignores_third_party_agency_credit_links() -> None:
    # A "Site by <agency>" footer credit must NOT be scored as the site's own profile.
    html = (
        "<footer><small>Site by "
        '<a href="https://instagram.com/web_agency">Acme Agency</a></small></footer>'
    )
    assert discover_social_links([_page(html)], site_url="https://builder.com/") == {}


def test_real_profile_beats_agency_credit_for_same_platform() -> None:
    # The site's own brand-matching footer profile wins over an agency credit on the same platform.
    html = """
    <footer>
      <ul class="social"><li><a href="https://instagram.com/builderco">Follow us</a></li></ul>
      <small>Website by <a href="https://instagram.com/web_agency">Agency</a></small>
    </footer>
    """
    assert discover_social_links([_page(html)], site_url="https://builderco.com/") == {
        "instagram": "https://www.instagram.com/builderco/"
    }


# --------------------------------------------------------------------------- merge (resolve)
_IG_FB_YT_FOOTER = """
<footer>
  <a href="https://www.instagram.com/site_ig/">IG</a>
  <a href="https://facebook.com/site_fb">FB</a>
  <a href="https://www.youtube.com/@site_yt">YT</a>
</footer>
"""


def test_resolve_fills_all_blanks_when_no_explicit_handles() -> None:
    job = AuditJob(url="https://example.com/", audit_type="website", social_handles=None)
    out = _resolve_social_handles(job, _crawl(_IG_FB_YT_FOOTER), Settings(_env_file=None))
    assert out == {
        "instagram": "https://www.instagram.com/site_ig/",
        "facebook": "https://www.facebook.com/site_fb/",
        "youtube": "https://www.youtube.com/@site_yt",
    }


def test_resolve_explicit_handle_wins_and_blanks_are_filled() -> None:
    # Operator typed Instagram only — keep it verbatim, discover Facebook + YouTube from the page.
    job = AuditJob(
        url="https://example.com/", audit_type="combined", social_handles={"instagram": "typed_ig"}
    )
    out = _resolve_social_handles(job, _crawl(_IG_FB_YT_FOOTER), Settings(_env_file=None))
    assert out["instagram"] == "typed_ig"  # explicit wins, not overwritten by discovery
    assert out["facebook"] == "https://www.facebook.com/site_fb/"
    assert out["youtube"] == "https://www.youtube.com/@site_yt"


def test_resolve_kill_switch_returns_only_explicit() -> None:
    job = AuditJob(
        url="https://example.com/", audit_type="combined", social_handles={"instagram": "typed_ig"}
    )
    out = _resolve_social_handles(
        job, _crawl(_IG_FB_YT_FOOTER), Settings(_env_file=None, social_autodiscovery_enabled=False)
    )
    assert out == {"instagram": "typed_ig"}


def test_resolve_returns_empty_when_no_social_and_no_explicit() -> None:
    job = AuditJob(url="https://example.com/", audit_type="website", social_handles=None)
    out = _resolve_social_handles(
        job, _crawl("<footer><a href='/contact'>Contact</a></footer>"), Settings(_env_file=None)
    )
    assert out == {}
