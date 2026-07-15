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

ATOM_NS = "{http://www.w3.org/2005/Atom}"
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


def _parse_date(raw):
    """Parse an RSS (RFC-822) or Atom (ISO-8601) date into an aware datetime."""
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
    # Atom / ISO-8601, e.g. "2026-07-13T09:00:00Z"
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _parse_feed(content):
    """Parse RSS 2.0 or Atom bytes into a list of article dicts."""
    root = ET.fromstring(content)
    tag = root.tag.lower()
    articles = []

    if tag.endswith("feed"):  # Atom
        for entry in root.findall(f"{ATOM_NS}entry"):
            title = entry.findtext(f"{ATOM_NS}title")
            link = ""
            for link_el in entry.findall(f"{ATOM_NS}link"):
                rel = link_el.get("rel", "alternate")
                if rel == "alternate" or not link:
                    link = link_el.get("href", link)
            raw_date = (
                entry.findtext(f"{ATOM_NS}published")
                or entry.findtext(f"{ATOM_NS}updated")
            )
            summary = (
                entry.findtext(f"{ATOM_NS}summary")
                or entry.findtext(f"{ATOM_NS}content")
            )
            articles.append((title, link, raw_date, summary))
    else:  # RSS 2.0 (and RDF-style feeds expose <item> too)
        for item in root.findall(".//item"):
            title = item.findtext("title")
            link = item.findtext("link")
            raw_date = (
                item.findtext("pubDate")
                or item.findtext("{http://purl.org/dc/elements/1.1/}date")
            )
            summary = item.findtext("description")
            articles.append((title, link, raw_date, summary))

    parsed = []
    for title, link, raw_date, summary in articles:
        parsed.append(
            {
                "title": _clean(title) or "(untitled)",
                "url": (link or "").strip(),
                "published": _parse_date(raw_date),
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
                if cutoff and art["published"] and art["published"] < cutoff:
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
                   help="only keep posts published within N days "
                        "(0 = no date filter, default: 7)")
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
