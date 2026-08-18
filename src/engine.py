import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from theme import (
    STATE_BROKEN,
    STATE_ERROR,
    STATE_HEALTHY,
    STATE_REDIRECT,
    STATE_TIMEOUT,
    STATE_UNKNOWN,
)
from url_parser import parse_file  # noqa: F401 -- re-exported for callers
from url_utils import normalize_url

TIMEOUT = 10
MAX_WORKERS = 10
PAUSE_POLL_INTERVAL = 0.1
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

    start = time.monotonic()
    try:
        resp = requests.head(url, timeout=TIMEOUT, headers=HEADERS, allow_redirects=True)
        if resp.status_code == 405:
            resp = requests.get(url, timeout=TIMEOUT, headers=HEADERS, allow_redirects=True, stream=True)
        latency_ms = (time.monotonic() - start) * 1000
        return _result(url, resp.status_code, latency_ms, _classify(resp.status_code))
    except requests.exceptions.Timeout:
        return _result(url, None, TIMEOUT * 1000, STATE_TIMEOUT)
    except Exception:
        return _result(url, None, 0, STATE_ERROR)


def _cancelled(cancel_event):
    return cancel_event is not None and cancel_event.is_set()


def _await_resume(pause_event, cancel_event):
    """Block while paused. Returns False if the scan should not continue."""
    while pause_event.is_set() and not _cancelled(cancel_event):
        time.sleep(PAUSE_POLL_INTERVAL)
    return not _cancelled(cancel_event)


def run_scan(urls, callback, pause_event, cancel_event=None):
    """
    Multi-threaded scan, submitted in batches of MAX_WORKERS.
    callback(result_dict) called on main thread via queue — caller handles threading.
    pause_event: threading.Event, set to hold the scan before the next batch,
                 clear to resume it.
    cancel_event: optional threading.Event, set to abort the scan for good.
    """
    urls = list(urls)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for offset in range(0, len(urls), MAX_WORKERS):
            if not _await_resume(pause_event, cancel_event):
                break
            futures = [executor.submit(check_url, url)
                       for url in urls[offset:offset + MAX_WORKERS]]
            for future in as_completed(futures):
                if _cancelled(cancel_event):
                    executor.shutdown(wait=False, cancel_futures=True)
                    return
                callback(future.result())
