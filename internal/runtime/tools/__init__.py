"""Runtime tool capability infrastructure."""

from __future__ import annotations

from importlib import import_module

_EXPORTS = {
    "ToolHandler": "internal.runtime.tools.types",
    "ToolRegistry": "internal.runtime.tools.registry",
    "ToolRuntime": "internal.runtime.tools.runtime",
}


def __getattr__(name: str):
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name)
    value = getattr(module, name)
    globals()[name] = value
    return value


__all__ = list(_EXPORTS)
