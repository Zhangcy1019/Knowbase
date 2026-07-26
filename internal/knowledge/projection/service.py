"""Case projection capability facade."""

from __future__ import annotations

from internal.knowledge.projection.models import ProjectionPlan


class KnowledgeProjectionService:
    """Plan case facet changes without applying them directly."""

    def __init__(self, *, case_repository, projector):
        self._case_repository = case_repository
        self._projector = projector

    def plan(self, *, partition: str, accepted_schema, case_ids: list[str]) -> ProjectionPlan:
        cases = self._case_repository.get_many(case_ids)
        changes = []
        unchanged: list[str] = []
        skipped: list[str] = []
        for case_id in case_ids:
            case = next((item for item in cases if item.case_id == case_id), None)
            if case is None or case.partition != partition:
                skipped.append(case_id)
                continue
            change = self._projector.project_one(case=case, schema=accepted_schema)
            if change is None:
                unchanged.append(case_id)
            else:
                changes.append(change)
        return ProjectionPlan(
            partition=partition,
            target_case_ids=list(case_ids),
            changes=changes,
            unchanged_case_ids=unchanged,
            skipped_case_ids=skipped,
            estimated_change_count=len(changes),
        )
