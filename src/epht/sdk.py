"""
High-level helpers over the EPHT client: resolve a measure to its state-level
series and return tidy records.
"""

from __future__ import annotations

from epht import client


def _find_state_geo_type(measure_id: int) -> dict | None:
    for gt in client.geographic_types(measure_id):
        if (gt.get("geographicType") or "").lower() == "state":
            return gt
    return None


def _find_base_state_level(measure_id: int, geo_type_id: int) -> dict | None:
    """The plain 'State' stratification level -- one row per state per year with
    no demographic split (empty stratificationType)."""
    levels = client.stratification_levels(measure_id, geo_type_id)
    for lvl in levels:
        if (lvl.get("name") or "").lower() == "state" and not lvl.get("stratificationType"):
            return lvl
    return levels[0] if levels else None


def get_state_series(measure_id: int) -> list[dict]:
    """All state x year records for a measure at the plain State level.

    Returns the raw ``tableResult`` rows (field names vary by content area, but
    always include a geography, a time period, and a value)."""
    geo = _find_state_geo_type(measure_id)
    if not geo:
        raise ValueError(f"measure {measure_id} has no State geographic type")
    geo_type_id = geo.get("geographicTypeId")
    level = _find_base_state_level(measure_id, geo_type_id)
    if not level:
        raise ValueError(f"measure {measure_id} has no stratification level")
    return client.core_holder(measure_id, level.get("id"), geo_type_id)


def search_measures(term: str) -> list[dict]:
    term = term.lower()
    return [
        m
        for m in client.measures()
        if term in (m.get("measureName") or "").lower()
        or term in (m.get("contentAreaName") or "").lower()
        or term in (m.get("indicatorName") or "").lower()
    ]
