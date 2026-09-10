"""Positive control (good.html — zero defects) and negative control
(bad.html — a known, deliberate set of defects) for every pure check in
seo_audit/parsing.py. No network involved anywhere in this file."""

from pathlib import Path

from seo_audit import parsing

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> str:
    return (FIXTURES / name).read_text()


def soup_of(name: str):
    return parsing.make_soup(load(name))


# --------------------------------------------------------------------------
# Positive control: good.html has none of the defects this tool looks for.
# --------------------------------------------------------------------------
def test_good_html_title_passes():
    result = parsing.check_title(soup_of("good.html"))
    assert result.present is True
    assert result.in_range is True
    assert result.passed is True
    assert result.issues == []


def test_good_html_meta_description_passes():
    result = parsing.check_meta_description(soup_of("good.html"))
    assert result.present is True
    assert result.in_range is True
    assert result.issues == []


def test_good_html_headings_pass():
    result = parsing.check_headings(soup_of("good.html"))
    assert result.h1_count == 1
    assert result.single_h1 is True
    assert result.hierarchy_ok is True
    assert result.issues == []


def test_good_html_canonical_self_consistent():
    result = parsing.check_canonical(soup_of("good.html"), "https://example.com/")
    assert result.present is True
    assert result.self_consistent is True
    assert result.issues == []


def test_good_html_no_noindex():
    result = parsing.check_robots_meta(soup_of("good.html"), {})
    assert result.noindex_in_meta is False
    assert result.noindex_in_header is False
    assert result.passed is True


def test_good_html_images_all_have_alt():
    result = parsing.check_image_alt(soup_of("good.html"))
    assert result.total_images == 2
    assert result.missing_alt == 0
    assert result.coverage_pct == 100.0
    assert result.missing_srcs == []


def test_good_html_social_tags_all_present():
    result = parsing.check_social_tags(soup_of("good.html"))
    assert set(result.og_found) == set(parsing.OG_EXPECTED)
    assert result.og_missing == []
    assert set(result.twitter_found) == set(parsing.TWITTER_EXPECTED)
    assert result.twitter_missing == []


# --------------------------------------------------------------------------
# Negative control: bad.html has exactly these defects, deliberately.
# --------------------------------------------------------------------------
def test_bad_html_title_missing():
    result = parsing.check_title(soup_of("bad.html"))
    assert result.present is False
    assert result.passed is False
    assert "no <title> tag (or it is empty)" in result.issues[0]


def test_bad_html_meta_description_missing():
    result = parsing.check_meta_description(soup_of("bad.html"))
    assert result.present is False
    assert result.passed is False


def test_bad_html_headings_multiple_h1_and_skip():
    result = parsing.check_headings(soup_of("bad.html"))
    assert result.h1_count == 2
    assert result.single_h1 is False
    assert result.hierarchy_ok is False
    assert result.sequence == [1, 1, 3]
    assert any("2 <h1>" in issue for issue in result.issues)
    assert any("skips from h1 to h3" in issue for issue in result.issues)


def test_bad_html_no_canonical():
    result = parsing.check_canonical(soup_of("bad.html"), "https://example.com/bad")
    assert result.present is False
    assert result.passed is False


def test_bad_html_noindex_detected():
    result = parsing.check_robots_meta(soup_of("bad.html"), {})
    assert result.noindex_in_meta is True
    assert result.passed is False


def test_bad_html_noindex_header_detected_independently_of_meta():
    # A clean page whose SERVER still sends X-Robots-Tag: noindex should be
    # caught even though the HTML itself has no noindex meta tag.
    result = parsing.check_robots_meta(soup_of("good.html"), {"X-Robots-Tag": "noindex"})
    assert result.noindex_in_meta is False
    assert result.noindex_in_header is True
    assert result.passed is False


def test_bad_html_two_of_three_images_missing_alt():
    result = parsing.check_image_alt(soup_of("bad.html"))
    assert result.total_images == 3
    assert result.missing_alt == 2
    assert result.coverage_pct == round(1 / 3 * 100, 1)
    assert "/b.jpg" in result.missing_srcs
    assert "/c.jpg" in result.missing_srcs
    assert "/a.jpg" not in result.missing_srcs


def test_bad_html_no_social_tags():
    result = parsing.check_social_tags(soup_of("bad.html"))
    assert result.og_found == []
    assert result.twitter_found == []
    assert set(result.og_missing) == set(parsing.OG_EXPECTED)


# --------------------------------------------------------------------------
# robots.txt parsing
# --------------------------------------------------------------------------
def test_robots_txt_normal_allows_crawling():
    result = parsing.parse_robots_txt(load("robots_ok.txt"))
    assert result.fetched is True
    assert result.disallows_all is False
    assert result.passed is True
    assert result.sitemap_urls == ["https://example.com/sitemap.xml"]


def test_robots_txt_blocks_everything():
    result = parsing.parse_robots_txt(load("robots_blocked.txt"))
    assert result.disallows_all is True
    assert result.passed is False
    assert "blocks all crawlers" in result.issues[0]


def test_robots_txt_missing_is_not_a_defect():
    result = parsing.parse_robots_txt(None)
    assert result.fetched is False
    assert result.passed is True
    assert result.issues == []


# --------------------------------------------------------------------------
# sitemap.xml parsing
# --------------------------------------------------------------------------
def test_sitemap_valid():
    result = parsing.parse_sitemap(load("sitemap_valid.xml"))
    assert result.well_formed is True
    assert result.is_index is False
    assert len(result.urls) == 3
    assert result.passed is True


def test_sitemap_invalid_xml():
    result = parsing.parse_sitemap(load("sitemap_invalid.xml"))
    assert result.well_formed is False
    assert result.passed is False
    assert "not well-formed" in result.issues[0]


def test_sitemap_missing_is_a_defect():
    result = parsing.parse_sitemap(None)
    assert result.fetched is False
    assert result.passed is False
    assert "no sitemap.xml found" in result.issues[0]


# --------------------------------------------------------------------------
# Internal link extraction
# --------------------------------------------------------------------------
def test_extract_internal_links_filters_correctly():
    html = """
    <a href="/about">About</a>
    <a href="https://example.com/contact">Contact</a>
    <a href="https://other-site.com/page">External</a>
    <a href="mailto:hi@example.com">Email</a>
    <a href="tel:+15551234567">Call</a>
    <a href="#section">Jump</a>
    <a href="javascript:void(0)">JS</a>
    <a href="/about#team">About (again, different fragment)</a>
    """
    links = parsing.extract_internal_links(html, "https://example.com/")
    assert "https://example.com/about" in links
    assert "https://example.com/contact" in links
    assert not any("other-site.com" in link for link in links)
    assert not any(link.startswith("mailto:") for link in links)
    assert not any(link.startswith("tel:") for link in links)
    # /about and /about#team dedupe to the same URL once the fragment is stripped
    assert links.count("https://example.com/about") == 1
