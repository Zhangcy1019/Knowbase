"""Build deterministic backlog working sets from persisted events."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from internal.backlog.events.models import BacklogBatch
from internal.knowledge.batch.models import BatchWorkingSet, NormalizedEvent, ResourceEventGroup
from internal.utils.logger import get_logger


logger = get_logger("knowbase.backlog.batch_working_set_builder")


class BatchWorkingSetBuilder:
    """Normalize raw backlog events into one backlog-oriented working set."""

    def build(self, *, batch: BacklogBatch) -> BatchWorkingSet:
        grouped: dict[tuple[str, str, str], list[NormalizedEvent]] = defaultdict(list)
        normalized_events = self._extract_event_signals(batch=batch)
        for normalized in normalized_events:
            grouped[(normalized.partition, normalized.resource_type, normalized.resource_id)].append(normalized)

        resource_groups = self._build_resource_groups(grouped=grouped)
        # sort by priority, then latest event time, then group id for deterministic ordering
        resource_groups.sort(key=lambda item: (item.priority, item.latest_event_at or datetime.min, item.group_id))

        affected_case_ids: list[str] = []
        observed_facet_keys: list[str] = []
        for group in resource_groups:
            if group.resource_type == "case" and group.resource_id not in affected_case_ids:
                affected_case_ids.append(group.resource_id)
            for facet_key in group.observed_facets:
                if facet_key not in observed_facet_keys:
                    observed_facet_keys.append(facet_key)

        working_set = BatchWorkingSet(
            batch_id=batch.batch_id,
            partition=batch.partition,
            trigger_source=batch.trigger_source,
            event_count=batch.event_count,
            event_type_counts=batch.event_type_counts,
            resource_groups=resource_groups,
            affected_case_ids=affected_case_ids,
            observed_facet_keys=observed_facet_keys,
            summary=self._build_batch_summary(batch=batch, resource_groups=resource_groups),
            metadata=batch.metadata,
        )
        logger.info(
            "Built backlog batch working set.",
            extra={
                "batch_id": batch.batch_id,
                "partition": batch.partition,
                "event_count": batch.event_count,
                "normalized_event_count": len(normalized_events),
                "resource_group_count": len(resource_groups),
                "affected_case_count": len(affected_case_ids),
                "observed_facet_key_count": len(observed_facet_keys),
            },
        )
        return working_set

    def _extract_event_signals(self, *, batch: BacklogBatch) -> list[NormalizedEvent]:
        normalized_events: list[NormalizedEvent] = []
        # sort by occurred_at ascending, then event_id ascending for deterministic ordering
        for item in sorted(batch.events, key=lambda event: (event.occurred_at or datetime.min, event.event_id)):
            payload = item.payload.model_dump(mode="json")
            related_targets = payload.get("related_targets", [])
            normalized_events.append(
                NormalizedEvent(
                    event_id=item.event_id,
                    event_type=str(item.event_type),
                    partition=item.partition,
                    resource_type=item.resource_type,
                    resource_id=item.resource_id,
                    change_kind=str(payload.get("change_kind", "")).strip(),
                    occurred_at=item.occurred_at,
                    changed_fields=list(payload.get("changed_fields", [])),
                    field_changes=dict(payload.get("field_changes", {})),
                    related_resource_refs=self._normalize_related_refs(related_targets),
                    observed_facets=self._normalize_observed_facets(payload.get("observed_facets", {})),
                    priority=self._resolve_event_priority(
                        resource_type=item.resource_type,
                        change_kind=str(payload.get("change_kind", "")).strip(),
                    ),
                )
            )
        return normalized_events

    # group by (partition, resource_type, resource_id) and collapse events for the same resource into one
    def _build_resource_groups(
        self,
        *,
        grouped: dict[tuple[str, str, str], list[NormalizedEvent]],
    ) -> list[ResourceEventGroup]:
        resource_groups: list[ResourceEventGroup] = []
        for (partition, resource_type, resource_id), raw_events in grouped.items():
            events = self._collapse_events(raw_events)
            changed_fields: list[str] = []
            related_resource_refs: list[str] = []
            observed_facets: dict[str, list[str]] = {}
            has_create = any(event.change_kind == "create" for event in raw_events)
            has_update = any(event.change_kind == "update" for event in raw_events)
            has_delete = any(event.change_kind == "delete" for event in raw_events)
            for event in events:
                changed_fields = _merge_string_lists(changed_fields, event.changed_fields)
                related_resource_refs = _merge_string_lists(related_resource_refs, event.related_resource_refs)
                for facet_key, values in event.observed_facets.items():
                    merged = observed_facets.setdefault(facet_key, [])
                    for value in values:
                        if value not in merged:
                            merged.append(value)
            latest_event_at = max((event.occurred_at for event in events if event.occurred_at is not None), default=None)
            priority = min((event.priority for event in events), default=100)
            is_cancelled_out = has_create and has_delete and not has_update
            resource_groups.append(
                ResourceEventGroup(
                    group_id=f"{partition}:{resource_type}:{resource_id}",
                    partition=partition,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    event_ids=[event.event_id for event in events],
                    changed_fields=changed_fields,
                    related_resource_refs=related_resource_refs,
                    latest_event_at=latest_event_at,
                    priority=priority,
                    is_cancelled_out=is_cancelled_out,
                    observed_facets=observed_facets,
                )
            )
        return resource_groups

    # collapse events for the same resource into one, preserving the latest event and merging changed fields
    # example: if a resource has events [create, update, update, delete], the result will be [delete] with all changed fields merged
    @staticmethod
    def _collapse_events(events: list[NormalizedEvent]) -> list[NormalizedEvent]:
        if len(events) <= 1:
            return events
        collapsed: list[NormalizedEvent] = []
        for event in events:
            if not collapsed:
                collapsed.append(event)
                continue
            previous = collapsed[-1]
            if previous.change_kind in {"create", "update"} and event.change_kind in {"update", "delete"}:
                collapsed[-1] = previous.model_copy(
                    update={
                        "event_id": event.event_id,
                        "event_type": event.event_type,
                        "change_kind": event.change_kind if event.change_kind == "delete" else previous.change_kind,
                        "occurred_at": event.occurred_at,
                        "changed_fields": _merge_string_lists(previous.changed_fields, event.changed_fields),
                        "field_changes": {**previous.field_changes, **event.field_changes},
                        "related_resource_refs": _merge_string_lists(
                            previous.related_resource_refs,
                            event.related_resource_refs,
                        ),
                        "observed_facets": _merge_observed_facets(
                            previous.observed_facets,
                            event.observed_facets,
                        ),
                        "priority": min(previous.priority, event.priority),
                    }
                )
                continue
            collapsed.append(event)
        return collapsed

    @staticmethod
    def _normalize_related_refs(refs: list[object]) -> list[str]:
        return list(dict.fromkeys(str(ref).strip() for ref in refs if str(ref).strip()))

    @staticmethod
    def _normalize_observed_facets(value: object) -> dict[str, list[str]]:
        if not isinstance(value, dict):
            return {}
        normalized: dict[str, list[str]] = {}
        for key, values in value.items():
            normalized_key = str(key).strip()
            if not normalized_key:
                continue
            raw_values = values if isinstance(values, list) else [values]
            normalized_values = [str(item).strip() for item in raw_values if str(item).strip()]
            if normalized_values:
                normalized[normalized_key] = list(dict.fromkeys(normalized_values))
        return normalized

    @staticmethod
    def _resolve_event_priority(*, resource_type: str, change_kind: str) -> int:
        if resource_type == "partition":
            return 10
        if change_kind == "delete":
            return 20
        if change_kind == "create":
            return 30
        # if change_kind == "update":
        return 50

    @staticmethod
    def _build_batch_summary(*, batch: BacklogBatch, resource_groups: list[ResourceEventGroup]) -> str:
        return (
            f"Batch {batch.batch_id} in partition {batch.partition} merged {batch.event_count} event(s) "
            f"into {len(resource_groups)} resource group(s)."
        )


def _merge_string_lists(existing: list[str], incoming: list[str]) -> list[str]:
    merged = list(existing)
    for item in incoming:
        normalized = str(item).strip()
        if normalized and normalized not in merged:
            merged.append(normalized)
    return merged


def _merge_observed_facets(
    left: dict[str, list[str]],
    right: dict[str, list[str]],
) -> dict[str, list[str]]:
    merged = {key: list(values) for key, values in left.items()}
    for key, values in right.items():
        merged[key] = _merge_string_lists(merged.get(key, []), values)
    return merged


__all__ = ["BatchWorkingSetBuilder"]
