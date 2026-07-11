from __future__ import annotations

from datetime import datetime, timezone

from internal.backlog.planning.batch_working_set_builder import BatchWorkingSetBuilder
from internal.models import BacklogBatch, EventRecord, KnowbaseEventType


def test_builder_collapses_case_updates_and_tracks_affected_keys() -> None:
    builder = BatchWorkingSetBuilder()
    batch = BacklogBatch(
        batch_id="batch-1",
        partition="CI",
        trigger_source="manual",
        event_ids=["e1", "e2"],
        event_count=2,
        event_type_counts={"case.updated": 2},
        resource_refs=["case:case-1"],
        events=[
            EventRecord(
                event_id="e1",
                event_type=KnowbaseEventType.CASE_UPDATED,
                partition="CI",
                resource_type="case",
                resource_id="case-1",
                occurred_at=datetime(2026, 1, 1, 10, tzinfo=timezone.utc),
                payload={
                    "change_kind": "update",
                    "changed_fields": ["summary_text"],
                    "field_changes": {"summary_text": {"change_type": "text_updated"}},
                    "observed_facets": {"team": ["alpha"]},
                    "related_targets": [{"type": "partition", "id": "CI"}],
                },
            ),
            EventRecord(
                event_id="e2",
                event_type=KnowbaseEventType.CASE_UPDATED,
                partition="CI",
                resource_type="case",
                resource_id="case-1",
                occurred_at=datetime(2026, 1, 1, 11, tzinfo=timezone.utc),
                payload={
                    "change_kind": "update",
                    "changed_fields": ["semantic_profile"],
                    "field_changes": {"semantic_profile": {"change_type": "text_updated"}},
                    "observed_facets": {"priority": ["p1"]},
                    "related_targets": [],
                },
            ),
        ],
    )

    working_set = builder.build(batch=batch)

    assert working_set.batch_id == "batch-1"
    assert len(working_set.normalized_events) == 2
    assert len(working_set.resource_groups) == 2
    assert working_set.affected_case_ids == ["case-1"]
    assert working_set.affected_facet_keys == ["team", "priority"]
    assert "case:case-1" in working_set.affected_resource_refs
    assert "partition:CI" in working_set.affected_resource_refs

    case_group = next(group for group in working_set.resource_groups if group.resource_type == "case")
    assert case_group.collapsed_event_count == 1
    assert case_group.event_ids == ["e2"]
    assert case_group.changed_fields == ["summary_text", "semantic_profile"]
    assert case_group.observed_facets == {"team": ["alpha"], "priority": ["p1"]}

    related_group = next(group for group in working_set.resource_groups if group.resource_type == "partition")
    assert related_group.event_types == ["related.inferred"]
    assert related_group.related_resource_refs == ["case:case-1"]


def test_builder_marks_create_delete_sequence_as_cancelled_out() -> None:
    builder = BatchWorkingSetBuilder()
    batch = BacklogBatch(
        batch_id="batch-2",
        partition="CI",
        trigger_source="manual",
        event_ids=["e1", "e2"],
        event_count=2,
        event_type_counts={"case.created": 1, "case.deleted": 1},
        resource_refs=["case:case-2"],
        events=[
            EventRecord(
                event_id="e1",
                event_type=KnowbaseEventType.CASE_CREATED,
                partition="CI",
                resource_type="case",
                resource_id="case-2",
                occurred_at=datetime(2026, 1, 2, 10, tzinfo=timezone.utc),
                payload={"change_kind": "create", "changed_fields": ["title"], "related_targets": []},
            ),
            EventRecord(
                event_id="e2",
                event_type=KnowbaseEventType.CASE_DELETED,
                partition="CI",
                resource_type="case",
                resource_id="case-2",
                occurred_at=datetime(2026, 1, 2, 11, tzinfo=timezone.utc),
                payload={"change_kind": "delete", "changed_fields": ["title"], "related_targets": []},
            ),
        ],
    )

    working_set = builder.build(batch=batch)

    assert len(working_set.resource_groups) == 1
    group = working_set.resource_groups[0]
    assert group.dominant_change_kind == "cancelled"
    assert group.is_cancelled_out is True
    assert group.summary == "case:case-2 cancelled out across 1 event(s)."
