"""Top-level runtime orchestrator coordinating loop, completion, and subruns."""

from __future__ import annotations

from dataclasses import dataclass

from internal.runtime.completion.decision import CompletionDecision
from internal.runtime.completion.feedback import build_verification_feedback_payload
from internal.runtime.contracts import RuntimeRunResult
from internal.runtime.memory.state import RuntimeRunState
from internal.runtime.subrun import RuntimeSubRunLauncher, RuntimeSubRunRequest, VerificationSubRunResultMapper


@dataclass(slots=True)
class RuntimeOrchestrationResult:
    """Final orchestration result returned to the runtime service."""

    state: RuntimeRunState
    final_status: str
    requires_review: bool


class RuntimeOrchestrator:
    """Coordinate the main loop with completion checks and verification subruns."""

    def __init__(
        self,
        *,
        loop_engine,
        completion_gate=None,
        subrun_launcher: RuntimeSubRunLauncher | None = None,
        trace_recorder=None,
        verification_subrun_mapper: VerificationSubRunResultMapper | None = None,
    ):
        self._loop_engine = loop_engine
        self._completion_gate = completion_gate
        self._subrun_launcher = subrun_launcher or RuntimeSubRunLauncher()
        self._trace_recorder = trace_recorder
        self._verification_subrun_mapper = verification_subrun_mapper or VerificationSubRunResultMapper()

    def run(self, *, run, request, state: RuntimeRunState) -> RuntimeOrchestrationResult:
        next_state, final_status, requires_review = self._loop_engine.run(
            run=run,
            request=request,
            state=state,
        )
        if final_status != "completed" or self._completion_gate is None:
            return RuntimeOrchestrationResult(
                state=next_state,
                final_status=final_status,
                requires_review=requires_review,
            )

        completion = self._completion_gate.evaluate(
            run=run,
            request=request,
            state=next_state,
        )
        if completion.status == "pass":
            return RuntimeOrchestrationResult(state=next_state, final_status="completed", requires_review=False)
        if completion.status == "retry_main":
            payload = build_verification_feedback_payload(
                summary=completion.summary,
                repair_prompt=completion.repair_prompt,
                issues=list(completion.issues),
            )
            next_state.add_observation(kind="verification_feedback", payload=payload)
            self._record_observation(run=run, state=next_state, kind="verification_feedback", payload=payload)
            return self.run(run=run, request=request, state=next_state)
        if completion.status == "run_subrun":
            subrun_result = self._launch_subrun(run=run, completion=completion)
            subrun_request_payload = completion.metadata.get("subrun_request", {})
            subrun_purpose = ""
            if isinstance(subrun_request_payload, dict):
                subrun_purpose = str(subrun_request_payload.get("purpose") or "").strip()
            if subrun_purpose == "verification":
                child_result = self._extract_child_result(subrun_result=subrun_result)
                if child_result is not None:
                    mapped = self._verification_subrun_mapper.map_result(result=child_result)
                    if mapped is not None:
                        subrun_result = mapped
            payload = {
                "status": subrun_result.status,
                "summary": subrun_result.summary,
                "repair_prompt": subrun_result.repair_prompt,
                "issues": list(subrun_result.issues),
                "output": dict(subrun_result.output),
            }
            next_state.add_observation(kind="verification_subrun", payload=payload)
            self._record_observation(run=run, state=next_state, kind="verification_subrun", payload=payload)
            if subrun_result.status == "completed":
                return RuntimeOrchestrationResult(state=next_state, final_status="completed", requires_review=False)
            if subrun_result.retryable:
                payload = build_verification_feedback_payload(
                    summary=subrun_result.summary,
                    repair_prompt=subrun_result.repair_prompt,
                    issues=list(subrun_result.issues),
                )
                next_state.add_observation(kind="verification_feedback", payload=payload)
                self._record_observation(run=run, state=next_state, kind="verification_feedback", payload=payload)
                return self.run(run=run, request=request, state=next_state)
            if subrun_result.status == "failed":
                next_state.failure_messages.append(subrun_result.summary or "verification sub-run failed")
                return RuntimeOrchestrationResult(state=next_state, final_status="failed", requires_review=True)
            return RuntimeOrchestrationResult(state=next_state, final_status="requires_review", requires_review=True)
        if completion.status == "fail":
            next_state.failure_messages.append(completion.summary or "runtime completion failed")
            return RuntimeOrchestrationResult(state=next_state, final_status="failed", requires_review=True)
        return RuntimeOrchestrationResult(state=next_state, final_status="requires_review", requires_review=True)

    def _launch_subrun(self, *, run, completion: CompletionDecision):
        request = RuntimeSubRunRequest.model_validate(completion.metadata.get("subrun_request", {}))
        return self._subrun_launcher.launch(parent_run=run, request=request)

    @staticmethod
    def _extract_child_result(*, subrun_result):
        child_result = subrun_result.output.get("child_result") if isinstance(subrun_result.output, dict) else None
        if not isinstance(child_result, dict):
            return None
        return RuntimeRunResult.model_validate(child_result)

    def _record_observation(self, *, run, state: RuntimeRunState, kind: str, payload: dict[str, object]) -> None:
        if self._trace_recorder is None:
            return
        turn_index = max(state.turn_count - 1, 0)
        self._trace_recorder.record_observation(
            run=run,
            kind=kind,
            payload=payload,
            turn_index=turn_index,
        )
