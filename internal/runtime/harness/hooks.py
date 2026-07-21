"""Hook protocols and shared hook results for the runtime harness."""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, Field

from internal.runtime.harness.context import RuntimeHarnessContext


class RuntimeHookResult(BaseModel):
    """Normalized result returned by harness hooks."""

    status: Literal["pass", "retry_main", "run_subrun", "requires_review", "fail"] = "pass"
    summary: str = ""
    repair_prompt: str = ""
    issues: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class RuntimeBeforeCompleteHook(Protocol):
    """Called when the main loop is about to finish successfully."""

    def before_complete(self, *, context: RuntimeHarnessContext) -> RuntimeHookResult: ...
