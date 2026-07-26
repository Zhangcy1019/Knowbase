"""Knowledge inspection and drain history routes."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from internal.api.schemas import (
    KnowledgeDrainDetailResponse,
    KnowledgeDrainSummaryResponse,
    KnowledgeOverviewResponse,
    CaseStatisticsResponse,
    QueryStatisticsResponse,
)

from .deps import KnowbaseRouteDeps


def register_knowledge_routes(app: FastAPI, *, deps: KnowbaseRouteDeps) -> None:
    @app.get(
        "/api/knowbase/knowledge/drains",
        response_model=list[KnowledgeDrainSummaryResponse],
    )
    async def list_knowledge_drains(partition: str = "") -> list[KnowledgeDrainSummaryResponse]:
        if deps.decision_service is None:
            return []
        records = deps.decision_service.list(partition=partition)
        return [_to_summary(record) for record in records]

    @app.get(
        "/api/knowbase/knowledge/drains/{decision_id}",
        response_model=KnowledgeDrainDetailResponse,
    )
    async def get_knowledge_drain(decision_id: str) -> KnowledgeDrainDetailResponse:
        if deps.decision_service is None:
            raise HTTPException(status_code=404, detail=f"knowledge drain not found: {decision_id}")
        record = deps.decision_service.get(decision_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"knowledge drain not found: {decision_id}")
        return _to_detail(record)

    @app.get(
        "/api/knowbase/knowledge/overview",
        response_model=KnowledgeOverviewResponse,
    )
    async def get_knowledge_overview(partition: str) -> KnowledgeOverviewResponse:
        if deps.decision_service is None:
            return KnowledgeOverviewResponse(partition=partition)
        statistics = (
            deps.statistics_service.load_partition_statistics(partition=partition)
            if deps.statistics_service is not None
            else None
        )
        records = deps.decision_service.list(partition=partition)
        pending = sum(record.status == "requires_review" for record in records)
        last_drain = max(records, key=lambda record: record.updated_at).updated_at if records else None
        return KnowledgeOverviewResponse(
            partition=partition,
            case_count=statistics.case_count if statistics is not None else 0,
            facet_key_count=len(statistics.case_key_stats) if statistics is not None else 0,
            pending_decision_count=pending,
            last_drain_at=last_drain,
        )

    @app.get(
        "/api/knowbase/partitions/{partition}/query-statistics",
        response_model=QueryStatisticsResponse,
    )
    async def get_partition_query_statistics(partition: str) -> QueryStatisticsResponse:
        if deps.query_statistics_service is None:
            return QueryStatisticsResponse(partition=partition)
        statistics = deps.query_statistics_service.load_partition_statistics(partition=partition)
        if statistics is None:
            return QueryStatisticsResponse(partition=partition)
        return QueryStatisticsResponse(**statistics.model_dump())

    @app.get(
        "/api/knowbase/partitions/{partition}/case-statistics",
        response_model=CaseStatisticsResponse,
    )
    async def get_partition_case_statistics(partition: str) -> CaseStatisticsResponse:
        if deps.statistics_service is None:
            return CaseStatisticsResponse(partition=partition)
        statistics = deps.statistics_service.load_partition_statistics(partition=partition)
        if statistics is None:
            return CaseStatisticsResponse(partition=partition)
        return CaseStatisticsResponse(
            partition=statistics.partition,
            generated_at=statistics.generated_at,
            case_count=statistics.case_count,
            case_key_stats=statistics.case_key_stats,
            case_value_stats=statistics.case_value_stats,
        )


def _to_summary(record) -> KnowledgeDrainSummaryResponse:
    mutation_plan = record.mutation_plan or {}
    governance = record.governance_result or {}
    proposal = governance.get("proposal") or {}
    return KnowledgeDrainSummaryResponse(
        decision_id=record.decision_id,
        partition=record.partition,
        batch_id=record.batch_id,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
        base_revision=record.base_revision,
        applied_revision=record.applied_revision,
        mutation_plan_id=str(mutation_plan.get("plan_id", "")),
        change_count=len(mutation_plan.get("case_changes", [])),
        schema_changed=any(
            proposal.get(name, [])
            for name in ("suggested_new_keys", "suggested_updated_keys", "suggested_removed_keys")
        ),
        requires_review=record.status == "requires_review",
        error_message=record.error_message,
    )


def _to_detail(record) -> KnowledgeDrainDetailResponse:
    summary = _to_summary(record)
    return KnowledgeDrainDetailResponse(
        **summary.model_dump(),
        statistics_fingerprint=record.statistics_fingerprint,
        statistics_snapshot=record.statistics_snapshot,
        working_set_snapshot=record.working_set_snapshot,
        governance_result=record.governance_result,
        mutation_plan=record.mutation_plan,
        reviewer=record.reviewer,
        review_reason=record.review_reason,
        supersedes_decision_id=record.supersedes_decision_id,
    )


__all__ = ["register_knowledge_routes"]
