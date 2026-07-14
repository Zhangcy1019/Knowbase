"""Core loop orchestrator for request-driven runtime runs."""

from __future__ import annotations

from internal.runtime.action_executor import RuntimeActionExecutor
from internal.runtime.agent import RuntimeAgentPort
from internal.runtime.contracts import RuntimeExecutionStatus
from internal.runtime.executor import RuntimeExecutor
from internal.runtime.memory import RuntimeMemoryManager
from internal.runtime.state import RuntimeRunState
from internal.runtime.termination import RuntimeTerminationPolicy


class RuntimeLoopEngine:
    """Orchestrate one runtime session through repeated agent decisions."""

    def __init__(
        self,
        *,
        executor: RuntimeExecutor,
        agent: RuntimeAgentPort,
        action_executor: RuntimeActionExecutor,
        memory_manager: RuntimeMemoryManager,
        termination_policy: RuntimeTerminationPolicy,
    ):
        self._executor = executor
        self._agent = agent
        self._action_executor = action_executor
        self._memory_manager = memory_manager
        self._termination_policy = termination_policy

    def run(
        self,
        *,
        run,
        request,
        state: RuntimeRunState,
        persist_artifact,
    ) -> tuple[RuntimeRunState, RuntimeExecutionStatus]:
        self._memory_manager.initialize_state(run=run, request=request, state=state)
        final_status: RuntimeExecutionStatus = "completed"
        while True:
            turn_input = self._memory_manager.build_turn_input(
                run=run,
                request=request,
                state=state,
            )
            decision = self._agent.decide(
                run=run,
                request=request,
                state=state,
                turn_input=turn_input,
            )
            state.record_decision(decision)
            self._executor.append_step(
                run=run,
                step_type="decision",
                name=decision.decision_id or "decision",
                input={},
                output=decision.model_dump(mode="json"),
                summary=decision.reasoning_summary or "Planner produced a decision.",
            )
            termination = self._termination_policy.should_stop(run=run, request=request, state=state, decision=decision)
            if termination.should_stop and not decision.actions:
                final_status = termination.status
                break
            try:
                self._action_executor.execute_decision(
                    run=run,
                    request=request,
                    state=state,
                    decision=decision,
                    persist_artifact=persist_artifact,
                )
            except Exception as exc:  # noqa: BLE001
                message = str(exc)
                state.failure_messages.append(message)
                self._executor.append_step(
                    run=run,
                    step_type="decision_error",
                    name=decision.decision_id or "decision_error",
                    input={},
                    output={"error": message},
                    summary=message,
                )
            termination = self._termination_policy.should_stop(run=run, request=request, state=state, decision=decision)
            if termination.should_stop:
                final_status = termination.status
                break
        return state, final_status
