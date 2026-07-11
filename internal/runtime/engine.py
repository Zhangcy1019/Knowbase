"""Core loop orchestrator for request-driven runtime runs."""

from __future__ import annotations

from internal.runtime.action_executor import RuntimeActionExecutor
from internal.runtime.agent import RuntimeAgentPort
from internal.runtime.context import RuntimeAgentContext
from internal.runtime.contracts import RuntimeExecutionStatus
from internal.runtime.executor import RuntimeExecutor
from internal.runtime.memory import RuntimeMemoryManager, RuntimeWorkingMemory
from internal.runtime.session import RuntimeLoopState, RuntimeSession
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
        session: RuntimeSession,
        loop_state: RuntimeLoopState,
        persist_artifact,
    ) -> tuple[RuntimeLoopState, RuntimeWorkingMemory, RuntimeExecutionStatus]:
        memory = self._memory_manager.build_initial_memory(session=session)
        final_status: RuntimeExecutionStatus = "completed"
        while True:
            agent_context = RuntimeAgentContext(
                session=session,
                loop_state=loop_state,
                memory=memory,
                turn_input=self._memory_manager.build_turn_input(
                    session=session,
                    loop_state=loop_state,
                    memory=memory,
                ),
            )
            decision = self._agent.decide(context=agent_context)
            loop_state.record_decision(decision)
            self._executor.append_step(
                run=session.run,
                step_type="decision",
                name=decision.decision_id or "decision",
                input={},
                output=decision.model_dump(mode="json"),
                summary=decision.reasoning_summary or "Planner produced a decision.",
            )
            termination = self._termination_policy.should_stop(session=session, loop_state=loop_state, decision=decision)
            if termination.should_stop and not decision.actions:
                final_status = termination.status
                break
            try:
                self._action_executor.execute_decision(
                    context=agent_context,
                    decision=decision,
                    persist_artifact=persist_artifact,
                )
            except Exception as exc:  # noqa: BLE001
                message = str(exc)
                loop_state.failure_messages.append(message)
                self._executor.append_step(
                    run=session.run,
                    step_type="decision_error",
                    name=decision.decision_id or "decision_error",
                    input={},
                    output={"error": message},
                    summary=message,
                )
            termination = self._termination_policy.should_stop(session=session, loop_state=loop_state, decision=decision)
            if termination.should_stop:
                final_status = termination.status
                break
        return loop_state, memory, final_status
