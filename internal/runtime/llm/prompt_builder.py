"""Prompt-building contracts for runtime decision generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from internal.runtime.llm.decision_parser import build_runtime_decision_payload_schema
from internal.runtime.loop.planner_components import RuntimePlannerContext


@dataclass(slots=True)
class RuntimeDecisionPrompt:
    """Structured prompt payload handed to a future model adapter."""

    model: str = ""
    system: str = ""
    instruction: str = ""
    response_schema: dict[str, Any] = field(default_factory=dict)
    temperature: float = 0.0
    max_output_tokens: int = 1200
    context: dict[str, Any] = field(default_factory=dict)


class RuntimePromptBuilderPort(Protocol):
    """Build a model-facing prompt from the planner context."""

    def build_prompt(self, *, planner_context: RuntimePlannerContext) -> RuntimeDecisionPrompt:
        ...


class DefaultRuntimePromptBuilder:
    """Current prompt builder that emits a structured placeholder payload."""

    def __init__(self, *, model: str = "gpt-4o-mini", temperature: float = 0.0, max_output_tokens: int = 1200):
        self._model = model.strip() or "gpt-4o-mini"
        self._temperature = temperature
        self._max_output_tokens = max(1, int(max_output_tokens))

    def build_prompt(self, *, planner_context: RuntimePlannerContext) -> RuntimeDecisionPrompt:
        context_payload = {
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
            "allowed_verification_tools": list(planner_context.allowed_verification_tools),
            "allowed_verification_skills": list(planner_context.allowed_verification_skills),
            "available_tool_specs": list(planner_context.available_tool_specs),
            "available_skill_specs": list(planner_context.available_skill_specs),
            "available_verification_tool_specs": list(planner_context.available_verification_tool_specs),
            "available_verification_skill_specs": list(planner_context.available_verification_skill_specs),
            "risk_level": planner_context.risk_level,
            "requires_review": planner_context.requires_review,
            "remaining_step_budget": planner_context.remaining_step_budget,
            "remaining_tool_budget": planner_context.remaining_tool_budget,
            "remaining_skill_budget": planner_context.remaining_skill_budget,
            "hinted_actions": list(planner_context.hinted_actions),
            "hint_metadata": dict(planner_context.hint_metadata),
        }
        digest_payload = self._build_digest_payload(planner_context=planner_context)
        response_schema = build_runtime_decision_payload_schema()
        return RuntimeDecisionPrompt(
            model=self._model,
            system=(
                "You are a knowbase runtime planning agent. "
                "Return exactly one JSON object that matches the provided schema. "
                "Choose only actions that are explicitly allowed by the planner context budgets and whitelists."
            ),
            instruction=self._build_instruction(digest_payload=digest_payload),
            response_schema=response_schema,
            temperature=self._temperature,
            max_output_tokens=self._max_output_tokens,
            context=context_payload,
        )

    def _build_instruction(self, *, digest_payload: dict[str, Any]) -> str:
        if digest_payload["runtime_mode"] == "analysis_only":
            return self._build_analysis_only_instruction(digest_payload=digest_payload)

        lines = [
            "Inspect the runtime planner digest and produce the next runtime decision.",
            "",
            "Rules:",
            "- Prefer the smallest safe next step.",
            "- Do not invent capability_id outside the allowed lists.",
            "- When invoking a capability, satisfy every required input field from its schema.",
            "- Reuse concrete values from input_context whenever a capability input clearly maps to them.",
            "- If no safe action is available, set should_stop=true.",
            "- Keep reasoning_summary and action_plan_summary concise.",
            "- Do not emit summary-only, respond, or stop actions.",
            "- Return JSON only.",
            "",
            "RuntimeDigest:",
            f"Objective: {digest_payload['objective']}",
            f"Mission: {digest_payload['mission_summary']}",
            f"Mode: {digest_payload['runtime_mode']}",
            f"Partition: {digest_payload['partition'] or '--'}",
            f"Source: {digest_payload['source_type']} / {digest_payload['source_ref'] or '--'}",
            "",
            "Bounds:",
            f"- allowed_tools: {self._join_items(digest_payload['allowed_tools'])}",
            f"- allowed_skills: {self._join_items(digest_payload['allowed_skills'])}",
            f"- remaining_steps: {digest_payload['remaining_step_budget']}",
            f"- remaining_tool_calls: {digest_payload['remaining_tool_budget']}",
            f"- remaining_skill_calls: {digest_payload['remaining_skill_budget']}",
            f"- risk_level: {digest_payload['risk_level']}",
            f"- requires_review: {self._format_bool(digest_payload['requires_review'])}",
            "",
            "Available Tools:",
            *[f"- {item}" for item in digest_payload["tool_spec_summary"]],
            "",
            "Available Skills:",
            *[f"- {item}" for item in digest_payload["skill_spec_summary"]],
            "",
            "Input Context:",
            *[f"- {item}" for item in digest_payload["input_context_summary"]],
            "",
            "Acceptance:",
            *[f"- {item}" for item in digest_payload["acceptance_summary"]],
            "",
            "Stop Policy:",
            *[f"- {item}" for item in digest_payload["stop_policy_summary"]],
            "",
            "Task Summary:",
            *[f"- {item}" for item in digest_payload["task_summary"]],
            "",
            "Top Candidates:",
            *[f"- {item}" for item in digest_payload["candidate_summary"]],
            "",
            "Recent Progress:",
            *[f"- {item}" for item in digest_payload["progress_summary"]],
            "",
            "Recent Failures:",
            *[f"- {item}" for item in digest_payload["failure_summary"]],
            "",
            "Hints:",
            *[f"- {item}" for item in digest_payload["hint_summary"]],
        ]
        return "\n".join(lines)

    def _build_analysis_only_instruction(self, *, digest_payload: dict[str, Any]) -> str:
        lines = [
            "Inspect the runtime planner digest and produce the next runtime decision.",
            "",
            "Execution mode:",
            "- analysis_only",
            "",
            "Hard constraints:",
            "- No executable capability actions are allowed.",
            "- Do not invent capability_id outside the allowed lists.",
            "- Any future executable action must satisfy all required capability inputs.",
            "- Do not emit summary-only, respond, or stop actions.",
            "- If no executable action exists, set should_stop=true.",
            "- Keep reasoning_summary and action_plan_summary concise.",
            "- Return JSON only.",
            "",
            "Decision expectation:",
            "- Decide whether this batch needs follow-up work in a non-analysis runtime.",
            "- Use reasoning_summary and action_plan_summary to summarize what matters.",
            "- Do not propose non-executable actions in this mode.",
            "",
            "RuntimeDigest:",
            f"Objective: {digest_payload['objective']}",
            f"Mission: {digest_payload['mission_summary']}",
            f"Partition: {digest_payload['partition'] or '--'}",
            f"Source: {digest_payload['source_type']} / {digest_payload['source_ref'] or '--'}",
            "",
            "Bounds:",
            f"- remaining_steps: {digest_payload['remaining_step_budget']}",
            f"- remaining_tool_calls: {digest_payload['remaining_tool_budget']}",
            f"- remaining_skill_calls: {digest_payload['remaining_skill_budget']}",
            f"- risk_level: {digest_payload['risk_level']}",
            f"- requires_review: {self._format_bool(digest_payload['requires_review'])}",
            "",
            "Available capabilities:",
            *[f"- {item}" for item in digest_payload["capability_spec_summary"]],
            "",
            "Input context:",
            *[f"- {item}" for item in digest_payload["input_context_summary"]],
            "",
            "Acceptance:",
            *[f"- {item}" for item in digest_payload["acceptance_summary"]],
            "",
            "Stop policy:",
            *[f"- {item}" for item in digest_payload["stop_policy_summary"]],
            "",
            "Batch facts:",
            *[f"- {item}" for item in digest_payload["task_summary"]],
            "",
            "Potential follow-up work:",
            *[f"- {item}" for item in digest_payload["candidate_summary"]],
            "",
            "Recent progress:",
            *[f"- {item}" for item in digest_payload["progress_summary"]],
            "",
            "Recent failures:",
            *[f"- {item}" for item in digest_payload["failure_summary"]],
            "",
            "Hints:",
            *[f"- {item}" for item in digest_payload["hint_summary"]],
        ]
        return "\n".join(lines)

    def _build_digest_payload(self, *, planner_context: RuntimePlannerContext) -> dict[str, Any]:
        input_context = dict(planner_context.input_context)
        hint_metadata = dict(planner_context.hint_metadata)
        runtime_mode = str(hint_metadata.get("runtime_mode") or "default")
        batch_event_type_counts = input_context.get("batch_event_type_counts")
        if not isinstance(batch_event_type_counts, dict):
            batch_event_type_counts = {}
        candidates = self._extract_candidate_summaries(input_context=input_context)
        task_summary = self._extract_task_summary(input_context=input_context)
        progress_summary = self._extract_progress_summary(planner_context=planner_context)
        failure_summary = list(planner_context.recent_failures[:3]) or ["none"]
        hint_summary = self._extract_hint_summary(planner_context=planner_context)
        tool_spec_summary = self._extract_tool_spec_summary(planner_context=planner_context)
        skill_spec_summary = self._extract_skill_spec_summary(planner_context=planner_context)
        input_context_summary = self._extract_input_context_summary(planner_context=planner_context)
        acceptance_summary = self._extract_acceptance_summary(planner_context=planner_context)
        stop_policy_summary = self._extract_stop_policy_summary(planner_context=planner_context)
        return {
            "objective": planner_context.objective,
            "mission_summary": planner_context.mission_summary,
            "runtime_mode": runtime_mode,
            "partition": planner_context.partition,
            "source_type": planner_context.source_type,
            "source_ref": planner_context.source_ref,
            "allowed_tools": list(planner_context.allowed_tools),
            "allowed_skills": list(planner_context.allowed_skills),
            "allowed_verification_tools": list(planner_context.allowed_verification_tools),
            "allowed_verification_skills": list(planner_context.allowed_verification_skills),
            "remaining_step_budget": planner_context.remaining_step_budget,
            "remaining_tool_budget": planner_context.remaining_tool_budget,
            "remaining_skill_budget": planner_context.remaining_skill_budget,
            "risk_level": planner_context.risk_level,
            "requires_review": planner_context.requires_review,
            "task_summary": task_summary,
            "candidate_summary": candidates or ["none"],
            "progress_summary": progress_summary,
            "failure_summary": failure_summary,
            "hint_summary": hint_summary,
            "tool_spec_summary": tool_spec_summary or ["none"],
            "skill_spec_summary": skill_spec_summary or ["none"],
            "verification_tool_spec_summary": self._extract_verification_tool_spec_summary(planner_context=planner_context)
            or ["none"],
            "verification_skill_spec_summary": self._extract_verification_skill_spec_summary(planner_context=planner_context)
            or ["none"],
            "capability_spec_summary": [*tool_spec_summary, *skill_spec_summary] or ["none"],
            "input_context_summary": input_context_summary or ["none"],
            "acceptance_summary": acceptance_summary or ["none"],
            "stop_policy_summary": stop_policy_summary or ["none"],
            "event_type_counts": dict(batch_event_type_counts),
        }

    def _extract_task_summary(self, *, input_context: dict[str, Any]) -> list[str]:
        summary: list[str] = []
        batch_id = str(input_context.get("batch_id") or "")
        if batch_id:
            summary.append(f"batch_id={batch_id}")
        batch_summary = str(input_context.get("batch_summary") or "").strip()
        if batch_summary:
            summary.append(batch_summary)
        event_ids = input_context.get("batch_event_ids")
        if isinstance(event_ids, list):
            summary.append(f"event_count={len(event_ids)}")
        event_type_counts = input_context.get("batch_event_type_counts")
        if isinstance(event_type_counts, dict) and event_type_counts:
            counts_text = ", ".join(
                f"{key}={value}"
                for key, value in list(event_type_counts.items())[:5]
            )
            summary.append(f"event_types={counts_text}")
        resource_refs = input_context.get("batch_resource_refs")
        if isinstance(resource_refs, list) and resource_refs:
            summary.append(f"resources={', '.join(str(item) for item in resource_refs[:3])}")
        preparation = input_context.get("batch_preparation")
        if isinstance(preparation, dict):
            prep_summary = str(preparation.get("summary") or "").strip()
            if prep_summary:
                summary.append(prep_summary)
            candidate_count = preparation.get("candidates")
            if isinstance(candidate_count, list):
                summary.append(f"candidate_count={len(candidate_count)}")
            facet_assessment = preparation.get("facet_coverage_assessment")
            if isinstance(facet_assessment, dict):
                coverage_score = facet_assessment.get("coverage_score")
                if isinstance(coverage_score, (int, float)):
                    summary.append(f"coverage_score={coverage_score}")
                missing_signals = facet_assessment.get("missing_key_signals")
                if isinstance(missing_signals, list) and missing_signals:
                    summary.append(f"missing_signals={len(missing_signals)}")
        return summary or ["no task summary"]

    def _extract_candidate_summaries(self, *, input_context: dict[str, Any]) -> list[str]:
        preparation = input_context.get("batch_preparation")
        if not isinstance(preparation, dict):
            return []
        candidates = preparation.get("candidates")
        if not isinstance(candidates, list):
            return []
        result: list[str] = []
        for item in candidates[:5]:
            if not isinstance(item, dict):
                continue
            action_type = str(item.get("action_type") or "unknown")
            target_type = str(item.get("target_type") or "target")
            target_id = str(item.get("target_id") or "--")
            risk_level = str(item.get("risk_level") or "unknown")
            reason = str(item.get("reason") or "").strip()
            text = f"{action_type} on {target_type}:{target_id} (risk={risk_level})"
            if reason:
                text = f"{text} - {reason}"
            result.append(text)
        return result

    def _extract_progress_summary(self, *, planner_context: RuntimePlannerContext) -> list[str]:
        summary: list[str] = []
        if planner_context.completed_actions:
            summary.append(f"completed_actions={len(planner_context.completed_actions)}")
        if planner_context.recent_decisions:
            summary.extend(f"decision={item}" for item in planner_context.recent_decisions[:3])
        if planner_context.latest_response:
            summary.append(f"latest_response={planner_context.latest_response[:180]}")
        return summary or ["none"]

    def _extract_hint_summary(self, *, planner_context: RuntimePlannerContext) -> list[str]:
        summary: list[str] = []
        runtime_mode = str(planner_context.hint_metadata.get("runtime_mode") or "")
        for note in planner_context.hint_metadata.get("preparation_notes", [])[:3]:
            if isinstance(note, str) and note.strip():
                summary.append(note.strip())
        if planner_context.hinted_actions:
            summary.append(f"hinted_actions={len(planner_context.hinted_actions)}")
        return summary or ["none"]

    def _extract_input_context_summary(self, *, planner_context: RuntimePlannerContext) -> list[str]:
        summary: list[str] = []
        for key, value in list(planner_context.input_context.items())[:8]:
            if isinstance(value, list):
                rendered = "[" + ", ".join(str(item) for item in value[:3]) + "]"
            elif isinstance(value, dict):
                rendered = "{...}"
            else:
                rendered = str(value)
            summary.append(f"{key}={rendered}")
        return summary

    def _extract_acceptance_summary(self, *, planner_context: RuntimePlannerContext) -> list[str]:
        summary: list[str] = []
        completion_checks = planner_context.acceptance.get("completion_checks")
        if isinstance(completion_checks, list):
            for item in completion_checks[:6]:
                text = str(item).strip()
                if text:
                    summary.append(text)
        return summary

    def _extract_stop_policy_summary(self, *, planner_context: RuntimePlannerContext) -> list[str]:
        summary: list[str] = []
        for key, value in list(planner_context.stop_policy.items())[:6]:
            if isinstance(value, bool):
                rendered = "true" if value else "false"
            else:
                rendered = str(value)
            summary.append(f"{key}={rendered}")
        if planner_context.stop_policy.get("stop_when_acceptance_satisfied") is True:
            summary.append("Do not stop before the acceptance checks are actually satisfied.")
        return summary

    def _extract_tool_spec_summary(self, *, planner_context: RuntimePlannerContext) -> list[str]:
        summary: list[str] = []
        for item in planner_context.available_tool_specs:
            if not isinstance(item, dict):
                continue
            tool_id = str(item.get("tool_id") or "").strip()
            if not tool_id:
                continue
            title = str(item.get("title") or "").strip()
            description = str(item.get("description") or "").strip()
            input_schema = item.get("input_schema")
            schema_keys = self._schema_keys(input_schema)
            required_keys = self._schema_required_keys(input_schema)
            examples = item.get("examples")
            usage_notes = item.get("usage_notes")
            binding_hints = item.get("argument_binding_hints")
            text = tool_id
            if title:
                text = f"{text} ({title})"
            if description:
                text = f"{text}: {description}"
            if schema_keys:
                text = f"{text}; inputs={', '.join(schema_keys)}"
            if required_keys:
                text = f"{text}; required={', '.join(required_keys)}"
            merged_binding_hints = self._merge_binding_hints(
                explicit_hints=binding_hints,
                derived_hints=self._derive_input_binding_hints(
                    input_schema=input_schema,
                    input_context_keys=list(planner_context.input_context.keys()),
                ),
            )
            if merged_binding_hints:
                text = f"{text}; bindings={'; '.join(merged_binding_hints)}"
            example_summary = self._extract_example_summary(examples)
            if example_summary:
                text = f"{text}; example={example_summary}"
            note_summary = self._extract_usage_note_summary(usage_notes)
            if note_summary:
                text = f"{text}; notes={note_summary}"
            summary.append(text)
        return summary

    def _extract_skill_spec_summary(self, *, planner_context: RuntimePlannerContext) -> list[str]:
        summary: list[str] = []
        for item in planner_context.available_skill_specs:
            if not isinstance(item, dict):
                continue
            skill_id = str(item.get("skill_id") or "").strip()
            if not skill_id:
                continue
            title = str(item.get("title") or "").strip()
            description = str(item.get("description") or "").strip()
            execution_mode = str(item.get("execution_mode") or "").strip()
            side_effect_scope = str(item.get("side_effect_scope") or "").strip()
            input_schema = item.get("input_schema")
            schema_keys = self._schema_keys(input_schema)
            required_keys = self._schema_required_keys(input_schema)
            examples = item.get("examples")
            usage_notes = item.get("usage_notes")
            binding_hints = item.get("argument_binding_hints")
            text = skill_id
            if title:
                text = f"{text} ({title})"
            if description:
                text = f"{text}: {description}"
            traits: list[str] = []
            if execution_mode:
                traits.append(f"mode={execution_mode}")
            if side_effect_scope:
                traits.append(f"scope={side_effect_scope}")
            if schema_keys:
                traits.append(f"inputs={', '.join(schema_keys)}")
            if required_keys:
                traits.append(f"required={', '.join(required_keys)}")
            merged_binding_hints = self._merge_binding_hints(
                explicit_hints=binding_hints,
                derived_hints=self._derive_input_binding_hints(
                    input_schema=input_schema,
                    input_context_keys=list(planner_context.input_context.keys()),
                ),
            )
            if merged_binding_hints:
                traits.append(f"bindings={'; '.join(merged_binding_hints)}")
            example_summary = self._extract_example_summary(examples)
            if example_summary:
                traits.append(f"example={example_summary}")
            note_summary = self._extract_usage_note_summary(usage_notes)
            if note_summary:
                traits.append(f"notes={note_summary}")
            if traits:
                text = f"{text}; {'; '.join(traits)}"
            summary.append(text)
        return summary

    def _extract_verification_tool_spec_summary(self, *, planner_context: RuntimePlannerContext) -> list[str]:
        return self._extract_spec_summary(
            specs=planner_context.available_verification_tool_specs,
            input_context_keys=list(planner_context.input_context.keys()),
            id_key="tool_id",
        )

    def _extract_verification_skill_spec_summary(self, *, planner_context: RuntimePlannerContext) -> list[str]:
        return self._extract_spec_summary(
            specs=planner_context.available_verification_skill_specs,
            input_context_keys=list(planner_context.input_context.keys()),
            id_key="skill_id",
        )

    def _extract_spec_summary(
        self,
        *,
        specs: list[dict[str, Any]],
        input_context_keys: list[str],
        id_key: str,
    ) -> list[str]:
        summary: list[str] = []
        for item in specs:
            if not isinstance(item, dict):
                continue
            capability_id = str(item.get(id_key) or "").strip()
            if not capability_id:
                continue
            title = str(item.get("title") or "").strip()
            description = str(item.get("description") or "").strip()
            input_schema = item.get("input_schema")
            schema_keys = self._schema_keys(input_schema)
            required_keys = self._schema_required_keys(input_schema)
            examples = item.get("examples")
            usage_notes = item.get("usage_notes")
            binding_hints = item.get("argument_binding_hints")
            text = capability_id
            if title:
                text = f"{text} ({title})"
            if description:
                text = f"{text}: {description}"
            if schema_keys:
                text = f"{text}; inputs={', '.join(schema_keys)}"
            if required_keys:
                text = f"{text}; required={', '.join(required_keys)}"
            merged_binding_hints = self._merge_binding_hints(
                explicit_hints=binding_hints,
                derived_hints=self._derive_input_binding_hints(
                    input_schema=input_schema,
                    input_context_keys=input_context_keys,
                ),
            )
            if merged_binding_hints:
                text = f"{text}; bindings={'; '.join(merged_binding_hints)}"
            example_summary = self._extract_example_summary(examples)
            if example_summary:
                text = f"{text}; example={example_summary}"
            note_summary = self._extract_usage_note_summary(usage_notes)
            if note_summary:
                text = f"{text}; notes={note_summary}"
            summary.append(text)
        return summary

    @staticmethod
    def _schema_keys(schema: Any) -> list[str]:
        if not isinstance(schema, dict):
            return []
        properties = schema.get("properties")
        if isinstance(properties, dict) and properties:
            return [str(key) for key in list(properties.keys())[:8]]
        return []

    @staticmethod
    def _schema_required_keys(schema: Any) -> list[str]:
        if not isinstance(schema, dict):
            return []
        required = schema.get("required")
        if isinstance(required, list):
            return [str(key) for key in required[:8]]
        return []

    @staticmethod
    def _derive_input_binding_hints(*, input_schema: Any, input_context_keys: list[str]) -> list[str]:
        if not isinstance(input_schema, dict):
            return []
        properties = input_schema.get("properties")
        if not isinstance(properties, dict):
            return []
        input_context_key_set = {key for key in input_context_keys if key}
        hints: list[str] = []
        for key, payload in list(properties.items())[:8]:
            field_name = str(key)
            if field_name in input_context_key_set:
                hints.append(f"{field_name}<-input_context.{field_name}")
                continue
            if not isinstance(payload, dict):
                continue
            description = str(payload.get("description") or "").strip().lower()
            for context_key in input_context_key_set:
                lowered_context_key = context_key.lower()
                if lowered_context_key and lowered_context_key in description:
                    hints.append(f"{field_name}<-input_context.{context_key}")
                    break
        return hints

    @staticmethod
    def _merge_binding_hints(*, explicit_hints: Any, derived_hints: list[str]) -> list[str]:
        merged: list[str] = []
        if isinstance(explicit_hints, dict):
            for key, value in explicit_hints.items():
                key_text = str(key).strip()
                value_text = str(value).strip()
                if key_text and value_text:
                    merged.append(f"{key_text}<-{value_text}")
        for item in derived_hints:
            if item not in merged:
                merged.append(item)
        return merged[:8]

    @staticmethod
    def _extract_example_summary(examples: Any) -> str:
        if not isinstance(examples, list) or not examples:
            return ""
        first = examples[0]
        if not isinstance(first, dict):
            return ""
        inputs = first.get("inputs")
        if not isinstance(inputs, dict):
            return ""
        parts: list[str] = []
        for key, value in list(inputs.items())[:4]:
            if isinstance(value, list):
                rendered = "[" + ", ".join(str(item) for item in value[:3]) + "]"
            else:
                rendered = str(value)
            parts.append(f"{key}={rendered}")
        return ", ".join(parts)

    @staticmethod
    def _extract_usage_note_summary(notes: Any) -> str:
        if not isinstance(notes, list):
            return ""
        values = [str(item).strip() for item in notes if str(item).strip()]
        if not values:
            return ""
        return " | ".join(values[:2])

    @staticmethod
    def _join_items(items: list[str]) -> str:
        return ", ".join(item for item in items if item) or "none"

    @staticmethod
    def _format_bool(value: bool) -> str:
        return "yes" if value else "no"


__all__ = [
    "RuntimeDecisionPrompt",
    "RuntimePromptBuilderPort",
    "DefaultRuntimePromptBuilder",
]
