"""Execute runtime decisions after agent planning."""

from __future__ import annotations

from internal.models.run import AgentRun
from internal.models.skill import SkillInvocation
from internal.models.tool import ToolCall
from internal.runtime.actions.capability_executor import RuntimeCapabilityExecutor
from internal.runtime.contracts import RuntimeRunRequest
from internal.runtime.core.memory import RuntimeMemoryManager
from internal.runtime.core.policy import RuntimePolicy
from internal.runtime.core.state import RuntimeRunState
from internal.runtime.trace.recorder import RuntimeTraceRecorder


class RuntimeActionRunner:
    """Validate and run decision actions with audit persistence."""

    def __init__(
        self,
        *,
        capability_executor: RuntimeCapabilityExecutor,
        policy: RuntimePolicy,
        memory_manager: RuntimeMemoryManager,
        trace_recorder: RuntimeTraceRecorder,
    ):
        self._capability_executor = capability_executor
        self._policy = policy
        self._memory_manager = memory_manager
        self._trace_recorder = trace_recorder

    def execute_decision(
        self,
        *,
        run: AgentRun,
        request: RuntimeRunRequest,
        state: RuntimeRunState,
        decision,
    ) -> None:
        decision_artifact = self._trace_recorder.record_decision_artifact(
            run=run,
            title=decision.decision_id or "decision",
            decision_payload=decision.model_dump(mode="json"),
        )
        state.artifacts.append(decision_artifact)
        for action in decision.actions:
            self._policy.validate_action(request=request, action=action)
            self._capability_executor.ensure_step_budget(run=run, next_steps=1)
            self._trace_recorder.record_action(
                run=run,
                name=action.title or action.action_id or action.kind,
                action_input=action.inputs,
                action_output={"kind": action.kind, "summary": action.summary},
                summary=action.summary or f"Executing runtime action {action.action_id or action.kind}",
            )
            if action.kind == "respond":
                state.applied_actions.append(action.action_id or action.title or "respond")
                state.response_messages.append(action.prompt or action.summary or request.objective)
                self._memory_manager.record_response(state=state, content=state.response_messages[-1])
                continue
            if action.kind == "tool_call":
                result_set = self._capability_executor.execute_tool_calls(
                    run=run,
                    calls=[
                        ToolCall(
                            call_id=f"{run.run_id}:{action.action_id or action.tool_id or 'tool'}",
                            run_id=run.run_id,
                            tool_id=action.tool_id,
                            partition=request.partition or run.partition,
                            inputs=action.inputs,
                            metadata=action.metadata,
                        )
                    ],
                )
                state.tool_results.extend(result_set)
                if result_set:
                    self._memory_manager.record_tool_result(
                        state=state,
                        tool_id=action.tool_id,
                        output=result_set[-1].output,
                    )
                if result_set and not result_set[-1].ok:
                    state.failure_messages.append(result_set[-1].error_message)
                state.applied_actions.append(action.action_id or action.tool_id or "tool_call")
                continue
            if action.kind == "skill_call":
                result_set = self._capability_executor.execute_invocations(
                    run=run,
                    invocations=[
                        SkillInvocation(
                            invocation_id=f"{run.run_id}:{action.action_id or action.skill_id or 'skill'}",
                            skill_id=action.skill_id,
                            partition=request.partition or run.partition,
                            inputs=action.inputs,
                            metadata=action.metadata,
                        )
                    ],
                )
                state.skill_results.extend(result_set)
                if result_set:
                    self._memory_manager.record_skill_result(
                        state=state,
                        skill_id=action.skill_id,
                        output=result_set[-1].output,
                    )
                if result_set and not result_set[-1].ok:
                    state.failure_messages.append(result_set[-1].error_message)
                state.applied_actions.append(action.action_id or action.skill_id or "skill_call")
                continue
            state.applied_actions.append(action.action_id or action.kind)
