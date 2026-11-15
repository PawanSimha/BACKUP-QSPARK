"""ORDS (Oracle REST Data Services) proxy.

Calls the qsparking.api.v3 module instead of touching SQLite directly.
Configuration comes from ORDS_BASE_URL, e.g.
    ORDS_BASE_URL=https://<host>/ords/nov_2026_batch
Read at call time so .env load order does not matter.
"""

import os
from typing import Any, Optional, Tuple

import requests

DEFAULT_TIMEOUT = 30


def _base_url() -> str:
    base = (os.getenv("ORDS_BASE_URL") or "").rstrip("/")
    if not base:
        raise RuntimeError(
            "ORDS_BASE_URL is not set. Add it to .env, e.g. "
            "ORDS_BASE_URL=https://<host>/ords/nov_2026_batch"
        )
    return base


def _url(path: str) -> str:
    return f"{_base_url()}/{'/' if not path.startswith('/') else ''}{path}"


def _split(resp: requests.Response) -> Tuple[int, Any]:
    try:
        return resp.status_code, resp.json()
    except ValueError:
        return resp.status_code, resp.text


def ords_get(path: str, params: Optional[dict] = None) -> Tuple[int, Any]:
    """GET an ORDS path. Returns (status_code, json_or_text). Never raises."""
    try:
        return _split(requests.get(_url(path), params=params, timeout=DEFAULT_TIMEOUT))
    except Exception as exc:
        return 0, str(exc)


def ords_post(path: str, json: Optional[dict] = None,
              params: Optional[dict] = None) -> Tuple[int, Any]:
    """POST an ORDS path. Returns (status_code, json_or_text). Never raises."""
    try:
        return _split(requests.post(_url(path), json=json, params=params,
                                    timeout=DEFAULT_TIMEOUT))
    except Exception as exc:
        return 0, str(exc)
