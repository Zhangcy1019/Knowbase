from __future__ import annotations

from collections import defaultdict

from fastapi import FastAPI, HTTPException

from internal.models import KnowbaseCaseDocument

from .deps import KnowbaseRouteDeps
from .schemas import (
    OverviewDocumentDetailResponse,
    OverviewGraphEdge,
    OverviewGraphMode,
    OverviewGraphNode,
    OverviewGraphResponse,
    OverviewGraphStats,
    OverviewNodeType,
)


def register_graph_routes(app: FastAPI, *, deps: KnowbaseRouteDeps) -> None:
    @app.get("/api/knowbase/graph/{partition_name}", response_model=OverviewGraphResponse)
    async def get_knowbase_graph(
        partition_name: str,
        mode: OverviewGraphMode = "facet-case",
    ) -> OverviewGraphResponse:
        partition = deps.partition_service.get_partition(partition_name)
        if partition is None:
            raise HTTPException(status_code=404, detail=f"partition not found: {partition_name}")

        cases = deps.case_repository.list_by_partition(partition_name)
        facet_nodes, edges = _build_facet_case_projection(cases)
        nodes = [*facet_nodes, *[_build_case_node(document) for document in cases]]

        return OverviewGraphResponse(
            partition=partition,
            mode=mode,
            nodes=nodes,
            edges=edges,
            stats=OverviewGraphStats(
                facet_count=len(facet_nodes),
                case_count=len(cases),
            ),
        )

    @app.get(
        "/api/knowbase/graph/{partition_name}/documents/{node_type}/{node_id}",
        response_model=OverviewDocumentDetailResponse,
    )
    async def get_knowbase_graph_document_detail(
        partition_name: str,
        node_type: OverviewNodeType,
        node_id: str,
    ) -> OverviewDocumentDetailResponse:
        partition = deps.partition_service.get_partition(partition_name)
        if partition is None:
            raise HTTPException(status_code=404, detail=f"partition not found: {partition_name}")

        if node_type == "case":
            document = deps.case_repository.get(node_id)
            if document is None or document.partition != partition_name:
                raise HTTPException(status_code=404, detail=f"case not found: {node_id}")
            return _build_case_detail_response(document)

        cases = deps.case_repository.list_by_partition(partition_name)
        detail = _build_facet_detail_response(partition_name=partition_name, node_id=node_id, cases=cases)
        if detail is None:
            raise HTTPException(status_code=404, detail=f"facet node not found: {node_id}")
        return detail


def _build_facet_case_projection(cases: list[KnowbaseCaseDocument]) -> tuple[list[OverviewGraphNode], list[OverviewGraphEdge]]:
    grouped_case_ids: dict[str, list[str]] = defaultdict(list)
    grouped_meta: dict[str, tuple[str, str]] = {}
    edges: list[OverviewGraphEdge] = []

    for document in cases:
        for key, values in document.facets.items():
            normalized_key = key.strip()
            if not normalized_key:
                continue
            for value in values:
                normalized_value = str(value).strip()
                if not normalized_value:
                    continue
                node_id = _make_facet_node_id(normalized_key, normalized_value)
                grouped_case_ids[node_id].append(document.case_id)
                grouped_meta[node_id] = (normalized_key, normalized_value)
                edges.append(
                    OverviewGraphEdge(
                        id=f"{node_id}->case:{document.case_id}",
                        source=f"facet:{node_id}",
                        target=f"case:{document.case_id}",
                        relation="has_case",
                    )
                )

    facet_nodes = [
        OverviewGraphNode(
            id=f"facet:{node_id}",
            type="facet",
            label=value,
            facet=value,
            status="active",
            dirty=False,
            meta={
                "facet_key": key,
                "facet_value": value,
                "case_count": len(grouped_case_ids[node_id]),
            },
        )
        for node_id, (key, value) in sorted(grouped_meta.items(), key=lambda item: (item[1][0], item[1][1].lower()))
    ]
    return facet_nodes, edges


def _build_case_node(document: KnowbaseCaseDocument) -> OverviewGraphNode:
    primary_tag = _select_primary_facet_label(document.facets)
    return OverviewGraphNode(
        id=f"case:{document.case_id}",
        type="case",
        label=document.title or document.case_id,
        facet=primary_tag,
        status=document.metadata.status,
        dirty=False,
        meta={
            "case_id": document.case_id,
            "facet_value_count": sum(len(values) for values in document.facets.values()),
        },
    )


def _build_case_detail_response(document: KnowbaseCaseDocument) -> OverviewDocumentDetailResponse:
    return OverviewDocumentDetailResponse(
        id=document.case_id,
        type="case",
        title=document.title or document.case_id,
        partition=document.partition,
        facet=_select_primary_facet_label(document.facets),
        raw_text=document.source_content,
        metadata={
            "status": document.metadata.status,
            "author": document.metadata.author,
            "source": document.metadata.source,
            "facets": document.facets,
            "created_at": document.created_at,
            "updated_at": document.updated_at,
        },
        content=document.model_dump(mode="json"),
    )


def _build_facet_detail_response(
    *,
    partition_name: str,
    node_id: str,
    cases: list[KnowbaseCaseDocument],
) -> OverviewDocumentDetailResponse | None:
    parsed = _parse_facet_node_id(node_id)
    if parsed is None:
        return None
    tag_key, tag_value = parsed
    matched_cases = [
        document
        for document in cases
        if tag_value in document.facets.get(tag_key, [])
    ]
    if not matched_cases:
        return None
    return OverviewDocumentDetailResponse(
        id=node_id,
        type="facet",
        title=tag_value,
        partition=partition_name,
        facet=tag_value,
        raw_text=f"Facet value node for {tag_key} = {tag_value}",
        metadata={
            "facet_key": tag_key,
            "facet_value": tag_value,
            "case_count": len(matched_cases),
            "case_ids": [document.case_id for document in matched_cases],
        },
        content={
            "facet_key": tag_key,
            "facet_value": tag_value,
            "cases": [document.model_dump(mode="json") for document in matched_cases],
        },
    )


def _select_primary_facet_label(facets: dict[str, list[str]]) -> str:
    for key in sorted(facets):
        values = facets.get(key) or []
        for value in values:
            normalized = str(value).strip()
            if normalized:
                return normalized
    return ""


def _make_facet_node_id(tag_key: str, tag_value: str) -> str:
    return f"{tag_key}={tag_value}"


def _parse_facet_node_id(node_id: str) -> tuple[str, str] | None:
    if "=" not in node_id:
        return None
    tag_key, tag_value = node_id.split("=", 1)
    normalized_key = tag_key.strip()
    normalized_value = tag_value.strip()
    if not normalized_key or not normalized_value:
        return None
    return normalized_key, normalized_value
