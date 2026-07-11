"""Types for knowbase skill registration and execution."""

from __future__ import annotations

from typing import Protocol

from internal.models.skill_context import SkillExecutionContext
from internal.models.skill import SkillInvocation, SkillResult, SkillSpec


class SkillHandler(Protocol):
    """Protocol implemented by concrete skills."""

    @property
    def spec(self) -> SkillSpec:
        """Static skill metadata."""

    def execute(self, invocation: SkillInvocation, *, context: SkillExecutionContext | None = None) -> SkillResult:
        """Run one skill invocation."""
