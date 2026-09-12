# seo-audit-cli

A small, honest, **$0** on-page/technical SEO audit command-line tool. No API
keys, no accounts, no paid services — every check is a plain, unauthenticated
HTTP fetch plus HTML/XML parsing.

This is the open-source core of the checks
[EliteSEO Consulting](https://eliteseo.evan-work34.workers.dev) runs by hand for
clients, extracted into a standalone tool. It is brand new — there is no user
base, no "used by," no track record to claim, and this README makes none.

## What it checks

10 checks feed the score (see "How the score works" below):

1. Title tag present
2. Title length within the ~10–60 char guidance range
3. Meta description present
4. Meta description length within the ~50–160 char guidance range
5. Exactly one `<h1>`
6. No skipped heading levels (e.g. `<h1>` straight to `<h3>`)
7. Canonical tag (`<link rel="canonical">`) present
8. No accidental `noindex` (checks both the `<meta name="robots">` tag and
   the `X-Robots-Tag` HTTP response header — a noindex set at the server
   level is invisible if you only look at the HTML)
9. `robots.txt` does not block every crawler from the entire site
10. `sitemap.xml` exists (checked at `/sitemap.xml` and any `Sitemap:` line
    declared in `robots.txt`), is well-formed XML, and lists at least one URL

Reported but **not** scored (see "Why isn't X in the score?"):

- Image `<img alt>` coverage — percentage of images with non-empty alt text
- Open Graph / Twitter Card tag presence
- A sample of sitemap URLs, spot-checked for a `200` response
- `--check-links`: a same-origin crawl (configurable depth/page cap) that
  reports any internal link returning a non-200 status or failing to resolve

## What it deliberately does not do

No Core Web Vitals, no PageSpeed/Lighthouse scoring, no backlink data, no
keyword rankings, no AI-generated recommendations. Those all require either a
paid API, a headless browser, or an account — this tool's entire value is
that it needs none of that. For a fuller audit, pair it with Google Search
Console (free, but requires an account) or a paid tool.

## Install

```bash
git clone https://github.com/evanwork34/seo-audit-cli.git
cd seo-audit-cli
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

Requires Python 3.9+. Two dependencies: `requests` and `beautifulsoup4`.

## Usage

```bash
seo-audit https://example.com
seo-audit https://example.com --json                 # machine-readable output
seo-audit https://example.com --check-links           # also crawl same-origin links
seo-audit https://example.com --check-links --depth 2 --max-pages 50
```

Or without installing: `python -m seo_audit https://example.com`

## How the score works

`score = (checks passed / 10) * 100`. Each of the 10 checks listed above is
worth exactly one point — no partial credit, no hidden weighting, no check
worth more than another. The arithmetic is in
[`seo_audit/audit.py`](seo_audit/audit.py) (`run_audit`, the `checks` list),
not hidden behind a black-box formula.

### Why isn't X in the score?

- **Image alt coverage** is a percentage, and folding a percentage into a
  fixed 10-point score means picking an arbitrary threshold ("80% is fine,
  70% isn't?") this tool has no basis for. It's reported plainly instead —
  you decide what coverage is acceptable for your site.
- **Open Graph / Twitter tags** matter for social sharing, not search
  ranking directly — real, but a different axis than the other 10 checks.
- **Sitemap URL sampling** and **the internal link crawl** both depend on
  parameters you control (`--depth`, `--max-pages`, sample size). A score
  that changes when you change how hard you look isn't a fair score.

## Example output

Run live against EliteSEO Consulting's own site
(`https://eliteseo.evan-work34.workers.dev`) on **2026-09-09**:

```
$ seo-audit https://eliteseo.evan-work34.workers.dev --check-links --max-pages 15

SEO audit: https://eliteseo.evan-work34.workers.dev
  (redirected to https://eliteseo.evan-work34.workers.dev/)
HTTP status: 200

SCORE: 100/100  (10/10 checks passed)

[PASS] Title tag
       "SEO Agency for Businesses That Sell | EliteSEO Consulting" (57 chars)
[PASS] Meta description
       "SEO consultancy running since 2022. Technical fixes, local visibility, and content built for buying intent. Get a free SEO audit of your site." (142 chars)
[PASS] Headings (single H1 + no skipped levels)
       sequence: [1, 2, 2, 2, 2, 2, 2, 2]
[PASS] Canonical tag
       -> https://eliteseo.evan-work34.workers.dev
[PASS] Robots meta / X-Robots-Tag (no accidental noindex)
[PASS] robots.txt
       sitemap(s) declared: ['https://eliteseo.evan-work34.workers.dev/sitemap.xml']
[PASS] sitemap.xml
       urlset, 30 <loc> entries
       sampled 5 sitemap URLs, 5 resolved 200

Informational (not part of the score — see README):
  Image alt coverage: 100.0% (1/1 images have alt text)
  Open Graph tags found: ['og:title', 'og:description', 'og:image', 'og:url']
  Twitter Card tags found: ['twitter:card', 'twitter:title', 'twitter:description']
  Internal link crawl: checked 25 same-origin URLs, 0 broken
```

For comparison, a real site missing a few of the checked items —
`https://example.com` on the same date:

```
$ seo-audit https://example.com

SCORE: 60/100  (6/10 checks passed)

[PASS] Title tag
       "Example Domain" (14 chars)
[FAIL] Meta description
       - no <meta name="description"> tag (or it is empty)
[PASS] Headings (single H1 + no skipped levels)
       sequence: [1]
[FAIL] Canonical tag
       - no <link rel="canonical"> tag
[PASS] Robots meta / X-Robots-Tag (no accidental noindex)
[PASS] robots.txt
[FAIL] sitemap.xml
       - no sitemap.xml found (checked conventional location + robots.txt Sitemap: line)
```

Both runs are real, unedited tool output — not illustrative/mocked examples.

## Benchmark

[`BENCHMARK.md`](BENCHMARK.md) runs this same scan against six real,
currently-live consulting/agency homepages (plus EliteSEO Consulting's own
site for reference) — real scores, dated, with the exact reproduction
command for each. It's a sanity check on the tool, not a ranking of anyone's
SEO skill; see that file for the disclaimer on what a homepage scan can and
can't tell you.

## Tests

```bash
pip install -e ".[dev]"
pytest
```

24 tests, all passing as of this writing: a positive control (a clean
fixture page with none of the 10 defects) and a negative control (a fixture
page with a deliberately known set of defects — missing title, missing meta
description, duplicate `<h1>`, a skipped heading level, no canonical,
`noindex` meta tag, 2 of 3 images missing alt, no social tags), asserting
each check reports *exactly* the defects present and nothing else — plus
`robots.txt`/`sitemap.xml` parsing tests (valid, blocking, malformed,
missing) and a full end-to-end scoring test with the network mocked out.
Parsing logic (`seo_audit/parsing.py`) has zero network dependency by
design, so these tests run in well under a second with no live requests.

## License

MIT — see [LICENSE](LICENSE).
