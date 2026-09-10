from __future__ import annotations

import argparse
import sys

from . import report
from .audit import run_audit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="seo-audit",
        description="A small, $0, no-account on-page SEO audit CLI. See README for what it checks.",
    )
    parser.add_argument("url", help="Page to audit, e.g. https://example.com")
    parser.add_argument(
        "--check-links", action="store_true",
        help="Also crawl same-origin internal links and check their HTTP status (slower).",
    )
    parser.add_argument(
        "--depth", type=int, default=1,
        help="How many hops to crawl when --check-links is set (default: 1).",
    )
    parser.add_argument(
        "--max-pages", type=int, default=25,
        help="Cap on pages crawled when --check-links is set (default: 25).",
    )
    parser.add_argument(
        "--sitemap-sample", type=int, default=5,
        help="How many sitemap URLs to spot-check for a 200 response (default: 5).",
    )
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON instead of text.")
    parser.add_argument("--timeout", type=int, default=10, help="Per-request timeout in seconds (default: 10).")
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not (args.url.startswith("http://") or args.url.startswith("https://")):
        args.url = "https://" + args.url

    try:
        result = run_audit(
            args.url,
            check_links=args.check_links,
            link_crawl_depth=args.depth,
            link_crawl_max_pages=args.max_pages,
            sitemap_sample_size=args.sitemap_sample,
            timeout=args.timeout,
        )
    except Exception as exc:  # noqa: BLE001 — CLI boundary: report, don't traceback-spam the user
        print(f"error: could not audit {args.url}: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(report.to_json(result))
    else:
        print(report.to_text(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
