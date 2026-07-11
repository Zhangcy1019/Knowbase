"""Cross-module ports for runtime-facing capabilities."""

from __future__ import annotations

from typing import Protocol

from internal.models import AgentRun, RunArtifact, RunStep
from internal.models.skill import SkillInvocation, SkillResult
from internal.models.skill_context import SkillExecutionContext
from internal.runtime.contracts import RuntimeRunRequest, RuntimeRunResult


class RuntimeHarnessPort(Protocol):
    """Primary runtime harness interface for the agent-first direction."""

    async def run_request(self, *, request: RuntimeRunRequest) -> RuntimeRunResult:
        ...


class RuntimeRunPort(RuntimeHarnessPort, Protocol):
    """Stable runtime inspection and admin surface used by API routes."""

    def list_runs(self, *, partition: str = "", status: str = "") -> list[AgentRun]:
        ...

    def get_run(self, run_id: str) -> AgentRun | None:
        ...

    def delete_run(self, run_id: str) -> None:
        ...

    def list_steps(self, run_id: str) -> list[RunStep]:
        ...

    def list_artifacts(self, run_id: str) -> list[RunArtifact]:
        ...


class SkillExecutionPort(Protocol):
    """Stable skill execution surface used by maintenance routes and runtime."""

    def execute(self, invocation: SkillInvocation, *, context: SkillExecutionContext | None = None) -> SkillResult:
        ...


__all__ = [
    "RuntimeHarnessPort",
    "RuntimeRunPort",
    "SkillExecutionPort",
]
