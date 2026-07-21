"""Core loop orchestrator for request-driven runtime runs."""

from __future__ import annotations

from internal.runtime.execution.action_runner import RuntimeActionRunner
from internal.runtime.execution.capability_executor import RuntimeCapabilityExecutor
from internal.runtime.contracts import RuntimeExecutionStatus
from internal.runtime.memory.manager import RuntimeMemoryManager
from internal.runtime.memory.state import RuntimeRunState
from internal.runtime.loop.termination import RuntimeTerminationPolicy
from internal.runtime.loop.turn_planner import RuntimeTurnPlannerPort
from internal.runtime.trace.recorder import RuntimeTraceRecorder
from internal.utils.logger import get_logger


logger = get_logger("knowbase.runtime.loop.engine")


class RuntimeLoopEngine:
    """Orchestrate one runtime session through repeated agent decisions."""

    def __init__(
        self,
        *,
        capability_executor: RuntimeCapabilityExecutor,
        planner: RuntimeTurnPlannerPort,
        action_runner: RuntimeActionRunner,
        memory_manager: RuntimeMemoryManager,
        termination_policy: RuntimeTerminationPolicy,
        trace_recorder: RuntimeTraceRecorder,
    ):
        self._capability_executor = capability_executor
        self._planner = planner
        self._action_runner = action_runner
        self._memory_manager = memory_manager
        self._termination_policy = termination_policy
        self._trace_recorder = trace_recorder

    def run(
        self,
        *,
        run,
        request,
        state: RuntimeRunState,
    ) -> tuple[RuntimeRunState, RuntimeExecutionStatus, bool]:
        logger.debug(
            "Initializing runtime loop state.",
            extra={
                "run_id": run.run_id,
                "request_id": request.request_id,
                "partition": request.partition,
            },
        )
        self._memory_manager.initialize_state(run=run, request=request, state=state)
        final_status: RuntimeExecutionStatus = "completed"
        requires_review = False
        while True:
            turn_input = self._memory_manager.build_turn_input(
                run=run,
                request=request,
                state=state,
            )
            logger.debug(
                "Starting runtime turn.",
                extra={
                    "run_id": run.run_id,
                    "turn_index": turn_input.turn_index,
                    "decision_count": len(state.decision_history),
                    "applied_action_count": len(state.applied_actions),
                    "tool_results": len(state.tool_results),
                    "skill_results": len(state.skill_results),
                    "failures": len(state.failure_messages),
                },
            )
            decision = self._planner.plan_turn(
                run=run,
                request=request,
                state=state,
                turn_input=turn_input,
            )
            state.record_decision(decision)
            logger.info(
                "Runtime decision generated.",
                extra={
                    "run_id": run.run_id,
                    "turn_index": turn_input.turn_index,
                    "decision_id": decision.decision_id,
                    "action_count": len(decision.actions),
                    "should_stop": decision.should_stop,
                    "requires_review": decision.requires_review,
                },
            )
            self._capability_executor.ensure_step_budget(run=run, next_steps=1)
            self._trace_recorder.record_decision(
                run=run,
                name=decision.decision_id or "decision",
                decision_payload=decision.model_dump(mode="json"),
                summary=decision.reasoning_summary or "Planner produced a decision.",
            )
            summary_message = decision.metadata.get("action_plan_summary") or decision.reasoning_summary
            if isinstance(summary_message, str) and summary_message.strip():
                state.response_messages.append(summary_message.strip())
                self._memory_manager.record_response(state=state, content=summary_message.strip())
            termination = self._termination_policy.should_stop(run=run, request=request, state=state, decision=decision)
            if termination.should_stop and not decision.actions:
                final_status = termination.status
                requires_review = termination.requires_review
                logger.warning(
                    "Runtime loop stopped before action execution.",
                    extra={
                        "run_id": run.run_id,
                        "turn_index": turn_input.turn_index,
                        "status": termination.status,
                        "requires_review": termination.requires_review,
                        "reason": termination.reason,
                    },
                )
                break
            try:
                self._action_runner.execute_decision(
                    run=run,
                    request=request,
                    state=state,
                    decision=decision,
                )
            except Exception as exc:  # noqa: BLE001
                message = str(exc)
                state.failure_messages.append(message)
                logger.error(
                    "Runtime decision execution failed.",
                    extra={
                        "run_id": run.run_id,
                        "turn_index": turn_input.turn_index,
                        "decision_id": decision.decision_id,
                        "error": message,
                    },
                )
                self._capability_executor.ensure_step_budget(run=run, next_steps=1)
                self._trace_recorder.record_decision_error(
                    run=run,
                    name=decision.decision_id or "decision_error",
                    error_message=message,
                )
            termination = self._termination_policy.should_stop(run=run, request=request, state=state, decision=decision)
            if termination.should_stop:
                final_status = termination.status
                requires_review = termination.requires_review
                logger.info(
                    "Runtime loop finished.",
                    extra={
                        "run_id": run.run_id,
                        "turn_index": turn_input.turn_index,
                        "status": termination.status,
                        "requires_review": termination.requires_review,
                        "reason": termination.reason,
                    },
                )
                break
        return state, final_status, requires_review
