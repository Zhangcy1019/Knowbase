"""Execution runtime for registered knowbase tools."""

from __future__ import annotations

from datetime import datetime, timezone

from internal.models.tool import ToolCall, ToolResult
from internal.tools.registry import ToolRegistry


class ToolRuntime:
    """Resolve and run read-only tool calls."""

    def __init__(self, *, registry: ToolRegistry | None = None):
        self._registry = registry or ToolRegistry()

    @property
    def registry(self) -> ToolRegistry:
        return self._registry

    def execute(self, call: ToolCall) -> ToolResult:
        handler = self._registry.resolve(call.tool_id)
        if handler is None:
            return ToolResult(
                call_id=call.call_id,
                tool_id=call.tool_id,
                ok=False,
                error_message=f"unknown tool: {call.tool_id}",
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc),
            )
        return handler.execute(call)
