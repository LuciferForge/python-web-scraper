#!/usr/bin/env python3
"""
python-web-scraper — Ready-to-use web scraper with zero dependencies beyond Python.

Usage:
    python3 scraper.py https://example.com                     # Scrape a page
    python3 scraper.py https://example.com -s "h2"             # Extract all h2 tags
    python3 scraper.py https://example.com -s "a[href]" -a href # Extract all links
    python3 scraper.py https://example.com -s ".price"         # CSS class selector
    python3 scraper.py https://example.com --json              # JSON output
    python3 scraper.py https://example.com --csv               # CSV output
    python3 scraper.py urls.txt                                # Scrape multiple URLs from file
    python3 scraper.py https://example.com --follow -d 2       # Follow links, depth 2
"""

import argparse
import csv
import io
import json
import re
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from html.parser import HTMLParser
from pathlib import Path


# ── Minimal HTML Parser (no dependencies) ───────────────────────────────

class Element:
    """Lightweight DOM element."""
    __slots__ = ("tag", "attrs", "children", "text", "parent")

    def __init__(self, tag, attrs=None):
        self.tag = tag
        self.attrs = dict(attrs) if attrs else {}
        self.children = []
        self.text = ""
        self.parent = None

    def get(self, attr, default=None):
        return self.attrs.get(attr, default)

    def select(self, selector):
        """CSS selector support: tag, .class, #id, tag.class, tag[attr], tag[attr=val]."""
        return list(_select(self, selector))

    def select_one(self, selector):
        for el in _select(self, selector):
            return el
        return None

    @property
    def text_content(self):
        parts = []
        _collect_text(self, parts)
        return " ".join(parts).strip()

    def __repr__(self):
        return f"<{self.tag} {self.attrs}>"


def _collect_text(el, parts):
    if el.text:
        parts.append(el.text.strip())
    for child in el.children:
        _collect_text(child, parts)


def _select(el, selector):
    """Match elements against a CSS selector."""
    for child in el.children:
        if _matches(child, selector):
            yield child
        yield from _select(child, selector)


def _matches(el, selector):
    """Check if element matches a CSS selector."""
    # tag[attr=value]
    m = re.match(r'^(\w+)\[(\w+)=["\']?([^"\'\]]+)["\']?\]$', selector)
    if m:
        return el.tag == m.group(1) and el.attrs.get(m.group(2)) == m.group(3)

    # tag[attr]
    m = re.match(r'^(\w+)\[(\w+)\]$', selector)
    if m:
        return el.tag == m.group(1) and m.group(2) in el.attrs

    # [attr]
    m = re.match(r'^\[(\w+)\]$', selector)
    if m:
        return m.group(1) in el.attrs

    # #id
    if selector.startswith("#"):
        return el.attrs.get("id") == selector[1:]

    # .class
    if selector.startswith("."):
        classes = el.attrs.get("class", "").split()
        return selector[1:] in classes

    # tag.class
    m = re.match(r'^(\w+)\.(.+)$', selector)
    if m:
        classes = el.attrs.get("class", "").split()
        return el.tag == m.group(1) and m.group(2) in classes

    # tag#id
    m = re.match(r'^(\w+)#(.+)$', selector)
    if m:
        return el.tag == m.group(1) and el.attrs.get("id") == m.group(2)

    # plain tag
    return el.tag == selector


class DOMBuilder(HTMLParser):
    """Build a lightweight DOM from HTML."""

    VOID_ELEMENTS = {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }

    def __init__(self):
        super().__init__()
        self.root = Element("root")
        self.current = self.root

    def handle_starttag(self, tag, attrs):
        el = Element(tag, attrs)
        el.parent = self.current
        self.current.children.append(el)
        if tag not in self.VOID_ELEMENTS:
            self.current = el

    def handle_endtag(self, tag):
        node = self.current
        while node and node.tag != tag and node.parent:
            node = node.parent
        if node and node.parent:
            self.current = node.parent

    def handle_data(self, data):
        if data.strip():
            if self.current.children:
                # Append to last child or create text node
                self.current.children[-1].text += " " + data.strip()
            else:
                self.current.text += " " + data.strip()


def parse_html(html):
    """Parse HTML string into a lightweight DOM."""
    builder = DOMBuilder()
    builder.feed(html)
    return builder.root


# ── HTTP Fetcher ────────────────────────────────────────────────────────

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def fetch(url, retries=3, delay=1.0, timeout=15):
    """Fetch URL with retries, rotating user agents, and rate limiting."""
    import random
    import ssl
    for attempt in range(retries):
        try:
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
            req = urllib.request.Request(url, headers=headers)
            # Try default SSL first, fall back to unverified (common on macOS)
            try:
                resp = urllib.request.urlopen(req, timeout=timeout)
            except (ssl.SSLCertVerificationError, urllib.error.URLError):
                ctx = ssl._create_unverified_context()
                resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
            with resp:
                charset = resp.headers.get_content_charset() or "utf-8"
                return resp.read().decode(charset, errors="replace"), resp.geturl()
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt < retries - 1:
                wait = delay * (attempt + 1)
                print(f"  Retry {attempt + 1}/{retries} for {url} (waiting {wait:.1f}s)...", file=sys.stderr)
                time.sleep(wait)
            else:
                print(f"  Failed: {url} — {e}", file=sys.stderr)
                return None, None


# ── Extraction ──────────────────────────────────────────────────────────

def extract(dom, selector=None, attribute=None):
    """Extract data from DOM using CSS selector."""
    if not selector:
        # Default: extract all text
        return [{"text": dom.text_content}]

    elements = dom.select(selector)
    results = []
    for el in elements:
        row = {"tag": el.tag, "text": el.text_content}
        if attribute:
            row["value"] = el.get(attribute, "")
        # Always include common attributes if present
        for attr in ("href", "src", "alt", "title"):
            if attr in el.attrs and attr != attribute:
                row[attr] = el.attrs[attr]
        results.append(row)
    return results


def extract_links(dom, base_url):
    """Extract all links from page, resolve relative URLs."""
    links = []
    for el in dom.select("a[href]"):
        href = el.get("href", "")
        if href and not href.startswith(("#", "javascript:", "mailto:")):
            full_url = urllib.parse.urljoin(base_url, href)
            links.append(full_url)
    return links


# ── Output Formatters ───────────────────────────────────────────────────

def output_text(results, url=None):
    """Plain text output."""
    if url:
        print(f"\n── {url} ──")
    for r in results:
        if "value" in r:
            print(f"  {r['value']}  |  {r['text']}")
        else:
            print(f"  {r['text']}")


def output_json(results, url=None):
    """JSON output."""
    out = {"url": url, "count": len(results), "data": results} if url else results
    print(json.dumps(out, indent=2, ensure_ascii=False))


def output_csv(results):
    """CSV output."""
    if not results:
        return
    buf = io.StringIO()
    keys = list(results[0].keys())
    writer = csv.DictWriter(buf, fieldnames=keys, extrasaction="ignore")
    writer.writeheader()
    for r in results:
        writer.writerow(r)
    print(buf.getvalue(), end="")


# ── Crawler (follow links) ─────────────────────────────────────────────

def crawl(start_url, selector=None, attribute=None, max_depth=1, max_pages=50, delay=1.0, same_domain=True):
    """Crawl pages following links up to max_depth."""
    from urllib.parse import urlparse
    visited = set()
    all_results = []
    queue = [(start_url, 0)]
    domain = urlparse(start_url).netloc

    while queue and len(visited) < max_pages:
        url, depth = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)

        if same_domain and urlparse(url).netloc != domain:
            continue

        print(f"  [{len(visited)}/{max_pages}] Depth {depth}: {url}", file=sys.stderr)
        html, final_url = fetch(url, delay=delay)
        if not html:
            continue

        dom = parse_html(html)
        results = extract(dom, selector, attribute)
        for r in results:
            r["source_url"] = url
        all_results.extend(results)

        if depth < max_depth:
            links = extract_links(dom, final_url or url)
            for link in links:
                if link not in visited:
                    queue.append((link, depth + 1))

        if len(visited) < max_pages and queue:
            time.sleep(delay)

    return all_results


# ── Main ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Web scraper — zero dependencies, works out of the box",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scraper.py https://example.com                      Scrape full page text
  python3 scraper.py https://example.com -s "h2"              All h2 headings
  python3 scraper.py https://example.com -s "a[href]" -a href All links
  python3 scraper.py https://example.com -s ".price"          Elements with class="price"
  python3 scraper.py https://example.com -s "img" -a src      All image URLs
  python3 scraper.py https://example.com --json               JSON output
  python3 scraper.py https://example.com --csv                CSV output
  python3 scraper.py urls.txt                                 Scrape URLs from file
  python3 scraper.py https://example.com --follow -d 2        Crawl links, depth 2
        """
    )
    parser.add_argument("target", help="URL to scrape, or path to file with URLs (one per line)")
    parser.add_argument("-s", "--selector", help="CSS selector (tag, .class, #id, tag[attr], tag[attr=val])")
    parser.add_argument("-a", "--attribute", help="Extract specific attribute from selected elements")
    parser.add_argument("--json", action="store_true", dest="json_out", help="Output as JSON")
    parser.add_argument("--csv", action="store_true", dest="csv_out", help="Output as CSV")
    parser.add_argument("--follow", action="store_true", help="Follow links and crawl")
    parser.add_argument("-d", "--depth", type=int, default=1, help="Crawl depth (default: 1)")
    parser.add_argument("--max-pages", type=int, default=50, help="Max pages to crawl (default: 50)")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between requests in seconds (default: 1.0)")
    parser.add_argument("--no-same-domain", action="store_true", help="Allow following links to other domains")

    args = parser.parse_args()

    # Determine if target is a file of URLs or a single URL
    target = args.target
    urls = []
    if Path(target).is_file():
        urls = [line.strip() for line in Path(target).read_text().splitlines() if line.strip() and not line.startswith("#")]
        print(f"Loaded {len(urls)} URLs from {target}", file=sys.stderr)
    elif target.startswith(("http://", "https://")):
        urls = [target]
    else:
        print(f"Error: '{target}' is not a valid URL or file path", file=sys.stderr)
        sys.exit(1)

    all_results = []

    for url in urls:
        if args.follow:
            results = crawl(
                url, args.selector, args.attribute,
                max_depth=args.depth, max_pages=args.max_pages,
                delay=args.delay, same_domain=not args.no_same_domain,
            )
        else:
            print(f"Scraping {url}...", file=sys.stderr)
            html, final_url = fetch(url, delay=args.delay)
            if not html:
                continue
            dom = parse_html(html)
            results = extract(dom, args.selector, args.attribute)

        all_results.extend(results)

        if not args.json_out and not args.csv_out:
            output_text(results, url)

    if args.json_out:
        output_json(all_results, urls[0] if len(urls) == 1 else None)
    elif args.csv_out:
        output_csv(all_results)

    print(f"\nExtracted {len(all_results)} items from {len(urls)} URL(s)", file=sys.stderr)


if __name__ == "__main__":
    main()
