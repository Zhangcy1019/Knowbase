"""Knowledge skill action models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from internal.models.types import ChangeActionType, ChangeTargetType


class SkillAction(BaseModel):
    """One atomic skill-oriented action derived from runtime inputs."""

    action_type: ChangeActionType
    target_type: ChangeTargetType
    target_id: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)


__all__ = ["SkillAction"]
