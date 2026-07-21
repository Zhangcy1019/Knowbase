"""Runtime verification entrypoint for deterministic checks and sub-run review."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from internal.runtime.harness.subrun import RuntimeSubRunRequest
from internal.runtime.memory.state import RuntimeRunState
from internal.runtime.verification.models import VerificationResult


@dataclass(slots=True)
class RuntimeVerificationContext:
    """Verification input bound to one runtime candidate state."""

    request: object
    state: RuntimeRunState


class RuntimeVerifierPort(Protocol):
    """Evaluate whether a runtime run produced an acceptable candidate."""

    def verify(self, *, context: RuntimeVerificationContext) -> VerificationResult: ...


class RuntimeVerifier:
    """Run hard checks first, then optional sub-run verification."""

    def __init__(self, *, acceptance_verifier):
        self._acceptance_verifier = acceptance_verifier

    def verify(self, *, context: RuntimeVerificationContext) -> VerificationResult:
        request = context.request
        state = context.state
        verification_profile = request.resolved_verification_profile()
        acceptance_required = (
            verification_profile.require_acceptance
            or request.stop_policy.stop_when_acceptance_satisfied is True
        )
        if acceptance_required:
            passed = self._acceptance_verifier.is_satisfied(request=request, state=state)
            if not passed:
                return VerificationResult(
                    passed=False,
                    retryable=True,
                    status="retry",
                    summary="Acceptance checks not yet satisfied.",
                    repair_prompt="Continue working until all acceptance checks are satisfied.",
                    hard_failures=["acceptance checks not yet satisfied"],
                )

        review_mode = verification_profile.mode
        if not verification_profile.enabled or review_mode == "deterministic":
            return VerificationResult(
                passed=True,
                retryable=False,
                status="completed",
                summary="Verification passed.",
            )
        if review_mode == "subrun":
            return VerificationResult(
                passed=False,
                retryable=False,
                status="run_subrun",
                summary="Verification requires a constrained sub-run.",
                metadata={
                    "subrun_request": RuntimeSubRunRequest(
                        purpose="verification",
                        objective=verification_profile.objective or "Verify whether the candidate satisfies runtime acceptance requirements.",
                        instructions=list(verification_profile.instructions),
                        input_context={
                            **dict(request.work.input_context),
                            "verification_prompt": verification_profile.prompt,
                            "verification_source_text": str(getattr(state, "facts", {}).get("source_text", "")),
                        },
                        allowed_tools=list(verification_profile.allowed_tools),
                        allowed_skills=list(verification_profile.allowed_skills),
                        max_steps=verification_profile.max_steps,
                        max_tool_calls=verification_profile.max_tool_calls,
                        max_skill_calls=verification_profile.max_skill_calls,
                        metadata={
                            "parent_run_id": getattr(getattr(state, "run", None), "run_id", ""),
                        },
                    ).model_dump(mode="json"),
                },
            )
        return VerificationResult(
            passed=False,
            retryable=False,
            status="requires_review",
            summary=f"Unsupported verification mode: {review_mode}",
            hard_failures=[f"unsupported verification mode: {review_mode}"],
        )
