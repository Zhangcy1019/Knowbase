"""Backlog-layer facade for knowbase."""

from importlib import import_module

_EXPORTS = {
    "EventWorkerRunResult": "internal.backlog.events",
    "KnowbaseEventBacklogService": "internal.backlog.events",
    "KnowbaseEventService": "internal.backlog.service",
    "KnowbaseEventWorker": "internal.backlog.events",
    "BacklogBatch": "internal.backlog.events",
    "PartitionTask": "internal.backlog.tasks",
    "PartitionTaskQueue": "internal.backlog.tasks",
    "PartitionTaskKind": "internal.backlog.tasks",
    "PartitionTaskStatus": "internal.backlog.tasks",
}


def __getattr__(name: str):
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name)
    value = getattr(module, name)
    globals()[name] = value
    return value


__all__ = [
    "EventWorkerRunResult",
    "KnowbaseEventBacklogService",
    "KnowbaseEventService",
    "KnowbaseEventWorker",
    "BacklogBatch",
    "PartitionTask",
    "PartitionTaskQueue",
    "PartitionTaskKind",
    "PartitionTaskStatus",
]
