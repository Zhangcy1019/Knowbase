"""Execute runtime decisions after agent planning."""

from __future__ import annotations

from internal.models import RunArtifact
from internal.models.skill import SkillInvocation
from internal.models.tool import ToolCall
from internal.runtime.context import RuntimeAgentContext
from internal.runtime.executor import RuntimeExecutor
from internal.runtime.memory import RuntimeMemoryManager
from internal.runtime.policy import RuntimePolicy


class RuntimeActionExecutor:
    """Validate and execute decision actions with audit persistence."""

    def __init__(
        self,
        *,
        executor: RuntimeExecutor,
        policy: RuntimePolicy,
        memory_manager: RuntimeMemoryManager,
    ):
        self._executor = executor
        self._policy = policy
        self._memory_manager = memory_manager

    def execute_decision(
        self,
        *,
        context: RuntimeAgentContext,
        decision,
        persist_artifact,
    ) -> None:
        session = context.session
        loop_state = context.loop_state
        memory = context.memory
        decision_artifact = persist_artifact(
            RunArtifact(
                run_id=session.run.run_id,
                artifact_type="decision",
                title=decision.decision_id or "decision",
                content=decision.model_dump(mode="json"),
            )
        )
        loop_state.artifacts.append(decision_artifact)
        for action in decision.actions:
            self._policy.validate_action(session=session, action=action)
            self._executor.append_step(
                run=session.run,
                step_type="action",
                name=action.title or action.action_id or action.kind,
                input=action.inputs,
                output={"kind": action.kind, "summary": action.summary},
                summary=action.summary or f"Executing runtime action {action.action_id or action.kind}",
            )
            if action.kind == "respond":
                loop_state.applied_actions.append(action.action_id or action.title or "respond")
                loop_state.response_messages.append(action.prompt or action.summary or session.request.objective)
                self._memory_manager.record_response(memory=memory, content=loop_state.response_messages[-1])
                continue
            if action.kind == "tool_call":
                result_set = self._executor.execute_tool_calls(
                    run=session.run,
                    calls=[
                        ToolCall(
                            call_id=f"{session.run.run_id}:{action.action_id or action.tool_id or 'tool'}",
                            run_id=session.run.run_id,
                            tool_id=action.tool_id,
                            partition=session.request.partition or session.run.partition,
                            inputs=action.inputs,
                            metadata=action.metadata,
                        )
                    ],
                )
                loop_state.tool_results.extend(result_set)
                if result_set:
                    self._memory_manager.record_tool_result(
                        memory=memory,
                        tool_id=action.tool_id,
                        output=result_set[-1].output,
                    )
                if result_set and not result_set[-1].ok:
                    loop_state.failure_messages.append(result_set[-1].error_message)
                loop_state.applied_actions.append(action.action_id or action.tool_id or "tool_call")
                continue
            if action.kind == "skill_call":
                result_set = self._executor.execute_invocations(
                    run=session.run,
                    invocations=[
                        SkillInvocation(
                            invocation_id=f"{session.run.run_id}:{action.action_id or action.skill_id or 'skill'}",
                            skill_id=action.skill_id,
                            partition=session.request.partition or session.run.partition,
                            inputs=action.inputs,
                            metadata=action.metadata,
                        )
                    ],
                )
                loop_state.skill_results.extend(result_set)
                if result_set:
                    self._memory_manager.record_skill_result(
                        memory=memory,
                        skill_id=action.skill_id,
                        output=result_set[-1].output,
                    )
                if result_set and not result_set[-1].ok:
                    loop_state.failure_messages.append(result_set[-1].error_message)
                loop_state.applied_actions.append(action.action_id or action.skill_id or "skill_call")
                continue
            loop_state.applied_actions.append(action.action_id or action.kind)

