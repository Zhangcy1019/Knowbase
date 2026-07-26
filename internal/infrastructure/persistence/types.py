"""Shared persistence backend types."""

from dataclasses import dataclass


@dataclass(slots=True)
class PersistenceBundle:
    partition_repository: object
    partition_facet_index_repository: object
    partition_facet_schema_repository: object
    partition_semantic_index_repository: object
    case_repository: object
    event_record_repository: object
    run_repository: object
    step_repository: object
    artifact_repository: object
    statistics_snapshot_repository: object
    query_statistics_snapshot_repository: object
