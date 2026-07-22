"""Completion-stage decisions produced after the main work loop finishes."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


CompletionStatus = Literal["pass", "retry_main", "run_subrun", "requires_review", "fail"]


class CompletionDecision(BaseModel):
    """Normalized completion decision returned by the completion gate."""

    status: CompletionStatus = "pass"
    summary: str = ""
    repair_prompt: str = ""
    issues: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)
