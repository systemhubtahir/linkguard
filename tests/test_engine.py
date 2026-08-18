from unittest.mock import patch, MagicMock
import pytest
from engine import check_url, parse_file, _classify


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


def test_check_url_rejects_non_http_scheme():
    result = check_url('file:///etc/passwd')
    assert result['state'] == 'Invalid'
    assert result['status_code'] is None


def test_check_url_rejects_embedded_credentials():
    assert check_url('https://user:pass@example.com')['state'] == 'Invalid'
