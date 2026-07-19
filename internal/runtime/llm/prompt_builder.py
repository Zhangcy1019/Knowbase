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
        lines = [
            "Inspect the runtime planner digest and produce the next runtime decision.",
            "",
            "Rules:",
            "- Prefer the smallest safe next step.",
            "- Do not invent tool_id or skill_id outside the allowed lists.",
            "- If no safe action is available, set should_stop=true.",
            "- Keep reasoning_summary and action_plan_summary concise.",
            "- Do not emit summary-only, respond, or stop actions.",
            "- Return JSON only.",
            "",
            "RuntimeDigest:",
            f"Objective: {digest_payload['objective']}",
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

    def _build_digest_payload(self, *, planner_context: RuntimePlannerContext) -> dict[str, Any]:
        task_payload = dict(planner_context.task_payload)
        hint_metadata = dict(planner_context.hint_metadata)
        runtime_mode = str(hint_metadata.get("runtime_mode") or "default")
        batch_event_type_counts = task_payload.get("batch_event_type_counts")
        if not isinstance(batch_event_type_counts, dict):
            batch_event_type_counts = {}
        candidates = self._extract_candidate_summaries(task_payload=task_payload)
        task_summary = self._extract_task_summary(task_payload=task_payload, planner_context=planner_context)
        progress_summary = self._extract_progress_summary(planner_context=planner_context)
        failure_summary = list(planner_context.recent_failures[:3]) or ["none"]
        hint_summary = self._extract_hint_summary(planner_context=planner_context)
        return {
            "objective": planner_context.objective,
            "runtime_mode": runtime_mode,
            "partition": planner_context.partition,
            "source_type": planner_context.source_type,
            "source_ref": planner_context.source_ref,
            "allowed_tools": list(planner_context.allowed_tools),
            "allowed_skills": list(planner_context.allowed_skills),
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
            "event_type_counts": dict(batch_event_type_counts),
        }

    def _extract_task_summary(self, *, task_payload: dict[str, Any], planner_context: RuntimePlannerContext) -> list[str]:
        summary: list[str] = []
        batch_id = str(task_payload.get("batch_id") or "")
        if batch_id:
            summary.append(f"batch_id={batch_id}")
        batch_summary = str(task_payload.get("batch_summary") or "").strip()
        if batch_summary:
            summary.append(batch_summary)
        event_ids = task_payload.get("batch_event_ids")
        if isinstance(event_ids, list):
            summary.append(f"event_count={len(event_ids)}")
        event_type_counts = task_payload.get("batch_event_type_counts")
        if isinstance(event_type_counts, dict) and event_type_counts:
            counts_text = ", ".join(
                f"{key}={value}"
                for key, value in list(event_type_counts.items())[:5]
            )
            summary.append(f"event_types={counts_text}")
        resource_refs = task_payload.get("batch_resource_refs")
        if isinstance(resource_refs, list) and resource_refs:
            summary.append(f"resources={', '.join(str(item) for item in resource_refs[:3])}")
        preparation = task_payload.get("batch_preparation")
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
        if planner_context.prompt.strip():
            summary.append(f"task_prompt={planner_context.prompt.strip().splitlines()[0]}")
        return summary or ["no task summary"]

    def _extract_candidate_summaries(self, *, task_payload: dict[str, Any]) -> list[str]:
        preparation = task_payload.get("batch_preparation")
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
        if runtime_mode:
            summary.append(f"runtime_mode={runtime_mode}")
        for note in planner_context.hint_metadata.get("preparation_notes", [])[:3]:
            if isinstance(note, str) and note.strip():
                summary.append(note.strip())
        if planner_context.hinted_actions:
            summary.append(f"hinted_actions={len(planner_context.hinted_actions)}")
        return summary or ["none"]

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
