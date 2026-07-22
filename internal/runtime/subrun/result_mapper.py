"""Map specialized child-run outputs into parent-visible subrun results."""

from __future__ import annotations

from internal.runtime.contracts import RuntimeRunResult
from internal.runtime.subrun.contracts import RuntimeSubRunResult


class VerificationSubRunResultMapper:
    """Interpret verification child-run results without polluting generic subrun code."""

    def map_result(self, *, result: RuntimeRunResult) -> RuntimeSubRunResult | None:
        latest_skill_result = self._latest_skill_result(result)
        if latest_skill_result is None:
            return None
        output = dict(latest_skill_result.output)
        if "passed" not in output:
            return None
        passed = bool(output.get("passed"))
        retryable = bool(output.get("retryable", False))
        summary = str(output.get("summary") or result.final_summary or result.reasoning_summary or "").strip()
        repair_prompt = str(output.get("repair_prompt") or "").strip()
        issues = [str(item) for item in list(output.get("issues") or []) if str(item).strip()]
        return RuntimeSubRunResult(
            status="completed" if passed else "requires_review",
            summary=summary,
            retryable=retryable and not passed,
            repair_prompt=repair_prompt,
            issues=issues,
            output={
                "child_result": result.model_dump(mode="json"),
                "verification_output": output,
            },
        )

    @staticmethod
    def _latest_skill_result(result: RuntimeRunResult):
        if not result.skill_results:
            return None
        return result.skill_results[-1]
