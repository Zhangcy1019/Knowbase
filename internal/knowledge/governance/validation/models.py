"""Models produced by governance validation policies."""

from typing import Any
from pydantic import BaseModel, Field


class GovernancePolicyEvaluation(BaseModel):
    policy: str = ""
    allowed: bool = True
    requires_review: bool = False
    reasons: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
