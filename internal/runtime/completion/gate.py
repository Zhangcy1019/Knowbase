"""Completion gate that decides whether a runtime run may finish."""

from __future__ import annotations

from internal.runtime.completion.decision import CompletionDecision
from internal.runtime.memory.state import RuntimeRunState
from internal.runtime.verification.executor import RuntimeVerificationContext


class RuntimeCompletionGate:
    """Evaluate completion-time verification and return a normalized decision."""

    def __init__(self, *, verifier):
        self._verifier = verifier

    def evaluate(self, *, run, request, state: RuntimeRunState) -> CompletionDecision:
        request_metadata = dict(getattr(request, "metadata", {}))
        verification_subrun_count = sum(
            1
            for item in getattr(state, "observations", [])
            if str(item.get("kind", "")) == "verification_subrun"
        )
        verification_profile = request.resolved_verification_profile()
        max_subruns = max(0, int(getattr(verification_profile, "max_subruns", 0) or 0))
        verification = self._verifier.verify(
            context=RuntimeVerificationContext(
                run=run,
                request=request,
                state=state,
            )
        )
        if verification.status == "completed":
            return CompletionDecision(status="pass", summary=verification.summary)
        if verification.status == "retry":
            return CompletionDecision(
                status="retry_main",
                summary=verification.summary,
                repair_prompt=verification.repair_prompt,
                issues=list(verification.review_notes or verification.hard_failures),
            )
        if verification.status == "run_subrun":
            if not bool(request_metadata.get("allow_subrun", True)):
                return CompletionDecision(
                    status="requires_review",
                    summary="Sub-run spawning is disabled for this runtime request.",
                    issues=["child run cannot spawn another child run"],
                )
            if (
                int(request_metadata.get("verification_subrun_count", 0) or 0) >= max_subruns
                or verification_subrun_count >= max_subruns
            ):
                return CompletionDecision(
                    status="requires_review",
                    summary="Verification sub-run budget exhausted.",
                    issues=[f"verification can spawn at most {max_subruns} child run(s)"],
                )
            return CompletionDecision(
                status="run_subrun",
                summary=verification.summary,
                issues=list(verification.review_notes or verification.hard_failures),
                metadata=dict(verification.metadata),
            )
        if verification.status == "failed":
            return CompletionDecision(
                status="fail",
                summary=verification.summary,
                issues=list(verification.review_notes or verification.hard_failures),
            )
        return CompletionDecision(
            status="requires_review",
            summary=verification.summary,
            issues=list(verification.review_notes or verification.hard_failures),
        )
