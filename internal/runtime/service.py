"""Runtime service for request-driven knowbase agent harness execution."""

from __future__ import annotations

from datetime import datetime, timezone

from internal.models import AgentRun, RunArtifact, RunStep, RuntimeTraceReplay
from internal.models.skill import SkillResult
from internal.models.tool import ToolResult
from internal.ports import PartitionReadPort, SkillExecutionPort
from internal.runtime.execution.action_runner import RuntimeActionRunner
from internal.runtime.execution.capability_executor import RuntimeCapabilityExecutor
from internal.runtime.execution.policy import RuntimePolicy
from internal.runtime.contracts import RuntimeRunRequest, RuntimeRunResult
from internal.runtime.harness.child_runner import RuntimeChildRunAdapter
from internal.runtime.memory.manager import RuntimeMemoryManager
from internal.runtime.memory.state import RuntimeRunState
from internal.runtime.harness.runner import RuntimeHarnessRunner
from internal.runtime.harness.subrun import RuntimeSubRunLauncher
from internal.runtime.loop.engine import RuntimeLoopEngine
from internal.runtime.loop.termination import RuntimeTerminationPolicy
from internal.runtime.loop.turn_planner import RuntimeTurnPlannerPort
from internal.runtime.trace.recorder import RuntimeTraceRecorder
from internal.runtime.tools.runtime import ToolRuntime
from internal.runtime.verification.acceptance import RuntimeAcceptanceVerifier
from internal.runtime.verification.stop_hook import VerificationStopHook
from internal.runtime.verification.verifier import RuntimeVerifier
from internal.utils.logger import get_logger


logger = get_logger("knowbase.runtime.service")


class _RuntimeServiceChildExecutor:
    """Execute child requests through the same runtime service instance."""

    def __init__(self, *, service: "KnowbaseRuntimeService"):
        self._service = service

    def execute_child_request(self, *, child_run, child_request) -> RuntimeRunResult:
        return self._service._execute_request(
            request=child_request,
            existing_run=child_run,
        )


class KnowbaseRuntimeService:
    """Create, execute, and audit request-driven runtime runs."""

    def __init__(
        self,
        *,
        partition_service: PartitionReadPort,
        case_repository,
        run_repository,
        step_repository,
        artifact_repository,
        tool_runtime: ToolRuntime,
        skill_runtime: SkillExecutionPort,
        planner: RuntimeTurnPlannerPort,
        trace_recorder: RuntimeTraceRecorder,
        verifier=None,
        subrun_launcher: RuntimeSubRunLauncher | None = None,
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
        self._memory_manager = RuntimeMemoryManager(capability_executor=self._capability_executor)
        self._policy = RuntimePolicy(capability_executor=self._capability_executor)
        self._acceptance_verifier = RuntimeAcceptanceVerifier()
        self._termination_policy = RuntimeTerminationPolicy(
            acceptance_verifier=self._acceptance_verifier,
        )
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
        child_adapter = RuntimeChildRunAdapter()
        child_adapter.set_executor(executor=_RuntimeServiceChildExecutor(service=self))
        self._subrun_launcher = subrun_launcher or RuntimeSubRunLauncher(executor=child_adapter)
        self._verifier = verifier or RuntimeVerifier(
            acceptance_verifier=self._acceptance_verifier,
        )
        self._before_complete_hook = VerificationStopHook(
            verifier=self._verifier,
        )
        self._harness_runner = RuntimeHarnessRunner(
            loop_engine=self._engine,
            before_complete_hook=self._before_complete_hook,
            subrun_launcher=self._subrun_launcher,
            trace_recorder=self._trace_recorder,
        )

    async def run_request(self, *, request: RuntimeRunRequest) -> RuntimeRunResult:
        return self._execute_request(request=request)

    def _execute_request(
        self,
        *,
        request: RuntimeRunRequest,
        existing_run: AgentRun | None = None,
    ) -> RuntimeRunResult:
        work_profile = request.work
        logger.info(
            "Executing runtime request.",
            extra={
                "request_id": request.request_id,
                "partition": request.partition,
                "objective": work_profile.objective,
            },
        )
        request = self._normalize_request_metadata(request=request)
        run = self._prepare_request_run(request=request, existing_run=existing_run)
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
        state = RuntimeRunState(artifacts=[request_artifact], run=run)

        def load_current_run() -> AgentRun:
            return self._run_repository.get(run.run_id) or run

        try:
            orchestration_result = self._harness_runner.run(
                run=run,
                request=request,
                state=state,
            )
            state = orchestration_result.state
            final_status = orchestration_result.final_status
            requires_review = orchestration_result.requires_review
            final_summary = self._memory_manager.build_final_summary(request=request, state=state)
            current_run = load_current_run()
            finished_run = self._run_repository.save(
                current_run.model_copy(
                    update={
                        "status": final_status,
                        "requires_review": requires_review,
                        "reasoning_summary": self._memory_manager.build_reasoning_summary(request=request, state=state),
                        "final_summary": final_summary,
                        "finished_at": datetime.now(timezone.utc),
                    }
                )
            )
        except Exception as exc:
            message = str(exc)
            state.failure_messages.append(message)
            logger.error(
                "Runtime request crashed before completion.",
                extra={
                    "request_id": request.request_id,
                    "run_id": run.run_id,
                    "partition": request.partition,
                    "error": message,
                },
            )
            self._trace_recorder.record_decision_error(
                run=run,
                name=f"{run.run_id}:fatal",
                error_message=message,
            )
            current_run = load_current_run()
            finished_run = self._run_repository.save(
                current_run.model_copy(
                    update={
                        "status": "failed",
                        "requires_review": True,
                        "reasoning_summary": self._memory_manager.build_reasoning_summary(request=request, state=state),
                        "final_summary": message,
                        "finished_at": datetime.now(timezone.utc),
                    }
                )
            )
            raise
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

    def _normalize_request_metadata(self, *, request: RuntimeRunRequest) -> RuntimeRunRequest:
        metadata = dict(request.metadata)
        subrun_depth = int(metadata.get("subrun_depth", 0) or 0)
        verification_subrun_count = int(metadata.get("verification_subrun_count", 0) or 0)
        if "allow_subrun" not in metadata:
            metadata["allow_subrun"] = subrun_depth == 0
        metadata["subrun_depth"] = subrun_depth
        metadata["verification_subrun_count"] = verification_subrun_count
        return request.model_copy(update={"metadata": metadata})

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

    def _prepare_request_run(
        self,
        *,
        request: RuntimeRunRequest,
        existing_run: AgentRun | None,
    ) -> AgentRun:
        work_profile = request.work
        partition = request.partition.strip()
        if not partition:
            logger.error(
                "Runtime request missing partition.",
                extra={
                    "request_id": request.request_id,
                },
            )
            raise ValueError("runtime request partition must not be empty")
        partition_document = self._partition_service.get_partition(partition)
        if partition_document is None:
            logger.error(
                "Runtime request references unknown partition.",
                extra={
                    "request_id": request.request_id,
                    "partition": partition,
                },
            )
            raise ValueError(f"partition not found: {partition}")
        partition_status = getattr(partition_document, "status", None)
        if isinstance(partition_document, dict):
            partition_status = partition_document.get("status")
        if partition_status and partition_status != "active":
            logger.error(
                "Runtime request references inactive partition.",
                extra={
                    "request_id": request.request_id,
                    "partition": partition,
                    "partition_status": partition_status,
                },
            )
            raise ValueError(f"partition is not active: {partition}")
        if existing_run is not None:
            return self._run_repository.save(
                existing_run.model_copy(
                    update={
                        "partition": partition,
                        "status": "running",
                        "source_type": request.source_type,
                        "source_event_type": "runtime.request",
                        "source_event_id": request.request_id,
                        "source_ref": request.source_ref,
                        "objective": work_profile.objective,
                        "planning_context": {"request": request.model_dump(mode="json")},
                        "tool_whitelist": work_profile.allowed_tools,
                        "skill_whitelist": work_profile.allowed_skills,
                        "max_steps": work_profile.max_steps,
                        "max_tool_calls": work_profile.max_tool_calls,
                        "max_skill_calls": work_profile.max_skill_calls,
                        "risk_level": request.risk_level,
                        "requires_review": request.requires_review,
                        "final_summary": "",
                        "reasoning_summary": "",
                        "finished_at": None,
                    }
                )
            )
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
                objective=work_profile.objective,
                planning_context={"request": request.model_dump(mode="json")},
                tool_whitelist=work_profile.allowed_tools,
                skill_whitelist=work_profile.allowed_skills,
                max_steps=work_profile.max_steps,
                max_tool_calls=work_profile.max_tool_calls,
                max_skill_calls=work_profile.max_skill_calls,
                risk_level=request.risk_level,
                requires_review=request.requires_review,
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
        return RuntimeRunResult(
            request_id=request.request_id,
            run_id=run.run_id,
            status=run.status,
            final_summary=run.final_summary,
            reasoning_summary=run.reasoning_summary,
            steps=self._step_repository.list_for_run(run.run_id),
            artifacts=self._artifact_repository.list_for_run(run.run_id),
            skill_results=skill_results,
            tool_results=tool_results,
            applied_actions=applied_actions,
            requires_review=run.requires_review,
            metadata={"source_type": request.source_type},
        )
