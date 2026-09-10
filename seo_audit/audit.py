"""Orchestrates one full audit run: fetch the page + robots.txt + sitemap.xml,
run every check in seo_audit.parsing against the results, sample the sitemap,
optionally crawl internal links, and compute the score.

Score arithmetic (documented here, not buried): 10 core checks, each worth
exactly 1 point, no partial credit, no hidden weighting:

  1. Title present
  2. Title length within the ~10-60 char guidance range
  3. Meta description present
  4. Meta description length within the ~50-160 char guidance range
  5. Exactly one <h1>
  6. No skipped heading levels
  7. Canonical tag present
  8. No accidental noindex (meta robots or X-Robots-Tag header)
  9. robots.txt does not block every crawler from the whole site
  10. sitemap.xml exists, is well-formed, and lists at least one URL

score = (points earned / 10) * 100

Image alt coverage, Open Graph/Twitter tag presence, sitemap URL sampling,
and the internal broken-link crawl are all reported but deliberately NOT
folded into the score — see README "Why isn't X in the score?".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import random

from . import fetch, parsing

SCORE_DENOMINATOR = 10


@dataclass
class AuditResult:
    url: str
    final_url: str
    status_code: int
    score: int
    points_earned: int
    points_possible: int
    title: parsing.TitleCheck
    meta_description: parsing.MetaDescriptionCheck
    headings: parsing.HeadingsCheck
    canonical: parsing.CanonicalCheck
    robots_meta: parsing.RobotsMetaCheck
    robots_txt: parsing.RobotsTxtCheck
    sitemap: parsing.SitemapCheck
    image_alt: parsing.ImageAltCheck
    social_tags: parsing.SocialTagsCheck
    sitemap_sample_checked: int = 0
    sitemap_sample_broken: list = field(default_factory=list)
    link_crawl_checked: int = 0
    link_crawl_broken: list = field(default_factory=list)
    link_crawl_skipped_reason: str = ""


def run_audit(
    url: str,
    check_links: bool = False,
    link_crawl_depth: int = 1,
    link_crawl_max_pages: int = 25,
    sitemap_sample_size: int = 5,
    timeout: int = 10,
) -> AuditResult:
    session = fetch._session()  # noqa: SLF001 (intentional: one UA/session for the whole run)

    page = fetch.fetch_page(url, session=session, timeout=timeout)
    soup = parsing.make_soup(page.html)

    title = parsing.check_title(soup)
    meta_description = parsing.check_meta_description(soup)
    headings = parsing.check_headings(soup)
    canonical = parsing.check_canonical(soup, page.url)
    robots_meta = parsing.check_robots_meta(soup, page.headers)
    image_alt = parsing.check_image_alt(soup)
    social_tags = parsing.check_social_tags(soup)

    robots_txt_text = fetch.fetch_text_or_none(fetch.robots_txt_url(page.url), session=session, timeout=timeout)
    robots_txt = parsing.parse_robots_txt(robots_txt_text)

    sitemap_text = None
    for candidate in fetch.sitemap_url_candidates(page.url, robots_txt.sitemap_urls):
        sitemap_text = fetch.fetch_text_or_none(candidate, session=session, timeout=timeout)
        if sitemap_text is not None:
            break
    sitemap = parsing.parse_sitemap(sitemap_text)

    checks = [
        title.present,        # 1. title present
        title.in_range,       # 2. title length in guidance range
        meta_description.present,   # 3. meta description present
        meta_description.in_range,  # 4. meta description length in guidance range
        headings.single_h1,   # 5. exactly one h1
        headings.hierarchy_ok,  # 6. no skipped heading levels
        canonical.passed,     # 7. canonical tag present
        robots_meta.passed,   # 8. no accidental noindex
        robots_txt.passed,    # 9. robots.txt doesn't block everyone
        sitemap.passed,       # 10. sitemap.xml exists, valid, non-empty
    ]
    # Each line above is exactly one of the 10 numbered checks in this
    # module's docstring, in the same order, with no hidden weighting.
    points_earned = sum(1 for c in checks if c)
    points_possible = SCORE_DENOMINATOR
    score = round(points_earned / points_possible * 100)

    result = AuditResult(
        url=url,
        final_url=page.url,
        status_code=page.status_code,
        score=score,
        points_earned=points_earned,
        points_possible=points_possible,
        title=title,
        meta_description=meta_description,
        headings=headings,
        canonical=canonical,
        robots_meta=robots_meta,
        robots_txt=robots_txt,
        sitemap=sitemap,
        image_alt=image_alt,
        social_tags=social_tags,
    )

    if sitemap.urls:
        sample = sitemap.urls if len(sitemap.urls) <= sitemap_sample_size else random.sample(sitemap.urls, sitemap_sample_size)
        broken = []
        for sample_url in sample:
            status = fetch.check_url_status(sample_url, session=session, timeout=timeout)
            if status is None or status >= 400:
                broken.append((sample_url, status))
        result.sitemap_sample_checked = len(sample)
        result.sitemap_sample_broken = broken

    if check_links:
        checked, broken = fetch.crawl_internal_links(
            page.url, max_depth=link_crawl_depth, max_pages=link_crawl_max_pages,
            session=session, timeout=timeout,
        )
        result.link_crawl_checked = len(checked)
        result.link_crawl_broken = broken
    else:
        result.link_crawl_skipped_reason = "pass --check-links to crawl same-origin links and check their status"

    return result
