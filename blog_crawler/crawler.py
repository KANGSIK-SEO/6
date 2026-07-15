#!/usr/bin/env python3
"""Crawl latest blog articles from Silicon Valley and Chinese tech companies.

The crawler reads RSS/Atom feeds listed in ``feeds.py``, parses the most
recent entries, filters them by publication date, de-duplicates by URL and
prints or exports the result.

It depends only on ``requests`` (plus the Python standard library), so there
is nothing to build and no heavyweight parsing library to install.

Usage examples
--------------
    # Latest posts from the last 7 days, all companies, printed to console
    python crawler.py

    # Only Chinese companies, last 14 days
    python crawler.py --region china --days 14

    # Only Google feeds, up to 5 posts each, export to JSON
    python crawler.py --company google --limit 5 --output articles.json

    # Export a Markdown digest
    python crawler.py --days 3 --format markdown --output digest.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

try:
    import requests
except ImportError:  # pragma: no cover
    sys.exit("This tool requires the 'requests' package. Run: pip install requests")

from feeds import filter_feeds

USER_AGENT = (
    "Mozilla/5.0 (compatible; TechBlogCrawler/1.0; "
    "+https://github.com/) blog-crawler"
)
TAG_RE = re.compile(r"<[^>]+>")


# --------------------------------------------------------------------------- #
# Parsing helpers
# --------------------------------------------------------------------------- #
def _clean(text):
    """Strip HTML tags and collapse whitespace from a summary snippet."""
    if not text:
        return ""
    text = TAG_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


_STRPTIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S %z",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d",
)


def _parse_date(raw):
    """Parse an RSS (RFC-822) or Atom/ISO-8601 date into an aware datetime.

    Real-world feeds are inconsistent, so several strategies are tried in
    turn. Returns ``None`` if the string cannot be understood.
    """
    if not raw:
        return None
    raw = raw.strip()

    # RSS 2.0 pubDate, e.g. "Tue, 14 Jul 2026 10:00:00 GMT"
    try:
        dt = parsedate_to_datetime(raw)
        if dt is not None:
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        pass

    # Atom / ISO-8601, e.g. "2026-07-13T09:00:00Z" or with "+08:00"
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass

    # Odd but common variants, e.g. "2026-07-12 00:00:00 +0800"
    for fmt in _STRPTIME_FORMATS:
        try:
            dt = datetime.strptime(raw, fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


_URL_DATE_RE = re.compile(r"/(\d{4})[/-](\d{2})[/-](\d{2})[/-]")


def _date_from_url(url):
    """Fallback: derive a date from a dated permalink like /2026/07/12/....

    Some feeds (e.g. Meituan's VuePress RSS) omit per-item dates but encode
    the publication date in the article URL. Returns an aware datetime at
    UTC midnight, or ``None`` if the URL has no date-like path segment.
    """
    if not url:
        return None
    m = _URL_DATE_RE.search(url)
    if not m:
        return None
    try:
        year, month, day = (int(g) for g in m.groups())
        return datetime(year, month, day, tzinfo=timezone.utc)
    except ValueError:
        return None


def _local(tag):
    """Return the lower-cased local name of an XML tag, dropping any namespace."""
    return tag.rsplit("}", 1)[-1].lower()


def _parse_feed(content):
    """Parse RSS 2.0, RDF or Atom bytes into a list of article dicts.

    Parsing is namespace-agnostic: elements are matched by their local name
    (``item``/``entry``, ``title``, ``link``, ``pubDate``/``published``/...),
    so feeds that mix namespaces (Atom + Dublin Core, Blogger, WordPress,
    etc.) all work without special-casing each provider.
    """
    root = ET.fromstring(content)

    items = [el for el in root.iter() if _local(el.tag) in ("item", "entry")]
    parsed = []

    for item in items:
        title = link = summary = None
        dates = {}
        for child in item:
            name = _local(child.tag)
            if name == "title" and not title:
                title = child.text
            elif name == "link":
                href = child.get("href")
                if href:  # Atom-style <link href="..." rel="..."/>
                    rel = child.get("rel", "alternate")
                    if rel == "alternate" or not link:
                        link = href
                elif child.text and not link:  # RSS-style <link>text</link>
                    link = child.text
            elif name in ("pubdate", "published", "updated", "date"):
                dates.setdefault(name, child.text)
            elif name in ("description", "summary", "content") and not summary:
                summary = child.text

        raw_date = (
            dates.get("pubdate")
            or dates.get("published")
            or dates.get("updated")
            or dates.get("date")
        )
        url = (link or "").strip()
        published = _parse_date(raw_date) or _date_from_url(url)
        parsed.append(
            {
                "title": _clean(title) or "(untitled)",
                "url": url,
                "published": published,
                "summary": _clean(summary)[:280],
            }
        )
    return parsed


# --------------------------------------------------------------------------- #
# Fetching
# --------------------------------------------------------------------------- #
def fetch_feed(feed, timeout, session):
    """Fetch and parse a single feed. Returns (articles, error)."""
    try:
        resp = session.get(feed["url"], timeout=timeout,
                           headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        articles = _parse_feed(resp.content)
    except requests.RequestException as exc:
        return [], f"network error: {exc}"
    except ET.ParseError as exc:
        return [], f"parse error: {exc}"

    for art in articles:
        art["company"] = feed["company"]
        art["region"] = feed["region"]
        art["category"] = feed["category"]
    return articles, None


def crawl(feeds, days=7, limit_per_feed=0, timeout=20, workers=8):
    """Crawl every feed concurrently and return (articles, errors)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days) if days else None
    all_articles = []
    errors = {}

    session = requests.Session()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(fetch_feed, feed, timeout, session): feed
            for feed in feeds
        }
        for future in as_completed(futures):
            feed = futures[future]
            articles, error = future.result()
            if error:
                errors[feed["company"]] = error
                continue

            # newest first; entries without a date sink to the bottom
            articles.sort(
                key=lambda a: a["published"] or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True,
            )
            kept = []
            for art in articles:
                if cutoff:
                    # When a date window is active, only keep posts we can
                    # confirm fall inside it. Undated posts (feeds that omit
                    # per-item dates and have no dated permalink) can't be
                    # confirmed recent, so they are dropped here; run with
                    # --days 0 to browse everything regardless of date.
                    if art["published"] is None or art["published"] < cutoff:
                        continue
                kept.append(art)
                if limit_per_feed and len(kept) >= limit_per_feed:
                    break
            all_articles.extend(kept)

    # de-duplicate by URL, keep first (newest) occurrence
    seen = set()
    deduped = []
    for art in all_articles:
        key = art["url"] or art["title"]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(art)

    deduped.sort(
        key=lambda a: a["published"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return deduped, errors


# --------------------------------------------------------------------------- #
# Output formatting
# --------------------------------------------------------------------------- #
def _fmt_date(dt):
    return dt.strftime("%Y-%m-%d") if dt else "----------"


def to_console(articles, errors):
    lines = []
    for art in articles:
        lines.append(
            f"[{_fmt_date(art['published'])}] {art['company']:<24} "
            f"| {art['title']}"
        )
        lines.append(f"    {art['url']}")
    lines.append("")
    lines.append(f"Total: {len(articles)} article(s)")
    if errors:
        lines.append(f"Feeds with errors: {len(errors)}")
        for company, err in errors.items():
            lines.append(f"  - {company}: {err}")
    return "\n".join(lines)


def to_markdown(articles, errors):
    lines = [f"# Tech Blog Digest ({datetime.now().strftime('%Y-%m-%d')})", ""]
    lines.append(f"_{len(articles)} article(s)_", )
    lines.append("")
    current_region = None
    for art in sorted(articles, key=lambda a: (a["region"], a["company"])):
        if art["region"] != current_region:
            current_region = art["region"]
            label = "Silicon Valley / US" if current_region == "usa" else "China"
            lines.append(f"## {label}")
            lines.append("")
        lines.append(
            f"- **{art['company']}** · {_fmt_date(art['published'])} — "
            f"[{art['title']}]({art['url']})"
        )
    if errors:
        lines.append("")
        lines.append("## Feeds with errors")
        for company, err in errors.items():
            lines.append(f"- {company}: {err}")
    return "\n".join(lines)


def to_json(articles, errors):
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(articles),
        "articles": [
            {
                "company": a["company"],
                "region": a["region"],
                "category": a["category"],
                "title": a["title"],
                "url": a["url"],
                "published": a["published"].isoformat() if a["published"] else None,
                "summary": a["summary"],
            }
            for a in articles
        ],
        "errors": errors,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser():
    p = argparse.ArgumentParser(
        description="Crawl latest blog articles from Silicon Valley and "
                    "Chinese tech companies.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--region", choices=["usa", "china"],
                   help="only crawl feeds from this region")
    p.add_argument("--company", help="substring match on company name "
                                     "(e.g. 'google')")
    p.add_argument("--category", help="substring match on category "
                                      "(e.g. 'ai', 'cloud', 'engineering')")
    p.add_argument("--days", type=int, default=7,
                   help="only keep posts published within N days; undated "
                        "posts are dropped when this is > 0 "
                        "(0 = no date filter, keep everything; default: 7)")
    p.add_argument("--limit", type=int, default=0,
                   help="max articles per feed (0 = unlimited)")
    p.add_argument("--format", choices=["console", "json", "markdown"],
                   default="console", help="output format (default: console)")
    p.add_argument("--output", help="write to this file instead of stdout")
    p.add_argument("--timeout", type=int, default=20,
                   help="per-request timeout in seconds (default: 20)")
    p.add_argument("--workers", type=int, default=8,
                   help="number of concurrent fetchers (default: 8)")
    p.add_argument("--list-feeds", action="store_true",
                   help="list configured feeds and exit")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)

    feeds = filter_feeds(region=args.region, company=args.company,
                         category=args.category)
    if not feeds:
        sys.exit("No feeds match the given filters. Try --list-feeds.")

    if args.list_feeds:
        for f in feeds:
            print(f"{f['region']:<6} {f['company']:<26} {f['category']:<12} "
                  f"{f['url']}")
        return 0

    print(f"Crawling {len(feeds)} feed(s)...", file=sys.stderr)
    articles, errors = crawl(
        feeds, days=args.days, limit_per_feed=args.limit,
        timeout=args.timeout, workers=args.workers,
    )

    renderers = {"console": to_console, "json": to_json, "markdown": to_markdown}
    output = renderers[args.format](articles, errors)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(output + "\n")
        print(f"Wrote {len(articles)} article(s) to {args.output}",
              file=sys.stderr)
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
