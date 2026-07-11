"""Runtime service for request-driven knowbase agent harness execution."""

from __future__ import annotations

from internal.models import AgentRun, RunArtifact, RunStep
from internal.models.skill import SkillResult
from internal.models.tool import ToolResult
from internal.domain.run.artifact_repository import RunArtifactRepository
from internal.domain.run.run_repository import AgentRunRepository
from internal.domain.run.step_repository import RunStepRepository
from internal.ports import PartitionAccessPort, SkillExecutionPort
from internal.runtime.action_executor import RuntimeActionExecutor
from internal.runtime.agent import DeterministicRuntimeAgent
from internal.runtime.contracts import RuntimeRunRequest, RuntimeRunResult
from internal.runtime.engine import RuntimeLoopEngine
from internal.runtime.executor import RuntimeExecutor
from internal.runtime.memory import RuntimeMemoryManager
from internal.runtime.policy import RuntimePolicy
from internal.runtime.session import RuntimeLoopState, RuntimeSession
from internal.runtime.termination import RuntimeTerminationPolicy
from internal.tools.runtime import ToolRuntime
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
    ):
        self._partition_service = partition_service
        self._case_repository = case_repository
        self._run_repository = run_repository
        self._step_repository = step_repository
        self._artifact_repository = artifact_repository
        self._tool_runtime = tool_runtime
        self._skill_runtime = skill_runtime
        self._executor = RuntimeExecutor(
            run_repository=self._run_repository,
            step_repository=self._step_repository,
            tool_runtime=self._tool_runtime,
            skill_runtime=self._skill_runtime,
        )
        self._memory_manager = RuntimeMemoryManager()
        self._policy = RuntimePolicy(executor=self._executor)
        self._termination_policy = RuntimeTerminationPolicy()
        self._agent = DeterministicRuntimeAgent()
        self._action_executor = RuntimeActionExecutor(
            executor=self._executor,
            policy=self._policy,
            memory_manager=self._memory_manager,
        )
        self._engine = RuntimeLoopEngine(
            executor=self._executor,
            agent=self._agent,
            action_executor=self._action_executor,
            memory_manager=self._memory_manager,
            termination_policy=self._termination_policy,
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
        request_artifact = self._artifact_repository.save(
            RunArtifact(
                run_id=run.run_id,
                artifact_type="runtime_request",
                title="Runtime Run Request",
                content=request.model_dump(mode="json"),
            )
        )
        session = RuntimeSession(run=run, request=request)
        loop_state = RuntimeLoopState(artifacts=[request_artifact])
        loop_state, memory, final_status = self._engine.run(
            session=session,
            loop_state=loop_state,
            persist_artifact=self._artifact_repository.save,
        )
        final_summary = self._memory_manager.build_final_summary(session=session, loop_state=loop_state)
        finished_run = self._run_repository.save(
            run.model_copy(
                update={
                    "status": final_status,
                    "reasoning_summary": self._memory_manager.build_reasoning_summary(
                        session=session,
                        loop_state=loop_state,
                        memory=memory,
                    ),
                    "final_summary": final_summary,
                }
            )
        )
        return self._build_run_result(
            request=request,
            run=finished_run,
            tool_results=loop_state.tool_results,
            skill_results=loop_state.skill_results,
            applied_actions=loop_state.applied_actions,
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

    def _create_request_run(self, *, request: RuntimeRunRequest) -> AgentRun:
        partition = request.partition.strip()
        if partition and self._partition_service.get_partition(partition) is None:
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
