"""Builders for partition facet and semantic aggregate documents."""

from __future__ import annotations

from datetime import datetime, timezone

from internal.models.facet import (
    PartitionFacetIndex,
    PartitionFacetIndexDocument,
    PartitionFacetKeyStat,
    PartitionFacetValueStat,
)
from internal.models.partition_semantic_index import (
    PartitionSemanticIndex,
    PartitionSemanticIndexDocument,
    PartitionSemanticKeyStat,
    PartitionSemanticValueStat,
)


class PartitionProfileBuilder:
    """Build persisted partition profile documents from case snapshots."""

    def build_semantic_index_document(
        self,
        *,
        partition_name: str,
        case_documents: list,
        current_document: PartitionSemanticIndexDocument | None = None,
    ) -> PartitionSemanticIndexDocument:
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
                "case_count": sum(1 for document in case_documents if getattr(document, "partition", "") == partition_name),
                "key_count": len(key_stats),
            },
        )
        return PartitionSemanticIndexDocument(
            partition_name=partition_name,
            semantic_index=semantic_index,
            created_at=current_document.created_at if current_document is not None else now,
            updated_at=now,
        )

    def build_facet_index_document(
        self,
        *,
        partition_name: str,
        case_documents: list,
        current_document: PartitionFacetIndexDocument | None = None,
    ) -> PartitionFacetIndexDocument:
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
            metadata={
                "case_count": sum(1 for document in case_documents if getattr(document, "partition", "") == partition_name),
                "key_count": len(key_counts),
            },
        )
        return PartitionFacetIndexDocument(
            partition_name=partition_name,
            facet_index=facet_index,
            created_at=current_document.created_at if current_document is not None else now,
            updated_at=now,
        )
