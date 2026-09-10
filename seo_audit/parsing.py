"""Pure parsing/scoring logic — no network I/O in this module.

Every function here takes already-fetched content (an HTML string, a
robots.txt string, a sitemap.xml string, response headers) and returns a
plain, inspectable result. Keeping parsing separate from fetching is what
lets the test suite exercise every check against static fixtures with zero
network flakiness — see tests/test_parsing.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin, urldefrag, urlparse
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup

# --------------------------------------------------------------------------
# Heuristic thresholds.
#
# Google has never published a hard character-count limit for titles or
# meta descriptions — its real constraint is a *pixel width* in the SERP,
# which varies by device and font. These ranges are the character-count
# proxies most on-page audits (including the manual one this tool is based
# on) use because most desktop results truncate somewhere near them. They
# are heuristics, not an official rule, and the README says so.
# --------------------------------------------------------------------------
TITLE_MIN_CHARS = 10
TITLE_MAX_CHARS = 60
DESCRIPTION_MIN_CHARS = 50
DESCRIPTION_MAX_CHARS = 160


def _normalize_url(url: str) -> str:
    """Normalize a URL for equality comparisons (scheme/host case, no
    fragment, no trailing slash except for a bare root path)."""
    url, _frag = urldefrag(url)
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    query = parsed.query
    normalized = f"{scheme}://{netloc}{path}"
    if query:
        normalized += f"?{query}"
    return normalized


# --------------------------------------------------------------------------
# Title
# --------------------------------------------------------------------------
@dataclass
class TitleCheck:
    present: bool
    text: str
    length: int
    in_range: bool
    passed: bool  # counts toward the score
    issues: list = field(default_factory=list)


def check_title(soup: BeautifulSoup) -> TitleCheck:
    tag = soup.find("title")
    text = tag.get_text(strip=True) if tag and tag.get_text(strip=True) else ""
    present = bool(text)
    length = len(text)
    issues = []
    if not present:
        issues.append("no <title> tag (or it is empty)")
    elif length < TITLE_MIN_CHARS:
        issues.append(
            f"title is only {length} chars (guidance floor: {TITLE_MIN_CHARS})"
        )
    elif length > TITLE_MAX_CHARS:
        issues.append(
            f"title is {length} chars, over the ~{TITLE_MAX_CHARS} char guidance "
            "(long titles are commonly truncated in search results)"
        )
    in_range = present and TITLE_MIN_CHARS <= length <= TITLE_MAX_CHARS
    return TitleCheck(
        present=present,
        text=text,
        length=length,
        in_range=in_range,
        passed=in_range,
        issues=issues,
    )


# --------------------------------------------------------------------------
# Meta description
# --------------------------------------------------------------------------
@dataclass
class MetaDescriptionCheck:
    present: bool
    text: str
    length: int
    in_range: bool
    passed: bool
    issues: list = field(default_factory=list)


def check_meta_description(soup: BeautifulSoup) -> MetaDescriptionCheck:
    tag = soup.find("meta", attrs={"name": "description"})
    text = (tag.get("content") or "").strip() if tag else ""
    present = bool(text)
    length = len(text)
    issues = []
    if not present:
        issues.append("no <meta name=\"description\"> tag (or it is empty)")
    elif length < DESCRIPTION_MIN_CHARS:
        issues.append(
            f"meta description is only {length} chars "
            f"(guidance floor: {DESCRIPTION_MIN_CHARS})"
        )
    elif length > DESCRIPTION_MAX_CHARS:
        issues.append(
            f"meta description is {length} chars, over the "
            f"~{DESCRIPTION_MAX_CHARS} char guidance (commonly truncated)"
        )
    in_range = present and DESCRIPTION_MIN_CHARS <= length <= DESCRIPTION_MAX_CHARS
    return MetaDescriptionCheck(
        present=present,
        text=text,
        length=length,
        in_range=in_range,
        passed=in_range,
        issues=issues,
    )


# --------------------------------------------------------------------------
# Headings: single H1 + no skipped levels
# --------------------------------------------------------------------------
@dataclass
class HeadingsCheck:
    h1_count: int
    sequence: list  # e.g. [1, 2, 2, 3]
    single_h1: bool
    hierarchy_ok: bool
    passed: bool
    issues: list = field(default_factory=list)


def check_headings(soup: BeautifulSoup) -> HeadingsCheck:
    tags = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    sequence = [int(t.name[1]) for t in tags]
    h1_count = sequence.count(1)
    issues = []

    if h1_count == 0:
        issues.append("no <h1> found")
    elif h1_count > 1:
        issues.append(f"{h1_count} <h1> tags found (expected exactly 1)")
    single_h1 = h1_count == 1

    hierarchy_ok = True
    prev = None
    for level in sequence:
        if prev is not None and level > prev + 1:
            issues.append(f"heading level skips from h{prev} to h{level}")
            hierarchy_ok = False
        prev = level

    return HeadingsCheck(
        h1_count=h1_count,
        sequence=sequence,
        single_h1=single_h1,
        hierarchy_ok=hierarchy_ok,
        passed=single_h1 and hierarchy_ok,
        issues=issues,
    )


# --------------------------------------------------------------------------
# Canonical tag
# --------------------------------------------------------------------------
@dataclass
class CanonicalCheck:
    present: bool
    href: str
    self_consistent: Optional[bool]  # None if not present or can't compare
    passed: bool  # scored: present only (see README on why)
    issues: list = field(default_factory=list)


def check_canonical(soup: BeautifulSoup, page_url: str) -> CanonicalCheck:
    tag = soup.find("link", attrs={"rel": lambda v: v and "canonical" in v})
    href = (tag.get("href") or "").strip() if tag else ""
    present = bool(href)
    issues = []
    self_consistent: Optional[bool] = None

    if not present:
        issues.append("no <link rel=\"canonical\"> tag")
    else:
        resolved = urljoin(page_url, href)
        self_consistent = _normalize_url(resolved) == _normalize_url(page_url)
        if not self_consistent:
            issues.append(
                f"canonical points to a different URL ({resolved}) — "
                "verify this is intentional, not a mistake"
            )

    return CanonicalCheck(
        present=present,
        href=href,
        self_consistent=self_consistent,
        passed=present,
        issues=issues,
    )


# --------------------------------------------------------------------------
# Robots meta tag / X-Robots-Tag header — accidental noindex
# --------------------------------------------------------------------------
@dataclass
class RobotsMetaCheck:
    noindex_in_meta: bool
    noindex_in_header: bool
    passed: bool  # True = no accidental noindex found
    issues: list = field(default_factory=list)


def check_robots_meta(soup: BeautifulSoup, response_headers: dict) -> RobotsMetaCheck:
    noindex_in_meta = False
    for name in ("robots", "googlebot"):
        tag = soup.find("meta", attrs={"name": name})
        if tag and "noindex" in (tag.get("content") or "").lower():
            noindex_in_meta = True

    header_value = ""
    for key, value in (response_headers or {}).items():
        if key.lower() == "x-robots-tag":
            header_value = value
    noindex_in_header = "noindex" in header_value.lower()

    issues = []
    if noindex_in_meta:
        issues.append("meta robots/googlebot tag contains 'noindex'")
    if noindex_in_header:
        issues.append(f"X-Robots-Tag response header contains 'noindex' ({header_value!r})")

    passed = not (noindex_in_meta or noindex_in_header)
    return RobotsMetaCheck(
        noindex_in_meta=noindex_in_meta,
        noindex_in_header=noindex_in_header,
        passed=passed,
        issues=issues,
    )


# --------------------------------------------------------------------------
# robots.txt
# --------------------------------------------------------------------------
@dataclass
class RobotsTxtCheck:
    fetched: bool
    disallows_all: bool
    sitemap_urls: list
    passed: bool  # True = does not block every crawler from everything
    issues: list = field(default_factory=list)


def parse_robots_txt(text: Optional[str]) -> RobotsTxtCheck:
    """`text` is None if robots.txt returned a non-200 (treated as: no
    robots.txt, which is not a defect — Google's default is "crawl
    everything" when robots.txt is absent)."""
    if text is None:
        return RobotsTxtCheck(
            fetched=False, disallows_all=False, sitemap_urls=[], passed=True, issues=[]
        )

    sitemap_urls = []
    groups = []  # list of (user_agents: [str], disallows: [str], allows: [str])
    current_agents: list = []
    current_disallows: list = []
    current_allows: list = []

    def flush():
        if current_agents:
            groups.append((list(current_agents), list(current_disallows), list(current_allows)))

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field_name, _, value = line.partition(":")
        field_name = field_name.strip().lower()
        value = value.strip()
        if field_name == "sitemap":
            sitemap_urls.append(value)
        elif field_name == "user-agent":
            # a new User-agent line right after disallow/allow lines starts
            # a new group; a run of consecutive user-agent lines belongs to
            # the same group.
            if current_disallows or current_allows:
                flush()
                current_agents, current_disallows, current_allows = [], [], []
            current_agents.append(value)
        elif field_name == "disallow" and current_agents:
            current_disallows.append(value)
        elif field_name == "allow" and current_agents:
            current_allows.append(value)
    flush()

    disallows_all = False
    for agents, disallows, allows in groups:
        applies_to_everyone = any(a.strip() == "*" for a in agents)
        if applies_to_everyone and "/" in [d.strip() for d in disallows]:
            # Blocking "/" is only a full block if nothing more specific
            # allows paths back in.
            if not allows:
                disallows_all = True

    issues = []
    if disallows_all:
        issues.append("robots.txt has 'User-agent: *' + 'Disallow: /' — blocks all crawlers from the whole site")

    return RobotsTxtCheck(
        fetched=True,
        disallows_all=disallows_all,
        sitemap_urls=sitemap_urls,
        passed=not disallows_all,
        issues=issues,
    )


# --------------------------------------------------------------------------
# sitemap.xml
# --------------------------------------------------------------------------
@dataclass
class SitemapCheck:
    fetched: bool
    well_formed: bool
    is_index: bool
    urls: list
    passed: bool
    issues: list = field(default_factory=list)


def parse_sitemap(text: Optional[str]) -> SitemapCheck:
    if text is None:
        return SitemapCheck(
            fetched=False, well_formed=False, is_index=False, urls=[],
            passed=False, issues=["no sitemap.xml found (checked conventional location + robots.txt Sitemap: line)"],
        )

    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        return SitemapCheck(
            fetched=True, well_formed=False, is_index=False, urls=[],
            passed=False, issues=[f"sitemap.xml is not well-formed XML: {exc}"],
        )

    tag = root.tag.rsplit("}", 1)[-1]  # strip XML namespace
    urls = []
    is_index = tag == "sitemapindex"
    child_tag = "sitemap" if is_index else "url"
    loc_tag = "loc"
    for child in root:
        child_local = child.tag.rsplit("}", 1)[-1]
        if child_local != child_tag:
            continue
        for grandchild in child:
            if grandchild.tag.rsplit("}", 1)[-1] == loc_tag and grandchild.text:
                urls.append(grandchild.text.strip())

    issues = []
    if not urls:
        issues.append("sitemap.xml parsed but contains zero <loc> entries")

    return SitemapCheck(
        fetched=True,
        well_formed=True,
        is_index=is_index,
        urls=urls,
        passed=bool(urls),
        issues=issues,
    )


# --------------------------------------------------------------------------
# Image alt coverage (informational — not part of the score, see README)
# --------------------------------------------------------------------------
@dataclass
class ImageAltCheck:
    total_images: int
    missing_alt: int
    coverage_pct: float
    missing_srcs: list = field(default_factory=list)


def check_image_alt(soup: BeautifulSoup) -> ImageAltCheck:
    imgs = soup.find_all("img")
    total = len(imgs)
    missing = []
    for img in imgs:
        alt = img.get("alt")
        if alt is None or not alt.strip():
            missing.append(img.get("src", "(no src)"))
    coverage = 100.0 if total == 0 else round((total - len(missing)) / total * 100, 1)
    return ImageAltCheck(
        total_images=total,
        missing_alt=len(missing),
        coverage_pct=coverage,
        missing_srcs=missing,
    )


# --------------------------------------------------------------------------
# Open Graph / Twitter Card presence (informational — not part of the score)
# --------------------------------------------------------------------------
@dataclass
class SocialTagsCheck:
    og_found: list
    og_missing: list
    twitter_found: list
    twitter_missing: list


OG_EXPECTED = ["og:title", "og:description", "og:image", "og:url"]
TWITTER_EXPECTED = ["twitter:card", "twitter:title", "twitter:description"]


def check_social_tags(soup: BeautifulSoup) -> SocialTagsCheck:
    og_found, og_missing = [], []
    for prop in OG_EXPECTED:
        tag = soup.find("meta", attrs={"property": prop})
        (og_found if tag and tag.get("content") else og_missing).append(prop)

    twitter_found, twitter_missing = [], []
    for name in TWITTER_EXPECTED:
        tag = soup.find("meta", attrs={"name": name})
        (twitter_found if tag and tag.get("content") else twitter_missing).append(name)

    return SocialTagsCheck(
        og_found=og_found, og_missing=og_missing,
        twitter_found=twitter_found, twitter_missing=twitter_missing,
    )


# --------------------------------------------------------------------------
# Internal link extraction (crawling itself lives in fetch.py, which needs
# the network; this part — "which links on this page are same-origin and
# worth following" — is pure and fixture-testable).
# --------------------------------------------------------------------------
def extract_internal_links(html: str, page_url: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    origin = urlparse(page_url)
    seen = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        absolute = urljoin(page_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in ("http", "https"):
            continue
        if parsed.netloc != origin.netloc:
            continue
        absolute, _ = urldefrag(absolute)
        if absolute not in seen:
            seen.append(absolute)
    return seen


def make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")
