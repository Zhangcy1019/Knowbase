"""Registry for knowbase tools."""

from __future__ import annotations

from collections.abc import Mapping

from internal.runtime.tools.types import ToolHandler


class ToolRegistry:
    """Hold the installed read-only tools for one runtime."""

    def __init__(self, *, handlers: Mapping[str, ToolHandler] | None = None):
        self._handlers: dict[str, ToolHandler] = dict(handlers or {})

    def register(self, handler: ToolHandler) -> None:
        self._handlers[handler.spec.tool_id] = handler

    def resolve(self, tool_id: str) -> ToolHandler | None:
        return self._handlers.get(tool_id)

    def resolve_spec(self, tool_id: str):
        handler = self.resolve(tool_id)
        if handler is None:
            return None
        return handler.spec

    def snapshot(self) -> dict[str, ToolHandler]:
        return dict(self._handlers)
