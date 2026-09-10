"""
Shared fetch helper for the health-department directory scrapers.

FSIS and NACCHO both sit behind bot protection that rejects plain ``requests``
and ``WebFetch`` with a 403. ``curl_cffi`` with browser TLS impersonation
(the same dependency the rest of the repo already ships) is accepted.
"""

import time

from curl_cffi import requests as cffi

_TIMEOUT = 45
_IMPERSONATE = "chrome"


class ScrapeError(RuntimeError):
    """A source did not return the document we asked for.

    Covers both a hard failure (timeout, 4xx/5xx) and the quieter case of a
    200 that is not the page we wanted -- a bot-protection challenge, say.
    """


def fetch(url: str, *, retries: int = 2, backoff: float = 2.0) -> str:
    """GET ``url`` as HTML text, impersonating Chrome. Retries on failure."""
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = cffi.get(url, impersonate=_IMPERSONATE, timeout=_TIMEOUT)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:  # noqa: BLE001 — surface the final error below
            last_exc = exc
            if attempt < retries:
                time.sleep(backoff * (attempt + 1))
    raise ScrapeError(f"Failed to fetch {url}: {last_exc}")
