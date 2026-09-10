"""All network I/O lives here. Every request is a plain, unauthenticated
GET — no API keys, no cookies/session persistence, no telemetry sent
anywhere. Kept separate from seo_audit/parsing.py so the parsing logic can
be unit-tested without a network."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests

USER_AGENT = "seo-audit-cli/0.1 (+https://github.com/evanwork34/seo-audit-cli)"
DEFAULT_TIMEOUT = 10


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s


@dataclass
class FetchedPage:
    url: str  # final URL after redirects
    status_code: int
    headers: dict
    html: str


def fetch_page(url: str, session: Optional[requests.Session] = None, timeout: int = DEFAULT_TIMEOUT) -> FetchedPage:
    session = session or _session()
    resp = session.get(url, timeout=timeout, allow_redirects=True)
    return FetchedPage(
        url=resp.url,
        status_code=resp.status_code,
        headers=dict(resp.headers),
        html=resp.text,
    )


def fetch_text_or_none(url: str, session: Optional[requests.Session] = None, timeout: int = DEFAULT_TIMEOUT) -> Optional[str]:
    """GET a URL, returning its body text, or None if it 404s / errors.
    Used for robots.txt and sitemap.xml, where a 404 is a meaningful,
    non-exceptional result (site simply doesn't have one)."""
    session = session or _session()
    try:
        resp = session.get(url, timeout=timeout, allow_redirects=True)
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    return resp.text


def robots_txt_url(page_url: str) -> str:
    parsed = urlparse(page_url)
    return f"{parsed.scheme}://{parsed.netloc}/robots.txt"


def sitemap_url_candidates(page_url: str, robots_sitemap_urls: list) -> list:
    """Sitemap declared in robots.txt takes priority; conventional
    /sitemap.xml is the fallback."""
    parsed = urlparse(page_url)
    conventional = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
    candidates = list(robots_sitemap_urls)
    if conventional not in candidates:
        candidates.append(conventional)
    return candidates


def check_url_status(url: str, session: Optional[requests.Session] = None, timeout: int = DEFAULT_TIMEOUT) -> Optional[int]:
    """HEAD (falling back to GET if HEAD isn't allowed) a URL, returning its
    status code, or None if the request errored entirely (DNS failure,
    connection refused, timeout)."""
    session = session or _session()
    try:
        resp = session.head(url, timeout=timeout, allow_redirects=True)
        if resp.status_code >= 400:
            # Some servers don't implement HEAD correctly; confirm with GET
            # before reporting a page as broken.
            resp = session.get(url, timeout=timeout, allow_redirects=True)
        return resp.status_code
    except requests.RequestException:
        return None


def crawl_internal_links(
    start_url: str,
    max_depth: int = 1,
    max_pages: int = 25,
    session: Optional[requests.Session] = None,
    timeout: int = DEFAULT_TIMEOUT,
):
    """Breadth-first same-origin crawl from start_url, up to max_depth
    hops, checking every discovered internal link's status. Returns
    (checked: {url: status_or_None}, broken: [(url, status_or_None)])."""
    from .parsing import extract_internal_links  # local import: avoids a cycle at module load

    session = session or _session()
    checked: dict = {}
    to_visit = [(start_url, 0)]
    visited_pages = set()

    while to_visit and len(visited_pages) < max_pages:
        url, depth = to_visit.pop(0)
        if url in visited_pages:
            continue
        visited_pages.add(url)

        try:
            page = fetch_page(url, session=session, timeout=timeout)
        except requests.RequestException:
            checked[url] = None
            continue

        checked[url] = page.status_code
        if page.status_code >= 400 or depth >= max_depth:
            continue

        for link in extract_internal_links(page.html, page.url):
            if link not in checked and link not in [u for u, _ in to_visit]:
                to_visit.append((link, depth + 1))

    # Any link discovered but never actually fetched (because max_pages was
    # hit) still gets its status checked with a cheap HEAD, so "checked"
    # reflects every same-origin link found, not just the ones crawled into.
    for url, _depth in to_visit:
        if url not in checked:
            checked[url] = check_url_status(url, session=session, timeout=timeout)

    broken = [(url, status) for url, status in checked.items() if status is None or status >= 400]
    return checked, broken
