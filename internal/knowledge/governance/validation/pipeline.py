"""Execution pipeline for governance validation plugins."""

from __future__ import annotations

from collections.abc import Iterable

from internal.knowledge.governance.validation.contracts import (
    GovernanceValidationContext,
    GovernanceValidationPlugin,
    GovernanceValidationReport,
    GovernanceValidationResult,
)


class GovernanceValidationPipeline:
    """Run enabled deterministic constraints in a stable order."""

    def __init__(self, *, plugins: Iterable[GovernanceValidationPlugin] = ()):
        self._plugins = list(plugins)

    @property
    def plugins(self) -> list[GovernanceValidationPlugin]:
        return list(self._plugins)

    def validate(self, *, context: GovernanceValidationContext) -> GovernanceValidationReport:
        results: list[GovernanceValidationResult] = []
        for plugin in self._plugins:
            try:
                results.append(plugin.validate(context=context))
            except Exception as exc:  # noqa: BLE001
                # One broken constraint must not hide the conclusions of the
                # remaining validators. The aggregate still fails closed.
                results.append(
                    GovernanceValidationResult(
                        plugin=getattr(plugin, "name", plugin.__class__.__name__),
                        passed=False,
                        reasons=[f"validation plugin failed: {exc}"],
                    )
                )
        return GovernanceValidationReport(
            passed=all(result.passed for result in results),
            results=results,
        )
