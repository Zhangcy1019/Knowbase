"""Execution pipeline for schema-proposal discovery plugins."""

from __future__ import annotations

from collections.abc import Iterable

from internal.knowledge.governance.proposal.models import PartitionFacetSchemaProposal
from internal.knowledge.governance.proposal.contracts import (
    GovernanceProposalContext,
    GovernanceProposalConflict,
    GovernanceProposalPlugin,
    GovernanceProposalPluginResult,
    GovernanceProposalReport,
)


class GovernanceProposalPipeline:
    """Run proposal detectors and merge their independent findings."""

    def __init__(self, *, plugins: Iterable[GovernanceProposalPlugin] = ()):
        self._plugins = list(plugins)

    @property
    def plugins(self) -> list[GovernanceProposalPlugin]:
        return list(self._plugins)

    def propose(self, *, context: GovernanceProposalContext) -> GovernanceProposalReport:
        # If the evidence is inconsistent, we cannot propose schema changes because the evidence is not reliable.
        if context.consistency_status in {"inconsistent", "stale"}:
            proposal = self._empty_proposal(
                context=context,
                rationale="Proposal blocked because Preparation found inconsistent evidence.",
            )
            return GovernanceProposalReport(
                proposal=proposal,
                status="blocked",
                reason_details=[{
                    "stage": "proposal",
                    "code": "proposal_blocked_by_evidence_consistency",
                    "message": "Proposal discovery was not run because snapshot and index evidence are inconsistent.",
                    "evidence": {"mismatches": list(context.consistency_mismatches)},
                    "next_action": "Refresh or rebuild Preparation evidence before proposing schema changes.",
                }],
            )
        
        results: list[GovernanceProposalPluginResult] = []
        for plugin in self._plugins:
            try:
                results.append(plugin.propose(context=context))
            except Exception as exc:  # noqa: BLE001
                results.append(
                    GovernanceProposalPluginResult(
                        plugin=getattr(plugin, "name", plugin.__class__.__name__),
                        reasons=[f"proposal plugin failed: {exc}"],
                    )
                )

        new_keys = self._merge(results, "suggested_new_keys")
        removed_keys = self._merge(results, "suggested_removed_keys")
        active = bool(new_keys or removed_keys)
        conflicts = self._find_conflicts(results)
        status = "proposed" if active else "no_change"
        reason_details = self._reason_details(results=results, conflicts=conflicts)
        proposal = PartitionFacetSchemaProposal(
            partition=context.partition,
            rationale=(
                "Deterministic proposal plugins found schema candidates for runtime governance review."
                if active
                else "Current partition facet keys appear sufficient against the current evidence snapshot."
            ),
            suggested_new_keys=new_keys,
            suggested_removed_keys=removed_keys,
            notes=[
                "Proposal candidates are assessment-only and require governance runtime review.",
                f"plugin_count={len(self._plugins)}",
            ],
        )
        return GovernanceProposalReport(
            proposal=proposal,
            results=results,
            status=status,
            conflicts=conflicts,
            impact={
                "affected_case_count": context.affected_case_count,
                "schema_change_count": len(set(new_keys + removed_keys)),
                "new_key_count": len(new_keys),
                "removed_key_count": len(removed_keys),
                "conflict_count": len(conflicts),
                "value_proposal_count": 0,
            },
            reason_details=reason_details,
        )

    @staticmethod
    def _empty_proposal(*, context: GovernanceProposalContext, rationale: str) -> PartitionFacetSchemaProposal:
        return PartitionFacetSchemaProposal(partition=context.partition, rationale=rationale)

    @staticmethod
    def _find_conflicts(results: list[GovernanceProposalPluginResult]) -> list[GovernanceProposalConflict]:
        candidates: dict[str, dict[str, list[str]]] = {}
        for result in results:
            for action, field_name in (
                ("new", "suggested_new_keys"),
                ("remove", "suggested_removed_keys"),
            ):
                for key in getattr(result, field_name):
                    candidates.setdefault(key, {}).setdefault(action, []).append(result.plugin)
        conflicts: list[GovernanceProposalConflict] = []
        for key, actions in candidates.items():
            if len(actions) < 2:
                continue
            conflicts.append(
                GovernanceProposalConflict(
                    key=key,
                    candidates=sorted(actions),
                    plugins=sorted({plugin for values in actions.values() for plugin in values}),
                    reason="Independent proposal plugins produced incompatible actions for the same key.",
                )
            )
        return conflicts

    @staticmethod
    def _reason_details(*, results, conflicts) -> list[dict[str, object]]:
        details = [
            {
                "stage": "proposal",
                "code": f"proposal_plugin_{result.plugin}",
                "message": result.root_cause or f"Proposal plugin {result.plugin} evaluated the evidence.",
                "candidate_changes": {
                    "new_keys": list(result.suggested_new_keys),
                    "removed_keys": list(result.suggested_removed_keys),
                },
                "reasons": list(result.reasons),
                "evidence": dict(result.evidence),
                "metrics": dict(result.metrics),
            }
            for result in results
            if result.root_cause or result.reasons or result.evidence
        ]
        details.extend({
            "stage": "proposal",
            "code": "proposal_conflict",
            "message": conflict.reason,
            "evidence": conflict.as_dict(),
            "next_action": "Let Runtime / LLM resolve the competing candidate actions.",
        } for conflict in conflicts)
        return details

    @staticmethod
    def _merge(results: list[GovernanceProposalPluginResult], field_name: str) -> list[str]:
        values: list[str] = []
        for result in results:
            values.extend(getattr(result, field_name))
        return list(dict.fromkeys(value for value in values if value.strip()))


__all__ = ["GovernanceProposalPipeline"]
