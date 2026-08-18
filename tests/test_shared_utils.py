"""Tests for the shared helpers extracted into theme, url_utils and paths."""
import os

import pytest

import paths
from paths import ensure_dir, project_path
from theme import (
    ERROR_STATES,
    GRAY_400,
    STATE_BROKEN,
    STATE_HEALTHY,
    STATE_UNKNOWN,
    STATUS_COLORS,
    is_error_state,
    state_color,
)
from url_utils import dedupe, is_header_label, looks_like_url, normalize_url


# ── theme ──────────────────────────────────────────────────────────────────

def test_error_states_are_the_failing_ones():
    assert set(ERROR_STATES) == {'Broken', 'Error', 'Timeout'}


@pytest.mark.parametrize('state,expected', [
    (STATE_HEALTHY, False),
    ('Redirect', False),
    (STATE_BROKEN, True),
    ('Error', True),
    ('Timeout', True),
    (STATE_UNKNOWN, False),
])
def test_is_error_state(state, expected):
    assert is_error_state(state) is expected


def test_state_color_known_state():
    assert state_color(STATE_HEALTHY) == STATUS_COLORS[STATE_HEALTHY]


def test_state_color_unknown_state_falls_back_to_gray():
    assert state_color('Something Else') == GRAY_400


# ── url_utils ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize('raw,expected', [
    ('example.com', 'https://example.com'),
    ('  example.com  ', 'https://example.com'),
    ('"example.com"', 'https://example.com'),
    ("'example.com'", 'https://example.com'),
    ('http://example.com', 'http://example.com'),
    ('https://example.com', 'https://example.com'),
])
def test_normalize_url(raw, expected):
    assert normalize_url(raw) == expected


@pytest.mark.parametrize('raw', ['', '   ', '""'])
def test_normalize_url_blank_stays_blank(raw):
    assert normalize_url(raw).strip('"') == ''


@pytest.mark.parametrize('value,expected', [
    ('url', True),
    ('URL', True),
    (' Link ', True),
    ('href', True),
    ('https://example.com', False),
])
def test_is_header_label(value, expected):
    assert is_header_label(value) is expected


@pytest.mark.parametrize('value,expected', [
    ('example.com', True),
    ('http://localhost', True),
    ('notaurl', False),
    ('', False),
    ('   ', False),
])
def test_looks_like_url(value, expected):
    assert looks_like_url(value) is expected


def test_dedupe_preserves_order():
    assert dedupe(['b', 'a', 'b', 'c', 'a']) == ['b', 'a', 'c']


def test_dedupe_empty():
    assert dedupe([]) == []


# ── paths ──────────────────────────────────────────────────────────────────

def test_project_path_joins_under_root():
    assert project_path('data', 'x.db') == os.path.join(paths.PROJECT_ROOT, 'data', 'x.db')


def test_project_path_respects_patched_root(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, 'PROJECT_ROOT', str(tmp_path))
    assert project_path('exports') == os.path.join(str(tmp_path), 'exports')


def test_ensure_dir_creates_and_is_idempotent(tmp_path):
    target = tmp_path / 'nested' / 'dir'
    assert ensure_dir(str(target)) == str(target)
    assert target.is_dir()
    assert ensure_dir(str(target)) == str(target)  # no error on second call
