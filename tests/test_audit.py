"""Exercises the full audit.run_audit() scoring pipeline with the network
faked out (monkeypatched), against the same good/bad HTML fixtures used in
test_parsing.py. This is the test that would fail if the score arithmetic
in audit.py ever drifted from the checks it claims to count."""

from pathlib import Path

import pytest

from seo_audit import audit, fetch

FIXTURES = Path(__file__).parent / "fixtures"


def _fake_fetch_page(url, session=None, timeout=10):
    html = (FIXTURES / "good.html").read_text() if "good" in url else (FIXTURES / "bad.html").read_text()
    return fetch.FetchedPage(url=url, status_code=200, headers={}, html=html)


def _fake_fetch_text_or_none(url, session=None, timeout=10):
    if url.endswith("robots.txt"):
        return (FIXTURES / "robots_ok.txt").read_text()
    if url.endswith("sitemap.xml"):
        return (FIXTURES / "sitemap_valid.xml").read_text()
    return None


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(fetch, "fetch_page", _fake_fetch_page)
    monkeypatch.setattr(fetch, "fetch_text_or_none", _fake_fetch_text_or_none)
    monkeypatch.setattr(fetch, "check_url_status", lambda *a, **k: 200)


def test_good_page_scores_10_of_10():
    result = audit.run_audit("https://example.com/good")
    assert result.points_earned == 10
    assert result.points_possible == 10
    assert result.score == 100


def test_bad_page_loses_exactly_the_expected_points():
    result = audit.run_audit("https://example.com/bad")
    # bad.html fails: title present, title in-range, meta desc present,
    # meta desc in-range, single-h1, hierarchy-ok, canonical-present,
    # no-noindex — 8 failures — but robots.txt and sitemap are faked clean
    # for this test, so it still earns those 2 points.
    assert result.points_earned == 2
    assert result.score == 20
    assert result.title.passed is False
    assert result.meta_description.passed is False
    assert result.headings.single_h1 is False
    assert result.headings.hierarchy_ok is False
    assert result.canonical.passed is False
    assert result.robots_meta.passed is False
    assert result.robots_txt.passed is True
    assert result.sitemap.passed is True
