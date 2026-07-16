"""Runtime service for request-driven knowbase agent harness execution."""

from __future__ import annotations

from internal.models import AgentRun, RunArtifact, RunStep, RuntimeTraceReplay
from internal.models.skill import SkillResult
from internal.models.tool import ToolResult
from internal.domain.run.artifact_repository import RunArtifactRepository
from internal.domain.run.run_repository import AgentRunRepository
from internal.domain.run.step_repository import RunStepRepository
from internal.ports import PartitionAccessPort, SkillExecutionPort
from internal.runtime.actions.action_runner import RuntimeActionRunner
from internal.runtime.actions.capability_executor import RuntimeCapabilityExecutor
from internal.runtime.contracts import RuntimeRunRequest, RuntimeRunResult
from internal.runtime.core.memory import RuntimeMemoryManager
from internal.runtime.core.policy import RuntimePolicy
from internal.runtime.core.state import RuntimeRunState
from internal.runtime.core.termination import RuntimeTerminationPolicy
from internal.runtime.loop.engine import RuntimeLoopEngine
from internal.runtime.loop.turn_planner import RuntimeTurnPlannerPort
from internal.runtime.trace.recorder import RuntimeTraceRecorder
from internal.runtime.tools.runtime import ToolRuntime
from internal.utils.logger import get_logger


logger = get_logger("knowbase.runtime.service")


class KnowbaseRuntimeService:
    """Create, execute, and audit request-driven runtime runs."""

    def __init__(
        self,
        *,
        partition_service: PartitionAccessPort,
        case_repository,
        run_repository: AgentRunRepository,
        step_repository: RunStepRepository,
        artifact_repository: RunArtifactRepository,
        tool_runtime: ToolRuntime,
        skill_runtime: SkillExecutionPort,
        planner: RuntimeTurnPlannerPort,
        trace_recorder: RuntimeTraceRecorder,
    ):
        self._partition_service = partition_service
        self._case_repository = case_repository
        self._run_repository = run_repository
        self._step_repository = step_repository
        self._artifact_repository = artifact_repository
        self._tool_runtime = tool_runtime
        self._skill_runtime = skill_runtime
        self._trace_recorder = trace_recorder
        self._capability_executor = RuntimeCapabilityExecutor(
            run_repository=self._run_repository,
            tool_runtime=self._tool_runtime,
            skill_runtime=self._skill_runtime,
            trace_recorder=self._trace_recorder,
        )
        self._memory_manager = RuntimeMemoryManager()
        self._policy = RuntimePolicy(capability_executor=self._capability_executor)
        self._termination_policy = RuntimeTerminationPolicy()
        self._planner = planner
        self._action_runner = RuntimeActionRunner(
            capability_executor=self._capability_executor,
            policy=self._policy,
            memory_manager=self._memory_manager,
            trace_recorder=self._trace_recorder,
        )
        self._engine = RuntimeLoopEngine(
            capability_executor=self._capability_executor,
            planner=self._planner,
            action_runner=self._action_runner,
            memory_manager=self._memory_manager,
            termination_policy=self._termination_policy,
            trace_recorder=self._trace_recorder,
        )

    async def run_request(self, *, request: RuntimeRunRequest) -> RuntimeRunResult:
        logger.info(
            "Executing runtime request.",
            extra={
                "request_id": request.request_id,
                "partition": request.partition,
                "objective": request.objective,
            },
        )
        run = self._create_request_run(request=request)
        logger.debug(
            "Runtime run created.",
            extra={
                "run_id": run.run_id,
                "request_id": request.request_id,
                "max_steps": run.max_steps,
                "max_tool_calls": run.max_tool_calls,
                "max_skill_calls": run.max_skill_calls,
            },
        )
        request_artifact = self._trace_recorder.record_runtime_request(
            run=run,
            request_payload=request.model_dump(mode="json"),
        )
        state = RuntimeRunState(artifacts=[request_artifact])
        state, final_status = self._engine.run(
            run=run,
            request=request,
            state=state,
        )
        final_summary = self._memory_manager.build_final_summary(request=request, state=state)
        finished_run = self._run_repository.save(
            run.model_copy(
                update={
                    "status": final_status,
                    "reasoning_summary": self._memory_manager.build_reasoning_summary(request=request, state=state),
                    "final_summary": final_summary,
                }
            )
        )
        logger.info(
            "Runtime request finished.",
            extra={
                "request_id": request.request_id,
                "run_id": finished_run.run_id,
                "status": finished_run.status,
                "applied_action_count": len(state.applied_actions),
                "tool_result_count": len(state.tool_results),
                "skill_result_count": len(state.skill_results),
                "failure_count": len(state.failure_messages),
            },
        )
        return self._build_run_result(
            request=request,
            run=finished_run,
            tool_results=state.tool_results,
            skill_results=state.skill_results,
            applied_actions=state.applied_actions,
        )

    def list_runs(self, *, partition: str = "", status: str = "") -> list[AgentRun]:
        return self._run_repository.list(partition=partition.strip(), status=status.strip())

    def get_run(self, run_id: str) -> AgentRun | None:
        return self._run_repository.get(run_id.strip())

    def delete_run(self, run_id: str) -> None:
        normalized = run_id.strip()
        self._artifact_repository.delete_for_run(normalized)
        self._step_repository.delete_for_run(normalized)
        self._run_repository.delete(normalized)

    def list_steps(self, run_id: str) -> list[RunStep]:
        return self._step_repository.list_for_run(run_id.strip())

    def list_artifacts(self, run_id: str) -> list[RunArtifact]:
        return self._artifact_repository.list_for_run(run_id.strip())

    def get_trace_replay(self, run_id: str) -> RuntimeTraceReplay | None:
        return self._trace_recorder.load_replay(run_id=run_id.strip())

    def _create_request_run(self, *, request: RuntimeRunRequest) -> AgentRun:
        partition = request.partition.strip()
        if partition and self._partition_service.get_partition(partition) is None:
            logger.error(
                "Runtime request references unknown partition.",
                extra={
                    "request_id": request.request_id,
                    "partition": partition,
                },
            )
            raise ValueError(f"partition not found: {partition}")
        return self._run_repository.save(
            AgentRun(
                partition=partition,
                agent_id="runtime.harness",
                mode="agent",
                status="running",
                source_type=request.source_type,
                source_event_type="runtime.request",
                source_event_id=request.request_id,
                source_ref=request.source_ref,
                objective=request.objective,
                planning_context={"request": request.model_dump(mode="json")},
                tool_whitelist=request.allowed_tools,
                skill_whitelist=request.allowed_skills,
                max_steps=request.max_steps,
                max_tool_calls=request.max_tool_calls,
                max_skill_calls=request.max_skill_calls,
                risk_level=request.risk_level,
            )
        )

    def _build_run_result(
        self,
        *,
        request: RuntimeRunRequest,
        run: AgentRun,
        tool_results: list[ToolResult],
        skill_results: list[SkillResult],
        applied_actions: list[str],
    ) -> RuntimeRunResult:
        normalized_status = run.status if run.status in {"completed", "failed", "cancelled"} else "requires_review"
        return RuntimeRunResult(
            request_id=request.request_id,
            run_id=run.run_id,
            status=normalized_status,
            final_summary=run.final_summary,
            reasoning_summary=run.reasoning_summary,
            steps=self._step_repository.list_for_run(run.run_id),
            artifacts=self._artifact_repository.list_for_run(run.run_id),
            skill_results=skill_results,
            tool_results=tool_results,
            applied_actions=applied_actions,
            requires_review=request.requires_review,
            metadata={"source_type": request.source_type},
        )
