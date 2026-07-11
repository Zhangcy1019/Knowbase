"""Shared helpers for knowbase models."""

from __future__ import annotations

from typing import Any


def normalize_text(value: Any) -> str:
    """Normalize a free-form field to a stripped string."""
    if value is None:
        return ""
    return str(value).strip()


def normalize_string_list(value: Any) -> list[str]:
    """Normalize a field into a deduplicated list of strings."""
    if value in (None, ""):
        return []
    raw_items = value if isinstance(value, list) else [value]
    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        text = normalize_text(item)
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized
