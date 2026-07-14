"""Index bootstrap helpers for application assembly."""

from __future__ import annotations

from internal.application.providers import CoreProviders


def ensure_indices(*, core: CoreProviders) -> None:
    for repository in (
        core.partition_service._repository,
        core.partition_service._facet_index_repository,
        core.partition_service._facet_schema_repository,
        core.partition_service._semantic_index_repository,
        core.case_repository,
        core.event_record_repository,
        core.run_repository,
        core.step_repository,
        core.artifact_repository,
    ):
        repository.create_index()
