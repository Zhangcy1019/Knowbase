"""Registry for knowbase skills."""

from __future__ import annotations

from collections.abc import Mapping

from internal.runtime.skills.types import SkillHandler


class SkillRegistry:
    """Hold the installed skills for one runtime."""

    def __init__(self, *, handlers: Mapping[str, SkillHandler] | None = None):
        self._handlers: dict[str, SkillHandler] = dict(handlers or {})

    def register(self, handler: SkillHandler) -> None:
        self._handlers[handler.spec.skill_id] = handler

    def resolve(self, skill_id: str) -> SkillHandler | None:
        return self._handlers.get(skill_id)

    def resolve_spec(self, skill_id: str):
        handler = self.resolve(skill_id)
        if handler is None:
            return None
        return handler.spec

    def snapshot(self) -> dict[str, SkillHandler]:
        return dict(self._handlers)
