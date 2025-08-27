"""OAuth helpers for obtaining and refreshing EVE SSO tokens.

The flow uses a temporary local HTTP server to capture the authorization
code after the user logs in via their browser.  Tokens are cached in
``token.json`` so subsequent runs can refresh automatically without
prompting for another login.

Environment variables required:

``EVE_CLIENT_ID`` and ``EVE_CLIENT_SECRET`` – credentials from the EVE
developer application.  ``EVE_CALLBACK_URL`` may also be set to override
the default ``http://localhost:5000/callback``.  ``CHAR_ID`` is handled
elsewhere.
"""

from __future__ import annotations

import base64
import json
import os
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict

import requests
from dotenv import load_dotenv


load_dotenv()

TOKEN_FILE = "token.json"

CLIENT_ID = os.environ.get("EVE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("EVE_CLIENT_SECRET")
CALLBACK_URL = os.environ.get("EVE_CALLBACK_URL", "http://localhost:5000/callback")

# Scopes required for character syncing
SCOPES = " ".join(
    [
        "esi-wallet.read_character_wallet.v1",
        "esi-markets.read_character_orders.v1",
        "esi-assets.read_assets.v1",
    ]
)


def _save_tokens(data: Dict[str, str]) -> None:
    expires_at = time.time() + int(data.get("expires_in", 0)) - 60
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token"),
                "expires_at": expires_at,
            },
            f,
        )


def _load_tokens() -> Dict[str, str] | None:
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _token_request(payload: Dict[str, str]) -> Dict[str, str]:
    auth = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    r = requests.post(
        "https://login.eveonline.com/v2/oauth/token",
        headers={"Authorization": f"Basic {auth}"},
        data=payload,
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    _save_tokens(data)
    return data


def _exchange_code(code: str) -> str:
    data = _token_request({"grant_type": "authorization_code", "code": code})
    return data["access_token"]


def _refresh(refresh_token: str) -> str:
    data = _token_request({"grant_type": "refresh_token", "refresh_token": refresh_token})
    return data["access_token"]


def _run_local_server() -> str:
    """Spin up a one-shot HTTP server to capture the auth code."""

    code_container: Dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # type: ignore[override]
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query)
            code_container["code"] = qs.get("code", [""])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Authorization successful. You may close this window.")

        def log_message(self, format, *args):  # pragma: no cover - silence server logs
            return

    url = urllib.parse.urlparse(CALLBACK_URL)
    # Bind to all interfaces so the callback can be received when running in
    # containers or behind port forwarding setups where ``localhost`` inside the
    # process would otherwise not be reachable from the user's browser.  Using
    # an empty string instead of ``localhost`` makes the server listen on
    # ``0.0.0.0`` which covers these cases while still working for local runs.
    server = HTTPServer(("", url.port or 5000), Handler)
    thread = threading.Thread(target=server.handle_request)
    thread.start()
    thread.join()
    server.server_close()
    return code_container.get("code", "")


def _start_authorization() -> str:
    params = {
        "response_type": "code",
        "redirect_uri": CALLBACK_URL,
        "client_id": CLIENT_ID,
        "scope": SCOPES,
        "state": "vh",
    }
    url = "https://login.eveonline.com/v2/oauth/authorize/" + "?" + urllib.parse.urlencode(params)
    webbrowser.open(url)
    return _run_local_server()


def get_token() -> str:
    """Return a valid access token, refreshing or logging in if needed."""

    if not CLIENT_ID or not CLIENT_SECRET:
        raise RuntimeError("EVE_CLIENT_ID and EVE_CLIENT_SECRET must be set in the environment")

    tokens = _load_tokens()
    now = time.time()
    if tokens and tokens.get("expires_at", 0) > now and tokens.get("access_token"):
        return tokens["access_token"]
    if tokens and tokens.get("refresh_token"):
        try:
            return _refresh(tokens["refresh_token"])
        except Exception:
            pass
    code = _start_authorization()
    if not code:
        raise RuntimeError("Authorization failed; no code received")
    return _exchange_code(code)

