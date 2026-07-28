"""Knowledge governance service facade."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from internal.knowledge.batch.models import BatchWorkingSet
from internal.models.facet import PartitionFacetSchema
from internal.knowledge.governance.contracts import (
    GovernanceEvidence,
    GovernanceResult,
    GovernanceStatisticsInput,
)
from internal.knowledge.governance.preparation.models import GovernanceRefreshScope, PartitionFacetCoverageAssessment
from internal.knowledge.governance.proposal.models import PartitionFacetSchemaProposal
from internal.knowledge.governance.runtime_agent import GovernanceRuntimeDecision
from internal.knowledge.governance.runtime_agent import GovernanceRuntimeAgent
from internal.knowledge.governance.preparation.context_builder import GovernanceContextBuilder
from internal.knowledge.governance.validation import (
    GovernanceValidationContext,
    GovernanceValidationPipeline,
    PartitionFitMetrics,
)
from internal.knowledge.governance.proposal import (
    FacetKeyDemotionProposal,
    GovernanceProposalPipeline,
    SemanticKeyPromotionProposal,
    has_effective_schema_proposal,
)


class GovernanceService:
    """Coordinate read-only knowledge governance for one Knowledge drain.

    The deterministic stage prepares evidence and enforces safety policies.
    When attached, a read-only runtime decision agent evaluates candidates;
    this service remains the final business and safety gate.
    """

    def __init__(
        self,
        *,
        context_builder: GovernanceContextBuilder | None = None,
        fit_metrics: PartitionFitMetrics | None = None,
        validation_pipeline: GovernanceValidationPipeline | None = None,
        proposal_pipeline: GovernanceProposalPipeline | None = None,
        decision_agent: GovernanceRuntimeAgent | None = None,
    ):
        self._context_builder: GovernanceContextBuilder | None = context_builder
        self._fit_metrics: PartitionFitMetrics | None = fit_metrics
        self._validation_pipeline: GovernanceValidationPipeline | None = validation_pipeline or (
            GovernanceValidationPipeline(plugins=[fit_metrics])
            if fit_metrics is not None
            else None
        )
        self._decision_agent: GovernanceRuntimeAgent | None = decision_agent
        self._proposal_pipeline: GovernanceProposalPipeline = proposal_pipeline or GovernanceProposalPipeline(
            plugins=[
                SemanticKeyPromotionProposal(),
                FacetKeyDemotionProposal(),
            ]
        )

    def set_runtime_agent(self, agent: GovernanceRuntimeAgent) -> None:
        """Attach the runtime adapter after application modules are assembled."""
        self._decision_agent = agent

    @property
    def fit_metrics(self) -> PartitionFitMetrics | None:
        """Expose the shared deterministic fit evaluator for runtime assembly."""
        return self._fit_metrics

    @property
    def validation_pipeline(self):
        """Expose the shared validation pipeline for the isolated runtime."""
        return self._validation_pipeline

    def assess_deterministic(
        self,
        *,
        statistics: GovernanceStatisticsInput,
        current_schema: PartitionFacetSchema,
        working_set: BatchWorkingSet,
    ) -> GovernanceResult:
        """Assess one working set without mutating files.

        This deterministic stage consumes the prepared evidence and applies
        safety policies. Runtime refinement is exposed separately through
        ``assess_async`` so the deterministic boundary remains reusable.
        """
        case_statistics = statistics.case if isinstance(statistics, GovernanceStatisticsInput) else statistics
        statistics = case_statistics
        partition = getattr(working_set, "partition", "")
        affected_case_ids = list(getattr(working_set, "affected_case_ids", []))
        preparation = (
            self._context_builder.build_context(
                batch_working_set=working_set,
                statistics=statistics,
            )
            if self._context_builder is not None
            else None
        )
        coverage = getattr(preparation, "facet_coverage_assessment", None)
        proposal_context = getattr(preparation, "proposal_context", None)
        proposal_diagnostics: list[dict[str, object]] = []
        proposal_report = None
        proposal = None
        if proposal_context is not None:
            proposal_report = self._proposal_pipeline.propose(context=proposal_context)
            proposal = proposal_report.proposal
            proposal_diagnostics = [result.as_dict() for result in proposal_report.results]
        
        refresh_scope = getattr(preparation, "refresh_scope", None)
        if coverage is None:
            existing_facet_keys = self._schema_keys(current_schema)
            coverage = PartitionFacetCoverageAssessment(
                partition=partition,
                affected_case_ids=affected_case_ids,
                existing_facet_keys=existing_facet_keys,
                observed_facet_keys=list(getattr(working_set, "observed_facet_keys", [])),
                semantic_candidate_keys=[],
                coverage_score=1.0 if not affected_case_ids else 0.0,
                notes=["governance context builder is not configured"],
            )
        if proposal is None:
            proposal = PartitionFacetSchemaProposal(
                partition=partition,
                rationale="No schema proposal was generated.",
            )
        if refresh_scope is None:
            refresh_scope = GovernanceRefreshScope(
                partition=partition,
                scope="affected_cases" if affected_case_ids else "none",
                case_ids=affected_case_ids,
                facet_keys=list(getattr(working_set, "observed_facet_keys", [])),
                reason="re-evaluate affected cases against the current facet schema",
            )

        statistics_summary = self._statistics_summary(statistics)
        if not statistics_summary and proposal_context is not None:
            statistics_summary = {
                "partition": partition,
                "case_count": int(
                    getattr(proposal_context, "statistics_case_count", 0)
                    or getattr(proposal_context, "semantic_index_case_count", 0)
                    or 0
                ),
                "case_key_stats": dict(
                    getattr(proposal_context, "statistics_semantic_key_counts", {})
                    or getattr(proposal_context, "semantic_index_key_counts", {})
                    or {}
                ),
            }

        evidence = GovernanceEvidence(
            coverage=coverage,
            proposal=proposal,
            refresh_scope=refresh_scope,
            statistics_summary=statistics_summary,
            proposal_diagnostics=proposal_diagnostics,
            preparation_notes=list(getattr(preparation, "notes", [])),
            consistency_status=getattr(preparation, "consistency_status", "unknown"),
            consistency_mismatches=list(getattr(preparation, "consistency_mismatches", [])),
            proposal_status=getattr(proposal_report, "status", "unknown"),
            proposal_conflicts=[item.as_dict() for item in getattr(proposal_report, "conflicts", [])],
            proposal_impact=dict(getattr(proposal_report, "impact", {})),
            proposal_reason_details=list(getattr(proposal_report, "reason_details", [])),
        )

        
        if evidence.consistency_status in {"inconsistent", "stale"}:
            return GovernanceResult(
                coverage=coverage,
                proposal=proposal,
                refresh_scope=refresh_scope,
                decision="requires_review",
                accepted_schema=None,
                requires_review=True,
                risk_level="high",
                reasons=[
                    "governance evidence snapshot and partition indexes are inconsistent",
                ],
                reason_details=[{
                    "stage": "preparation",
                    "code": "evidence_snapshot_index_mismatch",
                    "message": "The statistics snapshot and materialized partition indexes do not describe the same state.",
                    "evidence": {
                        "consistency_status": evidence.consistency_status,
                        "mismatches": evidence.consistency_mismatches,
                    },
                    "next_action": "Refresh or rebuild the partition indexes before running schema proposal analysis.",
                }],
                evidence=evidence,
            )
        proposal_plugin_failed = any(
            "proposal plugin failed:" in reason
            for item in evidence.proposal_diagnostics
            for reason in item.get("reasons", [])
        )
        if proposal_plugin_failed:
            return GovernanceResult(
                coverage=coverage,
                proposal=proposal,
                refresh_scope=refresh_scope,
                decision="requires_review",
                accepted_schema=None,
                requires_review=True,
                risk_level="high",
                reasons=["schema proposal discovery plugin failed"],
                reason_details=self._proposal_reason_details(
                    proposal=proposal,
                    proposal_diagnostics=proposal_diagnostics,
                    proposal_conflicts=evidence.proposal_conflicts,
                    proposal_impact=evidence.proposal_impact,
                    blocker_code="proposal_plugin_failed",
                    next_action="Fix the failing proposal plugin before retrying the drain.",
                ),
                evidence=evidence,
            )
        has_schema_proposal = has_effective_schema_proposal(proposal)
        if has_schema_proposal:
            return GovernanceResult(
                coverage=coverage,
                proposal=proposal,
                refresh_scope=refresh_scope,
                decision="requires_review",
                accepted_schema=None,
                requires_review=True,
                risk_level="medium",
                reasons=[
                    "schema proposal requires a read-only governance decision agent",
                ],
                reason_details=self._proposal_reason_details(
                    proposal=proposal,
                    proposal_diagnostics=proposal_diagnostics,
                    proposal_conflicts=evidence.proposal_conflicts,
                    proposal_impact=evidence.proposal_impact,
                    blocker_code="proposal_requires_runtime_decision",
                    next_action="Run the read-only governance runtime to accept, reject, or refine the proposal.",
                ),
                evidence=evidence,
            )
        return GovernanceResult(
            coverage=coverage,
            proposal=proposal,
            refresh_scope=refresh_scope,
            decision="no_change",
            accepted_schema=current_schema,
            requires_review=False,
            risk_level="medium" if affected_case_ids else "low",
            reasons=[
                "no schema mutation proposed; the current schema remains active",
            ],
            reason_details=[{
                "stage": "proposal",
                "code": "no_effective_proposal",
                "message": "Proposal plugins found no actionable schema change in the current evidence.",
                "next_action": "Continue to projection only if case facet refresh is required.",
            }],
            evidence=evidence,
        )

    async def assess_async(
        self,
        *,
        statistics: GovernanceStatisticsInput,
        current_schema: PartitionFacetSchema,
        working_set: BatchWorkingSet,
    ) -> GovernanceResult:
        """Assess and optionally ask a read-only runtime agent to decide.

        Deterministic policy checks always run first. The runtime agent can
        only refine a safe candidate; it cannot bypass a policy rejection.
        """
        base = self.assess_deterministic(
            statistics=statistics,
            current_schema=current_schema,
            working_set=working_set,
        )
        case_statistics = statistics.case if isinstance(statistics, GovernanceStatisticsInput) else statistics
        if self._decision_agent is None:
            return base
        has_schema_proposal = has_effective_schema_proposal(base.proposal)
        if not has_schema_proposal:
            return base
        decision = await self._decision_agent.decide(
            partition=getattr(working_set, "partition", ""),
            statistics=case_statistics,
            current_schema=current_schema,
            working_set=working_set,
            evidence=base.evidence,
        )
        return self._apply_runtime_decision(
            base=base,
            decision=decision,
            current_schema=current_schema,
            statistics=case_statistics,
        )

    def _apply_runtime_decision(
        self,
        *,
        base: GovernanceResult,
        decision: GovernanceRuntimeDecision,
        current_schema,
        statistics,
    ):
        reasons = [*base.reasons, *decision.reasons]
        reason_details = [
            *base.reason_details,
            {
                "stage": "runtime",
                "code": f"runtime_{decision.outcome}",
                "message": decision.summary or "Read-only governance runtime returned a decision.",
                "reasons": list(decision.reasons),
                "next_action": "Apply the accepted schema only after the final validation gate passes.",
            },
        ]
        metadata = dict(decision.metadata)
        if decision.summary:
            reasons.append(decision.summary)
        if decision.outcome == "accepted" and GovernanceService._is_schema(decision.accepted_schema):
            fit_result = self._final_fit_gate(
                partition=getattr(base.coverage, "partition", ""),
                statistics=statistics,
                current_schema=current_schema,
                candidate_schema=decision.accepted_schema,
                proposal=base.proposal,
                refresh_scope=base.refresh_scope,
            )
            metadata["final_fit_metrics"] = fit_result
            if not fit_result["passed"]:
                return replace(
                    base,
                    decision="requires_review",
                    accepted_schema=None,
                    requires_review=True,
                    risk_level="high",
                    reasons=[
                        *reasons,
                        "final governance fit-metrics gate failed",
                        *list(fit_result.get("reasons", [])),
                    ],
                    reason_details=[
                        *reason_details,
                        {
                            "stage": "validation",
                            "code": "final_fit_metrics_failed",
                            "message": "The candidate schema failed the final deterministic fit-metrics gate.",
                            "reasons": list(fit_result.get("reasons", [])),
                            "metrics": fit_result.get("metrics", {}),
                            "next_action": "Discard the candidate or request a new governance decision.",
                        },
                    ],
                    metadata=metadata,
                )
            return replace(
                base,
                # Runtime accepted a complete replacement schema and the
                # deterministic final gate passed. Preserve that distinction
                # so the workflow refreshes every partition case before the
                # schema is persisted; mapping it to no_change would allow a
                # schema key to be written without materialized case values.
                decision="accepted",
                accepted_schema=decision.accepted_schema,
                requires_review=False,
                reasons=reasons or ["runtime governance decision accepted"],
                reason_details=reason_details,
                metadata=metadata,
            )
        if decision.outcome == "no_change":
            return replace(
                base,
                decision="accepted",
                accepted_schema=current_schema,
                requires_review=False,
                reasons=reasons or ["runtime governance decision found no stable change"],
                reason_details=reason_details,
                metadata=metadata,
            )
        return replace(
            base,
            decision="requires_review",
            accepted_schema=None,
            requires_review=True,
            reasons=reasons or ["runtime governance decision requires review"],
            reason_details=reason_details,
            metadata=metadata,
        )

    @staticmethod
    def _proposal_reason_details(
        *,
        proposal,
        proposal_diagnostics,
        proposal_conflicts=None,
        proposal_impact=None,
        blocker_code,
        next_action,
    ):
        details: list[dict[str, object]] = [{
            "stage": "proposal",
            "code": blocker_code,
            "message": "Deterministic proposal discovery produced schema candidates; no file mutation was performed.",
            "candidate_changes": {
                "new_keys": list(getattr(proposal, "suggested_new_keys", []) or []),
                "removed_keys": list(getattr(proposal, "suggested_removed_keys", []) or []),
            },
            "next_action": next_action,
        }]
        if proposal_conflicts or proposal_impact:
            details[0]["proposal_impact"] = dict(proposal_impact or {})
            details[0]["conflicts"] = list(proposal_conflicts or [])
        for diagnostic in proposal_diagnostics:
            candidates = {
                field: list(diagnostic.get(field, []) or [])
                for field in ("suggested_new_keys", "suggested_removed_keys")
                if diagnostic.get(field)
            }
            reasons = list(diagnostic.get("reasons", []) or [])
            if not candidates and not reasons:
                continue
            details.append({
                "stage": "proposal",
                "code": f"proposal_plugin_{diagnostic.get('plugin', 'unknown')}",
                "message": f"Proposal plugin {diagnostic.get('plugin', 'unknown')} evaluated the evidence.",
                "candidate_changes": candidates,
                "root_cause": diagnostic.get("root_cause", ""),
                "evidence": dict(diagnostic.get("evidence", {}) or {}),
                "reasons": reasons,
                "metrics": dict(diagnostic.get("metrics", {}) or {}),
            })
        return details

    def _final_fit_gate(
        self,
        *,
        partition,
        statistics,
        current_schema,
        candidate_schema,
        proposal=None,
        refresh_scope=None,
    ) -> dict[str, object]:
        """Re-evaluate the returned schema outside the LLM runtime."""
        if self._validation_pipeline is None:
            return {"passed": False, "reasons": ["governance validation pipeline is not configured"]}
        report = self._validation_pipeline.validate(
            context=GovernanceValidationContext(
                partition=partition,
                statistics=statistics,
                current_schema=current_schema,
                candidate_schema=candidate_schema,
                proposal=proposal,
                refresh_scope=refresh_scope,
            )
        )
        return report.as_dict()

    @staticmethod
    def _dump_statistics(statistics) -> dict:
        if hasattr(statistics, "model_dump"):
            value = statistics.model_dump(mode="json")
            return value if isinstance(value, dict) else {}
        return statistics if isinstance(statistics, dict) else {}

    @staticmethod
    def _statistics_key_counts(statistics: dict) -> dict[str, int]:
        value = statistics.get("case_key_stats", {})
        if not isinstance(value, dict):
            return {}
        result: dict[str, int] = {}
        for key, count in value.items():
            try:
                result[str(key).strip()] = int(count)
            except (TypeError, ValueError):
                continue
        return {key: count for key, count in result.items() if key}

    @staticmethod
    def _is_schema(schema) -> bool:
        if schema is None:
            return False
        if isinstance(schema, dict):
            return isinstance(schema.get("definitions", []), list)
        return isinstance(getattr(schema, "definitions", None), list)

    @staticmethod
    def _statistics_summary(statistics) -> dict:
        if statistics is None:
            return {}
        if hasattr(statistics, "model_dump"):
            payload = statistics.model_dump(mode="json")
            return {
                key: payload[key]
                for key in ("partition", "generated_at", "case_count", "case_key_stats")
                if key in payload
            }
        if isinstance(statistics, dict):
            return {
                key: statistics[key]
                for key in ("partition", "generated_at", "case_count", "case_key_stats")
                if key in statistics
            }
        return {}

    @staticmethod
    def _schema_keys(schema) -> list[str]:
        definitions = getattr(schema, "definitions", None)
        if definitions is None and isinstance(schema, dict):
            definitions = schema.get("definitions", [])
        keys: list[str] = []
        for definition in definitions or []:
            key = getattr(definition, "key", "")
            if not key and isinstance(definition, dict):
                key = definition.get("key", "")
            if key and key not in keys:
                keys.append(key)
        return keys
