"""Verification profile contracts for runtime requests."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RuntimeVerificationProfile(BaseModel):
    """Bounded verification settings attached to one runtime request."""

    enabled: bool = False
    mode: Literal["deterministic", "subrun"] = "deterministic"
    objective: str = ""
    instructions: list[str] = Field(default_factory=list)
    allowed_skills: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    prompt: str = ""
    max_steps: int = 6
    max_tool_calls: int = 4
    max_skill_calls: int = 4
    max_retries: int = 0
    max_subruns: int = 3
    require_acceptance: bool = False
