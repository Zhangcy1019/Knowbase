"""Partition service skeleton."""

from __future__ import annotations

from datetime import datetime, timezone

from internal.models import PartitionDocument, PartitionFacetDefinition, PartitionFacetSchema
from internal.models.facet import (
    PartitionFacetIndex,
    PartitionFacetIndexDocument,
    PartitionFacetKeyStat,
    PartitionFacetSchemaDocument,
    PartitionFacetValueStat,
)
from internal.models.partition_semantic_index import (
    PartitionSemanticIndex,
    PartitionSemanticIndexDocument,
    PartitionSemanticKeyStat,
    PartitionSemanticValueStat,
)
from internal.domain.partition.repository import PartitionRepository
from internal.domain.partition.facet_index_repository import PartitionFacetIndexRepository
from internal.domain.partition.facet_schema_repository import PartitionFacetSchemaRepository
from internal.domain.partition.semantic_index_repository import PartitionSemanticIndexRepository


class PartitionService:
    """Manage partition resources for knowbase."""

    def __init__(
        self,
        *,
        repository: PartitionRepository,
        facet_index_repository: PartitionFacetIndexRepository,
        facet_schema_repository: PartitionFacetSchemaRepository,
        semantic_index_repository: PartitionSemanticIndexRepository,
    ):
        self._repository = repository
        self._facet_index_repository = facet_index_repository
        self._facet_schema_repository = facet_schema_repository
        self._semantic_index_repository = semantic_index_repository

    def list_partitions(self):
        return self._repository.list_documents()

    def get_partition(self, partition_name: str) -> PartitionDocument | None:
        return self._repository.get(partition_name)

    def save_partition(self, document: PartitionDocument) -> PartitionDocument:
        return self._repository.upsert(document)

    def get_facet_schema(self, partition_name: str) -> PartitionFacetSchema | None:
        partition = self.get_partition(partition_name)
        if partition is None:
            return None
        return self._facet_schema_repository.get_or_create(partition_name).facet_schema

    def get_facet_schema_document(self, partition_name: str) -> PartitionFacetSchemaDocument | None:
        partition = self.get_partition(partition_name)
        if partition is None:
            return None
        return self._facet_schema_repository.get_or_create(partition_name)

    def get_facet_index(self, partition_name: str) -> PartitionFacetIndex | None:
        partition = self.get_partition(partition_name)
        if partition is None:
            return None
        return self._facet_index_repository.get_or_create(partition_name).facet_index

    def get_facet_index_document(self, partition_name: str) -> PartitionFacetIndexDocument | None:
        partition = self.get_partition(partition_name)
        if partition is None:
            return None
        return self._facet_index_repository.get_or_create(partition_name)

    def get_semantic_index(self, partition_name: str) -> PartitionSemanticIndex | None:
        partition = self.get_partition(partition_name)
        if partition is None:
            return None
        return self._semantic_index_repository.get_or_create(partition_name).semantic_index

    def get_semantic_index_document(self, partition_name: str) -> PartitionSemanticIndexDocument | None:
        partition = self.get_partition(partition_name)
        if partition is None:
            return None
        return self._semantic_index_repository.get_or_create(partition_name)

    def refresh_semantic_index(self, *, partition_name: str, case_documents: list) -> PartitionSemanticIndexDocument:
        partition = self.get_partition(partition_name)
        if partition is None:
            raise ValueError(f"partition not found: {partition_name}")
        current = self._semantic_index_repository.get(partition_name)
        now = datetime.now(timezone.utc)
        key_counts: dict[str, int] = {}
        value_counts_by_key: dict[str, dict[str, int]] = {}
        for document in case_documents:
            if getattr(document, "partition", "") != partition_name:
                continue
            for key, raw_values in document.semantic_profile.ordered_items():
                normalized_key = str(key).strip()
                if not normalized_key:
                    continue
                values = [str(item).strip() for item in raw_values if str(item).strip()]
                if not values:
                    continue
                key_counts[normalized_key] = key_counts.get(normalized_key, 0) + 1
                value_counts = value_counts_by_key.setdefault(normalized_key, {})
                for value in values:
                    value_counts[value] = value_counts.get(value, 0) + 1
        key_stats = [
            PartitionSemanticKeyStat(
                key=key,
                count=count,
                sample_values=[
                    PartitionSemanticValueStat(value=value, count=value_count)
                    for value, value_count in sorted(
                        value_counts_by_key.get(key, {}).items(),
                        key=lambda item: (-item[1], item[0]),
                    )[:12]
                ],
                aliases=[],
                last_seen_at=now,
            )
            for key, count in sorted(key_counts.items(), key=lambda item: (-item[1], item[0]))
        ]
        semantic_index = PartitionSemanticIndex(
            partition_name=partition_name,
            key_stats=key_stats,
            metadata={
                "case_count": len(case_documents),
                "key_count": len(key_stats),
            },
        )
        document = PartitionSemanticIndexDocument(
            partition_name=partition_name,
            semantic_index=semantic_index,
            created_at=current.created_at if current is not None else now,
            updated_at=now,
        )
        return self._semantic_index_repository.upsert(document)

    def save_facet_schema(self, *, partition_name: str, facet_schema: PartitionFacetSchema) -> PartitionFacetSchemaDocument:
        partition = self.get_partition(partition_name)
        if partition is None:
            raise ValueError(f"partition not found: {partition_name}")
        current = self._facet_schema_repository.get(partition_name)
        now = datetime.now(timezone.utc)
        document = PartitionFacetSchemaDocument(
            partition_name=partition_name,
            facet_schema=facet_schema,
            created_at=current.created_at if current is not None else now,
            updated_at=now,
        )
        return self._facet_schema_repository.upsert(document)

    def refresh_facet_index(self, *, partition_name: str, case_documents: list) -> PartitionFacetIndexDocument:
        partition = self.get_partition(partition_name)
        if partition is None:
            raise ValueError(f"partition not found: {partition_name}")
        current = self._facet_index_repository.get(partition_name)
        now = datetime.now(timezone.utc)
        key_counts: dict[str, int] = {}
        value_counts_by_key: dict[str, dict[str, int]] = {}
        for document in case_documents:
            if getattr(document, "partition", "") != partition_name:
                continue
            for key, raw_values in document.facets.ordered_items():
                normalized_key = str(key).strip()
                values = [str(item).strip() for item in raw_values if str(item).strip()]
                if not normalized_key or not values:
                    continue
                key_counts[normalized_key] = key_counts.get(normalized_key, 0) + 1
                value_counts = value_counts_by_key.setdefault(normalized_key, {})
                for value in values:
                    value_counts[value] = value_counts.get(value, 0) + 1
        facet_index = PartitionFacetIndex(
            partition_name=partition_name,
            key_stats=[
                PartitionFacetKeyStat(
                    key=key,
                    count=count,
                    sample_values=[
                        PartitionFacetValueStat(value=value, count=value_count)
                        for value, value_count in sorted(
                            value_counts_by_key.get(key, {}).items(),
                            key=lambda item: (-item[1], item[0]),
                        )[:12]
                    ],
                    last_seen_at=now,
                )
                for key, count in sorted(key_counts.items(), key=lambda item: (-item[1], item[0]))
            ],
            metadata={"case_count": len(case_documents), "key_count": len(key_counts)},
        )
        document = PartitionFacetIndexDocument(
            partition_name=partition_name,
            facet_index=facet_index,
            created_at=current.created_at if current is not None else now,
            updated_at=now,
        )
        return self._facet_index_repository.upsert(document)

    def list_facet_definitions(self, partition_name: str) -> list[PartitionFacetDefinition]:
        config = self.get_facet_schema(partition_name)
        return [] if config is None else list(config.definitions)

    def delete_partition(self, partition_name: str):
        self._facet_index_repository.delete(partition_name)
        self._semantic_index_repository.delete(partition_name)
        self._facet_schema_repository.delete(partition_name)
        return self._repository.delete(partition_name)
