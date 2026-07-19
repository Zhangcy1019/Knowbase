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
from internal.utils.logger import get_logger


logger = get_logger("knowbase.runtime.actions.runner")


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
        logger.debug(
            "Executing runtime decision actions.",
            extra={
                "run_id": run.run_id,
                "decision_id": decision.decision_id,
                "action_count": len(decision.actions),
            },
        )
        decision_artifact = self._trace_recorder.record_decision_artifact(
            run=run,
            title=decision.decision_id or "decision",
            decision_payload=decision.model_dump(mode="json"),
        )
        state.artifacts.append(decision_artifact)
        for action in decision.actions:
            logger.info(
                "Executing runtime action.",
                extra={
                    "run_id": run.run_id,
                    "decision_id": decision.decision_id,
                    "action_id": action.action_id,
                    "action_kind": action.kind,
                    "tool_id": action.tool_id,
                    "skill_id": action.skill_id,
                },
            )
            self._policy.validate_action(request=request, action=action)
            self._capability_executor.ensure_step_budget(run=run, next_steps=1)
            self._trace_recorder.record_action(
                run=run,
                name=action.title or action.action_id or action.kind,
                action_input=action.inputs,
                action_output={"kind": action.kind, "summary": action.summary},
                summary=action.summary or f"Executing runtime action {action.action_id or action.kind}",
            )
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
                    logger.warning(
                        "Runtime tool action finished with failure.",
                        extra={
                            "run_id": run.run_id,
                            "action_id": action.action_id,
                            "tool_id": action.tool_id,
                            "error": result_set[-1].error_message,
                        },
                    )
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
                    logger.warning(
                        "Runtime skill action finished with failure.",
                        extra={
                            "run_id": run.run_id,
                            "action_id": action.action_id,
                            "skill_id": action.skill_id,
                            "error": result_set[-1].error_message,
                        },
                    )
                state.applied_actions.append(action.action_id or action.skill_id or "skill_call")
                continue
            logger.debug(
                "Runtime action completed without capability execution branch.",
                extra={
                    "run_id": run.run_id,
                    "action_id": action.action_id,
                    "action_kind": action.kind,
                },
            )
            state.applied_actions.append(action.action_id or action.kind)
