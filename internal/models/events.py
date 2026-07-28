"""Knowbase domain event schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from internal.models.types import KnowbaseEventType


class TextFieldChange(BaseModel):
    """Lightweight deterministic diff metadata for long text fields."""

    change_type: Literal["text_created", "text_updated", "text_deleted"] = "text_updated"
    before_length: int = 0
    after_length: int = 0


class CaseEventSnapshot(BaseModel):
    """Compact event snapshot for one case."""

    title: str = ""
    facet_count: int = 0
    facets: dict[str, list[str]] = Field(default_factory=dict)


class BaseResourceEventPayload(BaseModel):
    """Common event payload structure for resource lifecycle events."""

    change_kind: Literal["create", "update", "delete"]
    changed_fields: list[str] = Field(default_factory=list)
    related_targets: list[str] = Field(default_factory=list)


class CaseEventPayload(BaseResourceEventPayload):
    """Lifecycle payload for case events."""

    before: CaseEventSnapshot = Field(default_factory=CaseEventSnapshot)
    after: CaseEventSnapshot = Field(default_factory=CaseEventSnapshot)
    field_changes: dict[str, TextFieldChange] = Field(default_factory=dict)
    observed_facets: dict[str, list[str]] = Field(default_factory=dict)


class KnowbaseEvent(BaseModel):
    """One case lifecycle domain event emitted by knowbase workflows."""

    event_type: KnowbaseEventType
    partition: str = ""
    resource_type: str = ""
    resource_id: str = ""
    occurred_at: datetime | None = None
    payload: CaseEventPayload

    @classmethod
    def for_case(
        cls,
        *,
        event_type: KnowbaseEventType,
        change_kind: Literal["create", "update", "delete"],
        partition: str,
        case_id: str,
        occurred_at: datetime | None,
        before: CaseEventSnapshot | None = None,
        after: CaseEventSnapshot | None = None,
        changed_fields: list[str] | None = None,
        field_changes: dict[str, TextFieldChange] | None = None,
        observed_facets: dict[str, list[str]] | None = None,
    ) -> "KnowbaseEvent":
        """Build a case lifecycle event with a consistent resource envelope."""
        return cls(
            event_type=event_type,
            partition=partition,
            resource_type="case",
            resource_id=case_id,
            occurred_at=occurred_at,
            payload=CaseEventPayload(
                change_kind=change_kind,
                before=before or CaseEventSnapshot(),
                after=after or CaseEventSnapshot(),
                changed_fields=changed_fields or [],
                field_changes=field_changes or {},
                observed_facets=observed_facets or {},
            ),
        )
