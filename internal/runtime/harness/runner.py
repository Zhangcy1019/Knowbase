"""Unified runtime harness runner."""

from __future__ import annotations

from dataclasses import dataclass

from internal.runtime.contracts import RuntimeRunResult
from internal.runtime.harness.context import RuntimeHarnessContext
from internal.runtime.harness.subrun import RuntimeSubRunLauncher, RuntimeSubRunRequest
from internal.runtime.memory.state import RuntimeRunState
from internal.runtime.verification.adjudicator import RuntimeVerificationAdjudicator


@dataclass(slots=True)
class RuntimeHarnessResult:
    """Final harness result returned to the runtime service."""

    state: RuntimeRunState
    final_status: str
    requires_review: bool


class RuntimeHarnessRunner:
    """Own the main loop lifecycle and invoke hooks around completion."""

    def __init__(
        self,
        *,
        loop_engine,
        before_complete_hook=None,
        subrun_launcher: RuntimeSubRunLauncher | None = None,
        trace_recorder=None,
        verification_adjudicator: RuntimeVerificationAdjudicator | None = None,
    ):
        self._loop_engine = loop_engine
        self._before_complete_hook = before_complete_hook
        self._subrun_launcher = subrun_launcher or RuntimeSubRunLauncher()
        self._trace_recorder = trace_recorder
        self._verification_adjudicator = verification_adjudicator or RuntimeVerificationAdjudicator()

    def run(self, *, run, request, state: RuntimeRunState) -> RuntimeHarnessResult:
        next_state, final_status, requires_review = self._loop_engine.run(
            run=run,
            request=request,
            state=state,
        )
        if final_status != "completed" or self._before_complete_hook is None:
            return RuntimeHarnessResult(
                state=next_state,
                final_status=final_status,
                requires_review=requires_review,
            )
        
        #  for verification and review, we invoke the before_complete_hook to determine if the run is truly complete
        hook_result = self._before_complete_hook.before_complete(
            context=RuntimeHarnessContext(run=run, request=request, state=next_state)
        )
        if hook_result.status == "pass":
            return RuntimeHarnessResult(state=next_state, final_status="completed", requires_review=False)
        if hook_result.status == "retry_main":
            payload = {
                "summary": hook_result.summary,
                "repair_prompt": hook_result.repair_prompt,
                "issues": list(hook_result.issues),
            }
            next_state.add_observation(kind="verification_feedback", payload=payload)
            self._record_observation(run=run, state=next_state, kind="verification_feedback", payload=payload)
            return self.run(run=run, request=request, state=next_state)
        if hook_result.status == "run_subrun":
            subrun_result = self._launch_subrun(run=run, hook_result=hook_result)
            subrun_request_payload = hook_result.metadata.get("subrun_request", {})
            subrun_purpose = ""
            if isinstance(subrun_request_payload, dict):
                subrun_purpose = str(subrun_request_payload.get("purpose") or "").strip()
            if subrun_purpose == "verification":
                child_result = self._extract_child_result(subrun_result=subrun_result)
                if child_result is not None:
                    adjudicated = self._verification_adjudicator.adjudicate(result=child_result)
                    if adjudicated is not None:
                        subrun_result = adjudicated
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
                return RuntimeHarnessResult(state=next_state, final_status="completed", requires_review=False)
            if subrun_result.retryable:
                payload = {
                    "summary": subrun_result.summary,
                    "repair_prompt": subrun_result.repair_prompt,
                    "issues": list(subrun_result.issues),
                }
                next_state.add_observation(kind="verification_feedback", payload=payload)
                self._record_observation(run=run, state=next_state, kind="verification_feedback", payload=payload)
                return self.run(run=run, request=request, state=next_state)
            if subrun_result.status == "failed":
                next_state.failure_messages.append(subrun_result.summary or "verification sub-run failed")
                return RuntimeHarnessResult(state=next_state, final_status="failed", requires_review=True)
            return RuntimeHarnessResult(state=next_state, final_status="requires_review", requires_review=True)
        if hook_result.status == "fail":
            next_state.failure_messages.append(hook_result.summary or "runtime hook failed")
            return RuntimeHarnessResult(state=next_state, final_status="failed", requires_review=True)
        return RuntimeHarnessResult(state=next_state, final_status="requires_review", requires_review=True)

    def _launch_subrun(self, *, run, hook_result):
        request = RuntimeSubRunRequest.model_validate(hook_result.metadata.get("subrun_request", {}))
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
