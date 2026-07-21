"""Execution-time policy checks for runtime actions."""

from __future__ import annotations

from internal.runtime.contracts import RuntimeAction, RuntimeRunRequest


class RuntimePolicy:
    """Validate that proposed actions stay within the request's execution bounds."""

    def __init__(self, *, capability_executor=None):
        self._capability_executor = capability_executor

    def validate_action(self, *, request: RuntimeRunRequest, action: RuntimeAction) -> None:
        capability_id = action.capability_id.strip()
        if not capability_id:
            raise ValueError("runtime action missing capability_id")
        if capability_id in request.work.allowed_tools:
            return
        if capability_id in request.work.allowed_skills:
            return
        raise ValueError(f"runtime capability not allowed: {capability_id}")
