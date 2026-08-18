"""
url_parser.py -- Parse CSV and TXT files into a clean list of URL strings.
Handles: empty rows, duplicates, whitespace, missing scheme.
"""

import csv
import os

from url_utils import dedupe, is_header_label, is_safe_url, looks_like_url, normalize_url

# Kept for callers/tests that reference the original private helper.
_fix_scheme = normalize_url

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_URLS = 50_000


def _parse_txt(f) -> list:
    return [normalize_url(line) for line in f if line.strip()]


def _parse_csv(f) -> list:
    urls = []
    for row in csv.reader(f):
        for cell in row:
            if looks_like_url(cell) and not is_header_label(cell):
                urls.append(normalize_url(cell))
    return urls


PARSERS = {".txt": _parse_txt, ".csv": _parse_csv}


def parse_file(filepath: str) -> list:
    """
    Parse a .csv or .txt file and return a deduplicated list of URL strings.
    Raises ValueError on unsupported file types.
    """
    ext = os.path.splitext(filepath)[1].lower()
    parser = PARSERS.get(ext)
    if parser is None:
        raise ValueError(f"Unsupported file type: {ext}. Use .csv or .txt")
    if os.path.getsize(filepath) > MAX_FILE_BYTES:
        raise ValueError(
            f"File is larger than the {MAX_FILE_BYTES // (1024 * 1024)} MB limit."
        )

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        urls = [url for url in dedupe(parser(f)) if is_safe_url(url)]
    return urls[:MAX_URLS]
