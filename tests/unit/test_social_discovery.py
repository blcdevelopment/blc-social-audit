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
    # "UCabc" is not a valid 24-char channel id — must not become a bogus profile URL. Footer-placed
    # so the URL-form rejection is exercised, not masked by the placement floor.
    assert discover_social_links([_footer("https://youtube.com/channel/UCabc")]) == {}


def test_rejects_handles_with_leading_or_trailing_punctuation() -> None:
    # Instagram never allows a leading/trailing dot; Facebook slugs start/end alphanumeric.
    # Footer-placed so the handle-shape rejection is exercised, not masked by the placement floor.
    for href in (
        "https://instagram.com/.acmebuilders",
        "https://instagram.com/acmebuilders.",
        "https://facebook.com/-acmebuilders",
        "https://facebook.com/acmebuilders-",
    ):
        assert discover_social_links([_footer(href)]) == {}


def test_rejects_known_non_profile_first_segments() -> None:
    # Footer-placed so the reserved-segment rejection is exercised, not masked by the floor.
    for href in (
        "https://instagram.com/business",
        "https://instagram.com/developer",
        "https://www.facebook.com/business/",
        "https://www.facebook.com/ads/",
    ):
        assert discover_social_links([_footer(href)]) == {}


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


def test_social_proof_body_section_link_is_not_discovered() -> None:
    # A testimonial in a "social-proof" BODY section: the generic "social" class token (+1.0) alone
    # must not clear the floor, so a stranger's profile is never scraped or scored as the client's.
    html = (
        '<section class="social-proof"><blockquote>Great builder!</blockquote>'
        '<a href="https://instagram.com/influencer_x">@influencer_x</a></section>'
    )
    assert discover_social_links([_page(html)], site_url="https://builderco.com/") == {}


def test_footer_social_icons_block_still_discovered() -> None:
    # The canonical placement — a social-icons list inside the footer — still clears the floor.
    html = (
        '<footer><ul class="social-icons"><li>'
        '<a href="https://instagram.com/acmebuilders/">IG</a></li></ul></footer>'
    )
    assert discover_social_links([_page(html)]) == {
        "instagram": "https://www.instagram.com/acmebuilders/"
    }


def test_plain_nav_social_link_is_discovered() -> None:
    # Intended outcome: a semantic <nav> element is site chrome like header/footer, so its 2.0
    # bonus (base 1.0 + 2.0 = 3.0) clears the 2.5 floor — unlike a mere "social"/"menu" class
    # token on a body container, which scores only 1.0 + 1.0 = 2.0 and is rejected.
    html = '<nav><a href="https://instagram.com/acmebuilders/">IG</a></nav>'
    assert discover_social_links([_page(html)]) == {
        "instagram": "https://www.instagram.com/acmebuilders/"
    }


def test_facebook_pages_body_mention_discovered_via_brand_match() -> None:
    # The /pages/<Name>/<id> form carries the brand in the SLUG, not the trailing numeric id, so
    # the brand bonus fires (base 1.0 + 2.0 = 3.0), lifting a bare body mention over the floor.
    html = (
        "<p>Find us on "
        '<a href="https://www.facebook.com/pages/Acme-Builders/123456789">Facebook</a></p>'
    )
    assert discover_social_links([_page(html)], site_url="https://acmebuilders.com/") == {
        "facebook": "https://www.facebook.com/pages/Acme-Builders/123456789"
    }


def test_financing_copy_near_footer_link_is_not_attribution() -> None:
    # "credit approval" / "credit cards" is financing copy, not a photo/design credit line — it
    # must not discard the site's own footer profile link.
    html = (
        "<footer><p>Financing available, credit approval required. We accept all major credit "
        'cards. <a href="https://instagram.com/acmebuilders/">Follow us</a></p></footer>'
    )
    assert discover_social_links([_page(html)]) == {
        "instagram": "https://www.instagram.com/acmebuilders/"
    }


def test_credit_attribution_lines_still_discard_link() -> None:
    # Attribution-shaped credit lines ("Photo credit ...", "Credits: ...") still mark the link as
    # a third party's profile.
    for lead in ("Photo credit", "Credits:"):
        html = (
            f"<footer><small>{lead} "
            '<a href="https://instagram.com/photographer_x">@photographer_x</a></small></footer>'
        )
        assert discover_social_links([_page(html)]) == {}


# --------------------------------------------------------------------------- merge (resolve)
_IG_FB_YT_FOOTER = """
<footer>
  <a href="https://www.instagram.com/site_ig/">IG</a>
  <a href="https://facebook.com/site_fb">FB</a>
  <a href="https://www.youtube.com/@site_yt">YT</a>
</footer>
"""


_ALL_CREDS = {"apify_api_token": "tok", "youtube_api_key": "key"}


def test_resolve_fills_all_blanks_when_no_explicit_handles() -> None:
    job = AuditJob(url="https://example.com/", audit_type="website", social_handles=None)
    out = _resolve_social_handles(
        job, _crawl(_IG_FB_YT_FOOTER), Settings(_env_file=None, **_ALL_CREDS)
    )
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
    out = _resolve_social_handles(
        job, _crawl(_IG_FB_YT_FOOTER), Settings(_env_file=None, **_ALL_CREDS)
    )
    assert out["instagram"] == "typed_ig"  # explicit wins, not overwritten by discovery
    assert out["facebook"] == "https://www.facebook.com/site_fb/"
    assert out["youtube"] == "https://www.youtube.com/@site_yt"


def test_resolve_backfills_only_credentialed_platforms() -> None:
    # A discovered handle whose provider has no credential would fail on every run and pin the
    # social bundle at "partial" — discovery must not back-fill it.
    job = AuditJob(url="https://example.com/", audit_type="website", social_handles=None)
    out = _resolve_social_handles(
        job, _crawl(_IG_FB_YT_FOOTER), Settings(_env_file=None, apify_api_token="tok")
    )
    assert set(out) == {"instagram", "facebook"}  # Apify covers IG+FB; no YouTube key => dropped


def test_resolve_keeps_explicit_handle_without_credential() -> None:
    # Explicit operator handles are kept even without a credential — the operator asked, and the
    # report's collection-failure note is the honest outcome.
    job = AuditJob(
        url="https://example.com/", audit_type="combined", social_handles={"youtube": "typed_yt"}
    )
    out = _resolve_social_handles(
        job, _crawl(_IG_FB_YT_FOOTER), Settings(_env_file=None, apify_api_token="tok")
    )
    assert out["youtube"] == "typed_yt"
    assert set(out) == {"instagram", "facebook", "youtube"}


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
