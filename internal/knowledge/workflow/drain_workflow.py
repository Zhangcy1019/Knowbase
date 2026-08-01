"""Top-level orchestration for Knowledge maintenance."""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import hashlib
import json

from internal.domain.partition.service import PartitionService
from internal.knowledge.decision.service import KnowledgeDecisionService
from internal.knowledge.execution.mutation_executor import KnowledgeMutationExecutor
from internal.knowledge.ports import (
    KnowledgeProjectionPort,
    KnowledgeGovernancePort,
    KnowledgeStatisticsReaderPort,
)
from internal.knowledge.batch import BatchWorkingSetBuilder
from internal.knowledge.model import KnowledgeMutationPlan
from internal.knowledge.workflow.result import KnowledgeWorkflowResult
from internal.knowledge.governance.contracts import GovernanceStatisticsInput
from internal.infrastructure.coordination import PartitionMutationLockProvider
from internal.versioning.partition_manager import PartitionVersioningManager
from internal.knowledge.decision.models import (
    KnowledgeDecisionExecution,
    KnowledgeDecisionInput,
    KnowledgeDecisionOutcome,
    KnowledgeDecisionRecord,
    KnowledgeDecisionStage,
)


class KnowledgeDrainWorkflow:
    """Execute one Knowledge maintenance workflow."""

    def __init__(
        self,
        *,
        working_set_builder: BatchWorkingSetBuilder | None = None,
        partition_service: PartitionService | None = None,
        case_repository=None,
        statistics: KnowledgeStatisticsReaderPort | None = None,
        governance: KnowledgeGovernancePort | None = None,
        projection: KnowledgeProjectionPort | None = None,
        mutation_executor: KnowledgeMutationExecutor | None = None,
        versioning: PartitionVersioningManager | None = None,
        decision_service: KnowledgeDecisionService | None = None,
        mutation_lock_provider: PartitionMutationLockProvider | None = None,
    ):
        self._working_set_builder: BatchWorkingSetBuilder = working_set_builder or BatchWorkingSetBuilder()
        self._partition_service: PartitionService | None = partition_service
        self._case_repository = case_repository
        self._statistics: KnowledgeStatisticsReaderPort | None = statistics
        self._governance: KnowledgeGovernancePort | None = governance
        self._projection: KnowledgeProjectionPort | None = projection
        self._mutation_executor: KnowledgeMutationExecutor | None = mutation_executor
        self._versioning: PartitionVersioningManager | None = versioning
        self._decision_service: KnowledgeDecisionService | None = decision_service
        self._mutation_lock_provider: PartitionMutationLockProvider | None = mutation_lock_provider

    async def run_batch(self, *, batch):
        """Run the current batch workflow and return a Knowledge result."""
        # ensure partition is not frozen by a pending review decision
        if self._decision_service is not None and hasattr(self._decision_service, "ensure_partition_available"):
            self._decision_service.ensure_partition_available(partition=batch.partition)

        # build the working set for the batch
        working_set = self._working_set_builder.build(batch=batch)
        versioning = self._versioning.prepare(batch.partition) if self._versioning is not None else None

        # CaseStatisticsSnapshot
        statistics = (
            self._statistics.load_partition_statistics(partition=batch.partition)
            if self._statistics
            else None
        )
        governance_statistics = GovernanceStatisticsInput(case=statistics)
        base_revision = (
            versioning.begin_governance()
            if versioning is not None
            else ""
        )
        current_schema = (
            self._partition_service.get_facet_schema(batch.partition)
            if self._partition_service is not None
            else None
        )
        if current_schema is None:
            raise RuntimeError(
                f"partition facet schema is required before Knowledge governance: {batch.partition}"
            )
        if self._governance is None:
            governance = None
        elif hasattr(self._governance, "assess_async"):
            governance = await self._governance.assess_async(
                statistics=governance_statistics,
                current_schema=current_schema,
                working_set=working_set,
            )
        else:
            # Keep minimal synchronous test doubles usable; production governance
            # implements the typed async port above.
            governance = self._governance.assess_deterministic(
                statistics=governance_statistics,
                current_schema=current_schema,
                working_set=working_set,
            )
        if governance is None:
            decision_id = self._save_decision(
                batch=batch,
                status="requires_review",
                base_revision=base_revision,
                statistics=statistics,
                working_set=working_set,
                governance=None,
                review_reason="knowledge governance is not configured",
            )
            return KnowledgeWorkflowResult(
                batch_id=batch.batch_id,
                status="requires_review",
                iteration=1,
                decision_id=decision_id,
                requires_review=True,
                error_message="knowledge governance is not configured",
            )
        if governance.decision not in {"accepted", "no_change"} or governance.requires_review:
            status = "requires_review" if governance.requires_review else "no_change"
            decision_id = self._save_decision(
                batch=batch,
                status=status,
                base_revision=base_revision,
                statistics=statistics,
                working_set=working_set,
                governance=governance,
                review_reason="; ".join(governance.reasons),
            )
            return KnowledgeWorkflowResult(
                batch_id=batch.batch_id,
                status="requires_review" if governance.requires_review else "completed",
                iteration=1,
                decision_id=decision_id,
                requires_review=governance.requires_review,
                error_message="; ".join(governance.reasons),
            )
        if governance.decision == "accepted" and self._case_repository is not None:
            target_case_ids = [
                case.case_id
                for case in self._case_repository.list_by_partition(batch.partition)
            ]
        else:
            target_case_ids = (
                list(governance.refresh_scope.case_ids)
                if governance.refresh_scope is not None and governance.refresh_scope.case_ids
                else list(working_set.affected_case_ids)
            )
        projection = (
            self._projection.plan(
                partition=batch.partition,
                accepted_schema=governance.accepted_schema,
                case_ids=target_case_ids,
            )
            if self._projection and governance.accepted_schema is not None
            else None
        )
        mutation_plan = KnowledgeMutationPlan.from_governance(
            batch=batch,
            governance=governance,
            projection=projection,
        )
        if self._mutation_executor is None:
            decision_id = self._save_decision(
                batch=batch,
                status="requires_review",
                base_revision=base_revision,
                statistics=statistics,
                working_set=working_set,
                governance=governance,
                mutation_plan=mutation_plan,
                review_reason="knowledge mutation executor is not configured",
            )
            return KnowledgeWorkflowResult(
                batch_id=batch.batch_id,
                status="requires_review",
                iteration=1,
                mutation_plan_id=mutation_plan.plan_id,
                decision_id=decision_id,
                requires_review=True,
                error_message="knowledge mutation executor is not configured",
            )
        decision_id = self._save_decision(
            batch=batch,
            base_revision=base_revision,
            statistics=statistics,
            working_set=working_set,
            governance=governance,
            mutation_plan=mutation_plan,
            projection=projection,
            status="accepted",
        )
        lock_context = (
            self._mutation_lock_provider.lock(batch.partition)
            if self._mutation_lock_provider is not None
            else nullcontext()
        )
        with lock_context:
            transaction = None
            planned_paths = self._mutation_executor.planned_paths(plan=mutation_plan)
            projection_changes = list(getattr(projection, "changes", []) or []) if projection else []
            projection_targets = list(getattr(projection, "target_case_ids", []) or []) if projection else []
            projection_status = (
                "completed"
                if projection_changes
                else "no_materialized_values"
                if mutation_plan.accepted_schema is not None
                else "no_action"
                if projection_targets
                else "not_run"
            )
            mutation_kind = (
                "schema_and_projection"
                if mutation_plan.accepted_schema is not None and projection_changes
                else "schema_change"
                if mutation_plan.accepted_schema is not None
                else "projection_only"
                if projection_changes
                else "none"
            )
            self._transition_decision(
                decision_id=decision_id,
                status="applying",
                execution={
                    "plan": self._serialize(mutation_plan),
                    "planned_paths": planned_paths,
                    "mutation_kind": mutation_kind,
                    "projection_status": projection_status,
                    "apply_status": "not_run",
                },
            )
            try:
                transaction = (
                    versioning.begin_transaction(
                        message=f"knowledge: update partition {batch.partition}"
                    )
                    if versioning
                    else None
                )
                if transaction is not None:
                    transaction.register_paths(planned_paths)
                apply_result = self._mutation_executor.apply(plan=mutation_plan)
                if transaction is not None:
                    transaction.register_paths(apply_result.updated_paths)
                    commit = transaction.commit()
            except Exception as exc:
                changed_paths = transaction.changed_paths() if transaction is not None else []
                if transaction is not None:
                    transaction.register_paths(changed_paths)
                    transaction.rollback()
                self._transition_decision(
                    decision_id=decision_id,
                    status="failed",
                    error_message=str(exc),
                    stages={
                        "apply": KnowledgeDecisionStage(
                            status="failed",
                            input={"planned_paths": planned_paths},
                            reasons=[str(exc)],
                            error=str(exc),
                        )
                    },
                    execution={
                        "plan": self._serialize(mutation_plan),
                        "planned_paths": planned_paths,
                        "changed_paths": changed_paths,
                        "rolled_back": transaction is not None,
                        "error": str(exc),
                        "mutation_kind": mutation_kind,
                        "projection_status": projection_status,
                        "apply_status": "failed",
                    },
                )
                raise
        apply_has_changes = bool(apply_result.updated_case_ids or apply_result.updated_paths)
        if transaction is not None:
            apply_has_changes = apply_has_changes or bool(commit.paths)
        self._transition_decision(
            decision_id=decision_id,
            status="applied",
            applied_revision=commit.revision if transaction is not None else "",
            stages={
                "apply": KnowledgeDecisionStage(
                    status="completed" if apply_has_changes else "passed",
                    input={"planned_paths": planned_paths},
                    output={
                        "updated_case_ids": list(apply_result.updated_case_ids),
                        "updated_paths": list(apply_result.updated_paths),
                        "revision": commit.revision if transaction is not None else None,
                        "commit_paths": list(commit.paths) if transaction is not None else [],
                    },
                )
            },
            execution={
                "plan": self._serialize(mutation_plan),
                "planned_paths": planned_paths,
                "changed_paths": list(apply_result.updated_paths),
                "updated_case_ids": list(apply_result.updated_case_ids),
                "applied_revision": commit.revision if transaction is not None else None,
                "mutation_kind": mutation_kind,
                "projection_status": projection_status,
                "apply_status": "applied" if apply_has_changes else "no_op",
            },
        )
        return KnowledgeWorkflowResult(
            batch_id=batch.batch_id,
            status="completed",
            iteration=1,
            mutation_plan_id=mutation_plan.plan_id,
            decision_id=decision_id,
            committed_revision=commit.revision if transaction is not None else "",
            schema_changed=mutation_plan.accepted_schema is not None,
            applied_case_ids=apply_result.updated_case_ids,
            mutation_kind=mutation_kind,
            projection_status=projection_status,
            apply_status="applied" if apply_has_changes else "no_op",
        )

    async def run_manual(self, *, batch):
        """Run one manually submitted Knowledge batch through the same pipeline."""
        return await self.run_batch(batch=batch)

    def _save_decision(
        self,
        *,
        batch,
        status,
        base_revision,
        statistics,
        working_set,
        governance,
        mutation_plan=None,
        projection=None,
        review_reason="",
    ) -> str:
        if self._decision_service is None:
            return ""
        outcome = self._decision_outcome(governance=governance, status=status)
        governance_metadata = dict(getattr(governance, "metadata", {}) or {}) if governance is not None else {}
        record = KnowledgeDecisionRecord(
            partition=batch.partition,
            batch_id=batch.batch_id,
            status=status,
            runtime_run_id=str(governance_metadata.get("run_id") or "") or None,
            input=KnowledgeDecisionInput(
                base_revision=base_revision or None,
                statistics_fingerprint=self._fingerprint(statistics),
                statistics_snapshot=self._serialize(statistics) or None,
                working_set=self._serialize(working_set) or None,
            ),
            stages=self._build_stages(
                governance=governance,
                projection=projection,
                mutation_plan=mutation_plan,
            ),
            outcome=outcome,
            execution=(
                KnowledgeDecisionExecution(plan=self._serialize(mutation_plan))
                if mutation_plan is not None
                else None
            ),
            reviewer=None,
            review_reason=review_reason or None,
        )
        return self._decision_service.create(record).decision_id

    def _transition_decision(self, *, decision_id: str, status: str, **kwargs) -> None:
        if self._decision_service is not None and decision_id:
            self._decision_service.transition(
                decision_id=decision_id,
                status=status,
                **kwargs,
            )

    @classmethod
    def _build_stages(cls, *, governance, projection, mutation_plan) -> dict[str, KnowledgeDecisionStage]:
        if governance is None:
            return {}
        evidence = getattr(governance, "evidence", None)
        coverage = getattr(governance, "coverage", None)
        rebuild = getattr(governance, "rebuild", None)
        proposal = getattr(governance, "proposal", None)
        preparation_output = {
            "coverage": cls._serialize(coverage),
            "rebuild": cls._serialize(rebuild),
            "consistency_status": getattr(evidence, "consistency_status", None),
            "consistency_mismatches": list(getattr(evidence, "consistency_mismatches", [])),
            "notes": list(getattr(evidence, "preparation_notes", [])),
        }
        proposal_output = {
            "proposal": cls._serialize(proposal),
            "status": getattr(evidence, "proposal_status", None),
            "diagnostics": list(getattr(evidence, "proposal_diagnostics", [])),
            "conflicts": list(getattr(evidence, "proposal_conflicts", [])),
            "impact": dict(getattr(evidence, "proposal_impact", {})),
            "reason_details": list(getattr(evidence, "proposal_reason_details", [])),
        }
        consistency_status = getattr(evidence, "consistency_status", None)
        proposal_status = getattr(evidence, "proposal_status", None)
        preparation_stage_status = (
            "blocked"
            if consistency_status in {"inconsistent", "stale"}
            else "passed"
            if coverage is not None
            else "no_action"
        )
        proposal_stage_status = (
            "blocked"
            if proposal_status == "blocked"
            else "completed"
            if getattr(proposal, "suggested_new_keys", [])
            or getattr(proposal, "suggested_updated_keys", [])
            or getattr(proposal, "suggested_removed_keys", [])
            else "no_action"
        )
        stages = {
            "preparation": KnowledgeDecisionStage(
                status=preparation_stage_status,
                output=preparation_output,
                reasons=(
                    ["snapshot and materialized indexes are inconsistent"]
                    if consistency_status in {"inconsistent", "stale"}
                    else []
                ),
            ),
            "proposal": KnowledgeDecisionStage(
                status=proposal_stage_status,
                output=proposal_output,
            ),
        }
        metadata = dict(getattr(governance, "metadata", {}) or {})
        details = list(getattr(governance, "reason_details", []) or [])
        runtime_details = [item for item in details if item.get("stage") == "runtime"]
        validation_details = [item for item in details if item.get("stage") == "validation"]
        proposal_failed = any(
            item.get("code") == "proposal_plugin_failed"
            for item in details
        )
        if proposal_failed:
            stages["proposal"] = stages["proposal"].model_copy(update={"status": "failed"})
        if metadata.get("run_id") or runtime_details:
            stages["runtime"] = KnowledgeDecisionStage(
                status="completed" if metadata.get("run_id") else "failed",
                output={"metadata": metadata, "details": runtime_details},
            )
        if validation_details or metadata.get("final_fit_metrics") or metadata.get("validation"):
            stages["validation"] = KnowledgeDecisionStage(
                status="completed",
                output={
                    "details": validation_details,
                    "metadata": {
                        key: metadata[key]
                        for key in ("validation", "final_fit_metrics")
                        if key in metadata
                    },
                },
            )
        if projection is not None:
            projection_changes = list(getattr(projection, "changes", []) or [])
            projection_targets = list(getattr(projection, "target_case_ids", []) or [])
            stages["projection"] = KnowledgeDecisionStage(
                status=(
                    "completed"
                    if projection_changes
                    else "blocked"
                    if getattr(mutation_plan, "accepted_schema", None) is not None
                    else "passed"
                    if projection_targets
                    else "no_action"
                ),
                output=cls._serialize(projection),
            )
        if mutation_plan is not None:
            mutation_changes = list(getattr(mutation_plan, "case_changes", []) or [])
            schema_change = getattr(mutation_plan, "accepted_schema", None) is not None
            stages["mutation_plan"] = KnowledgeDecisionStage(
                status="completed" if mutation_changes or schema_change else "no_action",
                output=cls._serialize(mutation_plan),
            )
        return stages

    @staticmethod
    def _decision_outcome(*, governance, status: str) -> KnowledgeDecisionOutcome:
        if governance is None:
            return KnowledgeDecisionOutcome(
                outcome="requires_review",
                reasons=["knowledge governance is not configured"],
            )
        outcome = "requires_review" if status == "requires_review" else (
            "accepted" if status in {"accepted", "applying", "applied"} else "no_change"
        )
        return KnowledgeDecisionOutcome(
            outcome=outcome,
            accepted_schema=(
                governance.accepted_schema.model_dump(mode="json")
                if hasattr(getattr(governance, "accepted_schema", None), "model_dump")
                else getattr(governance, "accepted_schema", None)
            ),
            reasons=list(getattr(governance, "reasons", []) or []),
            reason_details=list(getattr(governance, "reason_details", []) or []),
        )

    @staticmethod
    def _fingerprint(value) -> str | None:
        payload = KnowledgeDrainWorkflow._serialize(value)
        if not payload:
            return None
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _serialize(value):
        if value is None:
            return {}
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if is_dataclass(value):
            return asdict(value)
        if isinstance(value, list):
            return [KnowledgeDrainWorkflow._serialize(item) for item in value]
        if isinstance(value, tuple):
            return [KnowledgeDrainWorkflow._serialize(item) for item in value]
        if isinstance(value, dict):
            return {
                str(key): KnowledgeDrainWorkflow._serialize(item)
                for key, item in value.items()
            }
        return {"value": str(value)}
