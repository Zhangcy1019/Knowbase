"""Structured search representation builders for knowbase cases."""

from __future__ import annotations

from typing import Any

from internal.models.case import KnowbaseCaseDraft, KnowbaseCaseMetadata
from internal.models.semantic_profile import DynamicSemanticProfile


def build_case_search_representation(*, draft: KnowbaseCaseDraft) -> str:
    return _join_sections(
        [
            _line("title", draft.title),
            _line("partition", draft.partition),
            _line("facets", _render_facets(draft.facets)),
            *_semantic_profile_lines(draft.semantic_profile),
            _line("summary", draft.summary_text),
        ]
    )


def build_case_content_representation(*, draft: KnowbaseCaseDraft) -> str:
    return _join_sections(
        [
            _line("title", draft.title),
            _line("summary", draft.summary_text),
            _line("content", draft.source_content),
        ]
    )


def _semantic_profile_lines(profile: DynamicSemanticProfile) -> list[str]:
    return [_line(key, value) for key, value in profile.ordered_items()]


def _line(label: str, value: Any) -> str:
    formatted = _format_value(value)
    if not formatted:
        return ""
    return f"{label}: {formatted}"


def _format_value(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, KnowbaseCaseMetadata):
        return ", ".join(part for part in [value.author, value.source, value.status] if part)
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


def _render_facets(facets: dict[str, list[str]]) -> list[str]:
    rendered: list[str] = []
    for key, values in facets.items():
        rendered.extend(f"{key}:{item}" for item in _normalize_list(values))
    return rendered
