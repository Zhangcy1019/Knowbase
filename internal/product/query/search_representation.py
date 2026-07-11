"""Structured search representation builders for knowbase queries."""

from __future__ import annotations

from typing import Any

from internal.models.semantic_profile import DynamicSemanticProfile


def build_query_search_representation(
    *,
    text: str,
    partition_name: str,
    semantic_profile: DynamicSemanticProfile,
    hypothetical_answer: str,
    expanded_terms: list[str] | None = None,
) -> str:
    resolved_terms = expanded_terms or []
    profile_lines = _query_semantic_profile_lines(semantic_profile=semantic_profile, expanded_terms=resolved_terms)
    return _join_sections(
        [
            _line("title", text),
            _line("partition", partition_name),
            *profile_lines,
            _line("summary", hypothetical_answer),
        ]
    )
def _query_semantic_profile_lines(*, semantic_profile: DynamicSemanticProfile, expanded_terms: list[str]) -> list[str]:
    lines: list[str] = []
    saw_keywords = False
    for key, value in semantic_profile.ordered_items():
        if key == "keywords":
            saw_keywords = True
            merged = list(dict.fromkeys([*semantic_profile.get_list("keywords"), *expanded_terms]))
            lines.append(_line("keywords", merged))
            continue
        lines.append(_line(key, value))
    if expanded_terms and not saw_keywords:
        lines.append(_line("expanded_terms", expanded_terms))
    return lines


def _line(label: str, value: Any) -> str:
    formatted = _format_value(value)
    if not formatted:
        return ""
    return f"{label}: {formatted}"


def _format_value(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, DynamicSemanticProfile):
        parts: list[str] = []
        for _, item in value.ordered_items():
            if isinstance(item, list):
                parts.extend(_normalize_list(item))
                continue
            normalized = str(item).strip()
            if normalized:
                parts.append(normalized)
        return ", ".join(parts)
    if isinstance(value, list):
        cleaned = _normalize_list(value)
        return ", ".join(cleaned)
    if isinstance(value, dict):
        parts: list[str] = []
        for key, values in value.items():
            parts.extend(f"{key}:{item}" for item in _normalize_list(values))
        return ", ".join(parts)
    if value is None:
        return ""
    return str(value).strip()


def _normalize_list(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, list):
        return [str(item).strip() for item in values if str(item).strip()]
    normalized = str(values).strip()
    return [normalized] if normalized else []


def _join_sections(sections: list[str]) -> str:
    return "\n".join(section for section in sections if section.strip())
