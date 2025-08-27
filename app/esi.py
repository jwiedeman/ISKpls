import time
import logging
import requests

from .config import DATASOURCE

BASE = "https://esi.evetech.net/latest"
HEADERS = {"Accept": "application/json"}

logger = logging.getLogger(__name__)

# Track ESI error limit headers for observability
ERROR_LIMIT_REMAIN = 100
ERROR_LIMIT_RESET = 0


def get(url, params=None, etag=None, token=None):
    headers = dict(HEADERS)
    if etag:
        headers["If-None-Match"] = etag
    if token:
        headers["Authorization"] = f"Bearer {token}"
    logger.info("GET %s params=%s", url, params)
    r = requests.get(url, params=params, headers=headers, timeout=30)
    global ERROR_LIMIT_REMAIN, ERROR_LIMIT_RESET
    ERROR_LIMIT_REMAIN = int(r.headers.get("X-ESI-Error-Limit-Remain", ERROR_LIMIT_REMAIN))
    ERROR_LIMIT_RESET = int(r.headers.get("X-ESI-Error-Limit-Reset", ERROR_LIMIT_RESET))
    logger.info(
        "response %s %s", r.status_code, r.headers.get("X-Pages")
    )
    if r.status_code == 304:
        return None, r.headers, 304
    if r.status_code >= 400:
        reset = ERROR_LIMIT_RESET or 5
        logger.warning("error %s, sleeping %s", r.status_code, reset)
        time.sleep(max(reset, 2))
        r.raise_for_status()
    return r.json(), r.headers, r.status_code


def paged(url, params=None, token=None):
    page = 1
    while True:
        p = dict(params or {})
        p["page"] = page
        logger.info("Fetching page %s for %s", page, url)
        data, hdrs, _ = get(url, params=p, token=token)
        if not data:
            logger.info("No data for page %s", page)
            break
        for row in data:
            yield row
        pages = int(hdrs.get("X-Pages", "1"))
        if page >= pages:
            break
        page += 1


def get_error_limit_status():
    """Return current cached ESI error limit information."""
    return {
        "error_limit_remain": ERROR_LIMIT_REMAIN,
        "error_limit_reset": ERROR_LIMIT_RESET,
    }
