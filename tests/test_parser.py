"""Tests for url_parser.parse_file."""
import os

import pytest

from src.url_parser import parse_file, _fix_scheme
from src.url_utils import is_safe_url


# ── _fix_scheme tests ────────────────────────────────────────────────────────

def test_fix_scheme_adds_https():
    assert _fix_scheme("example.com") == "https://example.com"

def test_fix_scheme_keeps_http():
    assert _fix_scheme("http://example.com") == "http://example.com"

def test_fix_scheme_keeps_https():
    assert _fix_scheme("https://example.com") == "https://example.com"

def test_fix_scheme_empty():
    assert _fix_scheme("") == ""


# ── parse_file TXT tests ─────────────────────────────────────────────────────

def test_parse_txt_basic(tmp_path):
    f = tmp_path / "urls.txt"
    f.write_text("https://google.com\nhttps://github.com\n")
    urls = parse_file(str(f))
    assert urls == ["https://google.com", "https://github.com"]

def test_parse_txt_deduplicates(tmp_path):
    f = tmp_path / "urls.txt"
    f.write_text("https://google.com\nhttps://google.com\nhttps://github.com\n")
    urls = parse_file(str(f))
    assert len(urls) == 2

def test_parse_txt_skips_empty_lines(tmp_path):
    f = tmp_path / "urls.txt"
    f.write_text("https://google.com\n\n  \nhttps://github.com\n")
    urls = parse_file(str(f))
    assert len(urls) == 2

def test_parse_txt_adds_scheme(tmp_path):
    f = tmp_path / "urls.txt"
    f.write_text("example.com\n")
    urls = parse_file(str(f))
    assert urls[0] == "https://example.com"


# ── parse_file CSV tests ─────────────────────────────────────────────────────

def test_parse_csv_single_column(tmp_path):
    f = tmp_path / "urls.csv"
    f.write_text("url\nhttps://google.com\nhttps://github.com\n")
    urls = parse_file(str(f))
    # 'url' header cell won't pass URL heuristic (no dot, no http)
    assert "https://google.com" in urls
    assert "https://github.com" in urls

def test_parse_csv_fixture():
    fixture = os.path.join(os.path.dirname(__file__), "fixtures", "sample.csv")
    urls = parse_file(fixture)
    assert len(urls) >= 3
    assert "https://www.google.com" in urls

def test_parse_unsupported_extension(tmp_path):
    f = tmp_path / "file.xlsx"
    f.write_text("data")
    with pytest.raises(ValueError, match="Unsupported"):
        parse_file(str(f))


# ── URL validation tests ─────────────────────────────────────────────────────

def test_is_safe_url_accepts_http_and_https():
    assert is_safe_url("http://example.com")
    assert is_safe_url("https://example.com/path?q=1")

def test_is_safe_url_rejects_other_schemes():
    assert not is_safe_url("file:///etc/passwd")
    assert not is_safe_url("javascript:alert(1)")

def test_is_safe_url_rejects_embedded_credentials():
    assert not is_safe_url("https://user:pass@example.com")

def test_is_safe_url_rejects_missing_host():
    assert not is_safe_url("https://")

def test_fix_scheme_keeps_existing_scheme():
    assert _fix_scheme("file:///etc/passwd") == "file:///etc/passwd"

def test_fix_scheme_adds_https_to_host_with_port():
    assert _fix_scheme("example.com:8080/a") == "https://example.com:8080/a"

def test_parse_file_drops_unsafe_urls(tmp_path):
    f = tmp_path / "urls.txt"
    f.write_text(
        "https://user:pass@example.com\n"
        "file:///etc/passwd\n"
        "javascript:alert(1)\n"
        "https://example.com\n"
    )
    assert parse_file(str(f)) == ["https://example.com"]

def test_parse_file_rejects_oversized_file(tmp_path, monkeypatch):
    from src import url_parser
    monkeypatch.setattr(url_parser, "MAX_FILE_BYTES", 10)
    f = tmp_path / "urls.txt"
    f.write_text("https://example.com\n" * 10)
    with pytest.raises(ValueError, match="larger than"):
        parse_file(str(f))
