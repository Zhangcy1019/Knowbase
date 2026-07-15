"""Backlog-layer facade for knowbase."""

from importlib import import_module

_EXPORTS = {
    "EventWorkerRunResult": "backlog",
    "KnowbaseEventBacklogService": "backlog",
    "KnowbaseEventService": "backlog",
    "KnowbaseEventWorker": "backlog",
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
]
