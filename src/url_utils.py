"""
url_utils.py -- Shared URL normalisation, validation and de-duplication helpers.
"""

import re
from urllib.parse import urlsplit

SCHEMES = ("http://", "https://")
DEFAULT_SCHEME = "https://"
ALLOWED_SCHEMES = ("http", "https")
MAX_URL_LENGTH = 2048

# Cells/lines that are column headers rather than URLs.
HEADER_LABELS = ("url", "link", "href")

_SCHEME_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):(//)?")


def has_scheme(url: str) -> bool:
    """True if the URL already carries a scheme (``host:8080`` does not)."""
    match = _SCHEME_RE.match(url)
    if not match:
        return False
    if match.group(2):
        return True
    return not url[match.end():][:1].isdigit()


def normalize_url(url: str) -> str:
    """Strip surrounding whitespace/quotes and prepend https:// when no scheme."""
    if not url:
        return url
    url = url.strip().strip('"').strip("'")
    if not url:
        return url
    if not has_scheme(url):
        url = DEFAULT_SCHEME + url
    return url


def is_safe_url(url: str) -> bool:
    """True only for well-formed http(s) URLs without embedded credentials."""
    if not url or len(url) > MAX_URL_LENGTH:
        return False
    if any(char in url for char in ("\n", "\r", "\t", " ")):
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


def is_header_label(value: str) -> bool:
    """True when a cell is a header label such as 'URL' rather than a URL."""
    return value.strip().lower() in HEADER_LABELS


def looks_like_url(value: str) -> bool:
    """Loose heuristic: a URL has a scheme or at least one dot."""
    value = value.strip()
    return bool(value) and (value.startswith(SCHEMES) or "." in value)


def dedupe(urls) -> list:
    """De-duplicate while preserving order."""
    seen = set()
    result = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            result.append(url)
    return result
