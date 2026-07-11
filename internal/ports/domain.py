"""Cross-module ports for domain capabilities."""

from __future__ import annotations

from typing import Any, Protocol

from internal.models import (
    KnowbaseCaseDocument,
    KnowbaseCaseSearchHit,
    KnowbaseCaseSearchQuery,
    KnowbaseEvent,
    PartitionDocument,
    PartitionFacetDefinition,
    PartitionFacetSchema,
)
from internal.models.partition_facet_schema import PartitionFacetSchemaDocument
from internal.models.partition_semantic_index import PartitionSemanticIndex, PartitionSemanticIndexDocument


class PartitionAccessPort(Protocol):
    """Stable partition read/write surface used across modules."""

    def list_partitions(self) -> list[PartitionDocument]:
        ...

    def get_partition(self, partition_name: str) -> PartitionDocument | None:
        ...

    def save_partition(self, document: PartitionDocument) -> PartitionDocument:
        ...

    def get_facet_schema_document(self, partition_name: str) -> PartitionFacetSchemaDocument | None:
        ...

    def save_facet_schema(
        self,
        *,
        partition_name: str,
        facet_schema: PartitionFacetSchema,
    ) -> PartitionFacetSchemaDocument:
        ...

    def list_facet_definitions(self, partition_name: str) -> list[PartitionFacetDefinition]:
        ...

    def get_semantic_index(self, partition_name: str) -> PartitionSemanticIndex | None:
        ...

    def get_semantic_index_document(self, partition_name: str) -> PartitionSemanticIndexDocument | None:
        ...

    def refresh_semantic_index(
        self,
        *,
        partition_name: str,
        case_documents: list[KnowbaseCaseDocument],
    ) -> PartitionSemanticIndexDocument:
        ...

    def delete_partition(self, partition_name: str):
        ...


class PartitionLookupPort(Protocol):
    """Narrow partition lookup surface used by skills and tools."""

    def get_partition(self, partition_name: str) -> PartitionDocument | None:
        ...

    def list_facet_definitions(self, partition_name: str) -> list[PartitionFacetDefinition]:
        ...


class PartitionSchemaSuggestPort(Protocol):
    """Stable schema suggestion capability exposed to API routes."""

    def suggest(
        self,
        *,
        partition_name: str,
        scenario_description: str,
        current_facet_definitions: list[PartitionFacetDefinition] | None = None,
        cautious_update: bool = False,
    ) -> Any:
        ...


class CaseReadPort(Protocol):
    """Stable case read surface used across modules."""

    def get(self, case_id: str) -> KnowbaseCaseDocument | None:
        ...

    def get_many(self, case_ids: list[str]) -> list[KnowbaseCaseDocument]:
        ...

    def list_by_partition(self, partition_name: str) -> list[KnowbaseCaseDocument]:
        ...

    def delete(self, case_id: str):
        ...


class CaseRepositoryPort(CaseReadPort, Protocol):
    """Full case persistence surface used by maintenance skills."""

    def upsert(self, document: KnowbaseCaseDocument) -> KnowbaseCaseDocument:
        ...


class CaseSearchPort(Protocol):
    """Stable case retrieval surface used by product query flows."""

    def recall_lexical(self, query: KnowbaseCaseSearchQuery) -> list[KnowbaseCaseSearchHit]:
        ...

    def recall_vector(self, query: KnowbaseCaseSearchQuery) -> list[KnowbaseCaseSearchHit]:
        ...


class CaseStorePort(Protocol):
    """Stable case persistence surface used by ingest commit paths."""

    def store(self, document: KnowbaseCaseDocument) -> KnowbaseCaseDocument:
        ...


class CaseWritePort(Protocol):
    """Stable case mutation surface used by online ingest and API updates."""

    def create_case(
        self,
        *,
        partition_name: str,
        title: str,
        source_content: str,
        source_refs: list[str],
        summary_text: str,
        semantic_profile: Any,
        metadata: Any,
        facets: dict[str, list[str]] | None = None,
    ) -> KnowbaseCaseDocument:
        ...

    def update_case(
        self,
        *,
        case_id: str,
        title: str | None = None,
        source_content: str | None = None,
        source_refs: list[str] | None = None,
        summary_text: str | None = None,
        semantic_profile: Any = None,
        metadata: Any = None,
        facets: dict[str, list[str]] | None = None,
        raw_text: str | None = None,
        case_detail: str | None = None,
    ) -> tuple[KnowbaseCaseDocument, KnowbaseCaseDocument, list[str]]:
        ...


class EventPublisherPort(Protocol):
    """Stable event publishing surface used by product and API layers."""

    async def publish(self, event: KnowbaseEvent) -> dict[str, object]:
        ...


class CaseSummaryPort(Protocol):
    """Case summary extraction capability used across product and skills."""

    async def extract(self, *, title: str, source_content: str) -> str:
        ...

    def extract_sync(self, *, title: str, source_content: str) -> str:
        ...


class CaseSemanticProfilePort(Protocol):
    """Semantic profile extraction capability used across product and skills."""

    async def extract(
        self,
        *,
        title: str,
        source_content: str,
        facet_definitions: list[PartitionFacetDefinition] | None = None,
        semantic_index: PartitionSemanticIndex | None = None,
    ):
        ...

    def extract_sync(
        self,
        *,
        title: str,
        source_content: str,
        facet_definitions: list[PartitionFacetDefinition] | None = None,
        semantic_index: PartitionSemanticIndex | None = None,
    ):
        ...


class CaseFacetResolutionPort(Protocol):
    """Facet resolution capability used across product and skills."""

    def normalize(
        self,
        *,
        facets: dict[str, list[str]],
        facet_definitions: list[PartitionFacetDefinition],
    ) -> dict[str, list[str]]:
        ...

    def project_from_semantic_profile(
        self,
        *,
        semantic_profile: Any,
        facet_definitions: list[PartitionFacetDefinition],
    ) -> dict[str, list[str]]:
        ...


class CaseRepresentationPort(Protocol):
    """Case representation builder used by rebuild flows."""

    def build_search_text(self, *, draft: Any) -> str:
        ...

    def build_content_text(self, *, draft: Any) -> str:
        ...


__all__ = [
    "CaseReadPort",
    "CaseRepositoryPort",
    "CaseRepresentationPort",
    "CaseSearchPort",
    "CaseSemanticProfilePort",
    "CaseStorePort",
    "CaseSummaryPort",
    "CaseWritePort",
    "CaseFacetResolutionPort",
    "EventPublisherPort",
    "PartitionAccessPort",
    "PartitionLookupPort",
    "PartitionSchemaSuggestPort",
]
