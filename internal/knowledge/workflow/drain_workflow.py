"""Top-level orchestration for Knowledge maintenance."""

from __future__ import annotations

from internal.knowledge.ports import (
    KnowledgePatchBuilderPort,
    KnowledgeProjectionPort,
    KnowledgeFacetGovernancePort,
    KnowledgeStatisticsReaderPort,
)
from internal.knowledge.workflow.result import KnowledgeWorkflowResult


class KnowledgeDrainWorkflow:
    """Execute one Knowledge maintenance workflow."""

    def __init__(
        self,
        *,
        request_factory,
        runtime_service,
        statistics: KnowledgeStatisticsReaderPort | None = None,
        facet_governance: KnowledgeFacetGovernancePort | None = None,
        projection: KnowledgeProjectionPort | None = None,
        patch: KnowledgePatchBuilderPort | None = None,
        versioning=None,
    ):
        self._request_factory = request_factory
        self._runtime_service = runtime_service
        self._statistics = statistics
        self._facet_governance = facet_governance
        self._projection = projection
        self._patch = patch
        self._versioning = versioning

    async def run_batch(self, *, batch):
        """Run the current batch workflow and return a Knowledge result."""
        transaction = (
            self._versioning.begin_transaction(
                message=f"knowledge: update partition {batch.partition}"
            )
            if self._versioning
            else None
        )
        statistics = (
            self._statistics.load_partition_statistics(partition=batch.partition)
            if self._statistics
            else None
        )
        governance = (
            self._facet_governance.assess(
                statistics=statistics,
                current_schema=None,
                working_set=batch,
            )
            if self._facet_governance
            else None
        )
        projection = (
            self._projection.plan(
                accepted_schema=governance.accepted_schema,
                case_ids=[],
            )
            if self._projection and governance and governance.accepted_schema is not None
            else None
        )
        patch = (
            self._patch.build(
                schema_change=governance,
                projection_change=projection,
                batch=batch,
            )
            if self._patch and governance
            else None
        )
        request = self._request_factory.build_for_batch(batch=batch, patch=patch)
        try:
            runtime_result = await self._runtime_service.run_request(request=request)
            if runtime_result.status == "completed":
                if transaction is not None:
                    if self._statistics and hasattr(self._statistics, "stamp_source_revision"):
                        self._statistics.stamp_source_revision(
                            partition=batch.partition,
                            source_revision=transaction.base_revision,
                        )
                    transaction.commit()
        except Exception:
            if transaction is not None:
                transaction.register_paths(transaction.changed_paths())
                transaction.rollback()
            raise
        return KnowledgeWorkflowResult(
            batch_id=batch.batch_id,
            status=runtime_result.status,
            iteration=1,
            runtime_run_ids=[runtime_result.run_id] if runtime_result.run_id else [],
            requires_review=runtime_result.requires_review,
            error_message=runtime_result.final_summary if runtime_result.status == "failed" else "",
        )

    async def run_manual(self, *, request):
        """Run a manually constructed Knowledge request."""
        runtime_result = await self._runtime_service.run_request(request=request)
        return KnowledgeWorkflowResult(
            status=runtime_result.status,
            iteration=1,
            runtime_run_ids=[runtime_result.run_id] if runtime_result.run_id else [],
            requires_review=runtime_result.requires_review,
            error_message=runtime_result.final_summary if runtime_result.status == "failed" else "",
        )
