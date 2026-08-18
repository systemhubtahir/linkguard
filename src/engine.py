import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from url_parser import _fix_scheme, is_safe_url
from url_parser import parse_file as _parse_url_file

TIMEOUT = 10
MAX_WORKERS = 10
MAX_REDIRECTS = 5
HEADERS = {
    'User-Agent': 'LinkGuard/1.0 (link health checker; +https://github.com/linkguard)'
}


def _classify(status_code):
    if status_code is None:
        return 'Timeout'
    if 200 <= status_code < 300:
        return 'Healthy'
    if 300 <= status_code < 400:
        return 'Redirect'
    if status_code == 404:
        return 'Broken'
    if status_code >= 400:
        return 'Error'
    return 'Unknown'


def check_url(url):
    """
    Send HEAD request, fall back to GET on 405.
    Returns dict: {url, status_code, latency_ms, state}
    """
    url = _fix_scheme(url.strip())

    if not is_safe_url(url):
        return {'url': url, 'status_code': None, 'latency_ms': 0, 'state': 'Invalid'}

    start = time.monotonic()
    streamed = None
    try:
        resp = requests.head(url, timeout=TIMEOUT, headers=HEADERS, allow_redirects=True)
        if resp.status_code == 405:
            resp = streamed = requests.get(url, timeout=TIMEOUT, headers=HEADERS,
                                           allow_redirects=True, stream=True)
        latency_ms = (time.monotonic() - start) * 1000
        if len(getattr(resp, 'history', ()) or ()) > MAX_REDIRECTS:
            return {'url': url, 'status_code': resp.status_code,
                    'latency_ms': round(latency_ms, 2), 'state': 'Error'}
        return {
            'url': url,
            'status_code': resp.status_code,
            'latency_ms': round(latency_ms, 2),
            'state': _classify(resp.status_code)
        }
    except requests.exceptions.TooManyRedirects:
        return {'url': url, 'status_code': None, 'latency_ms': 0, 'state': 'Error'}
    except requests.exceptions.Timeout:
        return {'url': url, 'status_code': None, 'latency_ms': TIMEOUT * 1000, 'state': 'Timeout'}
    except requests.exceptions.ConnectionError:
        return {'url': url, 'status_code': None, 'latency_ms': 0, 'state': 'Error'}
    except Exception:
        return {'url': url, 'status_code': None, 'latency_ms': 0, 'state': 'Error'}
    finally:
        if streamed is not None:
            streamed.close()


def parse_file(filepath):
    """
    Parse .csv or .txt file and return clean list of validated URL strings.
    Handles empty rows, duplicates, whitespace.
    """
    return _parse_url_file(filepath)


def run_scan(urls, callback, stop_event):
    """
    Multi-threaded scan.
    callback(result_dict) called on main thread via queue — caller handles threading.
    stop_event: threading.Event, set to pause/stop workers.
    """
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(check_url, url): url for url in urls}
        for future in as_completed(futures):
            if stop_event.is_set():
                executor.shutdown(wait=False, cancel_futures=True)
                break
            result = future.result()
            callback(result)
