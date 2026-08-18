import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

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
HEADERS = {
    'User-Agent': 'LinkGuard/1.0 (link health checker; +https://github.com/linkguard)'
}
logger = logging.getLogger(__name__)


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


def _result(url, status_code, latency_ms, state, error=None):
    return {
        'url': url,
        'status_code': status_code,
        'latency_ms': round(latency_ms, 2),
        'state': state,
        'error': error,
    }


def check_url(url):
    """
    Send HEAD request, fall back to GET on 405.
    Returns dict: {url, status_code, latency_ms, state, error}
    """
    url = normalize_url(url)

    start = time.monotonic()
    try:
        resp = requests.head(url, timeout=TIMEOUT, headers=HEADERS, allow_redirects=True)
        if resp.status_code == 405:
            resp = requests.get(url, timeout=TIMEOUT, headers=HEADERS, allow_redirects=True, stream=True)
        latency_ms = (time.monotonic() - start) * 1000
        return _result(url, resp.status_code, latency_ms, _classify(resp.status_code))
    except requests.exceptions.Timeout as exc:
        logger.warning('Timeout while checking %s: %s', url, exc)
        return _result(
            url,
            None,
            TIMEOUT * 1000,
            STATE_TIMEOUT,
            str(exc) or exc.__class__.__name__
        )
    except requests.exceptions.RequestException as exc:
        logger.warning('Request failed while checking %s: %s', url, exc)
        return _result(
            url,
            None,
            0,
            STATE_ERROR,
            str(exc) or exc.__class__.__name__
        )
    except Exception as exc:
        logger.exception('Unexpected error while checking %s', url)
        return _result(
            url,
            None,
            0,
            STATE_ERROR,
            str(exc) or exc.__class__.__name__
        )


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
            url = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                logger.exception('Unexpected worker error while checking %s', url)
                result = _result(
                    url,
                    None,
                    0,
                    STATE_ERROR,
                    str(exc) or exc.__class__.__name__
                )
            try:
                callback(result)
            except Exception:
                logger.exception('Scan callback failed while handling %s', url)
