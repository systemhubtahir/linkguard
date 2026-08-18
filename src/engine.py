import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from theme import (
    STATE_BROKEN,
    STATE_ERROR,
    STATE_HEALTHY,
    STATE_INVALID,
    STATE_REDIRECT,
    STATE_TIMEOUT,
    STATE_UNKNOWN,
)
from url_parser import parse_file  # noqa: F401 -- re-exported for callers
from url_utils import is_safe_url, normalize_url

TIMEOUT = 10
MAX_WORKERS = 10
MAX_REDIRECTS = 5
HEADERS = {
    'User-Agent': 'LinkGuard/1.0 (link health checker; +https://github.com/linkguard)'
}


def _classify(status_code):
    if status_code is None:
        return STATE_TIMEOUT
    if 200 <= status_code < 300:
        return STATE_HEALTHY
    if 300 <= status_code < 400:
        return STATE_REDIRECT
    if status_code == 404:
        return STATE_BROKEN
    if status_code >= 400:
        return STATE_ERROR
    return STATE_UNKNOWN


def _result(url, status_code, latency_ms, state):
    return {
        'url': url,
        'status_code': status_code,
        'latency_ms': round(latency_ms, 2),
        'state': state,
    }


def check_url(url):
    """
    Send HEAD request, fall back to GET on 405.
    Returns dict: {url, status_code, latency_ms, state}
    """
    url = normalize_url(url)
    if not is_safe_url(url):
        return _result(url, None, 0, STATE_INVALID)

    start = time.monotonic()
    streamed = None
    try:
        resp = requests.head(url, timeout=TIMEOUT, headers=HEADERS, allow_redirects=True)
        if resp.status_code == 405:
            resp = streamed = requests.get(url, timeout=TIMEOUT, headers=HEADERS,
                                           allow_redirects=True, stream=True)
        latency_ms = (time.monotonic() - start) * 1000
        if len(getattr(resp, 'history', ()) or ()) > MAX_REDIRECTS:
            return _result(url, resp.status_code, latency_ms, STATE_ERROR)
        return _result(url, resp.status_code, latency_ms, _classify(resp.status_code))
    except requests.exceptions.Timeout:
        return _result(url, None, TIMEOUT * 1000, STATE_TIMEOUT)
    except Exception:
        return _result(url, None, 0, STATE_ERROR)
    finally:
        if streamed is not None:
            streamed.close()


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
