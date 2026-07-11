"""Execution context passed to skills inside knowbase runtime."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SkillExecutionContext(BaseModel):
    """Minimal runtime context for one skill invocation."""

    run_id: str = ""
    partition: str = ""
    agent_id: str = ""
    source_event_type: str = ""
    source_event_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime | None = None
