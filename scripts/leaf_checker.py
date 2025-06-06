#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
leaf_checker.py  ——  Quick TraceParts leaf page validator (no login, no JS)

Usage:
    python scripts/leaf_checker.py <url>

Logic:
    • Download the page via requests (User-Agent spoofed).
    • Convert HTML to lowercase and search for the pattern:
        "数字(可含逗号) + 空格 + results|result"  (e.g. 2,569 results).
    • If found → leaf=True ; product_count = 前面的数字.
    • Otherwise → leaf=False ; product_count = 0.

This matches the simplified rule now used in classification_enhanced.py.
"""

import re
import sys
from typing import Tuple

import requests

# Regex: number (digits+commas) + space/NBSP + result/results
# NBSP in HTML may appear as actual \u00A0 or &nbsp; entity already decoded.
RESULTS_REGEX = re.compile(r"\b[\d,]+(?:\s|\u00a0)+results?\b", re.IGNORECASE)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    )
}

def check_leaf(url: str, timeout: int = 15) -> Tuple[bool, int]:
    """Return (is_leaf, product_count)."""
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    html_lower = resp.text.lower()

    match = RESULTS_REGEX.search(html_lower)
    if not match:
        return False, 0

    # Extract number part (first token before space)
    number_token = match.group(0).split()[0].replace(",", "")
    try:
        count = int(number_token)
    except ValueError:
        count = 0
    return True, count


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/leaf_checker.py <url>")
        sys.exit(1)

    url = sys.argv[1]
    is_leaf, count = check_leaf(url)

    status_symbol = "✅" if is_leaf else "❌"
    print(f"{status_symbol} Leaf: {is_leaf} | Products: {count} | URL: {url}")


if __name__ == "__main__":
    main() 