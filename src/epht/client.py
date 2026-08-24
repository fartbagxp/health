"""
Low-level HTTP client for CDC's Environmental Public Health Tracking Network
(EPHT) Data API at ephtracking.cdc.gov/apigateway/api/v1.

The API is a discovery-then-fetch REST/JSON service. Endpoints used here:

    GET  /contentareas/json
    GET  /measuresearch                              -> every measure + its IDs
    GET  /geographicTypes/{measureId}                -> State / County types
    GET  /stratificationlevel/{measureId}/{geoTypeId}/{smoothing}
    GET  /temporalItems/{measureId}/{geoTypeId}/ALL/ALL
    POST /getCoreHolder/{measureId}/{stratLevelId}/{smoothing}/0   -> the data

No API key is strictly required, but the server aggressively rate-limits
unauthenticated ("non-token") requests with HTTP 429. Set EPHT_API_TOKEN (a free
key from https://ephtracking.cdc.gov/apihelp) to raise the limit; the token is
passed as an ``apiToken`` query parameter. Responses are cached in-process for
24 hours, and 429s are retried with backoff.
"""

from __future__ import annotations

import os
import time
from typing import Any

import requests

_BASE = "https://ephtracking.cdc.gov/apigateway/api/v1"
_CACHE: dict[str, Any] = {}
_SESSION: requests.Session | None = None

_MAX_RETRIES = 5
_BACKOFF = [15, 30, 45, 60]  # seconds before retries 2..5


def _session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers.update({"Accept": "application/json"})
    return _SESSION


def _token() -> str | None:
    return os.environ.get("EPHT_API_TOKEN")


def _with_token(path: str) -> str:
    url = f"{_BASE}{path}"
    token = _token()
    if token:
        url += ("&" if "?" in path else "?") + f"apiToken={token}"
    return url


def _is_rate_limited(payload: Any) -> bool:
    return isinstance(payload, dict) and payload.get("code") == 429


def _request(method: str, path: str, body: dict | None = None) -> Any:
    url = _with_token(path)
    last: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        if attempt:
            time.sleep(_BACKOFF[min(attempt - 1, len(_BACKOFF) - 1)])
        try:
            if method == "GET":
                resp = _session().get(url, timeout=60)
            else:
                resp = _session().post(url, json=body, timeout=120)
            try:
                payload = resp.json()
            except ValueError:
                # A throttled POST can return a non-JSON body; treat as retryable.
                last = ValueError(f"non-JSON response (HTTP {resp.status_code})")
                continue
            if _is_rate_limited(payload):
                last = RuntimeError("EPHT rate limit (HTTP 429) -- set EPHT_API_TOKEN")
                continue
            return payload
        except Exception as exc:  # noqa: BLE001
            last = exc
    raise RuntimeError(f"EPHT request failed after {_MAX_RETRIES} tries: {last}")


def _cached(key: str, fn) -> Any:
    if key not in _CACHE:
        _CACHE[key] = fn()
    return _CACHE[key]


# ── Discovery ────────────────────────────────────────────────────────────────


def content_areas() -> list[dict]:
    """All content areas, e.g. {'id': 3, 'name': 'Asthma'}."""
    return _cached("contentareas", lambda: _request("GET", "/contentareas/json"))


def measures() -> list[dict]:
    """Every measure with its contentArea/indicator/measure IDs and name."""
    return _cached("measuresearch", lambda: _request("GET", "/measuresearch"))


def geographic_types(measure_id: int) -> list[dict]:
    """Geographic types available for a measure (State, County, ...)."""
    return _cached(
        f"geotypes:{measure_id}",
        lambda: _request("GET", f"/geographicTypes/{measure_id}"),
    )


def stratification_levels(measure_id: int, geo_type_id: int, smoothing: int = 0) -> list[dict]:
    """Stratification levels for a measure x geographic type. The plain level
    (``name == 'State'``) has an empty ``stratificationType`` -- that's the
    one-row-per-state-per-year series with no demographic split."""
    return _cached(
        f"strat:{measure_id}:{geo_type_id}:{smoothing}",
        lambda: _request(
            "GET", f"/stratificationlevel/{measure_id}/{geo_type_id}/{smoothing}"
        ),
    )


# ── Data ─────────────────────────────────────────────────────────────────────


def core_holder(
    measure_id: int,
    stratification_level_id: int,
    geo_type_id: int,
    smoothing: int = 0,
) -> list[dict]:
    """Fetch the data table for a measure at one stratification level, across all
    geographies and all time periods (``ALL``/``ALL`` wildcards). Returns the
    ``tableResult`` record list (one row per geography x time period)."""
    body = {
        "geographicTypeIdFilter": str(geo_type_id),
        "geographicItemsFilter": "ALL",
        "temporalTypeIdFilter": "ALL",
        "temporalItemsFilter": "ALL",
    }
    payload = _request(
        "POST",
        f"/getCoreHolder/{measure_id}/{stratification_level_id}/{smoothing}/0",
        body=body,
    )
    if not isinstance(payload, dict):
        return []
    table = payload.get("tableResult")
    if isinstance(table, list):
        return table
    # The data element's name can vary by measure; fall back to the first list
    # of records we can find.
    for value in payload.values():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            return value
    return []


def clear_cache() -> None:
    _CACHE.clear()
