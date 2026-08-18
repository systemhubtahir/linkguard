import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import threading
from unittest.mock import patch, MagicMock
import pytest
import requests
from engine import check_url, parse_file, run_scan, _classify


# ── _classify ──────────────────────────────────────────────────────────────

def test_classify_200():
    assert _classify(200) == 'Healthy'

def test_classify_301():
    assert _classify(301) == 'Redirect'

def test_classify_404():
    assert _classify(404) == 'Broken'

def test_classify_500():
    assert _classify(500) == 'Error'

def test_classify_none():
    assert _classify(None) == 'Timeout'


# ── check_url ──────────────────────────────────────────────────────────────

@patch('engine.requests.head')
def test_check_url_200(mock_head):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_head.return_value = mock_resp

    result = check_url('https://example.com')
    assert result['status_code'] == 200
    assert result['state'] == 'Healthy'
    assert result['latency_ms'] >= 0


@patch('engine.requests.head')
@patch('engine.requests.get')
def test_check_url_405_fallback(mock_get, mock_head):
    head_resp = MagicMock(); head_resp.status_code = 405
    get_resp  = MagicMock(); get_resp.status_code  = 200
    mock_head.return_value = head_resp
    mock_get.return_value  = get_resp

    result = check_url('https://example.com')
    assert result['status_code'] == 200
    assert mock_get.called


@patch('engine.requests.head')
def test_check_url_404(mock_head):
    mock_resp = MagicMock(); mock_resp.status_code = 404
    mock_head.return_value = mock_resp
    result = check_url('https://example.com/missing')
    assert result['state'] == 'Broken'


@patch('engine.requests.head', side_effect=__import__('requests').exceptions.Timeout)
def test_check_url_timeout(mock_head):
    result = check_url('https://slow-server.example.com')
    assert result['state'] == 'Timeout'
    assert result['status_code'] is None


@patch('engine.requests.head', side_effect=requests.exceptions.ConnectionError('DNS failed'))
def test_check_url_request_error_is_recorded(mock_head):
    result = check_url('https://unreachable.example.com')
    assert result['state'] == 'Error'
    assert result['error'] == 'DNS failed'


def test_check_url_prepends_scheme():
    with patch('engine.requests.head') as mock_head:
        mock_resp = MagicMock(); mock_resp.status_code = 200
        mock_head.return_value = mock_resp
        result = check_url('example.com')
        assert result['url'].startswith('https://')


def test_run_scan_delivers_worker_error_and_continues(monkeypatch):
    def fake_check_url(url):
        if url == 'bad.example.com':
            raise RuntimeError('worker failed')
        return {
            'url': url,
            'status_code': 200,
            'latency_ms': 1,
            'state': 'Healthy',
            'error': None
        }

    monkeypatch.setattr('engine.check_url', fake_check_url)
    results = []
    run_scan(
        ['bad.example.com', 'good.example.com'],
        results.append,
        threading.Event()
    )

    assert {result['url'] for result in results} == {
        'bad.example.com', 'good.example.com'
    }
    error_result = next(result for result in results if result['url'] == 'bad.example.com')
    assert error_result['state'] == 'Error'
    assert error_result['error'] == 'worker failed'


def test_run_scan_survives_callback_error(monkeypatch):
    monkeypatch.setattr(
        'engine.check_url',
        lambda url: {
            'url': url,
            'status_code': 200,
            'latency_ms': 1,
            'state': 'Healthy',
            'error': None
        }
    )
    received = []

    def callback(result):
        received.append(result)
        if len(received) == 1:
            raise RuntimeError('callback failed')

    run_scan(['first.example.com', 'second.example.com'], callback, threading.Event())

    assert len(received) == 2


# ── parse_file ─────────────────────────────────────────────────────────────

def test_parse_file_csv(tmp_path):
    f = tmp_path / 'urls.csv'
    f.write_text('url\nhttps://example.com\nhttps://test.org\nhttps://example.com\n')
    urls = parse_file(str(f))
    assert 'https://example.com' in urls
    assert len(urls) == 2  # deduplicated

def test_parse_file_txt(tmp_path):
    f = tmp_path / 'urls.txt'
    f.write_text('https://a.com\nhttps://b.com\n\n')
    urls = parse_file(str(f))
    assert len(urls) == 2

def test_parse_file_skips_headers(tmp_path):
    f = tmp_path / 'urls.csv'
    f.write_text('url\nhttps://a.com\n')
    urls = parse_file(str(f))
    assert all('url' not in u.lower() or u.startswith('http') for u in urls)
