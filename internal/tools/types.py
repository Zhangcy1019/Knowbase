"""Types for knowbase tool registration and execution."""

from __future__ import annotations

from typing import Protocol

from internal.models.tool import ToolCall, ToolResult, ToolSpec


class ToolHandler(Protocol):
    """Protocol implemented by concrete read-only tools."""

    @property
    def spec(self) -> ToolSpec:
        """Static tool metadata."""

    def execute(self, call: ToolCall) -> ToolResult:
        """Run one read-only tool call."""
