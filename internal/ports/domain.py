"""Cross-module ports for domain capabilities."""

from __future__ import annotations

from typing import Any, Protocol

from internal.models import (
    CaseFacetProfile,
    KnowbaseCaseDocument,
    KnowbaseCaseSearchHit,
    KnowbaseCaseSearchQuery,
    KnowbaseEvent,
    PartitionDocument,
    PartitionFacetDefinition,
    PartitionFacetIndex,
    PartitionFacetSchema,
)
from internal.models.facet import PartitionFacetIndexDocument, PartitionFacetSchemaDocument
from internal.models.partition_semantic_index import PartitionSemanticIndex, PartitionSemanticIndexDocument


class PartitionReadPort(Protocol):
    """Stable partition read surface used across modules."""

    def list_partitions(self) -> list[PartitionDocument]:
        ...

    def get_partition(self, partition_name: str) -> PartitionDocument | None:
        ...


class PartitionWritePort(Protocol):
    """Stable partition write surface used by API and maintenance flows."""

    def save_partition(self, document: PartitionDocument) -> PartitionDocument:
        ...

    def delete_partition(self, partition_name: str):
        ...


class PartitionProfileReadPort(Protocol):
    """Read surface for partition schema, facet, and semantic profiles."""

    def get_facet_schema(self, partition_name: str) -> PartitionFacetSchema | None:
        ...

    def get_facet_schema_document(self, partition_name: str) -> PartitionFacetSchemaDocument | None:
        ...

    def list_facet_definitions(self, partition_name: str) -> list[PartitionFacetDefinition]:
        ...

    def get_facet_index(self, partition_name: str) -> PartitionFacetIndex | None:
        ...

    def get_facet_index_document(self, partition_name: str) -> PartitionFacetIndexDocument | None:
        ...

    def get_semantic_index(self, partition_name: str) -> PartitionSemanticIndex | None:
        ...

    def get_semantic_index_document(self, partition_name: str) -> PartitionSemanticIndexDocument | None:
        ...


class PartitionProfileWritePort(Protocol):
    """Write surface for partition schema/profile maintenance."""

    def save_facet_schema(
        self,
        *,
        partition_name: str,
        facet_schema: PartitionFacetSchema,
    ) -> PartitionFacetSchemaDocument:
        ...

    def refresh_semantic_index(
        self,
        *,
        partition_name: str,
        case_documents: list[KnowbaseCaseDocument],
    ) -> PartitionSemanticIndexDocument:
        ...

    def refresh_facet_index(
        self,
        *,
        partition_name: str,
        case_documents: list[KnowbaseCaseDocument],
    ) -> PartitionFacetIndexDocument:
        ...


class PartitionAccessPort(
    PartitionReadPort,
    PartitionWritePort,
    PartitionProfileReadPort,
    PartitionProfileWritePort,
    Protocol,
):
    """Composite partition surface kept for broader existing integrations."""


class PartitionLookupPort(PartitionReadPort, PartitionProfileReadPort, Protocol):
    """Narrow partition lookup surface used by skills and tools."""


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
        facets: CaseFacetProfile | dict[str, list[str]] | None = None,
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
        facets: CaseFacetProfile | dict[str, list[str]] | None = None,
        raw_text: str | None = None,
        case_detail: str | None = None,
    ) -> tuple[KnowbaseCaseDocument, KnowbaseCaseDocument, list[str]]:
        ...

    def delete_case(self, *, case_id: str) -> KnowbaseCaseDocument:
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
        facets: CaseFacetProfile | dict[str, list[str]],
        facet_definitions: list[PartitionFacetDefinition],
    ) -> CaseFacetProfile:
        ...

    def project_from_semantic_profile(
        self,
        *,
        semantic_profile: Any,
        facet_definitions: list[PartitionFacetDefinition],
    ) -> CaseFacetProfile:
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
    "PartitionProfileReadPort",
    "PartitionProfileWritePort",
    "PartitionReadPort",
    "PartitionAccessPort",
    "PartitionLookupPort",
    "PartitionSchemaSuggestPort",
    "PartitionWritePort",
]
