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
        normalized_events = self._normalize_events(batch=batch)
        for normalized in normalized_events:
            grouped[(normalized.partition, normalized.resource_type, normalized.resource_id)].append(normalized)

        resource_groups = self._build_resource_groups(grouped=grouped)
        resource_groups = self._propagate_related_resources(resource_groups=resource_groups)
        resource_groups.sort(key=lambda item: (item.priority, item.latest_event_at or datetime.min, item.group_id))

        affected_case_ids: list[str] = []
        affected_facet_keys: list[str] = []
        affected_resource_refs: list[str] = []
        for group in resource_groups:
            if group.resource_type == "case" and group.resource_id not in affected_case_ids:
                affected_case_ids.append(group.resource_id)
            for facet_key in group.observed_facets:
                if facet_key not in affected_facet_keys:
                    affected_facet_keys.append(facet_key)
            for ref in [f"{group.resource_type}:{group.resource_id}", *group.related_resource_refs]:
                if ref not in affected_resource_refs:
                    affected_resource_refs.append(ref)

        working_set = BatchWorkingSet(
            batch_id=batch.batch_id,
            partition=batch.partition,
            trigger_source=batch.trigger_source,
            event_count=batch.event_count,
            event_type_counts=batch.event_type_counts,
            normalized_events=normalized_events,
            resource_groups=resource_groups,
            affected_case_ids=affected_case_ids,
            affected_facet_keys=affected_facet_keys,
            affected_resource_refs=affected_resource_refs,
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
                "affected_facet_key_count": len(affected_facet_keys),
            },
        )
        return working_set

    def _normalize_events(self, *, batch: BacklogBatch) -> list[NormalizedEvent]:
        normalized_events: list[NormalizedEvent] = []
        for item in sorted(batch.events, key=lambda event: (event.occurred_at or datetime.min, event.event_id)):
            payload = item.payload.model_dump(mode="json") if hasattr(item.payload, "model_dump") else dict(item.payload or {})
            related_targets = payload.get("related_targets", []) if isinstance(payload, dict) else []
            normalized_events.append(
                NormalizedEvent(
                    event_id=item.event_id,
                    event_type=str(item.event_type),
                    partition=item.partition,
                    resource_type=item.resource_type,
                    resource_id=item.resource_id,
                    change_kind=str(payload.get("change_kind", "")).strip(),
                    occurred_at=item.occurred_at,
                    changed_fields=list(payload.get("changed_fields", [])) if isinstance(payload, dict) else [],
                    field_changes=dict(payload.get("field_changes", {})) if isinstance(payload, dict) else {},
                    related_resource_refs=self._normalize_related_targets(related_targets),
                    priority=self._resolve_event_priority(
                        resource_type=item.resource_type,
                        change_kind=str(payload.get("change_kind", "")).strip(),
                    ),
                    payload=payload if isinstance(payload, dict) else {},
                )
            )
        return normalized_events

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
                if isinstance(event.payload, dict):
                    for facet_key, values in (event.payload.get("observed_facets", {}) or {}).items():
                        normalized_key = str(facet_key).strip()
                        if not normalized_key:
                            continue
                        merged = observed_facets.setdefault(normalized_key, [])
                        for value in values:
                            normalized_value = str(value).strip()
                            if normalized_value and normalized_value not in merged:
                                merged.append(normalized_value)
            latest_event_at = max((event.occurred_at for event in events if event.occurred_at is not None), default=None)
            dominant_change_kind = self._resolve_group_change_kind(
                has_create=has_create,
                has_update=has_update,
                has_delete=has_delete,
            )
            priority = min((event.priority for event in events), default=100)
            is_cancelled_out = has_create and has_delete and not has_update
            resource_groups.append(
                ResourceEventGroup(
                    group_id=f"{partition}:{resource_type}:{resource_id}",
                    partition=partition,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    event_ids=[event.event_id for event in events],
                    event_types=[event.event_type for event in events],
                    dominant_change_kind=dominant_change_kind,
                    changed_fields=changed_fields,
                    related_resource_refs=related_resource_refs,
                    latest_event_at=latest_event_at,
                    priority=priority,
                    collapsed_event_count=len(events),
                    has_create=has_create,
                    has_update=has_update,
                    has_delete=has_delete,
                    is_cancelled_out=is_cancelled_out,
                    observed_facets=observed_facets,
                    summary=self._build_group_summary(
                        resource_type=resource_type,
                        resource_id=resource_id,
                        event_count=len(events),
                        dominant_change_kind=dominant_change_kind,
                        changed_fields=changed_fields,
                        is_cancelled_out=is_cancelled_out,
                    ),
                )
            )
        return resource_groups

    def _propagate_related_resources(self, *, resource_groups: list[ResourceEventGroup]) -> list[ResourceEventGroup]:
        existing_refs = {f"{group.resource_type}:{group.resource_id}" for group in resource_groups}
        synthetic_groups: list[ResourceEventGroup] = []
        for group in resource_groups:
            for related_ref in group.related_resource_refs:
                if related_ref in existing_refs:
                    continue
                target_type, _, target_id = related_ref.partition(":")
                if not target_type or not target_id:
                    continue
                synthetic_groups.append(
                    ResourceEventGroup(
                        group_id=f"{group.partition}:{target_type}:{target_id}:related",
                        partition=group.partition,
                        resource_type=target_type,
                        resource_id=target_id,
                        event_ids=list(group.event_ids),
                        event_types=["related.inferred"],
                        dominant_change_kind="related",
                        changed_fields=[],
                        related_resource_refs=[f"{group.resource_type}:{group.resource_id}"],
                        latest_event_at=group.latest_event_at,
                        priority=min(group.priority + 5, 99),
                        collapsed_event_count=0,
                        has_create=False,
                        has_update=True,
                        has_delete=False,
                        is_cancelled_out=False,
                        summary=f"related impact inferred for {target_type}:{target_id} from {group.resource_type}:{group.resource_id}.",
                    )
                )
                existing_refs.add(related_ref)
        return [*resource_groups, *synthetic_groups]

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
                        "priority": min(previous.priority, event.priority),
                        "payload": _merge_payloads(previous.payload, event.payload),
                    }
                )
                continue
            collapsed.append(event)
        return collapsed

    @staticmethod
    def _normalize_related_targets(targets: list[dict[str, str]] | list[object]) -> list[str]:
        refs: list[str] = []
        for item in targets:
            if isinstance(item, dict):
                target_type = str(item.get("type") or "").strip()
                target_id = str(item.get("id") or "").strip()
            else:
                target_type = str(getattr(item, "type", "")).strip()
                target_id = str(getattr(item, "id", "")).strip()
            if target_type and target_id:
                ref = f"{target_type}:{target_id}"
                if ref not in refs:
                    refs.append(ref)
        return refs

    @staticmethod
    def _resolve_event_priority(*, resource_type: str, change_kind: str) -> int:
        if resource_type == "partition":
            return 10
        if change_kind == "delete":
            return 20
        if change_kind == "create":
            return 30
        return 50

    @staticmethod
    def _resolve_group_change_kind(*, has_create: bool, has_update: bool, has_delete: bool) -> str:
        if has_create and has_delete:
            return "cancelled"
        if has_delete:
            return "delete"
        if has_create:
            return "create"
        if has_update:
            return "update"
        return "unknown"

    @staticmethod
    def _build_group_summary(
        *,
        resource_type: str,
        resource_id: str,
        event_count: int,
        dominant_change_kind: str,
        changed_fields: list[str],
        is_cancelled_out: bool,
    ) -> str:
        if is_cancelled_out:
            return f"{resource_type}:{resource_id} cancelled out across {event_count} event(s)."
        field_summary = ", ".join(changed_fields[:5])
        if field_summary:
            return f"{resource_type}:{resource_id} {dominant_change_kind} across {event_count} event(s); changed_fields={field_summary}."
        return f"{resource_type}:{resource_id} {dominant_change_kind} across {event_count} event(s)."

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


def _merge_payloads(left: dict[str, object], right: dict[str, object]) -> dict[str, object]:
    merged = dict(left)
    for key, value in right.items():
        if key == "changed_fields":
            merged[key] = _merge_string_lists(list(merged.get(key, [])), list(value if isinstance(value, list) else []))
            continue
        if key == "related_targets":
            existing = list(merged.get(key, [])) if isinstance(merged.get(key), list) else []
            additions = list(value) if isinstance(value, list) else []
            merged[key] = existing + [item for item in additions if item not in existing]
            continue
        if key == "observed_facets" and isinstance(value, dict):
            current = dict(merged.get(key, {})) if isinstance(merged.get(key), dict) else {}
            for facet_key, facet_values in value.items():
                existing_values = list(current.get(facet_key, [])) if isinstance(current.get(facet_key), list) else []
                for facet_value in facet_values:
                    normalized = str(facet_value).strip()
                    if normalized and normalized not in existing_values:
                        existing_values.append(normalized)
                current[facet_key] = existing_values
            merged[key] = current
            continue
        if key == "field_changes" and isinstance(value, dict):
            current = dict(merged.get(key, {})) if isinstance(merged.get(key), dict) else {}
            current.update(value)
            merged[key] = current
            continue
        merged[key] = value
    return merged


__all__ = ["BatchWorkingSetBuilder"]
