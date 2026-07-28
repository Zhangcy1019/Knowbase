"""Knowledge inspection and drain history routes."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from internal.api.schemas import (
    KnowledgeDrainDetailResponse,
    KnowledgeDrainSummaryResponse,
    KnowledgeReviewActionRequest,
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

    @app.post(
        "/api/knowbase/knowledge/drains/{decision_id}/review",
        response_model=KnowledgeDrainDetailResponse,
    )
    async def review_knowledge_drain(
        decision_id: str,
        request: KnowledgeReviewActionRequest,
    ) -> KnowledgeDrainDetailResponse:
        if deps.decision_service is None:
            raise HTTPException(status_code=404, detail="knowledge decision service is unavailable")
        record = deps.decision_service.get(decision_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"knowledge drain not found: {decision_id}")
        if record.status != "requires_review":
            raise HTTPException(
                status_code=409,
                detail=f"knowledge drain is not waiting for review: {record.status}",
            )
        target_status = {
            "approve": "approved",
            "discard": "discarded",
            "retry": "retry_requested",
        }[request.action]
        try:
            updated = deps.decision_service.transition(
                decision_id=decision_id,
                status=target_status,
                reviewer=request.reviewer.strip() or "manual",
                reason=request.reason.strip(),
                actor="manual_review",
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return _to_detail(updated)

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
    execution = record.execution
    plan = execution.plan if execution is not None else None
    plan = plan or {}
    outcome = record.outcome
    accepted_schema = outcome.accepted_schema
    transition_error = next(
        (item.error for item in reversed(record.status_history) if item.error),
        None,
    )
    return KnowledgeDrainSummaryResponse(
        decision_id=record.decision_id,
        runtime_run_id=record.runtime_run_id or "",
        partition=record.partition,
        batch_id=record.batch_id,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
        base_revision=record.input.base_revision or "",
        applied_revision=(record.execution.applied_revision if record.execution is not None else None) or "",
        mutation_plan_id=str(plan.get("plan_id", "")),
        change_count=len(plan.get("case_changes", [])),
        schema_changed=accepted_schema is not None,
        requires_review=record.status == "requires_review",
        error_message=transition_error or (execution.error if execution is not None else None) or "",
    )


def _to_detail(record) -> KnowledgeDrainDetailResponse:
    summary = _to_summary(record)
    return KnowledgeDrainDetailResponse(
        **summary.model_dump(),
        input=record.input.model_dump(mode="json"),
        stages={key: value.model_dump(mode="json") for key, value in record.stages.items()},
        outcome=record.outcome.model_dump(mode="json"),
        execution=record.execution.model_dump(mode="json") if record.execution is not None else None,
        status_history=[item.model_dump(mode="json") for item in record.status_history],
        reviewer=record.reviewer,
        review_reason=record.review_reason,
        supersedes_decision_id=record.supersedes_decision_id,
    )


__all__ = ["register_knowledge_routes"]
