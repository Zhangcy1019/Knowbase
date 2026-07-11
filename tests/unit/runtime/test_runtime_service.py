from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from internal.models import AgentRun, RunArtifact, RunStep, SkillResult, ToolResult
from internal.models.skill import SkillInvocation, SkillSpec
from internal.models.skill_context import SkillExecutionContext
from internal.models.tool import ToolCall
from internal.runtime.contracts import RuntimeRunRequest
from internal.runtime.service import KnowbaseRuntimeService


class InMemoryRunRepository:
    def __init__(self) -> None:
        self._items: dict[str, AgentRun] = {}
        self._counter = 0

    def save(self, run: AgentRun) -> AgentRun:
        if not run.run_id:
            self._counter += 1
            run = run.model_copy(update={"run_id": f"run-{self._counter}"})
        now = datetime.now(timezone.utc)
        persisted = run.model_copy(
            update={
                "created_at": run.created_at or now,
                "updated_at": now,
                "finished_at": now if run.status in {"completed", "failed", "cancelled"} else run.finished_at,
            }
        )
        self._items[persisted.run_id] = persisted
        return persisted

    def get(self, run_id: str) -> AgentRun | None:
        return self._items.get(run_id)

    def list(self, *, partition: str = "", status: str = "") -> list[AgentRun]:
        return [
            item
            for item in self._items.values()
            if (not partition or item.partition == partition) and (not status or item.status == status)
        ]

    def delete(self, run_id: str) -> None:
        self._items.pop(run_id, None)


class InMemoryStepRepository:
    def __init__(self) -> None:
        self._items: dict[str, list[RunStep]] = {}

    def save(self, step: RunStep) -> RunStep:
        bucket = self._items.setdefault(step.run_id, [])
        persisted = step.model_copy(update={"step_id": step.step_id or f"{step.run_id}:step:{len(bucket)}"})
        bucket.append(persisted)
        return persisted

    def list_for_run(self, run_id: str) -> list[RunStep]:
        return list(self._items.get(run_id, []))

    def delete_for_run(self, run_id: str) -> None:
        self._items.pop(run_id, None)


class InMemoryArtifactRepository:
    def __init__(self) -> None:
        self._items: dict[str, list[RunArtifact]] = {}

    def save(self, artifact: RunArtifact) -> RunArtifact:
        bucket = self._items.setdefault(artifact.run_id, [])
        persisted = artifact.model_copy(update={"artifact_id": artifact.artifact_id or f"{artifact.run_id}:artifact:{len(bucket)}"})
        bucket.append(persisted)
        return persisted

    def list_for_run(self, run_id: str) -> list[RunArtifact]:
        return list(self._items.get(run_id, []))

    def delete_for_run(self, run_id: str) -> None:
        self._items.pop(run_id, None)


class StubPartitionService:
    def get_partition(self, partition: str):
        return object() if partition == "CI" else None


class StubToolRegistry:
    def __init__(self, existing: set[str]) -> None:
        self._existing = existing

    def resolve(self, tool_id: str):
        return object() if tool_id in self._existing else None


class StubToolRuntime:
    def __init__(self, *, existing: set[str] | None = None) -> None:
        self.registry = StubToolRegistry(existing or set())

    def execute(self, call: ToolCall) -> ToolResult:
        return ToolResult(
            call_id=call.call_id,
            tool_id=call.tool_id,
            ok=True,
            output={"echo": call.inputs},
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
        )


class StubSkillRuntime:
    def __init__(self, *, existing: set[str] | None = None, failing: set[str] | None = None) -> None:
        self._existing = existing or set()
        self._failing = failing or set()

    def resolve_spec(self, skill_id: str) -> SkillSpec | None:
        if skill_id not in self._existing:
            return None
        return SkillSpec(skill_id=skill_id, title=skill_id)

    def execute(self, invocation: SkillInvocation, *, context: SkillExecutionContext | None = None) -> SkillResult:
        ok = invocation.skill_id not in self._failing
        return SkillResult(
            invocation_id=invocation.invocation_id,
            skill_id=invocation.skill_id,
            ok=ok,
            updated_objects=["case:1"] if ok else [],
            output={"context_partition": context.partition if context else ""},
            error_message="" if ok else f"skill failed: {invocation.skill_id}",
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
        )


def build_service(*, tool_ids: set[str] | None = None, skill_ids: set[str] | None = None, failing_skills: set[str] | None = None):
    return KnowbaseRuntimeService(
        partition_service=StubPartitionService(),
        case_repository=None,
        run_repository=InMemoryRunRepository(),
        step_repository=InMemoryStepRepository(),
        artifact_repository=InMemoryArtifactRepository(),
        tool_runtime=StubToolRuntime(existing=tool_ids),
        skill_runtime=StubSkillRuntime(existing=skill_ids, failing=failing_skills),
    )


def test_run_request_executes_explicit_skill_action() -> None:
    service = build_service(skill_ids={"case.rebuild_case"})
    request = RuntimeRunRequest(
        request_id="req-1",
        source_type="manual",
        partition="CI",
        objective="refresh one case",
        allowed_skills=["case.rebuild_case"],
        metadata={
            "actions": [
                {
                    "action_id": "action-1",
                    "kind": "skill_call",
                    "skill_id": "case.rebuild_case",
                    "title": "case.rebuild_case",
                    "summary": "refresh one case",
                    "inputs": {"case_id": "case-1"},
                }
            ]
        },
    )

    result = asyncio.run(service.run_request(request=request))

    assert result.status == "completed"
    assert len(result.skill_results) == 1
    assert result.skill_results[0].ok is True
    assert any(step.step_type == "skill_result" for step in result.steps)


def test_run_request_synthesizes_agent_task_loop() -> None:
    service = build_service(tool_ids={"case.list"})
    request = RuntimeRunRequest(
        request_id="req-2",
        source_type="api",
        partition="CI",
        objective="inspect partition cases",
        prompt="collect current case context",
        allowed_tools=["case.list"],
        max_steps=12,
    )

    result = asyncio.run(service.run_request(request=request))

    assert result.status == "completed"
    assert len(result.tool_results) == 1
    assert result.tool_results[0].tool_id == "case.list"
    assert any(artifact.artifact_type == "decision" for artifact in result.artifacts)
    assert any(step.step_type == "decision" for step in result.steps)


def test_run_request_fails_when_explicit_action_uses_disallowed_skill() -> None:
    service = build_service(skill_ids={"case.rebuild_case"})
    request = RuntimeRunRequest(
        request_id="req-3",
        source_type="manual",
        partition="CI",
        objective="run blocked skill",
        allowed_skills=["case.refresh_case_facets"],
        metadata={
            "actions": [
                {
                    "action_id": "action-1",
                    "kind": "skill_call",
                    "skill_id": "case.rebuild_case",
                    "title": "case.rebuild_case",
                    "inputs": {"case_id": "case-1"},
                }
            ]
        },
    )

    result = asyncio.run(service.run_request(request=request))

    assert result.status == "failed"
    assert "not allowed" in result.final_summary


def test_run_request_returns_requires_review_when_request_requires_review() -> None:
    service = build_service()
    request = RuntimeRunRequest(
        request_id="req-4",
        source_type="manual",
        partition="CI",
        objective="review-only flow",
        requires_review=True,
        metadata={
            "actions": [
                {
                    "action_id": "action-1",
                    "kind": "respond",
                    "title": "instruction",
                    "summary": "review generated state",
                    "prompt": "review generated state",
                }
            ]
        },
    )

    result = asyncio.run(service.run_request(request=request))

    assert result.status == "requires_review"


def test_run_request_reasoning_summary_includes_observation_count() -> None:
    service = build_service(tool_ids={"case.list"})
    request = RuntimeRunRequest(
        request_id="req-5",
        source_type="api",
        partition="CI",
        objective="inspect partition cases",
        prompt="collect current case context",
        context={"seed": "value"},
        allowed_tools=["case.list"],
        max_steps=12,
    )

    result = asyncio.run(service.run_request(request=request))

    assert result.status == "completed"
    assert "observation(s)" in result.reasoning_summary
