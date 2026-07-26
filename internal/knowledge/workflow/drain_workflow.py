"""Top-level orchestration for Knowledge maintenance."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from contextlib import nullcontext

from internal.knowledge.ports import (
    KnowledgeProjectionPort,
    KnowledgeFacetGovernancePort,
    KnowledgeStatisticsReaderPort,
)
from internal.knowledge.batch import BatchWorkingSetBuilder
from internal.knowledge.model import KnowledgeMutationPlan
from internal.knowledge.workflow.result import KnowledgeWorkflowResult


class KnowledgeDrainWorkflow:
    """Execute one Knowledge maintenance workflow."""

    def __init__(
        self,
        *,
        working_set_builder: BatchWorkingSetBuilder | None = None,
        partition_service=None,
        statistics: KnowledgeStatisticsReaderPort | None = None,
        facet_governance: KnowledgeFacetGovernancePort | None = None,
        projection: KnowledgeProjectionPort | None = None,
        mutation_executor=None,
        versioning_factory=None,
        decision_service=None,
        mutation_lock_factory=None,
    ):
        self._working_set_builder = working_set_builder or BatchWorkingSetBuilder()
        self._partition_service = partition_service
        self._statistics = statistics
        self._facet_governance = facet_governance
        self._projection = projection
        self._mutation_executor = mutation_executor
        self._versioning_factory = versioning_factory
        self._decision_service = decision_service
        self._mutation_lock_factory = mutation_lock_factory

    async def run_batch(self, *, batch):
        """Run the current batch workflow and return a Knowledge result."""
        working_set = self._working_set_builder.build(batch=batch)
        versioning = (
            self._versioning_factory(batch.partition)
            if self._versioning_factory is not None
            else None
        )
        statistics = (
            self._statistics.load_partition_statistics(partition=batch.partition)
            if self._statistics
            else None
        )
        base_revision = (
            versioning.begin_governance()
            if versioning is not None
            else ""
        )
        governance = (
            self._facet_governance.assess(
                statistics=statistics,
                current_schema=(
                    self._partition_service.get_facet_schema(batch.partition)
                    if self._partition_service is not None
                    else None
                ),
                working_set=working_set,
            )
            if self._facet_governance
            else None
        )
        if governance is None:
            decision_id = self._save_decision(
                batch=batch,
                status="requires_review",
                base_revision=base_revision,
                statistics=statistics,
                working_set=working_set,
                governance=None,
                review_reason="facet governance is not configured",
            )
            return KnowledgeWorkflowResult(
                batch_id=batch.batch_id,
                status="requires_review",
                iteration=1,
                decision_id=decision_id,
                requires_review=True,
                error_message="facet governance is not configured",
            )
        if governance.decision != "accepted" or governance.requires_review:
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
        target_case_ids = (
            list(governance.rebuild.target_case_ids)
            if governance.rebuild is not None and governance.rebuild.target_case_ids
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
            status="accepted",
            base_revision=base_revision,
            statistics=statistics,
            working_set=working_set,
            governance=governance,
            mutation_plan=mutation_plan,
        )
        lock_context = (
            self._mutation_lock_factory(batch.partition)
            if self._mutation_lock_factory is not None
            else nullcontext()
        )
        with lock_context:
            transaction = None
            try:
                transaction = (
                    versioning.begin_transaction(
                        message=f"knowledge: update partition {batch.partition}"
                    )
                    if versioning
                    else None
                )
                if transaction is not None:
                    transaction.register_paths(self._mutation_executor.planned_paths(plan=mutation_plan))
                apply_result = self._mutation_executor.apply(plan=mutation_plan)
                if transaction is not None:
                    transaction.register_paths(apply_result.updated_paths)
                    commit = transaction.commit()
            except Exception as exc:
                if transaction is not None:
                    transaction.register_paths(transaction.changed_paths())
                    transaction.rollback()
                self._transition_decision(
                    decision_id=decision_id,
                    status="failed",
                    error_message=str(exc),
                )
                raise
        self._transition_decision(
            decision_id=decision_id,
            status="applied",
            applied_revision=commit.revision if transaction is not None else "",
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
        review_reason="",
    ) -> str:
        if self._decision_service is None:
            return ""
        from internal.knowledge.decision import KnowledgeDecisionRecord

        record = KnowledgeDecisionRecord(
            partition=batch.partition,
            batch_id=batch.batch_id,
            status=status,
            base_revision=base_revision,
            statistics_snapshot=self._serialize(statistics),
            working_set_snapshot=self._serialize(working_set),
            governance_result=self._serialize(governance),
            mutation_plan=self._serialize(mutation_plan),
            review_reason=review_reason,
        )
        return self._decision_service.create(record).decision_id

    def _transition_decision(self, *, decision_id: str, status: str, **kwargs) -> None:
        if self._decision_service is not None and decision_id:
            self._decision_service.transition(
                decision_id=decision_id,
                status=status,
                **kwargs,
            )

    @staticmethod
    def _serialize(value):
        if value is None:
            return {}
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if is_dataclass(value):
            return asdict(value)
        if isinstance(value, dict):
            return value
        return {"value": str(value)}
