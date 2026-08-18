import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import threading
from unittest.mock import patch, MagicMock
import requests
import pytest
import engine
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


def test_check_url_prepends_scheme():
    with patch('engine.requests.head') as mock_head:
        mock_resp = MagicMock(); mock_resp.status_code = 200
        mock_head.return_value = mock_resp
        result = check_url('example.com')
        assert result['url'].startswith('https://')


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


# ── _classify (remaining branches) ─────────────────────────────────────────

def test_classify_informational_is_unknown():
    assert _classify(100) == 'Unknown'

def test_classify_403_is_error():
    assert _classify(403) == 'Error'

def test_classify_boundaries():
    assert _classify(299) == 'Healthy'
    assert _classify(399) == 'Redirect'


# ── check_url (error paths) ────────────────────────────────────────────────

@patch('engine.requests.head', side_effect=requests.exceptions.ConnectionError)
def test_check_url_connection_error(mock_head):
    result = check_url('https://does-not-resolve.example')
    assert result == {
        'url': 'https://does-not-resolve.example',
        'status_code': None,
        'latency_ms': 0,
        'state': 'Error',
    }


@patch('engine.requests.head', side_effect=ValueError('bad url'))
def test_check_url_unexpected_exception(mock_head):
    result = check_url('https://example.com')
    assert result['state'] == 'Error'
    assert result['status_code'] is None


@patch('engine.requests.head', side_effect=requests.exceptions.Timeout)
def test_check_url_timeout_latency_is_timeout_budget(mock_head):
    result = check_url('https://example.com')
    assert result['latency_ms'] == engine.TIMEOUT * 1000


@patch('engine.requests.head')
def test_check_url_strips_whitespace(mock_head):
    mock_head.return_value = MagicMock(status_code=200)
    result = check_url('  https://example.com  ')
    assert result['url'] == 'https://example.com'
    assert mock_head.call_args.args[0] == 'https://example.com'


@patch('engine.requests.head')
def test_check_url_follows_redirects_with_headers(mock_head):
    mock_head.return_value = MagicMock(status_code=200)
    check_url('https://example.com')
    kwargs = mock_head.call_args.kwargs
    assert kwargs['allow_redirects'] is True
    assert kwargs['timeout'] == engine.TIMEOUT
    assert kwargs['headers'] is engine.HEADERS


# ── run_scan ──────────────────────────────────────────────────────────────

def test_run_scan_calls_callback_for_every_url():
    urls = ['https://a.com', 'https://b.com', 'https://c.com']
    results = []
    with patch('engine.check_url', side_effect=lambda u: {'url': u, 'state': 'Healthy'}):
        run_scan(urls, results.append, threading.Event())
    assert sorted(r['url'] for r in results) == urls


def test_run_scan_empty_urls_does_nothing():
    results = []
    with patch('engine.check_url') as check:
        run_scan([], results.append, threading.Event())
    check.assert_not_called()
    assert results == []


def test_run_scan_stops_when_event_already_set():
    results = []
    stop_event = threading.Event()
    stop_event.set()
    with patch('engine.check_url', side_effect=lambda u: {'url': u, 'state': 'Healthy'}):
        run_scan(['https://a.com', 'https://b.com'], results.append, stop_event)
    assert results == []


def test_run_scan_stops_mid_flight_when_event_set():
    urls = [f'https://{i}.com' for i in range(20)]
    results = []
    stop_event = threading.Event()

    def callback(result):
        results.append(result)
        stop_event.set()  # stop after the first delivered result

    with patch('engine.check_url', side_effect=lambda u: {'url': u, 'state': 'Healthy'}):
        run_scan(urls, callback, stop_event)

    assert len(results) == 1
