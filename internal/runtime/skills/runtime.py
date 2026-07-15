"""Execution runtime for registered knowbase skills."""

from __future__ import annotations

from datetime import datetime, timezone

from internal.models.skill_context import SkillExecutionContext
from internal.models.skill import SkillInvocation, SkillResult, SkillSpec
from internal.runtime.skills.registry import SkillRegistry
from internal.utils.logger import get_logger


logger = get_logger("knowbase.skills.runtime")


class SkillRuntime:
    """Resolve and run skill invocations."""

    def __init__(self, *, registry: SkillRegistry | None = None):
        self._registry = registry or SkillRegistry()

    @property
    def registry(self) -> SkillRegistry:
        return self._registry

    def resolve_spec(self, skill_id: str) -> SkillSpec | None:
        return self._registry.resolve_spec(skill_id)

    def execute(self, invocation: SkillInvocation, *, context: SkillExecutionContext | None = None) -> SkillResult:
        handler = self._registry.resolve(invocation.skill_id)
        if handler is None:
            return SkillResult(
                invocation_id=invocation.invocation_id,
                skill_id=invocation.skill_id,
                ok=False,
                error_message=f"unknown skill: {invocation.skill_id}",
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc),
            )
        started_at = datetime.now(timezone.utc)
        try:
            return handler.execute(invocation, context=context)
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "Skill execution raised an exception.",
                extra={
                    "skill_id": invocation.skill_id,
                    "invocation_id": invocation.invocation_id,
                    "partition": invocation.partition,
                    "error": str(exc),
                },
            )
            return SkillResult(
                invocation_id=invocation.invocation_id,
                skill_id=invocation.skill_id,
                ok=False,
                error_message=str(exc),
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
            )
