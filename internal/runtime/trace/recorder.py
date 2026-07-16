"""Centralized runtime trace and audit recording."""

from __future__ import annotations

from typing import Any

from internal.domain.run.artifact_repository import RunArtifactRepository
from internal.domain.run.run_repository import AgentRunRepository
from internal.domain.run.step_repository import RunStepRepository
from internal.models import AgentRun, RunArtifact, RunStep, RuntimeTraceReplay, RuntimeTraceTurn


class RuntimeTraceRecorder:
    """Record runtime steps and artifacts in one place."""

    def __init__(
        self,
        *,
        run_repository: AgentRunRepository,
        step_repository: RunStepRepository,
        artifact_repository: RunArtifactRepository,
    ):
        self._run_repository = run_repository
        self._step_repository = step_repository
        self._artifact_repository = artifact_repository

    def append_step(
        self,
        *,
        run: AgentRun,
        step_type: str,
        name: str,
        input: dict[str, Any],
        output: dict[str, Any],
        summary: str,
    ) -> RunStep:
        step = self._step_repository.save(
            RunStep(
                run_id=run.run_id,
                index=len(self._step_repository.list_for_run(run.run_id)),
                step_type=step_type,
                name=name,
                input=input,
                output=output,
                summary=summary,
            )
        )
        persisted = self._run_repository.get(run.run_id)
        if persisted is not None:
            self._run_repository.save(persisted.model_copy(update={"step_count": step.index + 1}))
        return step

    def record_artifact(
        self,
        *,
        run: AgentRun,
        artifact_type: str,
        title: str,
        content: dict[str, Any],
    ) -> RunArtifact:
        return self._artifact_repository.save(
            RunArtifact(
                run_id=run.run_id,
                artifact_type=artifact_type,
                title=title,
                content=content,
            )
        )

    def record_runtime_request(self, *, run: AgentRun, request_payload: dict[str, Any]) -> RunArtifact:
        return self.record_artifact(
            run=run,
            artifact_type="runtime_request",
            title="Runtime Run Request",
            content=request_payload,
        )

    def record_planner_context(self, *, run: AgentRun, turn_index: int, planner_context: dict[str, Any]) -> RunArtifact:
        return self.record_artifact(
            run=run,
            artifact_type="planner_context",
            title=f"Planner Context Turn {turn_index}",
            content=planner_context,
        )

    def record_llm_prompt(self, *, run: AgentRun, turn_index: int, prompt_payload: dict[str, Any]) -> RunArtifact:
        return self.record_artifact(
            run=run,
            artifact_type="llm_prompt",
            title=f"LLM Prompt Turn {turn_index}",
            content=prompt_payload,
        )

    def record_llm_response(self, *, run: AgentRun, turn_index: int, response_payload: dict[str, Any]) -> RunArtifact:
        return self.record_artifact(
            run=run,
            artifact_type="llm_response",
            title=f"LLM Response Turn {turn_index}",
            content=response_payload,
        )

    def record_decision(self, *, run: AgentRun, decision_payload: dict[str, Any], summary: str, name: str) -> RunStep:
        return self.append_step(
            run=run,
            step_type="decision",
            name=name,
            input={},
            output=decision_payload,
            summary=summary,
        )

    def record_decision_artifact(self, *, run: AgentRun, decision_payload: dict[str, Any], title: str) -> RunArtifact:
        return self.record_artifact(
            run=run,
            artifact_type="decision",
            title=title,
            content=decision_payload,
        )

    def record_decision_error(self, *, run: AgentRun, name: str, error_message: str) -> RunStep:
        return self.append_step(
            run=run,
            step_type="decision_error",
            name=name,
            input={},
            output={"error": error_message},
            summary=error_message,
        )

    def record_action(self, *, run: AgentRun, name: str, action_input: dict[str, Any], action_output: dict[str, Any], summary: str) -> RunStep:
        return self.append_step(
            run=run,
            step_type="action",
            name=name,
            input=action_input,
            output=action_output,
            summary=summary,
        )

    def record_tool_call(self, *, run: AgentRun, tool_id: str, tool_input: dict[str, Any], summary: str) -> RunStep:
        return self.append_step(
            run=run,
            step_type="tool_call",
            name=tool_id,
            input=tool_input,
            output={},
            summary=summary,
        )

    def record_tool_result(self, *, run: AgentRun, tool_id: str, result_payload: dict[str, Any], summary: str) -> RunStep:
        return self.append_step(
            run=run,
            step_type="tool_result",
            name=tool_id,
            input={},
            output=result_payload,
            summary=summary,
        )

    def record_skill_call(self, *, run: AgentRun, skill_id: str, skill_input: dict[str, Any], summary: str) -> RunStep:
        return self.append_step(
            run=run,
            step_type="skill_call",
            name=skill_id,
            input=skill_input,
            output={},
            summary=summary,
        )

    def record_skill_result(self, *, run: AgentRun, skill_id: str, result_payload: dict[str, Any], summary: str) -> RunStep:
        return self.append_step(
            run=run,
            step_type="skill_result",
            name=skill_id,
            input={},
            output=result_payload,
            summary=summary,
        )

    def load_replay(self, *, run_id: str) -> RuntimeTraceReplay | None:
        run = self._run_repository.get(run_id)
        if run is None:
            return None
        steps = self._step_repository.list_for_run(run_id)
        artifacts = self._artifact_repository.list_for_run(run_id)
        request_artifact = next((item for item in artifacts if item.artifact_type == "runtime_request"), None)
        turns = self._reconstruct_turns(steps=steps, artifacts=artifacts)
        return RuntimeTraceReplay(
            run=run,
            request_artifact=request_artifact,
            turns=turns,
            steps=steps,
            artifacts=artifacts,
        )

    def _reconstruct_turns(self, *, steps: list[RunStep], artifacts: list[RunArtifact]) -> list[RuntimeTraceTurn]:
        turns_by_index: dict[int, RuntimeTraceTurn] = {}

        def ensure_turn(turn_index: int) -> RuntimeTraceTurn:
            turn = turns_by_index.get(turn_index)
            if turn is None:
                turn = RuntimeTraceTurn(turn_index=turn_index)
                turns_by_index[turn_index] = turn
            return turn

        current_turn_index = -1
        for step in steps:
            explicit_turn_index = self._resolve_turn_index_from_step(step=step)
            if step.step_type == "decision":
                current_turn_index = explicit_turn_index
            elif explicit_turn_index >= 0:
                current_turn_index = explicit_turn_index
            if current_turn_index < 0:
                continue
            turn = ensure_turn(current_turn_index)
            if step.step_type == "decision":
                turn.decision_step = step
            elif step.step_type == "action":
                turn.action_steps.append(step)
            elif step.step_type == "tool_call":
                turn.tool_calls.append(step)
            elif step.step_type == "tool_result":
                turn.tool_results.append(step)
            elif step.step_type == "skill_call":
                turn.skill_calls.append(step)
            elif step.step_type == "skill_result":
                turn.skill_results.append(step)
            elif step.step_type == "decision_error":
                turn.errors.append(step)

        for artifact in artifacts:
            turn_index = self._resolve_turn_index_from_artifact(artifact=artifact)
            if turn_index < 0:
                continue
            turn = ensure_turn(turn_index)
            if artifact.artifact_type == "decision":
                turn.decision_artifact = artifact
            elif artifact.artifact_type == "planner_context":
                turn.planner_context_artifact = artifact
            elif artifact.artifact_type == "llm_prompt":
                turn.llm_prompt_artifact = artifact
            elif artifact.artifact_type == "llm_response":
                turn.llm_response_artifact = artifact

        return [turns_by_index[key] for key in sorted(turns_by_index)]

    @staticmethod
    def _resolve_turn_index_from_step(*, step: RunStep) -> int:
        if step.step_type == "decision":
            return RuntimeTraceRecorder._extract_turn_index(step.name)
        if step.step_type == "decision_error":
            return RuntimeTraceRecorder._extract_turn_index(step.name)
        for payload in (step.input, step.output):
            if not isinstance(payload, dict):
                continue
            metadata = payload.get("metadata")
            if isinstance(metadata, dict):
                raw_turn = metadata.get("turn_index")
                if isinstance(raw_turn, int):
                    return raw_turn
                if isinstance(raw_turn, str) and raw_turn.isdigit():
                    return int(raw_turn)
        return -1

    @staticmethod
    def _resolve_turn_index_from_artifact(*, artifact: RunArtifact) -> int:
        if artifact.artifact_type == "decision":
            raw_turn = artifact.content.get("metadata", {}).get("turn_index") if isinstance(artifact.content, dict) else None
            if isinstance(raw_turn, int):
                return raw_turn
            if isinstance(raw_turn, str) and raw_turn.isdigit():
                return int(raw_turn)
            decision_id = artifact.content.get("decision_id") if isinstance(artifact.content, dict) else ""
            return RuntimeTraceRecorder._extract_turn_index(str(decision_id or ""))
        return RuntimeTraceRecorder._extract_turn_index(artifact.title)

    @staticmethod
    def _extract_turn_index(value: str) -> int:
        if not value:
            return -1
        suffix = value.rsplit(":", 1)[-1].strip()
        if suffix.isdigit():
            return int(suffix)
        if value.lower().startswith("planner context turn "):
            suffix = value.split()[-1].strip()
            return int(suffix) if suffix.isdigit() else -1
        if value.lower().startswith("llm prompt turn "):
            suffix = value.split()[-1].strip()
            return int(suffix) if suffix.isdigit() else -1
        if value.lower().startswith("llm response turn "):
            suffix = value.split()[-1].strip()
            return int(suffix) if suffix.isdigit() else -1
        return -1
