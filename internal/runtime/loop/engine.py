"""Core loop orchestrator for request-driven runtime runs."""

from __future__ import annotations

from internal.runtime.actions.action_runner import RuntimeActionRunner
from internal.runtime.actions.capability_executor import RuntimeCapabilityExecutor
from internal.runtime.contracts import RuntimeExecutionStatus
from internal.runtime.core.memory import RuntimeMemoryManager
from internal.runtime.core.state import RuntimeRunState
from internal.runtime.core.termination import RuntimeTerminationPolicy
from internal.runtime.loop.agent import RuntimeAgentPort
from internal.runtime.trace.recorder import RuntimeTraceRecorder


class RuntimeLoopEngine:
    """Orchestrate one runtime session through repeated agent decisions."""

    def __init__(
        self,
        *,
        capability_executor: RuntimeCapabilityExecutor,
        agent: RuntimeAgentPort,
        action_runner: RuntimeActionRunner,
        memory_manager: RuntimeMemoryManager,
        termination_policy: RuntimeTerminationPolicy,
        trace_recorder: RuntimeTraceRecorder,
    ):
        self._capability_executor = capability_executor
        self._agent = agent
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
            self._capability_executor.ensure_step_budget(run=run, next_steps=1)
            self._trace_recorder.record_decision(
                run=run,
                name=decision.decision_id or "decision",
                decision_payload=decision.model_dump(mode="json"),
                summary=decision.reasoning_summary or "Planner produced a decision.",
            )
            termination = self._termination_policy.should_stop(run=run, request=request, state=state, decision=decision)
            if termination.should_stop and not decision.actions:
                final_status = termination.status
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
                self._capability_executor.ensure_step_budget(run=run, next_steps=1)
                self._trace_recorder.record_decision_error(
                    run=run,
                    name=decision.decision_id or "decision_error",
                    error_message=message,
                )
            termination = self._termination_policy.should_stop(run=run, request=request, state=state, decision=decision)
            if termination.should_stop:
                final_status = termination.status
                break
        return state, final_status
