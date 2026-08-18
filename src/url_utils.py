"""
url_utils.py -- Shared URL normalisation and de-duplication helpers.
"""

SCHEMES = ("http://", "https://")
DEFAULT_SCHEME = "https://"

# Cells/lines that are column headers rather than URLs.
HEADER_LABELS = ("url", "link", "href")


def normalize_url(url: str) -> str:
    """Strip surrounding whitespace/quotes and prepend https:// when no scheme."""
    if not url:
        return url
    url = url.strip().strip('"').strip("'")
    if not url:
        return url
    if not url.startswith(SCHEMES):
        url = DEFAULT_SCHEME + url
    return url


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
