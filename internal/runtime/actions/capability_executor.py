"""Execution helpers for tools and skills inside one runtime loop."""

from __future__ import annotations

from typing import Any

from internal.domain.run.run_repository import AgentRunRepository
from internal.domain.run.step_repository import RunStepRepository
from internal.models import (
    AgentRun,
    RunStep,
    SkillExecutionContext,
    SkillInvocation,
    SkillResult,
    SkillSpec,
    ToolCall,
    ToolResult,
)
from internal.runtime.skills.runtime import SkillRuntime
from internal.runtime.tools.runtime import ToolRuntime


class RuntimeCapabilityExecutor:
    """Execute tool and skill capabilities with step-level audit persistence."""

    def __init__(
        self,
        *,
        run_repository: AgentRunRepository,
        step_repository: RunStepRepository,
        tool_runtime: ToolRuntime,
        skill_runtime: SkillRuntime,
    ):
        self._run_repository = run_repository
        self._step_repository = step_repository
        self._tool_runtime = tool_runtime
        self._skill_runtime = skill_runtime

    def collect_initial_tool_observations(self, *, run: AgentRun) -> list[ToolResult]:
        tool_results: list[ToolResult] = []
        for tool_id in run.tool_whitelist:
            tool_results.extend(
                self.execute_tool_calls(
                    run=run,
                    calls=[
                        ToolCall(
                            call_id=f"{run.run_id}:{tool_id}",
                            run_id=run.run_id,
                            tool_id=tool_id,
                            partition=run.partition,
                            inputs={"partition": run.partition, "resource_id": run.source_ref},
                            metadata={"source_event_type": run.source_event_type},
                        )
                    ],
                    step_summary_prefix="Collecting initial context through",
                )
            )
        return tool_results

    def execute_tool_calls(
        self,
        *,
        run: AgentRun,
        calls: list[ToolCall],
        step_summary_prefix: str = "Executing read-only tool",
    ) -> list[ToolResult]:
        results: list[ToolResult] = []
        for call in calls:
            self.ensure_tool_budget(run=run, next_calls=1)
            normalized_call = call.model_copy(
                update={
                    "run_id": run.run_id,
                    "partition": call.partition or run.partition,
                }
            )
            self.append_step(
                run=run,
                step_type="tool_call",
                name=normalized_call.tool_id,
                input=normalized_call.inputs,
                output={},
                summary=f"{step_summary_prefix} {normalized_call.tool_id}",
            )
            result = self._tool_runtime.execute(normalized_call)
            results.append(result)
            self.append_step(
                run=run,
                step_type="tool_result",
                name=normalized_call.tool_id,
                input={},
                output=result.model_dump(mode="json"),
                summary="Tool finished successfully." if result.ok else f"Tool failed: {result.error_message}",
            )
            persisted = self._run_repository.get(run.run_id)
            if persisted is not None:
                self._run_repository.save(
                    persisted.model_copy(update={"tool_call_count": persisted.tool_call_count + 1})
                )
        return results

    def execute_invocations(self, *, run: AgentRun, invocations: list[SkillInvocation]) -> list[SkillResult]:
        results: list[SkillResult] = []
        for invocation in invocations:
            self.ensure_skill_budget(run=run, next_calls=1)
            self.append_step(
                run=run,
                step_type="skill_call",
                name=invocation.skill_id,
                input=invocation.inputs,
                output={},
                summary=f"Executing skill {invocation.skill_id}",
            )
            result = self._skill_runtime.execute(
                invocation,
                context=SkillExecutionContext(
                    run_id=run.run_id,
                    partition=run.partition,
                    agent_id=run.agent_id,
                    source_event_type=run.source_event_type,
                    source_event_id=run.source_event_id,
                    metadata={"run_mode": run.mode},
                    started_at=run.created_at,
                ),
            )
            results.append(result)
            self.append_step(
                run=run,
                step_type="skill_result",
                name=invocation.skill_id,
                input={},
                output=result.model_dump(mode="json"),
                summary="Skill finished successfully." if result.ok else f"Skill failed: {result.error_message}",
            )
            persisted = self._run_repository.get(run.run_id)
            if persisted is not None:
                self._run_repository.save(
                    persisted.model_copy(update={"skill_call_count": persisted.skill_call_count + 1})
                )
        return results

    def resolve_skill_spec(self, skill_id: str) -> SkillSpec | None:
        return self._skill_runtime.resolve_spec(skill_id)

    def tool_exists(self, tool_id: str) -> bool:
        return self._tool_runtime.registry.resolve(tool_id) is not None

    def append_step(
        self,
        *,
        run: AgentRun,
        step_type: str,
        name: str,
        input: dict[str, Any],
        output: dict[str, Any],
        summary: str,
    ) -> RunStep:
        self.ensure_step_budget(run=run, next_steps=1)
        step = self._step_repository.save(
            RunStep(
                run_id=run.run_id,
                index=len(self._step_repository.list_for_run(run.run_id)),
                step_type=step_type,
                name=name,
                input=input,
                output=output,
                summary=summary,
            )
        )
        persisted = self._run_repository.get(run.run_id)
        if persisted is not None:
            self._run_repository.save(persisted.model_copy(update={"step_count": step.index + 1}))
        return step

    def ensure_step_budget(self, *, run: AgentRun, next_steps: int) -> None:
        persisted = self._run_repository.get(run.run_id) or run
        if persisted.step_count + next_steps > persisted.max_steps:
            raise RuntimeError(
                f"run step budget exceeded: {persisted.step_count + next_steps}>{persisted.max_steps}"
            )

    def ensure_tool_budget(self, *, run: AgentRun, next_calls: int) -> None:
        persisted = self._run_repository.get(run.run_id) or run
        if persisted.tool_call_count + next_calls > persisted.max_tool_calls:
            raise RuntimeError(
                f"run tool budget exceeded: {persisted.tool_call_count + next_calls}>{persisted.max_tool_calls}"
            )

    def ensure_skill_budget(self, *, run: AgentRun, next_calls: int) -> None:
        persisted = self._run_repository.get(run.run_id) or run
        if persisted.skill_call_count + next_calls > persisted.max_skill_calls:
            raise RuntimeError(
                f"run skill budget exceeded: {persisted.skill_call_count + next_calls}>{persisted.max_skill_calls}"
            )
