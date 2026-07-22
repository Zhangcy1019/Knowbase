"""Restricted child-run contracts shared by subrun infrastructure."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

from pydantic import BaseModel, Field

from internal.models import AgentRun
from internal.runtime.contracts import RuntimeRunRequest, RuntimeWorkProfile


class RuntimeSubRunRequest(BaseModel):
    """Describe a bounded child run derived from a parent runtime run."""

    purpose: str = ""
    partition: str = ""
    objective: str = ""
    instructions: list[str] = Field(default_factory=list)
    input_context: dict[str, Any] = Field(default_factory=dict)
    allowed_tools: list[str] = Field(default_factory=list)
    allowed_skills: list[str] = Field(default_factory=list)
    max_steps: int = 6
    max_tool_calls: int = 4
    max_skill_calls: int = 4
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeSubRunResult(BaseModel):
    """Minimal structured result returned by a child run."""

    status: str = "completed"
    summary: str = ""
    output: dict[str, Any] = Field(default_factory=dict)
    retryable: bool = False
    repair_prompt: str = ""
    issues: list[str] = Field(default_factory=list)


class RuntimeSubRunExecutorPort(Protocol):
    """Execute a prepared constrained child request."""

    def execute(
        self,
        *,
        parent_run,
        child_run: AgentRun,
        child_request: RuntimeRunRequest,
        subrun_request: RuntimeSubRunRequest,
    ) -> RuntimeSubRunResult: ...


class StubRuntimeSubRunExecutor:
    """Default executor that only materializes child run context."""

    def execute(
        self,
        *,
        parent_run,
        child_run: AgentRun,
        child_request: RuntimeRunRequest,
        subrun_request: RuntimeSubRunRequest,
    ) -> RuntimeSubRunResult:
        return RuntimeSubRunResult(
            status="requires_review",
            summary="Sub-run request prepared but no child runtime executor is configured yet.",
            issues=["child runtime execution backend is not configured"],
            output={
                "purpose": subrun_request.purpose,
                "parent_run_id": getattr(parent_run, "run_id", ""),
                "child_request": child_request.model_dump(mode="json"),
                "child_run": child_run.model_dump(mode="json"),
            },
        )


class RuntimeSubRunLauncher:
    """Materialize and dispatch a constrained child request."""

    def __init__(self, *, executor: RuntimeSubRunExecutorPort | None = None):
        self._executor = executor or StubRuntimeSubRunExecutor()

    def launch(self, *, parent_run, request: RuntimeSubRunRequest) -> RuntimeSubRunResult:
        child_request = self.build_child_request(parent_run=parent_run, request=request)
        child_run = self.build_child_run_stub(parent_run=parent_run, child_request=child_request, request=request)
        return self._executor.execute(
            parent_run=parent_run,
            child_run=child_run,
            child_request=child_request,
            subrun_request=request,
        )

    def build_child_request(self, *, parent_run, request: RuntimeSubRunRequest) -> RuntimeRunRequest:
        child_request_id = self._build_child_request_id(parent_run=parent_run, request=request)
        partition = request.partition.strip() or getattr(parent_run, "partition", "")
        parent_metadata = dict(getattr(parent_run, "planning_context", {}).get("request", {}).get("metadata", {}))
        parent_subrun_depth = int(parent_metadata.get("subrun_depth", 0) or 0)
        parent_verification_subrun_count = int(parent_metadata.get("verification_subrun_count", 0) or 0)
        metadata = {
            **dict(request.metadata),
            "parent_run_id": getattr(parent_run, "run_id", ""),
            "subrun_purpose": request.purpose,
            "subrun_mode": "restricted",
            "subrun_depth": parent_subrun_depth + 1,
            "verification_subrun_count": parent_verification_subrun_count + 1,
            "allow_subrun": False,
        }
        return RuntimeRunRequest(
            request_id=child_request_id,
            source_type="system",
            source_ref=getattr(parent_run, "run_id", ""),
            partition=partition,
            work=RuntimeWorkProfile(
                objective=request.objective,
                mission_summary=f"Restricted sub-run for {request.purpose or 'follow-up'}.",
                instructions=list(request.instructions),
                input_context=dict(request.input_context),
                allowed_tools=list(request.allowed_tools),
                allowed_skills=list(request.allowed_skills),
                max_steps=max(1, int(request.max_steps)),
                max_tool_calls=max(0, int(request.max_tool_calls)),
                max_skill_calls=max(0, int(request.max_skill_calls)),
            ),
            risk_level="medium",
            requires_review=False,
            metadata=metadata,
        )

    def build_child_run_stub(self, *, parent_run, child_request: RuntimeRunRequest, request: RuntimeSubRunRequest) -> AgentRun:
        now = datetime.now(timezone.utc)
        child_run_id = self._build_child_run_id(parent_run=parent_run, request=request)
        return AgentRun(
            run_id=child_run_id,
            partition=child_request.partition,
            agent_id=f"{getattr(parent_run, 'agent_id', 'runtime')}.subrun",
            mode="agent",
            status="pending",
            source_type=child_request.source_type,
            source_event_type="runtime.subrun",
            source_event_id=child_request.request_id,
            source_ref=child_request.source_ref,
            objective=child_request.work.objective,
            planning_context={
                "parent_run_id": getattr(parent_run, "run_id", ""),
                "subrun_purpose": request.purpose,
                "allowed_tools": list(child_request.work.allowed_tools),
                "allowed_skills": list(child_request.work.allowed_skills),
            },
            tool_whitelist=list(child_request.work.allowed_tools),
            skill_whitelist=list(child_request.work.allowed_skills),
            max_steps=child_request.work.max_steps,
            max_tool_calls=child_request.work.max_tool_calls,
            max_skill_calls=child_request.work.max_skill_calls,
            risk_level="medium",
            requires_review=False,
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def _build_child_request_id(*, parent_run, request: RuntimeSubRunRequest) -> str:
        purpose = request.purpose.strip().replace(" ", "_") or "subrun"
        return f"{getattr(parent_run, 'run_id', 'run')}:subreq:{purpose}"

    @staticmethod
    def _build_child_run_id(*, parent_run, request: RuntimeSubRunRequest) -> str:
        purpose = request.purpose.strip().replace(" ", "_") or "subrun"
        return f"{getattr(parent_run, 'run_id', 'run')}:subrun:{purpose}"
