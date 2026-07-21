"""Verification contracts for runtime candidate review."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


VerificationStatus = Literal["completed", "retry", "run_subrun", "requires_review", "failed"]


class VerificationReviewResult(BaseModel):
    """Structured review result produced by a verification reviewer."""

    passed: bool = False
    retryable: bool = False
    score: int = 0
    summary: str = ""
    repair_prompt: str = ""
    issues: list[str] = Field(default_factory=list)


class VerificationResult(BaseModel):
    """Normalized verification outcome returned to the runtime orchestrator."""

    passed: bool = False
    retryable: bool = False
    status: VerificationStatus = "completed"
    summary: str = ""
    repair_prompt: str = ""
    hard_failures: list[str] = Field(default_factory=list)
    review_notes: list[str] = Field(default_factory=list)
    score: int | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
