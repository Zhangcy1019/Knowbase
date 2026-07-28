"""Decision-generator contracts and normalization helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from internal.models import AgentRun
from internal.runtime.contracts import RuntimeAction, RuntimeDecision, RuntimeRunRequest, RuntimeTurnInput
from internal.runtime.memory.state import RuntimeRunState
from internal.runtime.llm.decision_parser import DefaultRuntimeDecisionParser, RuntimeDecisionParserPort
from internal.runtime.llm.prompt_builder import DefaultRuntimePromptBuilder, RuntimePromptBuilderPort
from internal.runtime.loop.planner_components import RuntimePlannerContext, RuntimePlannerStopAssessment
from internal.runtime.llm.model_adapter import (
    DefaultRuntimeModelAdapter,
    RuntimeModelAdapterPort,
)
from internal.runtime.trace.recorder import RuntimeTraceRecorder
from internal.utils.config import LLMRuntimeConfig
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

@dataclass(slots=True)
class RuntimeDecisionConstraints:
    """Output constraints applied before a planner decision is accepted."""

    max_actions: int = 4
    allow_mixed_capabilities: bool = True
    allow_empty_continue: bool = False


@dataclass(slots=True)
class RuntimeProposedAction:
    """Generator-facing action draft before normalization into RuntimeAction."""

    capability_id: str = ""
    title: str = ""
    summary: str = ""
    target_ref: str = ""
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
        llm_config: LLMRuntimeConfig | None = None,
    ):
        self._normalizer = normalizer or RuntimeDecisionNormalizer()
        self._prompt_builder = prompt_builder or DefaultRuntimePromptBuilder(
            model=(llm_config.model if llm_config is not None else "gpt-4o-mini"),
            temperature=(llm_config.temperature if llm_config is not None else 0.0),
            max_output_tokens=(llm_config.max_output_tokens if llm_config is not None else 1200),
        )
        self._model_adapter = model_adapter or DefaultRuntimeModelAdapter.from_llm_config(llm_config)
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
        logger.debug(
            "Runtime model raw response payload.",
            extra={
                "run_id": run.run_id,
                "turn_index": turn_input.turn_index,
                "model_name": response.model_name,
                "finish_reason": response.finish_reason,
                "raw_text": response.raw_text,
                "payload": response.payload,
                "usage": response.usage,
                "provider_metadata": response.provider_metadata,
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
            "mission_summary": planner_context.mission_summary,
            "instructions": list(planner_context.instructions),
            "partition": planner_context.partition,
            "source_type": planner_context.source_type,
            "source_ref": planner_context.source_ref,
            "input_context": dict(planner_context.input_context),
            "acceptance": dict(planner_context.acceptance),
            "stop_policy": dict(planner_context.stop_policy),
            "risk_policy": dict(planner_context.risk_policy),
            "facts": dict(planner_context.facts),
            "observations": list(planner_context.observations),
            "completed_actions": list(planner_context.completed_actions),
            "recent_decisions": list(planner_context.recent_decisions),
            "recent_failures": list(planner_context.recent_failures),
            "latest_response": planner_context.latest_response,
            "allowed_tools": list(planner_context.allowed_tools),
            "allowed_skills": list(planner_context.allowed_skills),
            "available_tool_specs": list(planner_context.available_tool_specs),
            "available_skill_specs": list(planner_context.available_skill_specs),
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
        contract_error = self._validate_output_contract(
            turn_input=turn_input,
            should_stop=should_stop,
            metadata=metadata,
        )
        requires_review = draft.requires_review
        if contract_error:
            requires_review = True
            metadata["output_contract_error"] = contract_error
        return RuntimeDecision(
            decision_id=f"{run.run_id}:decision:{turn_input.turn_index}",
            objective=turn_input.task.objective,
            reasoning_summary=draft.reasoning_summary or "planner produced a decision",
            actions=actions,
            should_stop=should_stop,
            requires_review=requires_review,
            metadata=metadata,
        )

    @staticmethod
    def _validate_output_contract(
        *,
        turn_input: RuntimeTurnInput,
        should_stop: bool,
        metadata: dict[str, Any],
    ) -> str:
        if not should_stop:
            return ""
        contract = dict(turn_input.task.output_contract)
        required_metadata = contract.get("required_metadata", [])
        if not isinstance(required_metadata, list):
            return "output contract required_metadata must be a list"
        for key in required_metadata:
            if not isinstance(key, str) or not isinstance(metadata.get(key), dict):
                return f"missing required metadata object: {key}"
        return ""

    def _normalize_actions(
        self,
        *,
        run: AgentRun,
        turn_input: RuntimeTurnInput,
        draft: RuntimeDecisionDraft,
    ) -> list[RuntimeAction]:
        proposed = list(draft.actions[: self._constraints.max_actions])
        actions: list[RuntimeAction] = []
        for index, item in enumerate(proposed):
            normalized_item = self._normalize_proposed_action(item, turn_input=turn_input)
            self._validate_proposed_action(normalized_item)
            actions.append(
                RuntimeAction(
                    action_id=normalized_item.action_id or f"{run.run_id}:action:{turn_input.turn_index}:{index}",
                    title=normalized_item.title,
                    summary=normalized_item.summary,
                    capability_id=normalized_item.capability_id,
                    prompt=normalized_item.prompt,
                    inputs=dict(normalized_item.inputs),
                    metadata={"target_ref": normalized_item.target_ref, **dict(normalized_item.metadata)},
                    risk_level=normalized_item.risk_level,
                    requires_review=normalized_item.requires_review,
                )
            )
        return actions

    def _normalize_proposed_action(
        self,
        item: RuntimeProposedAction,
        *,
        turn_input: RuntimeTurnInput,
    ) -> RuntimeProposedAction:
        title = item.title.strip()
        summary = item.summary.strip()
        capability_id = item.capability_id.strip()
        target_ref = item.target_ref.strip()
        normalized_inputs = dict(item.inputs)

        capability_type = self._resolve_capability_type(
            capability_id=capability_id,
            turn_input=turn_input,
        )
        if capability_type == "skill" and capability_id and not normalized_inputs:
            normalized_inputs = self._hydrate_inputs_from_bindings(
                capability_id=capability_id,
                capability_type="skill",
                turn_input=turn_input,
            )
        elif capability_type == "tool" and capability_id and not normalized_inputs:
            normalized_inputs = self._hydrate_inputs_from_bindings(
                capability_id=capability_id,
                capability_type="tool",
                turn_input=turn_input,
            )

        if not title:
            if capability_id:
                title = f"Invoke {capability_id}"
            else:
                title = "Invoke capability"
        if not summary:
            if capability_id:
                summary = f"Invoke {capability_id}."
            else:
                summary = "Invoke capability."
        if not target_ref:
            target_ref = str(
                normalized_inputs.get("file_path")
                or normalized_inputs.get("case_id")
                or normalized_inputs.get("partition")
                or ""
            )

        return RuntimeProposedAction(
            capability_id=capability_id,
            title=title,
            summary=summary,
            target_ref=target_ref,
            prompt=item.prompt,
            inputs=normalized_inputs,
            metadata=dict(item.metadata),
            risk_level=item.risk_level or "medium",
            requires_review=item.requires_review,
            action_id=item.action_id,
        )

    def _hydrate_inputs_from_bindings(
        self,
        *,
        capability_id: str,
        capability_type: str,
        turn_input: RuntimeTurnInput,
    ) -> dict[str, object]:
        specs = (
            turn_input.bounds.available_skill_specs
            if capability_type == "skill"
            else turn_input.bounds.available_tool_specs
        )
        matching_spec = None
        id_key = "skill_id" if capability_type == "skill" else "tool_id"
        for spec in specs:
            if getattr(spec, id_key, "") == capability_id:
                matching_spec = spec
                break
        if matching_spec is None:
            return {}

        bindings = dict(getattr(matching_spec, "argument_binding_hints", {}) or {})
        hydrated: dict[str, object] = {}
        for input_name, binding in bindings.items():
            value = self._resolve_binding_value(binding=binding, turn_input=turn_input)
            if value is not None:
                hydrated[input_name] = value
        return hydrated

    @staticmethod
    def _resolve_binding_value(*, binding: str, turn_input: RuntimeTurnInput) -> object | None:
        normalized = str(binding or "").strip()
        if not normalized:
            return None
        if normalized.startswith("input_context."):
            key = normalized.split(".", 1)[1].strip()
            return turn_input.task.input_context.get(key)
        if normalized.startswith("memory.facts."):
            key = normalized.split(".", 2)[2].strip()
            return turn_input.memory.facts.get(key)
        if normalized == "partition":
            return turn_input.task.partition
        return None

    def _validate_proposed_action(self, item: RuntimeProposedAction) -> None:
        if not item.capability_id.strip():
            raise ValueError("runtime action missing capability_id")
        if not item.inputs:
            raise ValueError("runtime action missing inputs")

    @staticmethod
    def _resolve_capability_type(*, capability_id: str, turn_input: RuntimeTurnInput) -> str:
        if capability_id in {spec.skill_id for spec in turn_input.bounds.available_skill_specs if spec.skill_id}:
            return "skill"
        if capability_id in {spec.tool_id for spec in turn_input.bounds.available_tool_specs if spec.tool_id}:
            return "tool"
        return ""


__all__ = [
    "RuntimeDecisionConstraints",
    "RuntimeProposedActionKind",
    "RuntimeProposedAction",
    "RuntimeDecisionDraft",
    "RuntimeDecisionGeneratorPort",
    "DefaultRuntimeDecisionGenerator",
    "RuntimeDecisionNormalizer",
]
