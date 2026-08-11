"""
NCHS DQS SDK — Socrata SODA access for the Health, United States datasets.

Every DQS dataset lives on data.cdc.gov and shares one tidy schema, so a single
generic query covers all of them. `trend()` is a convenience over that: the
all-persons ("Total") national series, oldest→newest.

Note: `group` is a SoQL reserved word and must be backtick-quoted in a $select —
this module quotes it for you in the default trend projection.
"""

from __future__ import annotations

import os
from typing import Any

import requests

BASE_URL = "https://data.cdc.gov/resource"
_TIMEOUT = 60

# Shared DQS columns; `group` is backtick-quoted because it is a SoQL keyword.
CORE_COLUMNS = [
    "topic", "subtopic", "classification", "`group`", "subgroup",
    "estimate_type", "time_period", "estimate", "standard_error",
    "estimate_lci", "estimate_uci",
]


def query_dataset(
    dataset_id: str,
    where: str | None = None,
    select: str | None = None,
    group: str | None = None,
    order: str | None = None,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    """Generic SODA query against any DQS dataset by its Socrata ID."""
    headers = {"Accept": "application/json"}
    token = os.environ.get("CDC_DATA_APP_TOKEN")
    if token:
        headers["X-App-Token"] = token

    params: dict[str, str | int] = {"$limit": limit}
    if where:
        params["$where"] = where
    if select:
        params["$select"] = select
    if group:
        params["$group"] = group
    if order:
        params["$order"] = order

    resp = requests.get(f"{BASE_URL}/{dataset_id}.json", params=params, headers=headers, timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def trend(dataset_id: str, estimate_type: str | None = None, limit: int = 1000) -> list[dict[str, Any]]:
    """All-persons ('Total' classification) national series for a dataset, oldest→newest."""
    where = "classification = 'Total'"
    if estimate_type:
        where += f" AND estimate_type = '{estimate_type.replace(chr(39), chr(39) * 2)}'"
    return query_dataset(
        dataset_id,
        where=where,
        select=", ".join(CORE_COLUMNS),
        order="time_period ASC",
        limit=limit,
    )
