"""
url_parser.py -- Parse CSV and TXT files into a clean list of URL strings.
Handles: empty rows, duplicates, whitespace, missing scheme.
"""

import csv
import os


def _fix_scheme(url: str) -> str:
    """Prepend https:// if scheme is missing."""
    if url and not url.startswith(("http://", "https://")):
        return "https://" + url
    return url


def parse_file(filepath: str) -> list:
    """
    Parse a .csv or .txt file and return a deduplicated list of URL strings.
    Raises ValueError on unsupported file types.
    """
    ext = os.path.splitext(filepath)[1].lower()
    urls = []

    if ext == ".txt":
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                url = line.strip()
                if url:
                    urls.append(_fix_scheme(url))

    elif ext == ".csv":
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            for row in reader:
                for cell in row:
                    url = cell.strip()
                    # Accept cells that look like URLs
                    if url and ("." in url or url.startswith("http")):
                        urls.append(_fix_scheme(url))
    else:
        raise ValueError(f"Unsupported file type: {ext}. Use .csv or .txt")

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            deduped.append(url)

    return deduped
