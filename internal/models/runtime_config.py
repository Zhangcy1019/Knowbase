"""Runtime configuration models for knowbase runs."""

from __future__ import annotations

from pydantic import BaseModel, Field

from internal.models.types import RuntimeRunMode


class RuntimeRunConfig(BaseModel):
    """Execution limits and allowlists attached to one runtime run."""

    run_mode: RuntimeRunMode = "agent"
    max_steps: int = 12
    max_tool_calls: int = 20
    max_skill_calls: int = 6
    tool_whitelist: list[str] = Field(default_factory=list)
    skill_whitelist: list[str] = Field(default_factory=list)
