"""Small shared helpers."""

from __future__ import annotations

import re
from typing import Any


def to_number(value: Any) -> float | None:
    """Convert an API value to float, or None when it is not numeric."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_sns(text: str | None) -> list[str]:
    """Split a free-text list of serial numbers (commas, spaces, newlines)."""
    seen: dict[str, None] = {}
    for sn in re.split(r"[\s,;]+", text or ""):
        if sn:
            seen[sn] = None
    return list(seen)
