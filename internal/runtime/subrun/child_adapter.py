"""Adapters for executing prepared child runtime runs."""

from __future__ import annotations

from typing import Protocol

from internal.runtime.contracts import RuntimeRunResult
from internal.runtime.subrun.contracts import RuntimeSubRunResult


class RuntimeChildRunExecutorPort(Protocol):
    """Execute a prepared child runtime request through the unified runtime substrate."""

    def execute_child_request(self, *, child_run, child_request) -> RuntimeRunResult: ...


class StubRuntimeChildRunExecutor:
    """Default child-run executor used until a real nested runtime runner is wired in."""

    def execute_child_request(self, *, child_run, child_request) -> RuntimeRunResult:
        raise RuntimeError(
            f"child runtime executor is not configured for request {child_request.request_id or '<unknown>'}"
        )


class RuntimeChildRunAdapter:
    """Bridge child runtime execution results into subrun-friendly results."""

    def __init__(self, *, executor: RuntimeChildRunExecutorPort | None = None):
        self._executor = executor or StubRuntimeChildRunExecutor()

    def set_executor(self, *, executor: RuntimeChildRunExecutorPort) -> None:
        self._executor = executor

    def execute(self, *, parent_run, child_run, child_request, subrun_request) -> RuntimeSubRunResult:
        try:
            result = self._executor.execute_child_request(
                child_run=child_run,
                child_request=child_request,
            )
        except Exception as exc:  # noqa: BLE001
            return RuntimeSubRunResult(
                status="requires_review",
                summary=f"Child runtime execution is not available: {exc}",
                issues=["child runtime executor is not configured"],
                output={
                    "purpose": subrun_request.purpose,
                    "parent_run_id": getattr(parent_run, "run_id", ""),
                    "child_request": child_request.model_dump(mode="json"),
                    "child_run": child_run.model_dump(mode="json"),
                },
            )
        return RuntimeSubRunResult(
            status=result.status,
            summary=result.final_summary or result.reasoning_summary or "",
            retryable=False,
            repair_prompt="",
            issues=[],
            output={
                "purpose": subrun_request.purpose,
                "parent_run_id": getattr(parent_run, "run_id", ""),
                "child_request": child_request.model_dump(mode="json"),
                "child_run": child_run.model_dump(mode="json"),
                "child_result": result.model_dump(mode="json"),
            },
        )
