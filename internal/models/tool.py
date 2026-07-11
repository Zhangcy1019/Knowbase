"""Tool-facing runtime models for knowbase agents."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ToolSideEffectScope = Literal["read_only"]


class ToolSpec(BaseModel):
    """Describe one read-only tool exposed to agents."""

    tool_id: str
    title: str = ""
    description: str = ""
    side_effect_scope: ToolSideEffectScope = "read_only"
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    """One read-only tool call made during one run."""

    call_id: str = ""
    run_id: str = ""
    tool_id: str
    partition: str = ""
    inputs: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Structured result of one tool call."""

    call_id: str = ""
    tool_id: str
    ok: bool = True
    output: dict[str, Any] = Field(default_factory=dict)
    error_message: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None
