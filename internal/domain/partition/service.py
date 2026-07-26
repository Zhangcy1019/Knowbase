"""Partition service skeleton."""

from __future__ import annotations

from datetime import datetime, timezone

from internal.models import PartitionDocument, PartitionFacetDefinition, PartitionFacetSchema
from internal.models.facet import PartitionFacetIndex, PartitionFacetIndexDocument, PartitionFacetSchemaDocument
from internal.models.partition_semantic_index import PartitionSemanticIndex, PartitionSemanticIndexDocument
from internal.domain.partition.profile_builder import PartitionProfileBuilder
from internal.domain.partition.store import PartitionProfileStore, PartitionStore


class PartitionService:
    """Manage partition resources for knowbase."""

    def __init__(
        self,
        *,
        repository,
        facet_index_repository,
        facet_schema_repository,
        semantic_index_repository,
        profile_builder: PartitionProfileBuilder | None = None,
        versioning_manager=None,
    ):
        self._repository = repository
        self._facet_index_repository = facet_index_repository
        self._facet_schema_repository = facet_schema_repository
        self._semantic_index_repository = semantic_index_repository
        self._versioning_manager = versioning_manager
        self._profile_builder = profile_builder or PartitionProfileBuilder()
        self._partition_store = PartitionStore(repository=repository)
        self._profile_store = PartitionProfileStore(
            facet_index_repository=facet_index_repository,
            facet_schema_repository=facet_schema_repository,
            semantic_index_repository=semantic_index_repository,
            profile_builder=self._profile_builder,
        )

    def list_partitions(self):
        return self._partition_store.list_partitions()

    def get_partition(self, partition_name: str) -> PartitionDocument | None:
        return self._partition_store.get_partition(partition_name)

    def save_partition(self, document: PartitionDocument) -> PartitionDocument:
        existing = self._partition_store.get_partition(document.partition_name)
        saved = self._partition_store.save_partition(document)
        if existing is None and self._versioning_manager is not None:
            # Create the initial partition-owned profile files before the
            # baseline commit so the first case write is not seen as dirty.
            self._profile_store.get_facet_schema_document(document.partition_name)
            self._profile_store.get_facet_index_document(document.partition_name)
            self._profile_store.get_semantic_index_document(document.partition_name)
            self._versioning_manager.initialize_partition(document.partition_name)
        return saved

    def get_facet_schema(self, partition_name: str) -> PartitionFacetSchema | None:
        partition = self.get_partition(partition_name)
        if partition is None:
            return None
        return self._profile_store.get_facet_schema(partition_name)

    def get_facet_schema_document(self, partition_name: str) -> PartitionFacetSchemaDocument | None:
        partition = self.get_partition(partition_name)
        if partition is None:
            return None
        return self._profile_store.get_facet_schema_document(partition_name)

    def get_facet_index(self, partition_name: str) -> PartitionFacetIndex | None:
        partition = self.get_partition(partition_name)
        if partition is None:
            return None
        return self._profile_store.get_facet_index(partition_name)

    def get_facet_index_document(self, partition_name: str) -> PartitionFacetIndexDocument | None:
        partition = self.get_partition(partition_name)
        if partition is None:
            return None
        return self._profile_store.get_facet_index_document(partition_name)

    def get_semantic_index(self, partition_name: str) -> PartitionSemanticIndex | None:
        partition = self.get_partition(partition_name)
        if partition is None:
            return None
        return self._profile_store.get_semantic_index(partition_name)

    def get_semantic_index_document(self, partition_name: str) -> PartitionSemanticIndexDocument | None:
        partition = self.get_partition(partition_name)
        if partition is None:
            return None
        return self._profile_store.get_semantic_index_document(partition_name)

    def refresh_semantic_index(self, *, partition_name: str, case_documents: list) -> PartitionSemanticIndexDocument:
        partition = self.get_partition(partition_name)
        if partition is None:
            raise ValueError(f"partition not found: {partition_name}")
        return self._profile_store.refresh_semantic_index(
            partition_name=partition_name,
            case_documents=case_documents,
        )

    def save_facet_schema(self, *, partition_name: str, facet_schema: PartitionFacetSchema) -> PartitionFacetSchemaDocument:
        partition = self.get_partition(partition_name)
        if partition is None:
            raise ValueError(f"partition not found: {partition_name}")
        return self._profile_store.save_facet_schema(
            partition_name=partition_name,
            facet_schema=facet_schema,
        )

    def refresh_facet_index(self, *, partition_name: str, case_documents: list) -> PartitionFacetIndexDocument:
        partition = self.get_partition(partition_name)
        if partition is None:
            raise ValueError(f"partition not found: {partition_name}")
        return self._profile_store.refresh_facet_index(
            partition_name=partition_name,
            case_documents=case_documents,
        )

    def list_facet_definitions(self, partition_name: str) -> list[PartitionFacetDefinition]:
        if self.get_partition(partition_name) is None:
            return []
        return self._profile_store.list_facet_definitions(partition_name)

    def delete_partition(self, partition_name: str):
        self._profile_store.delete_partition_profiles(partition_name)
        return self._partition_store.delete_partition(partition_name)
