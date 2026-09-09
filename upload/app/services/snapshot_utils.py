"""Pure helpers for calculation-history snapshot values."""
from __future__ import annotations


def snapshot_number(value):
    """Convert a snapshot numeric field without turning UNKNOWN/None into zero."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
