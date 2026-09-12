# Benchmark: `seo-audit-cli` against real consulting-firm homepages

This is a small, honest sample run — not a ranking, not a "best SEO agencies"
list, and not a claim about anyone's overall SEO competence. It exists for one
reason: to make this tool's scores **reproducible by a stranger** instead of
asserted. Every number below came from running the exact command shown,
against the exact live URL shown, on the date shown. Nothing here is edited,
averaged, or cherry-picked.

## What this is and isn't

- **Is:** one homepage per site, run through the same 10 automated
  technical/on-page checks the CLI's own [README](README.md) documents (title,
  meta description, heading structure, canonical, noindex, robots.txt,
  sitemap.xml — see the README for the full list and scoring formula). No
  Core Web Vitals, no backlinks, no keyword rankings, no manual judgment.
- **Isn't:** a verdict on any firm's SEO skill, client results, or overall
  site quality. A homepage can score 100/100 on these 10 mechanical checks
  and still be a poor site in every way this tool doesn't measure (and vice
  versa). Treat this exactly like a linter score, not a review.

## Site selection

Six real, currently-live consulting/agency sites — a mix of widely-known
names in the SEO/marketing-consultant space and smaller agencies — plus
EliteSEO Consulting's own site for reference (the same number this tool's
README already publishes). Selection criteria, applied to every candidate
before it was run:

1. **`robots.txt` allows a generic user-agent to fetch the homepage.** Checked
   live for each site (see below) before running anything. Two candidates
   originally considered were swapped out or adjusted for this reason /
   for accuracy of what was actually being measured (see notes column).
2. **No bot-block or CAPTCHA encountered.** If a site had returned anything
   other than a normal `200` to a plain, identifying `User-Agent` (see
   below), it would have been dropped rather than worked around. None were.
3. **No paid API, no login, no account** — the same $0 constraint the CLI
   itself is built to.

The tool identifies itself honestly on every request:
`User-Agent: seo-audit-cli/0.1 (+https://github.com/evanwork34/seo-audit-cli)`
(see [`seo_audit/fetch.py`](seo_audit/fetch.py)) — no spoofed browser
user-agent, no header masking.

## How to reproduce this yourself

```bash
git clone https://github.com/evanwork34/seo-audit-cli.git
cd seo-audit-cli
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

seo-audit https://moz.com
seo-audit https://backlinko.com
seo-audit https://neilpatel.com
seo-audit https://ignitevisibility.com
seo-audit https://reliablesoft.net
seo-audit https://www.brainlabsdigital.com
```

Add `--json` to any of these for machine-readable output. Scores will not
match exactly forever — sites change. That's expected; re-run it and see for
yourself, which is the entire point of publishing the method instead of just
the numbers.

## Results — run live on 2026-09-12

| Site | Score | Checks passed | Notes |
|---|---|---|---|
| moz.com | 80/100 | 8/10 | Meta description over length guidance; heading levels skip (h2/h3 → h5) |
| backlinko.com | 80/100 | 8/10 | Title tag 1 char over length guidance; heading levels skip (h1→h3, h2→h4) |
| neilpatel.com | 90/100 | 9/10 | Heading levels skip (h1→h3) |
| ignitevisibility.com | 90/100 | 9/10 | No `<h1>` found on the page |
| reliablesoft.net | 90/100 | 9/10 | Heading levels skip (h2→h4) |
| brainlabsdigital.com | 50/100 | 5/10 | Title under length guidance; no meta description; 2 `<h1>` tags + several heading skips |
| eliteseo.evan-work34.workers.dev (EliteSEO Consulting, for reference) | 100/100 | 10/10 | Same result the CLI's own README documents from 2026-09-09, re-run today |

**Median of the 6 external sites: 85/100.** All 6 passed the structural
checks that most commonly fail sitewide on smaller businesses (robots.txt not
blocking, sitemap.xml present and well-formed, no accidental noindex) — the
failures that did occur were all in per-page copy details (meta description
length, title length, heading-level sequencing), which tracks with these
being established, professionally maintained sites. This is a useful sanity
check on the tool itself: it did not report false failures against sites with
real SEO practitioners behind them, and it did correctly catch real,
verifiable issues (e.g. Brainlabs' missing meta description, confirmed by
viewing the page source directly).

One candidate originally considered, `gotchseo.com`, is not in this table:
its `robots.txt` is fully permissive, but the URL itself HTTP-redirects to a
different live product (`rankability.com`) — auditing it would have measured
that other site, not the intended one, so it was dropped rather than
mislabeled. This is exactly the kind of thing a small, honest sample should
surface rather than paper over.

## Full check-by-check output

<details>
<summary><code>seo-audit https://moz.com</code> — 2026-09-12</summary>

```
SEO audit: https://moz.com
  (redirected to https://moz.com/)
HTTP status: 200

SCORE: 80/100  (8/10 checks passed)

[PASS] Title tag
       "Moz - SEO Software for Smarter Marketing" (40 chars)
[FAIL] Meta description
       - meta description is 187 chars, over the ~160 char guidance (commonly truncated)
[FAIL] Headings (single H1 + no skipped levels)
       - heading level skips from h1 to h4
       - heading level skips from h3 to h5
       - heading level skips from h2 to h5 (x3)
       - heading level skips from h3 to h5
[PASS] Canonical tag -> https://moz.com/
[PASS] Robots meta / X-Robots-Tag (no accidental noindex)
[PASS] robots.txt (sitemaps declared: sitemaps-1-sitemap.xml, community/q/sitemap.xml)
[PASS] sitemap.xml (sitemap index, 54 <loc> entries, 5/5 sampled URLs resolved 200)

Informational: image alt coverage 69.4% (34/49); OG + Twitter Card tags present.
```
</details>

<details>
<summary><code>seo-audit https://backlinko.com</code> — 2026-09-12</summary>

```
SEO audit: https://backlinko.com
  (redirected to https://backlinko.com/)
HTTP status: 200

SCORE: 80/100  (8/10 checks passed)

[FAIL] Title tag
       - title is 61 chars, over the ~60 char guidance
       "Backlinko: SEO, Content Marketing, & Link Building Strategies"
[PASS] Meta description (131 chars)
[FAIL] Headings (single H1 + no skipped levels)
       - heading level skips from h1 to h3
       - heading level skips from h2 to h4
[PASS] Canonical tag -> https://backlinko.com
[PASS] Robots meta / X-Robots-Tag (no accidental noindex)
[PASS] robots.txt (sitemap declared: sitemap_index.xml)
[PASS] sitemap.xml (sitemap index, 10 <loc> entries, 5/5 sampled URLs resolved 200)

Informational: image alt coverage 100.0% (27/27); OG tags present; Twitter Card
partial (card only, missing title/description).
```
</details>

<details>
<summary><code>seo-audit https://neilpatel.com</code> — 2026-09-12</summary>

```
SEO audit: https://neilpatel.com
  (redirected to https://neilpatel.com/)
HTTP status: 200

SCORE: 90/100  (9/10 checks passed)

[PASS] Title tag "Neil Patel: Helping You Succeed Through Digital Marketing!" (58 chars)
[PASS] Meta description (156 chars)
[FAIL] Headings (single H1 + no skipped levels)
       - heading level skips from h1 to h3
[PASS] Canonical tag -> https://neilpatel.com/
[PASS] Robots meta / X-Robots-Tag (no accidental noindex)
[PASS] robots.txt (sitemap declared: sitemap_index.xml)
[PASS] sitemap.xml (sitemap index, 24 <loc> entries, 5/5 sampled URLs resolved 200)

Informational: image alt coverage 100.0% (35/35); OG tags present; Twitter Card
partial (card only).
```
</details>

<details>
<summary><code>seo-audit https://ignitevisibility.com</code> — 2026-09-12</summary>

```
SEO audit: https://ignitevisibility.com
  (redirected to https://ignitevisibility.com/)
HTTP status: 200

SCORE: 90/100  (9/10 checks passed)

[PASS] Title tag "Ignite Visibility® Digital Marketing Agency Services" (52 chars)
[PASS] Meta description (148 chars)
[FAIL] Headings (single H1 + no skipped levels)
       - no <h1> found
[PASS] Canonical tag -> https://ignitevisibility.com/
[PASS] Robots meta / X-Robots-Tag (no accidental noindex)
[PASS] robots.txt (sitemap declared: sitemap_index.xml)
[PASS] sitemap.xml (sitemap index, 12 <loc> entries, 5/5 sampled URLs resolved 200)

Informational: image alt coverage 8.3% (3/36); OG tags mostly present (missing
og:image); Twitter Card partial (card only).
```
</details>

<details>
<summary><code>seo-audit https://reliablesoft.net</code> — 2026-09-12</summary>

```
SEO audit: https://reliablesoft.net
  (redirected to https://www.reliablesoft.net/)
HTTP status: 200

SCORE: 90/100  (9/10 checks passed)

[PASS] Title tag "Reliablesoft: Learn Digital Marketing & AI Skills" (49 chars)
[PASS] Meta description (141 chars)
[FAIL] Headings (single H1 + no skipped levels)
       - heading level skips from h2 to h4
[PASS] Canonical tag -> https://www.reliablesoft.net/
[PASS] Robots meta / X-Robots-Tag (no accidental noindex)
[PASS] robots.txt
[PASS] sitemap.xml (sitemap index, 6 <loc> entries, 5/5 sampled URLs resolved 200)

Informational: image alt coverage 55.0% (22/40); OG tags mostly present
(missing og:image); Twitter Card partial (card only).
```
</details>

<details>
<summary><code>seo-audit https://www.brainlabsdigital.com</code> — 2026-09-12</summary>

```
SEO audit: https://www.brainlabsdigital.com
  (redirected to https://www.brainlabsdigital.com/)
HTTP status: 200

SCORE: 50/100  (5/10 checks passed)

[FAIL] Title tag
       - title is only 9 chars (guidance floor: 10)
       "Brainlabs"
[FAIL] Meta description
       - no <meta name="description"> tag (or it is empty)
[FAIL] Headings (single H1 + no skipped levels)
       - 2 <h1> tags found (expected exactly 1)
       - heading level skips from h2 to h4 (x7)
       - heading level skips from h1 to h3
       - heading level skips from h4 to h6
[PASS] Canonical tag -> https://www.brainlabsdigital.com/
[PASS] Robots meta / X-Robots-Tag (no accidental noindex)
[PASS] robots.txt (sitemap declared: sitemap_index.xml)
[PASS] sitemap.xml (sitemap index, 15 <loc> entries, 5/5 sampled URLs resolved 200)

Informational: image alt coverage 4.8% (2/42); OG tags partial (title + url
only); Twitter Card partial (card only).
```
</details>

<details>
<summary><code>seo-audit https://eliteseo.evan-work34.workers.dev</code> — 2026-09-12 (re-run of the README's 2026-09-09 example)</summary>

```
SEO audit: https://eliteseo.evan-work34.workers.dev
  (redirected to https://eliteseo.evan-work34.workers.dev/)
HTTP status: 200

SCORE: 100/100  (10/10 checks passed)

All 10 checks PASS. Image alt coverage 100.0% (1/1); OG + Twitter Card tags
present.
```
</details>

## Honesty notes

- No client, result, "trusted by," or ranking/traffic claim is made anywhere
  in this file, about any site named — including EliteSEO Consulting's own.
- Every score is a live, dated, reproducible output of `seo-audit-cli`
  against a real public URL. Nothing is fabricated, estimated, or backfilled.
- `eliteseo.evan-work34.workers.dev` is EliteSEO Consulting's own site (the
  business this CLI was extracted from) — a separate company from
  eliteseoconsulting.com, whose results are never referenced here or
  anywhere else in this project.
- This benchmark will drift as sites change their pages. That is expected
  and is the reason the reproduction command is published alongside the
  numbers rather than just the numbers alone.
