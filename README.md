# python-web-scraper

A ready-to-use web scraper with **zero dependencies** — just Python 3. No pip install, no virtual env, no setup. Clone and scrape.

## Quick Start

```bash
git clone https://github.com/LuciferForge/python-web-scraper.git
cd python-web-scraper

# Scrape a page
python3 scraper.py https://example.com

# Extract all links
python3 scraper.py https://example.com -s "a[href]" -a href

# Extract all headings
python3 scraper.py https://example.com -s "h2"

# Get prices from a product page
python3 scraper.py https://example.com -s ".price"

# JSON output
python3 scraper.py https://example.com -s "h2" --json

# CSV output
python3 scraper.py https://example.com -s "a[href]" -a href --csv
```

## Features

- **Zero dependencies** — uses only Python standard library
- **CSS selectors** — `tag`, `.class`, `#id`, `tag[attr]`, `tag[attr=value]`
- **Multiple output formats** — text, JSON, CSV
- **Built-in rate limiting** — configurable delay between requests
- **Retry with backoff** — automatic retries on failure
- **Rotating user agents** — avoids basic bot detection
- **Crawl mode** — follow links with depth control
- **Batch scraping** — pass a file of URLs
- **No config files** — everything via command line flags

## Usage

### Basic Scraping

```bash
# Full page text
python3 scraper.py https://news.ycombinator.com

# All links
python3 scraper.py https://news.ycombinator.com -s "a[href]" -a href

# All images
python3 scraper.py https://example.com -s "img" -a src

# Elements by class
python3 scraper.py https://example.com -s ".article-title"

# Elements by ID
python3 scraper.py https://example.com -s "#main-content"
```

### Output Formats

```bash
# JSON (pipe to jq, save to file, etc.)
python3 scraper.py https://example.com -s "h2" --json

# CSV (open in Excel, import to database, etc.)
python3 scraper.py https://example.com -s "a[href]" -a href --csv

# Plain text (default)
python3 scraper.py https://example.com -s "p"
```

### Crawling (Follow Links)

```bash
# Follow links 1 level deep
python3 scraper.py https://example.com --follow

# Follow links 3 levels deep, max 100 pages
python3 scraper.py https://example.com --follow -d 3 --max-pages 100

# Crawl with 2 second delay between requests
python3 scraper.py https://example.com --follow --delay 2.0
```

### Batch Scraping

Create a file with URLs (one per line):

```
# urls.txt
https://example.com/page1
https://example.com/page2
https://example.com/page3
```

```bash
python3 scraper.py urls.txt -s "h1" --json
```

## CSS Selector Reference

| Selector | Matches | Example |
|----------|---------|---------|
| `tag` | Elements by tag name | `h2`, `p`, `div` |
| `.class` | Elements by class | `.price`, `.title` |
| `#id` | Elements by ID | `#header`, `#content` |
| `tag.class` | Tag with class | `div.article`, `span.highlight` |
| `tag[attr]` | Tag with attribute | `a[href]`, `img[src]` |
| `tag[attr=val]` | Tag with attribute value | `input[type=text]`, `a[rel=nofollow]` |
| `[attr]` | Any element with attribute | `[data-id]`, `[role]` |

## Common Recipes

```bash
# Extract all email addresses from a page
python3 scraper.py https://example.com -s "a[href]" -a href | grep mailto:

# Get all image URLs as JSON
python3 scraper.py https://example.com -s "img" -a src --json

# Scrape product names and prices
python3 scraper.py https://store.example.com -s ".product-name" --json
python3 scraper.py https://store.example.com -s ".product-price" --json

# Extract table data
python3 scraper.py https://example.com -s "td" --csv

# Crawl a blog and extract all article titles
python3 scraper.py https://blog.example.com -s "h2.post-title" --follow -d 2 --json
```

## Customization

The scraper is a single file (`scraper.py`). Common modifications:

- **Add a selector**: The `_matches()` function handles CSS matching — extend it for new patterns
- **Add an output format**: Add a function like `output_json()` / `output_csv()`
- **Change retry behavior**: Modify `fetch()` — adjust `retries`, `delay`, `timeout`
- **Add headers**: Edit the `headers` dict in `fetch()` for cookies, auth tokens, etc.

## Requirements

- Python 3.6+
- No external packages

## License

MIT
