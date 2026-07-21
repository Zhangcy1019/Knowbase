"""Completion hook that bridges the harness into runtime verification."""

from __future__ import annotations

from internal.runtime.harness.hooks import RuntimeHookResult
from internal.runtime.verification.verifier import RuntimeVerificationContext


class VerificationStopHook:
    """Run deterministic and optional reviewer verification before completion."""

    def __init__(self, *, verifier):
        self._verifier = verifier

    def before_complete(self, *, context) -> RuntimeHookResult:
        request_metadata = dict(getattr(context.request, "metadata", {}))
        verification_subrun_count = sum(
            1
            for item in getattr(context.state, "observations", [])
            if str(item.get("kind", "")) == "verification_subrun"
        )
        verification_profile = context.request.resolved_verification_profile()
        max_subruns = max(0, int(getattr(verification_profile, "max_subruns", 0) or 0))
        verification = self._verifier.verify(
            context=RuntimeVerificationContext(
                request=context.request,
                state=context.state,
            )
        )
        if verification.status == "completed":
            return RuntimeHookResult(status="pass", summary=verification.summary)
        if verification.status == "retry":
            return RuntimeHookResult(
                status="retry_main",
                summary=verification.summary,
                repair_prompt=verification.repair_prompt,
                issues=list(verification.review_notes or verification.hard_failures),
            )
        if verification.status == "run_subrun":
            if not bool(request_metadata.get("allow_subrun", True)):
                return RuntimeHookResult(
                    status="requires_review",
                    summary="Sub-run spawning is disabled for this runtime request.",
                    issues=["child run cannot spawn another child run"],
                )
            if (
                int(request_metadata.get("verification_subrun_count", 0) or 0) >= max_subruns
                or verification_subrun_count >= max_subruns
            ):
                return RuntimeHookResult(
                    status="requires_review",
                    summary="Verification sub-run budget exhausted.",
                    issues=[f"verification can spawn at most {max_subruns} child run(s)"],
                )
            return RuntimeHookResult(
                status="run_subrun",
                summary=verification.summary,
                issues=list(verification.review_notes or verification.hard_failures),
                metadata=dict(verification.metadata),
            )
        if verification.status == "failed":
            return RuntimeHookResult(
                status="fail",
                summary=verification.summary,
                issues=list(verification.review_notes or verification.hard_failures),
            )
        return RuntimeHookResult(
            status="requires_review",
            summary=verification.summary,
            issues=list(verification.review_notes or verification.hard_failures),
        )
