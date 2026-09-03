"""
CDC PLACES client -- streaming bulk export from data.cdc.gov.

Two endpoints matter here, and picking the right one is the whole ballgame:

  /api/views/{id}/rows.csv?accessType=DOWNLOAD
      Streams the entire dataset over one connection. Measured: the 694MB
      census-tract file in 94.6s, the 53MB county file in 7.4s. This is what
      bulk ingest uses.

  /resource/{id}.csv?$order=:id&$limit=...&$offset=...
      Paged SoQL, the approach cdc_open.download uses. One 50,000-row page of
      the tract dataset took 435 SECONDS, and Socrata's $offset degrades as the
      offset grows -- 61 pages would never finish inside a CI job. Not used for
      bulk here; still correct (and honors $where) for small live queries.

Note that $where is SILENTLY IGNORED on the export endpoint: requesting
`&$where=stateabbr='WY'` against the county dataset returned all 229,299 lines,
byte-identical to unfiltered. It fails open, so no filtering can be pushed to
the server on this path -- everything is filtered client-side while streaming.

No auth required; set CDC_DATA_APP_TOKEN for higher rate limits.
"""

import csv
import os
import time
from collections.abc import Iterator
from pathlib import Path

import requests

BASE_URL = "https://data.cdc.gov"
_TIMEOUT = (30, 300)  # (connect, read) -- read timeout is per-chunk, not total
_MAX_RETRIES = 3
_RETRY_BACKOFF = [10, 30]  # seconds to wait before retry 2 and 3
_CHUNK = 1 << 20  # 1MiB


class PlacesClient:
    """Streaming HTTP client for the data.cdc.gov bulk export endpoint."""

    def __init__(self, app_token: str | None = None, timeout=_TIMEOUT):
        self.timeout = timeout
        self.session = requests.Session()
        token = app_token or os.environ.get("CDC_DATA_APP_TOKEN")
        if token:
            self.session.headers["X-App-Token"] = token

    # ── metadata ──────────────────────────────────────────────────────────────

    def metadata(self, socrata_id: str) -> dict:
        """Dataset metadata. `rowsUpdatedAt` is the change signal that lets a
        scheduled run skip a release it has already ingested."""
        url = f"{BASE_URL}/api/views/{socrata_id}.json"
        resp = self._get_with_retry(url, stream=False)
        return resp.json()

    def rows_updated_at(self, socrata_id: str) -> int:
        """Unix timestamp of the last data change, per Socrata."""
        return int(self.metadata(socrata_id)["rowsUpdatedAt"])

    # ── bulk export ───────────────────────────────────────────────────────────

    def download(self, socrata_id: str, dest: Path) -> int:
        """Stream the full dataset export to `dest`. Returns bytes written.

        Writes straight to disk in chunks; the tract export is 694MB and must
        never be materialized as a string (which is what cdc_open.download's
        `_fetch_csv_paginated` does, and why it is not reused here).
        """
        url = f"{BASE_URL}/api/views/{socrata_id}/rows.csv"
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        resp = self._get_with_retry(url, params={"accessType": "DOWNLOAD"}, stream=True)
        written = 0
        with tmp.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=_CHUNK):
                if chunk:
                    f.write(chunk)
                    written += len(chunk)
        # Rename only once the stream completed, so an interrupted download can
        # never be mistaken for a finished one on a later run.
        tmp.replace(dest)
        return written

    @staticmethod
    def read_csv(path: Path) -> Iterator[dict[str, str]]:
        """Iterate a downloaded export row by row, never loading it whole."""
        with path.open(newline="", encoding="utf-8") as f:
            yield from csv.DictReader(f)

    # ── internals ─────────────────────────────────────────────────────────────

    def _get_with_retry(
        self, url: str, params: dict | None = None, stream: bool = False
    ):
        last_exc: requests.RequestException | None = None
        for attempt in range(_MAX_RETRIES):
            if attempt > 0:
                wait = _RETRY_BACKOFF[attempt - 1]
                print(
                    f"retry {attempt}/{_MAX_RETRIES - 1} (waiting {wait}s) ...",
                    end=" ",
                    flush=True,
                )
                time.sleep(wait)
            try:
                resp = self.session.get(
                    url, params=params, timeout=self.timeout, stream=stream
                )
                resp.raise_for_status()
                return resp
            # Transport faults and HTTP errors are what retrying can fix
            # (raise_for_status raises HTTPError, itself a RequestException).
            # Anything else is a bug in this file and should surface at once
            # rather than be swallowed three times over.
            except requests.RequestException as exc:
                last_exc = exc
                print(f"ERROR: {exc}")
        raise last_exc
