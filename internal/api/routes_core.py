from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException

from internal.models import (
    IngestRequest,
    IngestResult,
    PartitionDocument,
    PartitionFacetDefinition,
    PartitionFacetSchema,
    PartitionSemanticIndexDocument,
    QueryRequest,
    QueryResult,
)

from .deps import KnowbaseRouteDeps
from .schemas import (
    PartitionFacetSchemaResponse,
    PartitionFacetSchemaUpsertRequest,
    PartitionSchemaSuggestionRequest,
    PartitionSchemaSuggestionResponse,
    PartitionUpsertRequest,
)


def register_core_routes(app: FastAPI, *, deps: KnowbaseRouteDeps) -> None:
    @app.get("/api/knowbase/partitions", response_model=list[PartitionDocument])
    async def list_knowbase_partitions() -> list[PartitionDocument]:
        return deps.partition_service.list_partitions()

    @app.post("/api/knowbase/partitions", response_model=PartitionDocument)
    async def create_knowbase_partition(req: PartitionUpsertRequest) -> PartitionDocument:
        existing = deps.partition_service.get_partition(req.partition_name)
        if existing is not None:
            raise HTTPException(status_code=409, detail=f"partition already exists: {req.partition_name}")

        now = datetime.now(timezone.utc)
        document = PartitionDocument(
            partition_name=req.partition_name,
            scenario_description=req.scenario_description,
            status=req.status,
            created_at=now,
            updated_at=now,
        )
        persisted = deps.partition_service.save_partition(document)
        deps.partition_service.save_facet_schema(
            partition_name=req.partition_name,
            facet_schema=PartitionFacetSchema(),
        )
        return persisted

    @app.get("/api/knowbase/partitions/{partition_name}", response_model=PartitionDocument)
    async def get_knowbase_partition(partition_name: str) -> PartitionDocument:
        document = deps.partition_service.get_partition(partition_name)
        if document is None:
            raise HTTPException(status_code=404, detail=f"partition not found: {partition_name}")
        return document

    @app.post("/api/knowbase/partitions/schema-suggestions", response_model=PartitionSchemaSuggestionResponse)
    async def suggest_partition_schema(req: PartitionSchemaSuggestionRequest) -> PartitionSchemaSuggestionResponse:
        try:
            suggestion = deps.partition_schema_suggester.suggest(
                partition_name=req.partition_name,
                scenario_description=req.scenario_description,
                current_facet_definitions=[
                    PartitionFacetDefinition(**item.model_dump())
                    for item in req.current_facet_definitions
                ],
                cautious_update=req.cautious_update,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return PartitionSchemaSuggestionResponse(
            suggested_facets=[{"key": item.key, "value": item.value} for item in suggestion.suggested_facets],
            rationale=suggestion.rationale,
            should_update_existing=suggestion.should_update_existing,
        )

    @app.get("/api/knowbase/partitions/{partition_name}/facet-schema", response_model=PartitionFacetSchemaResponse)
    async def get_knowbase_partition_facet_schema(partition_name: str) -> PartitionFacetSchemaResponse:
        document = deps.partition_service.get_facet_schema_document(partition_name)
        if document is None:
            raise HTTPException(status_code=404, detail=f"partition not found: {partition_name}")
        return PartitionFacetSchemaResponse(
            partition_name=document.partition_name,
            facet_schema=document.facet_schema,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )

    @app.put("/api/knowbase/partitions/{partition_name}/facet-schema", response_model=PartitionFacetSchemaResponse)
    async def upsert_knowbase_partition_facet_schema(
        partition_name: str,
        req: PartitionFacetSchemaUpsertRequest,
    ) -> PartitionFacetSchemaResponse:
        document = deps.partition_service.save_facet_schema(
            partition_name=partition_name,
            facet_schema=PartitionFacetSchema(
                definitions=[item.model_dump() for item in req.definitions],
                metadata=req.metadata,
            ),
        )
        return PartitionFacetSchemaResponse(
            partition_name=document.partition_name,
            facet_schema=document.facet_schema,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )

    @app.get("/api/knowbase/partitions/{partition_name}/semantic-index", response_model=PartitionSemanticIndexDocument)
    async def get_knowbase_partition_semantic_index(partition_name: str) -> PartitionSemanticIndexDocument:
        document = deps.partition_service.get_semantic_index_document(partition_name)
        if document is None:
            raise HTTPException(status_code=404, detail=f"partition not found: {partition_name}")
        return document

    @app.put("/api/knowbase/partitions/{partition_name}", response_model=PartitionDocument)
    async def upsert_knowbase_partition(partition_name: str, req: PartitionUpsertRequest) -> PartitionDocument:
        if partition_name != req.partition_name:
            raise HTTPException(status_code=400, detail="path partition_name must match request.partition_name")
        now = datetime.now(timezone.utc)
        existing = deps.partition_service.get_partition(partition_name)
        if existing is None:
            raise HTTPException(status_code=404, detail=f"partition not found: {partition_name}")
        document = PartitionDocument(
            partition_name=req.partition_name,
            scenario_description=req.scenario_description,
            status=req.status,
            created_at=existing.created_at,
            updated_at=now,
        )
        return deps.partition_service.save_partition(document)

    @app.delete("/api/knowbase/partitions/{partition_name}")
    async def delete_knowbase_partition(partition_name: str) -> dict[str, Any]:
        existing = deps.partition_service.get_partition(partition_name)
        if existing is None:
            raise HTTPException(status_code=404, detail=f"partition not found: {partition_name}")
        try:
            deleted_case_count = 0
            for case_document in deps.case_repository.list_by_partition(partition_name):
                deps.case_repository.delete(case_document.case_id)
                deleted_case_count += 1

            deleted_run_count = 0
            for run in deps.runtime_service.list_runs(partition=partition_name):
                deps.runtime_service.delete_run(run.run_id)
                deleted_run_count += 1

            deps.partition_service.delete_partition(partition_name)
            return {
                "deleted_type": "partition",
                "deleted_id": partition_name,
                "deleted_case_count": deleted_case_count,
                "deleted_run_count": deleted_run_count,
                "deleted_event_backlog_count": 0,
            }
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=f"failed to delete partition: {exc}") from exc

    @app.post("/api/knowbase/ingest", response_model=IngestResult)
    async def knowbase_ingest(req: IngestRequest) -> IngestResult:
        try:
            return await deps.ingest_service.ingest(req)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=f"knowbase ingest failed: {exc}") from exc

    @app.post("/api/knowbase/query", response_model=QueryResult)
    async def knowbase_query(req: QueryRequest) -> QueryResult:
        try:
            return await deps.query_flow.run(req)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=f"knowbase query failed: {exc}") from exc
