"""Policy checks for runtime actions, tools, and skills."""

from __future__ import annotations

from typing import TYPE_CHECKING

from internal.runtime.contracts import RuntimeAction, RuntimeRunRequest

if TYPE_CHECKING:
    from internal.runtime.actions.capability_executor import RuntimeCapabilityExecutor


class RuntimePolicy:
    """Apply allowlists and existence checks before execution."""

    def __init__(self, *, capability_executor: RuntimeCapabilityExecutor):
        self._capability_executor = capability_executor

    def validate_action(self, *, request: RuntimeRunRequest, action: RuntimeAction) -> None:
        if action.kind == "tool_call":
            self._validate_tool_action(request=request, action=action)
            return
        if action.kind == "skill_call":
            self._validate_skill_action(request=request, action=action)

    def _validate_tool_action(self, *, request: RuntimeRunRequest, action: RuntimeAction) -> None:
        if not action.tool_id.strip():
            raise ValueError(f"runtime tool action missing tool_id: {action.action_id}")
        if request.allowed_tools and action.tool_id not in request.allowed_tools:
            raise ValueError(f"runtime tool not allowed: {action.tool_id}")
        if not self._capability_executor.tool_exists(action.tool_id):
            raise ValueError(f"runtime tool not found: {action.tool_id}")

    def _validate_skill_action(self, *, request: RuntimeRunRequest, action: RuntimeAction) -> None:
        if not action.skill_id.strip():
            raise ValueError(f"runtime skill action missing skill_id: {action.action_id}")
        if request.allowed_skills and action.skill_id not in request.allowed_skills:
            raise ValueError(f"runtime skill not allowed: {action.skill_id}")
        if self._capability_executor.resolve_skill_spec(action.skill_id) is None:
            raise ValueError(f"runtime skill not found: {action.skill_id}")
