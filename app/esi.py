import time
import requests

from .config import DATASOURCE

BASE = "https://esi.evetech.net/latest"
HEADERS = {"Accept": "application/json"}


def get(url, params=None, etag=None, token=None):
    headers = dict(HEADERS)
    if etag:
        headers["If-None-Match"] = etag
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(url, params=params, headers=headers, timeout=30)
    if r.status_code == 304:
        return None, r.headers, 304
    if r.status_code >= 400:
        reset = int(r.headers.get("X-ESI-Error-Limit-Reset", "5"))
        time.sleep(max(reset, 2))
        r.raise_for_status()
    return r.json(), r.headers, r.status_code


def paged(url, params=None, token=None):
    page = 1
    while True:
        p = dict(params or {})
        p["page"] = page
        data, hdrs, _ = get(url, params=p, token=token)
        if not data:
            break
        for row in data:
            yield row
        pages = int(hdrs.get("X-Pages", "1"))
        if page >= pages:
            break
        page += 1
