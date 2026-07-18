from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

from internal.models import (
    CaseEventPayload,
    CaseEventSnapshot,
    IngestRequest,
    KnowbaseCaseDocument,
    KnowbaseEvent,
    KnowbaseEventType,
    TextFieldChange,
)

from .deps import KnowbaseRouteDeps
from .schemas import CaseCreateRequest, CaseUpdateRequest, CreateResourceResponse


def register_resource_routes(app: FastAPI, *, deps: KnowbaseRouteDeps) -> None:
    @app.get("/api/knowbase/cases", response_model=list[KnowbaseCaseDocument])
    async def list_knowbase_cases(partition: str) -> list[KnowbaseCaseDocument]:
        if deps.partition_service.get_partition(partition) is None:
            raise HTTPException(status_code=404, detail=f"partition not found: {partition}")
        return deps.case_repository.list_by_partition(partition)

    @app.post("/api/knowbase/cases", response_model=CreateResourceResponse)
    async def create_knowbase_case(req: CaseCreateRequest) -> CreateResourceResponse:
        try:
            ingest_result = await deps.ingest_service.ingest(
                IngestRequest(
                    partition_name=req.partition,
                    title=req.title,
                    source_content=req.source_content,
                    source_refs=req.source_refs,
                    author=req.metadata.author,
                    source=req.metadata.source or "user",
                )
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return CreateResourceResponse(
            created_type="case",
            created_id=ingest_result.case_id,
            partition=ingest_result.partition or req.partition,
            detail={
                "accepted": ingest_result.accepted,
                "processing_status": ingest_result.processing_status,
                "backlog_event_id": ingest_result.backlog_event_id,
            },
        )

    @app.get("/api/knowbase/cases/{case_id}", response_model=KnowbaseCaseDocument)
    async def get_knowbase_case_resource(case_id: str) -> KnowbaseCaseDocument:
        document = deps.case_repository.get(case_id)
        if document is None:
            raise HTTPException(status_code=404, detail=f"case not found: {case_id}")
        return document

    @app.put("/api/knowbase/cases/{case_id}", response_model=KnowbaseCaseDocument)
    async def update_knowbase_case(case_id: str, req: CaseUpdateRequest) -> KnowbaseCaseDocument:
        try:
            existing, updated, changed_fields = deps.case_write_service.update_case(
                case_id=case_id,
                title=req.title,
                source_content=req.source_content,
                source_refs=req.source_refs,
                summary_text=req.summary_text,
                semantic_profile=req.semantic_profile,
                metadata=req.metadata,
                facets=req.facets,
                raw_text=req.raw_text,
                case_detail=req.case_detail,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        await deps.event_publisher.publish(
            KnowbaseEvent(
                event_type=KnowbaseEventType.CASE_UPDATED,
                partition=updated.partition,
                resource_type="case",
                resource_id=updated.case_id,
                occurred_at=updated.updated_at,
                payload=CaseEventPayload(
                    change_kind="update",
                    before=CaseEventSnapshot(
                        title=existing.title,
                        facet_count=sum(len(values) for values in existing.facets.values()),
                        facets=existing.facets,
                    ),
                    after=CaseEventSnapshot(
                        title=updated.title,
                        facet_count=sum(len(values) for values in updated.facets.values()),
                        facets=updated.facets,
                    ),
                    changed_fields=changed_fields,
                    field_changes={
                        key: value
                        for key, value in {
                            "source_content": TextFieldChange(
                                change_type="text_updated",
                                before_length=len(existing.source_content or ""),
                                after_length=len(updated.source_content or ""),
                            ) if "source_content" in changed_fields else None,
                            "summary_text": TextFieldChange(
                                change_type="text_updated",
                                before_length=len(existing.summary_text or ""),
                                after_length=len(updated.summary_text or ""),
                            ) if "summary_text" in changed_fields else None,
                        }.items()
                        if value is not None
                    },
                    observed_facets=updated.facets,
                ),
            )
        )
        return updated

    @app.delete("/api/knowbase/cases/{case_id}")
    async def delete_knowbase_case(case_id: str) -> dict[str, str]:
        existing = deps.case_repository.get(case_id)
        if existing is None:
            raise HTTPException(status_code=404, detail=f"case not found: {case_id}")
        deps.case_repository.delete(case_id)
        await deps.event_publisher.publish(
            KnowbaseEvent(
                event_type=KnowbaseEventType.CASE_DELETED,
                partition=existing.partition,
                resource_type="case",
                resource_id=case_id,
                occurred_at=datetime.now(timezone.utc),
                payload=CaseEventPayload(
                    change_kind="delete",
                    before=CaseEventSnapshot(
                        title=existing.title,
                        facet_count=sum(len(values) for values in existing.facets.values()),
                        facets=existing.facets,
                    ),
                    observed_facets=existing.facets,
                ),
            )
        )
        return {"deleted_type": "case", "deleted_id": case_id}
