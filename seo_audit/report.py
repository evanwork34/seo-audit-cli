"""Turns an AuditResult into human-readable text or a JSON-serializable dict.
No formatting logic lives in audit.py — this module is the only place that
decides how findings are displayed."""

from __future__ import annotations

import json
from dataclasses import asdict

from .audit import AuditResult

PASS = "PASS"
FAIL = "FAIL"


def _mark(passed: bool) -> str:
    return PASS if passed else FAIL


def to_dict(result: AuditResult) -> dict:
    d = asdict(result)
    return d


def to_json(result: AuditResult) -> str:
    return json.dumps(to_dict(result), indent=2)


def to_text(result: AuditResult) -> str:
    lines = []
    lines.append(f"SEO audit: {result.url}")
    if result.final_url != result.url:
        lines.append(f"  (redirected to {result.final_url})")
    lines.append(f"HTTP status: {result.status_code}")
    lines.append("")
    lines.append(f"SCORE: {result.score}/100  ({result.points_earned}/{result.points_possible} checks passed)")
    lines.append("")

    def section(name: str, passed: bool, issues: list):
        lines.append(f"[{_mark(passed)}] {name}")
        for issue in issues:
            lines.append(f"       - {issue}")

    section("Title tag", result.title.passed, result.title.issues)
    if result.title.present:
        lines.append(f"       \"{result.title.text}\" ({result.title.length} chars)")

    section("Meta description", result.meta_description.passed, result.meta_description.issues)
    if result.meta_description.present:
        lines.append(f"       \"{result.meta_description.text}\" ({result.meta_description.length} chars)")

    section(
        "Headings (single H1 + no skipped levels)",
        result.headings.single_h1 and result.headings.hierarchy_ok,
        result.headings.issues,
    )
    lines.append(f"       sequence: {result.headings.sequence}")

    section("Canonical tag", result.canonical.passed, result.canonical.issues)
    if result.canonical.present:
        lines.append(f"       -> {result.canonical.href}")

    section("Robots meta / X-Robots-Tag (no accidental noindex)", result.robots_meta.passed, result.robots_meta.issues)

    section("robots.txt", result.robots_txt.passed, result.robots_txt.issues)
    if result.robots_txt.sitemap_urls:
        lines.append(f"       sitemap(s) declared: {result.robots_txt.sitemap_urls}")

    section("sitemap.xml", result.sitemap.passed, result.sitemap.issues)
    if result.sitemap.fetched:
        kind = "sitemap index" if result.sitemap.is_index else "urlset"
        lines.append(f"       {kind}, {len(result.sitemap.urls)} <loc> entries")
    if result.sitemap_sample_checked:
        broken_n = len(result.sitemap_sample_broken)
        lines.append(
            f"       sampled {result.sitemap_sample_checked} sitemap URLs, "
            f"{result.sitemap_sample_checked - broken_n} resolved 200"
        )
        for u, status in result.sitemap_sample_broken:
            lines.append(f"         - {u} -> {status if status is not None else 'request failed'}")

    lines.append("")
    lines.append("Informational (not part of the score — see README):")
    lines.append(
        f"  Image alt coverage: {result.image_alt.coverage_pct}% "
        f"({result.image_alt.total_images - result.image_alt.missing_alt}/{result.image_alt.total_images} images have alt text)"
    )
    for src in result.image_alt.missing_srcs[:10]:
        lines.append(f"    - missing alt: {src}")
    if len(result.image_alt.missing_srcs) > 10:
        lines.append(f"    ... and {len(result.image_alt.missing_srcs) - 10} more")

    lines.append(
        f"  Open Graph tags found: {result.social_tags.og_found or 'none'}"
        + (f" (missing: {result.social_tags.og_missing})" if result.social_tags.og_missing else "")
    )
    lines.append(
        f"  Twitter Card tags found: {result.social_tags.twitter_found or 'none'}"
        + (f" (missing: {result.social_tags.twitter_missing})" if result.social_tags.twitter_missing else "")
    )

    if result.link_crawl_checked:
        lines.append(
            f"  Internal link crawl: checked {result.link_crawl_checked} same-origin URLs, "
            f"{len(result.link_crawl_broken)} broken"
        )
        for u, status in result.link_crawl_broken[:15]:
            lines.append(f"    - {u} -> {status if status is not None else 'request failed'}")
        if len(result.link_crawl_broken) > 15:
            lines.append(f"    ... and {len(result.link_crawl_broken) - 15} more")
    else:
        lines.append(f"  Internal link crawl: skipped ({result.link_crawl_skipped_reason})")

    return "\n".join(lines)
