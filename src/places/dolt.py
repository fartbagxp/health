"""
DoltHub API client -- import files without cloning the database.

Cloning a multi-GB Dolt database into a CI runner is impractical, so this uses
DoltHub's HTTP import path instead. No `dolt` binary is involved.

## Why v1alpha1 and not v2

The v2 REST API documents a nicer import flow (pre-signed multipart upload, no
size ceiling). It is unusable here: tokens issued by
https://www.dolthub.com/settings/tokens are rejected by every v2 endpoint with
401 `no token found for given API token` -- verified with two independently
generated tokens, scoped and unscoped, against `/user`, `/databases/{o}/{d}`,
`/branches` and `/imports/uploads`. The same tokens authenticate v1alpha1
perfectly. Whatever credential v2 wants, that settings page does not issue it.

So this speaks v1alpha1:

    POST /api/v1alpha1/{owner}/{db}/upload          multipart file + params
    POST /api/v1alpha1/{owner}/{db}/write/{f}/{t}   SQL write (DDL and DML)
    GET  /api/v1alpha1/{owner}/{db}/write?operationName=...   poll either one
    GET  /api/v1alpha1/{owner}/{db}/{branch}?q=...  read (no credential needed)

Auth is `authorization: token <TOKEN>` -- note the `token` scheme, not `Bearer`.

## The 100MB ceiling

v1alpha1 caps an uploaded file at 100MB, which v2's multipart flow would not
have. The tract fact table is ~137MB, so `import_csv` splits anything large
into chunks and uploads them in sequence. Tables are created from schema.sql
first and every import is an upsert, so chunking is safe: each chunk is just
more rows keyed by the same primary key.

Reads need no credential at all -- the database is public, which is also what
lets health-charts query it straight from the browser.
"""

import csv
import json
import os
import time
import urllib.parse
from pathlib import Path

import requests

API = "https://www.dolthub.com/api/v1alpha1"
DEFAULT_OWNER = "fartbagxp"
DEFAULT_DATABASE = "cdc-places"

# Stay clear of the documented 100MB ceiling; the header is repeated per chunk
# and multipart framing adds a little on top.
_MAX_UPLOAD_BYTES = 80 * 1024 * 1024
_TIMEOUT = (30, 600)
# DoltHub goes through spells of 5xx and write timeouts that last minutes, and
# a sync has already spent a long time downloading and transforming by the time
# it uploads, so the retry budget is deliberately patient.
_MAX_RETRIES = 5
_RETRY_BACKOFF = [10, 30, 60, 120]
_POLL_INTERVAL = 5
_BUSY_INTERVAL = 20  # DoltHub runs one import job per database at a time
_POLL_TIMEOUT = 3600
_SQL_ROW_LIMIT = 1000


class DoltError(RuntimeError):
    pass


class DoltHubClient:
    def __init__(
        self,
        owner: str = DEFAULT_OWNER,
        database: str = DEFAULT_DATABASE,
        token: str | None = None,
    ):
        self.owner = owner
        self.database = database
        self._token = token if token is not None else os.environ.get("DOLTHUB_TOKEN")
        self.session = requests.Session()

    @property
    def base(self) -> str:
        return f"{API}/{self.owner}/{self.database}"

    # ── transport ─────────────────────────────────────────────────────────────

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """One HTTP call, retried through transient network faults.

        A sync spends minutes downloading and transforming before it talks to
        DoltHub at all, so a single reset partway through should not throw that
        work away -- which is exactly what happened on the first ZCTA run:
        234MB downloaded, 1.17M rows transformed, then `Connection reset by
        peer` on the schema check.

        Retries connection-level failures and 5xx. Never retries a 4xx: those
        are the request's own fault and will fail identically.
        """
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            if attempt > 0:
                wait = _RETRY_BACKOFF[attempt - 1]
                print(f"(retry in {wait}s)", end=" ", flush=True)
                time.sleep(wait)
            try:
                resp = self.session.request(method, url, timeout=_TIMEOUT, **kwargs)
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_exc = exc
                continue
            if resp.status_code >= 500:
                last_exc = DoltError(f"{resp.status_code} from {url}")
                continue
            return resp
        raise DoltError(
            f"{method} {url} failed after {_MAX_RETRIES} attempts: {last_exc}"
        )

    # ── auth ──────────────────────────────────────────────────────────────────

    @property
    def token(self) -> str:
        if not self._token:
            raise DoltError(
                "DOLTHUB_TOKEN is not set. Create an API token at "
                "https://www.dolthub.com/settings/tokens, then put it in .env "
                "for local runs or in the repo's `prod` environment for CI."
            )
        return self._token

    def _auth_headers(self) -> dict[str, str]:
        # v1alpha1 uses the `token` scheme; `Bearer` is a v2 thing and fails here.
        return {"authorization": f"token {self.token}"}

    # ── checks ────────────────────────────────────────────────────────────────

    def check_database(self) -> dict:
        """Verify the database exists. Does not create it -- it is made by hand
        in the web UI so its visibility is confirmed by a human.

        A brand-new database has no commits and therefore no `main` branch, so
        "branch not found" means empty-but-present, not an error.
        """
        resp = self._request("GET", f"{self.base}/main", params={"q": "select 1"})
        resp.raise_for_status()
        body = resp.json()
        message = body.get("query_execution_message", "")
        if "no such repository" in message:
            raise DoltError(
                f"database {self.owner}/{self.database} not found. Create it at "
                "https://www.dolthub.com/repositories/new with visibility 'public'."
            )
        return {
            "owner": body.get("repository_owner", self.owner),
            "name": body.get("repository_name", self.database),
            "empty": "branch not found" in message,
        }

    def check_token(self) -> dict:
        """Verify DOLTHUB_TOKEN authenticates against the API used for writes."""
        resp = self._request(
            "GET", f"{self.base}/branches", headers=self._auth_headers()
        )
        if resp.status_code in (401, 403):
            raise DoltError(
                f"DOLTHUB_TOKEN was rejected ({resp.status_code}). Check the token "
                "is still listed at https://www.dolthub.com/settings/tokens and "
                "grants write access to "
                f"{self.owner}/{self.database}, then re-copy it."
            )
        resp.raise_for_status()
        branches = [b["branch_name"] for b in resp.json().get("branches", [])]
        return {"scope": f"{self.owner}/{self.database}", "branches": branches}

    # ── SQL read (unauthenticated) ────────────────────────────────────────────

    def sql(self, query: str, branch: str = "main") -> list[dict]:
        """Run a read-only query. Raises if the 1000-row cap truncated it."""
        resp = self._request("GET", f"{self.base}/{branch}", params={"q": query})
        resp.raise_for_status()
        body = resp.json()
        status = body.get("query_execution_status")
        if status == "RowLimit":
            raise DoltError(
                f"query hit DoltHub's {_SQL_ROW_LIMIT}-row API cap; add a LIMIT or "
                "aggregate server-side:\n  " + query
            )
        if status != "Success":
            raise DoltError(
                f"query failed ({status}): {body.get('query_execution_message')}"
            )
        return body.get("rows", [])

    def table_exists(self, table: str, branch: str = "main") -> bool:
        try:
            rows = self.sql(
                "select count(*) as n from information_schema.tables "
                f"where table_schema = database() and table_name = '{table}'",
                branch=branch,
            )
        except DoltError as exc:
            # An empty database has no branch yet, so nothing exists in it.
            if "branch not found" in str(exc):
                return False
            raise
        return bool(rows) and int(rows[0]["n"]) > 0

    # ── SQL write / DDL ───────────────────────────────────────────────────────

    def sql_write(self, query: str, branch: str = "main") -> str:
        """Run one write statement. Returns the operation name to poll."""
        resp = self._request(
            "POST",
            f"{self.base}/write/{branch}/{branch}",
            params={"q": query},
            headers=self._auth_headers(),
        )
        if resp.status_code >= 400:
            raise DoltError(f"{resp.status_code} from write: {resp.text[:400]}")
        body = resp.json()
        if body.get("query_execution_status") == "Error":
            raise DoltError(f"write rejected: {body.get('query_execution_message')}")
        return body["operation_name"]

    def apply_schema(self, ddl_path: Path, branch: str = "main") -> list[str]:
        """Apply each CREATE TABLE in `ddl_path`, skipping tables that exist."""
        applied = []
        for table, statement in _split_ddl(ddl_path.read_text()):
            if self.table_exists(table, branch):
                print(f"    {table}: exists")
                continue
            print(f"    {table}: creating ...", end=" ", flush=True)
            self.wait(self.sql_write(statement, branch))
            print("ok")
            applied.append(table)
        return applied

    # ── file import ───────────────────────────────────────────────────────────

    def import_csv(
        self,
        path: Path,
        table: str,
        primary_keys: list[str],
        branch: str = "main",
        operation: str = "Update",
    ) -> int:
        """Upload `path` into `table`, splitting past the 100MB API ceiling.

        Each upload runs as a server-side job that opens a pull request; the
        data only reaches `branch` once that PR is merged, so this does both.
        Returns the number of chunks uploaded.

        DoltHub runs one import job per database at a time, so chunks go up
        strictly in sequence -- and for the same reason two geographies must
        not sync against this database concurrently.
        """
        chunks = _split_csv(path, _MAX_UPLOAD_BYTES)
        try:
            for i, chunk in enumerate(chunks, start=1):
                if len(chunks) > 1:
                    print(
                        f"\n      chunk {i}/{len(chunks)} "
                        f"({chunk.stat().st_size / 1e6:.1f} MB) ...",
                        end=" ",
                        flush=True,
                    )
                self.wait(self._upload(chunk, table, primary_keys, branch, operation))
                self._merge_import_pull(table)
            return len(chunks)
        finally:
            for chunk in chunks:
                if chunk != path:
                    chunk.unlink(missing_ok=True)

    def _upload(
        self,
        path: Path,
        table: str,
        primary_keys: list[str],
        branch: str,
        operation: str,
    ) -> str:
        params = {
            "tableName": table,
            # Required. Omitting it fails with an opaque upstream 400.
            "fileName": path.name,
            "branchName": branch,
            "fileType": "Csv",
            "importOp": operation,
            "primaryKeys": primary_keys,
        }
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            if attempt > 0:
                time.sleep(_RETRY_BACKOFF[attempt - 1])
            try:
                with path.open("rb") as f:
                    resp = self.session.post(
                        f"{self.base}/upload",
                        headers=self._auth_headers(),
                        files={"file": (path.name, f, "application/octet-stream")},
                        data={"params": json.dumps(params)},
                        timeout=_TIMEOUT,
                    )
                if resp.status_code >= 400:
                    raise DoltError(f"{resp.status_code}: {resp.text[:300]}")
                body = resp.json()
                if body.get("status") != "Success":
                    raise DoltError(f"upload rejected: {body.get('message')}")
                return body["operation_name"]
            # Everything this block can legitimately fail with: the two
            # DoltErrors raised just above, a transport fault or non-JSON body
            # from requests, OSError from reopening the chunk, and KeyError if
            # a Success response somehow omits operation_name. Listed rather
            # than blanket-caught so a bug here is not retried three times and
            # then reported as an upload failure.
            except (DoltError, requests.RequestException, OSError, KeyError) as exc:
                last_exc = exc
        raise DoltError(f"upload of {path.name} failed: {last_exc}")

    def _merge_import_pull(self, table: str) -> None:
        """Merge the pull request the import job opened.

        An upload lands on a generated branch and opens a PR rather than
        writing to `main` directly, so without this the job reports success and
        the table stays empty. Only one import runs at a time, so the single
        open pull request is unambiguously ours.

        No open pull request is a legitimate outcome, not a failure: importing
        rows identical to what is already on the branch produces no diff, so
        DoltHub has nothing to open a PR for. That is exactly what a re-run
        with --force does, and it must stay a no-op rather than an error.
        """
        pulls = [p for p in self.list_pulls() if p.get("state") == "Open"]
        if not pulls:
            print("(no changes)", end=" ", flush=True)
            return
        pull_id = pulls[0]["pull_id"]
        resp = self._request(
            "POST",
            f"{self.base}/pulls/{pull_id}/merge",
            headers=self._auth_headers(),
        )
        if resp.status_code >= 400:
            raise DoltError(f"merging pull {pull_id}: {resp.text[:300]}")
        body = resp.json()
        if body.get("status") != "Success":
            raise DoltError(f"merging pull {pull_id}: {body.get('message')}")
        self.wait(body["operation_name"])

    # Note: the `{owner}/import-*` branches that merged imports leave behind
    # cannot be cleaned up through this API. v1alpha1 has no delete-branch
    # endpoint, and the write endpoint rejects the stored procedure with
    # "Unsupported SQL statement: CALL DOLT_BRANCH('-D', ...)". They are
    # cosmetic; delete them from the web UI if they become distracting.
    def list_branches(self) -> list[str]:
        resp = self._request(
            "GET", f"{self.base}/branches", headers=self._auth_headers()
        )
        resp.raise_for_status()
        return [b["branch_name"] for b in resp.json().get("branches", [])]

    def list_pulls(self) -> list[dict]:
        resp = self._request("GET", f"{self.base}/pulls", headers=self._auth_headers())
        resp.raise_for_status()
        return resp.json().get("pulls", [])

    # ── polling ───────────────────────────────────────────────────────────────

    def wait(self, operation_name: str, timeout: int = _POLL_TIMEOUT) -> dict:
        """Poll a job until it reaches a terminal state.

        The two kinds of operation are polled at different endpoints and answer
        in different shapes, and sending one to the other's endpoint fails
        validation, so the operation name picks the route:

          users/{u}/userOperations/{id}          SQL writes   -> /write, `done`
          repositoryOwners/{o}/repositories/...  imports and
                                                 merges       -> /upload, `job_status`
        """
        is_job = operation_name.startswith("repositoryOwners/")
        endpoint = f"{self.base}/upload" if is_job else f"{self.base}/write"
        params = {"operationName": operation_name}
        if is_job:
            params["branchName"] = "main"

        deadline = time.monotonic() + timeout
        while True:
            try:
                resp = self._request(
                    "GET", endpoint, params=params, headers=self._auth_headers()
                )
                resp.raise_for_status()
                body = resp.json()
            except (DoltError, requests.RequestException, ValueError) as exc:
                # A failed poll says nothing about the job, which keeps running
                # server-side regardless. Losing a status read is harmless, so
                # keep polling to the deadline instead of abandoning an import
                # that is very likely still succeeding.
                if time.monotonic() > deadline:
                    raise DoltError(
                        f"operation {operation_name}: polling kept failing ({exc})"
                    ) from exc
                print("(poll retry)", end=" ", flush=True)
                time.sleep(_BUSY_INTERVAL)
                continue

            if body.get("status") == "Error":
                message = body.get("message", "")
                # DoltHub serializes jobs per database and asks callers to back
                # off while the previous one is torn down.
                if "cleaning up existing job" in message:
                    if time.monotonic() > deadline:
                        raise DoltError(f"still waiting on a previous job: {message}")
                    time.sleep(_BUSY_INTERVAL)
                    continue
                raise DoltError(f"job failed: {message}")

            if body.get("done"):
                details = body.get("res_details") or {}
                status = details.get("query_execution_status")
                if status and status != "Success":
                    raise DoltError(
                        f"operation failed: {details.get('query_execution_message')}"
                    )
                return body

            job_status = str(body.get("job_status", ""))
            if job_status and not _job_running(job_status):
                if "fail" in job_status.lower() or "error" in job_status.lower():
                    raise DoltError(f"job failed: {job_status}")
                return body

            if time.monotonic() > deadline:
                raise DoltError(
                    f"operation {operation_name} unfinished after {timeout}s "
                    f"(last status {job_status or body.get('status')!r})"
                )
            time.sleep(_POLL_INTERVAL)


# ── helpers ───────────────────────────────────────────────────────────────────


def _job_running(job_status: str) -> bool:
    """True while a DoltHub job is still working."""
    return job_status.strip().lower() in {
        "in progress",
        "created",
        "pending",
        "queued",
        "running",
    }


def _split_csv(path: Path, max_bytes: int) -> list[Path]:
    """Split a CSV into pieces under `max_bytes`, repeating the header on each.

    Returns [path] unchanged when it already fits, so the common case does no
    copying at all.
    """
    if path.stat().st_size <= max_bytes:
        return [path]

    parts: list[Path] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        writer = None
        handle = None
        written = 0
        for row in reader:
            if writer is None or written >= max_bytes:
                if handle:
                    handle.close()
                part = path.with_name(f"{path.stem}.part{len(parts) + 1}{path.suffix}")
                parts.append(part)
                handle = part.open("w", newline="", encoding="utf-8")
                writer = csv.writer(handle, lineterminator="\n")
                writer.writerow(header)
                written = 0
            writer.writerow(row)
            # Cheap running estimate; exact size would mean flushing per row.
            written += sum(len(str(c)) for c in row) + len(row)
        if handle:
            handle.close()
    return parts


def _split_ddl(sql: str) -> list[tuple[str, str]]:
    """(table_name, statement) for each CREATE TABLE in a schema file.

    Comments are stripped BEFORE splitting on ";" -- a prose semicolon inside
    a `--` comment would otherwise cut a CREATE TABLE in half.
    """
    body = "\n".join(
        line
        for line in sql.splitlines()
        if line.strip() and not line.strip().startswith("--")
    )
    out = []
    for chunk in body.split(";"):
        statement = chunk.strip()
        if not statement.lower().startswith("create table"):
            continue
        after = statement[len("create table") :].strip()
        if after.lower().startswith("if not exists"):
            after = after[len("if not exists") :].strip()
        name = after.split("(", 1)[0].strip().strip("`")
        out.append((name, statement))
    return out


def sql_url(
    query: str,
    owner: str = DEFAULT_OWNER,
    database: str = DEFAULT_DATABASE,
    branch: str = "main",
) -> str:
    """The URL health-charts would fetch for `query` -- handy for docs."""
    return f"{API}/{owner}/{database}/{branch}?q={urllib.parse.quote(query)}"
