"""Decision-generator contracts and normalization helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from internal.models import AgentRun
from internal.runtime.contracts import RuntimeAction, RuntimeDecision, RuntimeRunRequest, RuntimeTurnInput
from internal.runtime.core.state import RuntimeRunState
from internal.runtime.llm.decision_parser import DefaultRuntimeDecisionParser, RuntimeDecisionParserPort
from internal.runtime.llm.prompt_builder import DefaultRuntimePromptBuilder, RuntimePromptBuilderPort
from internal.runtime.loop.planner_components import RuntimePlannerContext, RuntimePlannerStopAssessment
from internal.runtime.providers.openai_runtime_adapter import (
    DefaultRuntimeModelAdapter,
    RuntimeModelAdapterPort,
)
from internal.runtime.trace.recorder import RuntimeTraceRecorder
from internal.utils.logger import get_logger


logger = get_logger("knowbase.runtime.llm.decisioning")


RuntimeDecisionDraftStopReason = Literal[
    "completed",
    "no_action",
    "budget_exhausted",
    "requires_review",
    "waiting_for_observation",
    "unknown",
]

RuntimeDecisionDraftReviewReason = Literal[
    "unsafe_action",
    "insufficient_context",
    "policy_boundary",
    "manual_confirmation",
    "unknown",
]

RuntimeProposedActionKind = Literal["tool_call", "skill_call", "respond", "stop"]


@dataclass(slots=True)
class RuntimeDecisionConstraints:
    """Output constraints applied before a planner decision is accepted."""

    max_actions: int = 4
    allow_mixed_capabilities: bool = True
    allow_respond_action: bool = True
    allow_empty_continue: bool = False


@dataclass(slots=True)
class RuntimeProposedAction:
    """Generator-facing action draft before normalization into RuntimeAction."""

    kind: RuntimeProposedActionKind
    title: str = ""
    summary: str = ""
    target_ref: str = ""
    tool_id: str = ""
    skill_id: str = ""
    prompt: str = ""
    inputs: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    risk_level: str = "medium"
    requires_review: bool = False
    action_id: str = ""


@dataclass(slots=True)
class RuntimeDecisionDraft:
    """Generator-facing decision draft before runtime normalization."""

    reasoning_summary: str = ""
    action_plan_summary: str = ""
    actions: list[RuntimeProposedAction] = field(default_factory=list)
    should_stop: bool = False
    stop_reason: RuntimeDecisionDraftStopReason = "unknown"
    requires_review: bool = False
    review_reason: RuntimeDecisionDraftReviewReason = "unknown"
    notes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class RuntimeDecisionGeneratorPort(Protocol):
    """Generate one runtime decision from the planner context."""

    def generate(
        self,
        *,
        run: AgentRun,
        request: RuntimeRunRequest,
        state: RuntimeRunState,
        turn_input: RuntimeTurnInput,
        planner_context: RuntimePlannerContext,
        stop_assessment: RuntimePlannerStopAssessment,
    ) -> RuntimeDecision:
        ...


class DefaultRuntimeDecisionGenerator:
    """Generate one runtime decision through prompt, model, parser, and normalizer."""

    def __init__(
        self,
        *,
        normalizer: RuntimeDecisionNormalizer | None = None,
        prompt_builder: RuntimePromptBuilderPort | None = None,
        model_adapter: RuntimeModelAdapterPort | None = None,
        decision_parser: RuntimeDecisionParserPort | None = None,
        trace_recorder: RuntimeTraceRecorder | None = None,
    ):
        self._normalizer = normalizer or RuntimeDecisionNormalizer()
        self._prompt_builder = prompt_builder or DefaultRuntimePromptBuilder(
            model=str(os.getenv("CIAGENT_LEAD_AGENT_MODEL") or "gpt-4o-mini"),
            temperature=float(str(os.getenv("CIAGENT_LEAD_AGENT_TEMPERATURE") or "0.0") or "0.0"),
            max_output_tokens=int(str(os.getenv("CIAGENT_LEAD_AGENT_MAX_OUTPUT_TOKENS") or "1200") or "1200"),
        )
        self._model_adapter = model_adapter or DefaultRuntimeModelAdapter.from_env()
        self._decision_parser = decision_parser or DefaultRuntimeDecisionParser()
        self._trace_recorder = trace_recorder

    def generate(
        self,
        *,
        run: AgentRun,
        request: RuntimeRunRequest,
        state: RuntimeRunState,
        turn_input: RuntimeTurnInput,
        planner_context: RuntimePlannerContext,
        stop_assessment: RuntimePlannerStopAssessment,
    ) -> RuntimeDecision:
        del request, state
        logger.debug(
            "Generating runtime decision.",
            extra={
                "run_id": run.run_id,
                "turn_index": turn_input.turn_index,
                "allowed_tools": planner_context.allowed_tools,
                "allowed_skills": planner_context.allowed_skills,
                "remaining_step_budget": planner_context.remaining_step_budget,
                "remaining_tool_budget": planner_context.remaining_tool_budget,
                "remaining_skill_budget": planner_context.remaining_skill_budget,
            },
        )
        if self._trace_recorder is not None:
            self._trace_recorder.record_planner_context(
                run=run,
                turn_index=turn_input.turn_index,
                planner_context=self._serialize_planner_context(planner_context=planner_context),
            )
        if stop_assessment.should_stop:
            logger.warning(
                "Stop assessment requested immediate stop.",
                extra={
                    "run_id": run.run_id,
                    "turn_index": turn_input.turn_index,
                    "reason": stop_assessment.reason,
                    "requires_review": stop_assessment.requires_review,
                },
            )
            return self._build_stop_decision(
                run=run,
                turn_input=turn_input,
                stop_assessment=stop_assessment,
            )
        prompt = self._prompt_builder.build_prompt(planner_context=planner_context)
        logger.debug(
            "Prompt built for runtime decision.",
            extra={
                "run_id": run.run_id,
                "turn_index": turn_input.turn_index,
                "model": prompt.model,
            },
        )
        if self._trace_recorder is not None:
            self._trace_recorder.record_llm_prompt(
                run=run,
                turn_index=turn_input.turn_index,
                prompt_payload=self._serialize_prompt(prompt=prompt),
            )
        response = self._model_adapter.invoke(prompt=prompt)
        logger.info(
            "Model response received for runtime decision.",
            extra={
                "run_id": run.run_id,
                "turn_index": turn_input.turn_index,
                "model_name": response.model_name,
                "finish_reason": response.finish_reason,
            },
        )
        if self._trace_recorder is not None:
            self._trace_recorder.record_llm_response(
                run=run,
                turn_index=turn_input.turn_index,
                response_payload=self._serialize_model_response(response=response),
            )
        draft = self._decision_parser.parse(prompt=prompt, payload=response.payload)
        draft.metadata = {
            "model_name": response.model_name,
            "finish_reason": response.finish_reason,
            "usage": dict(response.usage),
            "provider_metadata": dict(response.provider_metadata),
            **dict(draft.metadata),
        }
        logger.debug(
            "Runtime decision draft parsed.",
            extra={
                "run_id": run.run_id,
                "turn_index": turn_input.turn_index,
                "draft_action_count": len(draft.actions),
                "draft_should_stop": draft.should_stop,
                "draft_requires_review": draft.requires_review,
            },
        )
        return self._normalizer.build(
            run=run,
            turn_input=turn_input,
            draft=draft,
        )

    @staticmethod
    def _serialize_planner_context(*, planner_context: RuntimePlannerContext) -> dict[str, Any]:
        return {
            "run_id": planner_context.run_id,
            "request_id": planner_context.request_id,
            "turn_index": planner_context.turn_index,
            "objective": planner_context.objective,
            "prompt": planner_context.prompt,
            "partition": planner_context.partition,
            "source_type": planner_context.source_type,
            "source_ref": planner_context.source_ref,
            "task_payload": dict(planner_context.task_payload),
            "facts": dict(planner_context.facts),
            "observations": list(planner_context.observations),
            "completed_actions": list(planner_context.completed_actions),
            "recent_decisions": list(planner_context.recent_decisions),
            "recent_failures": list(planner_context.recent_failures),
            "latest_response": planner_context.latest_response,
            "allowed_tools": list(planner_context.allowed_tools),
            "allowed_skills": list(planner_context.allowed_skills),
            "risk_level": planner_context.risk_level,
            "requires_review": planner_context.requires_review,
            "remaining_step_budget": planner_context.remaining_step_budget,
            "remaining_tool_budget": planner_context.remaining_tool_budget,
            "remaining_skill_budget": planner_context.remaining_skill_budget,
            "hinted_actions": list(planner_context.hinted_actions),
            "hint_metadata": dict(planner_context.hint_metadata),
        }

    @staticmethod
    def _serialize_prompt(*, prompt) -> dict[str, Any]:
        return {
            "model": prompt.model,
            "system": prompt.system,
            "instruction": prompt.instruction,
            "response_schema": dict(prompt.response_schema),
            "temperature": prompt.temperature,
            "max_output_tokens": prompt.max_output_tokens,
            "context": dict(prompt.context),
        }

    @staticmethod
    def _serialize_model_response(*, response) -> dict[str, Any]:
        return {
            "payload": dict(response.payload),
            "raw_text": response.raw_text,
            "model_name": response.model_name,
            "finish_reason": response.finish_reason,
            "usage": dict(response.usage),
            "provider_metadata": dict(response.provider_metadata),
        }

    def _build_stop_decision(
        self,
        *,
        run: AgentRun,
        turn_input: RuntimeTurnInput,
        stop_assessment: RuntimePlannerStopAssessment,
    ) -> RuntimeDecision:
        stop_reason: RuntimeDecisionDraftStopReason = "completed"
        reason_text = (stop_assessment.reason or "").lower()
        if "budget" in reason_text:
            stop_reason = "budget_exhausted"
        elif stop_assessment.requires_review:
            stop_reason = "requires_review"
        return self._normalizer.build(
            run=run,
            turn_input=turn_input,
            draft=RuntimeDecisionDraft(
                reasoning_summary=stop_assessment.reason or "planner requested stop",
                action_plan_summary="No further actions will be executed.",
                actions=[],
                should_stop=True,
                stop_reason=stop_reason,
                requires_review=stop_assessment.requires_review,
                review_reason="unknown",
                notes=[stop_assessment.reason] if stop_assessment.reason else [],
                metadata={"source": "stop_evaluator"},
            ),
        )


class RuntimeDecisionNormalizer:
    """Normalize and validate decision drafts before runtime execution."""

    def __init__(self, *, constraints: RuntimeDecisionConstraints | None = None):
        self._constraints = constraints or RuntimeDecisionConstraints()

    def build(
        self,
        *,
        run: AgentRun,
        turn_input: RuntimeTurnInput,
        draft: RuntimeDecisionDraft,
    ) -> RuntimeDecision:
        actions = self._normalize_actions(run=run, turn_input=turn_input, draft=draft)
        should_stop = draft.should_stop
        if not actions and not should_stop and not self._constraints.allow_empty_continue:
            should_stop = True
        metadata = {
            "turn_index": turn_input.turn_index,
            "stop_reason": draft.stop_reason,
            "review_reason": draft.review_reason,
            "action_plan_summary": draft.action_plan_summary,
            "notes": list(draft.notes),
            **dict(draft.metadata),
        }
        return RuntimeDecision(
            decision_id=f"{run.run_id}:decision:{turn_input.turn_index}",
            objective=turn_input.task.objective,
            reasoning_summary=draft.reasoning_summary or "planner produced a decision",
            actions=actions,
            should_stop=should_stop,
            requires_review=draft.requires_review,
            metadata=metadata,
        )

    def _normalize_actions(
        self,
        *,
        run: AgentRun,
        turn_input: RuntimeTurnInput,
        draft: RuntimeDecisionDraft,
    ) -> list[RuntimeAction]:
        proposed = list(draft.actions[: self._constraints.max_actions])
        kinds = {item.kind for item in proposed if item.kind in {"tool_call", "skill_call"}}
        if not self._constraints.allow_mixed_capabilities and len(kinds) > 1:
            raise ValueError("runtime decision draft mixes tool_call and skill_call actions")

        actions: list[RuntimeAction] = []
        for index, item in enumerate(proposed):
            self._validate_proposed_action(item)
            actions.append(
                RuntimeAction(
                    action_id=item.action_id or f"{run.run_id}:action:{turn_input.turn_index}:{index}",
                    kind=item.kind,
                    title=item.title,
                    summary=item.summary,
                    tool_id=item.tool_id,
                    skill_id=item.skill_id,
                    prompt=item.prompt,
                    inputs=dict(item.inputs),
                    metadata={"target_ref": item.target_ref, **dict(item.metadata)},
                    risk_level=item.risk_level,
                    requires_review=item.requires_review,
                )
            )
        return actions

    def _validate_proposed_action(self, item: RuntimeProposedAction) -> None:
        if not item.summary.strip():
            raise ValueError("runtime proposed action missing summary")
        if item.kind == "respond":
            if not self._constraints.allow_respond_action:
                raise ValueError("runtime decision draft includes forbidden respond action")
            if not item.prompt.strip():
                raise ValueError("runtime respond action missing prompt")
            return
        if item.kind == "tool_call":
            if not item.tool_id.strip():
                raise ValueError("runtime tool_call action missing tool_id")
            return
        if item.kind == "skill_call":
            if not item.skill_id.strip():
                raise ValueError("runtime skill_call action missing skill_id")
            return
        if item.kind == "stop":
            return
        raise ValueError(f"unsupported runtime proposed action kind: {item.kind}")


__all__ = [
    "RuntimeDecisionConstraints",
    "RuntimeProposedActionKind",
    "RuntimeProposedAction",
    "RuntimeDecisionDraft",
    "RuntimeDecisionGeneratorPort",
    "DefaultRuntimeDecisionGenerator",
    "RuntimeDecisionNormalizer",
]
