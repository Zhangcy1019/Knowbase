"""Partition persistence coordinators inside the domain layer."""

from __future__ import annotations

from datetime import datetime, timezone

from internal.models import PartitionDocument, PartitionFacetDefinition, PartitionFacetSchema
from internal.models.facet import PartitionFacetIndex, PartitionFacetIndexDocument, PartitionFacetSchemaDocument
from internal.models.partition_semantic_index import PartitionSemanticIndex, PartitionSemanticIndexDocument

from internal.domain.partition.profile_builder import PartitionProfileBuilder


class PartitionStore:
    """Coordinate basic partition document persistence."""

    def __init__(self, *, repository):
        self._repository = repository

    def list_partitions(self) -> list[PartitionDocument]:
        return self._repository.list_documents()

    def get_partition(self, partition_name: str) -> PartitionDocument | None:
        return self._repository.get(partition_name)

    def save_partition(self, document: PartitionDocument) -> PartitionDocument:
        return self._repository.upsert(document)

    def delete_partition(self, partition_name: str):
        return self._repository.delete(partition_name)


class PartitionProfileStore:
    """Coordinate partition schema/profile persistence and rebuilds."""

    def __init__(
        self,
        *,
        facet_index_repository,
        facet_schema_repository,
        semantic_index_repository,
        profile_builder: PartitionProfileBuilder | None = None,
    ):
        self._facet_index_repository = facet_index_repository
        self._facet_schema_repository = facet_schema_repository
        self._semantic_index_repository = semantic_index_repository
        self._profile_builder = profile_builder or PartitionProfileBuilder()

    def get_facet_schema(self, partition_name: str) -> PartitionFacetSchema:
        return self._facet_schema_repository.get_or_create(partition_name).facet_schema

    def get_facet_schema_document(self, partition_name: str) -> PartitionFacetSchemaDocument:
        return self._facet_schema_repository.get_or_create(partition_name)

    def save_facet_schema(
        self,
        *,
        partition_name: str,
        facet_schema: PartitionFacetSchema,
    ) -> PartitionFacetSchemaDocument:
        current = self._facet_schema_repository.get(partition_name)
        normalized_schema = PartitionFacetSchema.model_validate(facet_schema)
        if current is not None and current.facet_schema == normalized_schema:
            # A governance pass may accept the current schema without proposing
            # a mutation. Do not touch updated_at in that case: the no-op must
            # remain invisible to partition Git cleanliness checks.
            return current
        now = datetime.now(timezone.utc)
        document = PartitionFacetSchemaDocument(
            partition_name=partition_name,
            facet_schema=normalized_schema,
            created_at=current.created_at if current is not None else now,
            updated_at=now,
        )
        return self._facet_schema_repository.upsert(document)

    def list_facet_definitions(self, partition_name: str) -> list[PartitionFacetDefinition]:
        return list(self.get_facet_schema(partition_name).definitions)

    def get_facet_index(self, partition_name: str) -> PartitionFacetIndex:
        return self._facet_index_repository.get_or_create(partition_name).facet_index

    def get_facet_index_document(self, partition_name: str) -> PartitionFacetIndexDocument:
        return self._facet_index_repository.get_or_create(partition_name)

    def refresh_facet_index(
        self,
        *,
        partition_name: str,
        case_documents: list,
    ) -> PartitionFacetIndexDocument:
        current = self._facet_index_repository.get(partition_name)
        document = self._profile_builder.build_facet_index_document(
            partition_name=partition_name,
            case_documents=case_documents,
            current_document=current,
        )
        return self._facet_index_repository.upsert(document)

    def get_semantic_index(self, partition_name: str) -> PartitionSemanticIndex:
        return self._semantic_index_repository.get_or_create(partition_name).semantic_index

    def get_semantic_index_document(self, partition_name: str) -> PartitionSemanticIndexDocument:
        return self._semantic_index_repository.get_or_create(partition_name)

    def refresh_semantic_index(
        self,
        *,
        partition_name: str,
        case_documents: list,
    ) -> PartitionSemanticIndexDocument:
        current = self._semantic_index_repository.get(partition_name)
        document = self._profile_builder.build_semantic_index_document(
            partition_name=partition_name,
            case_documents=case_documents,
            current_document=current,
        )
        return self._semantic_index_repository.upsert(document)

    def delete_partition_profiles(self, partition_name: str) -> None:
        self._facet_index_repository.delete(partition_name)
        self._semantic_index_repository.delete(partition_name)
        self._facet_schema_repository.delete(partition_name)
