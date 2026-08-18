"""Tests for url_parser.parse_file."""
import os

import pytest

from src.url_parser import parse_file, _fix_scheme


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
    # duplicated example.com appears once, 'bad-url-no-scheme' fails the URL heuristic
    assert urls == [
        "https://example.com",
        "https://httpstat.us/404",
        "https://httpstat.us/200",
    ]


def test_parse_txt_fixture():
    fixture = os.path.join(os.path.dirname(__file__), "fixtures", "sample.txt")
    urls = parse_file(fixture)
    assert "https://www.google.com" in urls
    assert len(urls) == 5

def test_parse_unsupported_extension(tmp_path):
    f = tmp_path / "file.xlsx"
    f.write_text("data")
    with pytest.raises(ValueError, match="Unsupported"):
        parse_file(str(f))
