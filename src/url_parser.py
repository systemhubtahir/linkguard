"""
url_parser.py -- Parse CSV and TXT files into a clean list of URL strings.
Handles: empty rows, duplicates, whitespace, missing scheme.
"""

import csv
import os
import re
from urllib.parse import urlsplit

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_URLS = 50_000
MAX_URL_LENGTH = 2048
ALLOWED_SCHEMES = ("http", "https")


_SCHEME_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):(//)?")


def _has_scheme(url: str) -> bool:
    """True if the URL already carries a scheme (``host:8080`` does not)."""
    match = _SCHEME_RE.match(url)
    if not match:
        return False
    if match.group(2):
        return True
    return not url[match.end():][:1].isdigit()


def _fix_scheme(url: str) -> str:
    """Prepend https:// if scheme is missing; leave any existing scheme intact."""
    if url and not _has_scheme(url):
        return "https://" + url
    return url


def is_safe_url(url: str) -> bool:
    """True only for well-formed http(s) URLs without embedded credentials."""
    if not url or len(url) > MAX_URL_LENGTH:
        return False
    if any(c in url for c in ("\n", "\r", "\t", " ")):
        return False
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    if parts.scheme not in ALLOWED_SCHEMES or not parts.hostname:
        return False
    if parts.username or parts.password:
        return False
    try:
        parts.port
    except ValueError:
        return False
    return True


def parse_file(filepath: str) -> list:
    """
    Parse a .csv or .txt file and return a deduplicated list of URL strings.
    Raises ValueError on unsupported file types.
    """
    ext = os.path.splitext(filepath)[1].lower()
    if os.path.getsize(filepath) > MAX_FILE_BYTES:
        raise ValueError(
            f"File is larger than {MAX_FILE_BYTES // (1024 * 1024)} MB limit."
        )
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
        if url in seen or not is_safe_url(url):
            continue
        seen.add(url)
        deduped.append(url)
        if len(deduped) >= MAX_URLS:
            break

    return deduped
