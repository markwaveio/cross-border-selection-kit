#!/usr/bin/env python3
"""Extract trend-signal candidates from a saved Amazon homepage HTML file."""

from __future__ import annotations

import argparse
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin


AMAZON_BASE = "https://www.amazon.com"


def clean(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def unique(items):
    seen = set()
    out = []
    for item in items:
        key = json.dumps(item, sort_keys=True, ensure_ascii=False) if isinstance(item, dict) else item
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def extract_headings(source: str):
    headings = []
    for match in re.finditer(r"<h2[^>]*>(.*?)</h2>", source, flags=re.I | re.S):
        value = clean(match.group(1))
        if value and value.lower() not in {"skip to", "keyboard shortcuts"}:
            headings.append(value)
    return unique(headings)


def extract_image_alts(source: str):
    alts = []
    pattern = re.compile(
        r"<img[^>]+alt=\"([^\"]{8,260})\"[^>]*>|<img[^>]+alt='([^']{8,260})'[^>]*>",
        flags=re.I | re.S,
    )
    for match in pattern.finditer(source):
        value = clean(match.group(1) or match.group(2) or "")
        if not value or value == "Amazon":
            continue
        if value.startswith("Amazon US Home"):
            continue
        alts.append(value)
    return unique(alts)


def extract_carousel_products(source: str):
    pattern = re.compile(
        r"<li[^>]+data-sgproduct=\"\{&quot;asin&quot;:&quot;([^&]+)&quot;\}\"[\s\S]*?"
        r"<a[^>]+href=\"([^\"]+)\"[\s\S]*?"
        r"<img[^>]+alt=\"([^\"]+)\"",
        flags=re.I,
    )
    products = []
    for asin, href, title in pattern.findall(source):
        products.append(
            {
                "signal_type": "homepage_module",
                "asin": clean(asin),
                "product_name": clean(title),
                "product_url": urljoin(AMAZON_BASE, html.unescape(href).split("?")[0]),
                "category": None,
                "rank": None,
                "source": "amazon_homepage_html",
            }
        )
    return unique(products)


def parse(path: Path):
    source = path.read_text(encoding="utf-8", errors="replace")
    return {
        "source": "amazon",
        "crawl_mode": "saved_html_parse",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "source_file": str(path),
        "module_headings": extract_headings(source),
        "visible_product_alts": extract_image_alts(source),
        "items": extract_carousel_products(source),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse saved Amazon homepage HTML into trend-signal JSON.")
    parser.add_argument("html_file", type=Path)
    parser.add_argument("-o", "--output", type=Path, help="Write JSON to this file instead of stdout.")
    args = parser.parse_args()

    result = parse(args.html_file)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
