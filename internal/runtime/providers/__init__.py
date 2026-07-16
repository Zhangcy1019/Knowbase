"""External provider adapters used by runtime."""

from __future__ import annotations

from importlib import import_module

_EXPORTS = {
    "RuntimeModelRequest": "internal.runtime.providers.openai_runtime_adapter",
    "RuntimeModelResponse": "internal.runtime.providers.openai_runtime_adapter",
    "RuntimeModelAdapterPort": "internal.runtime.providers.openai_runtime_adapter",
    "OpenAIRuntimeModelAdapter": "internal.runtime.providers.openai_runtime_adapter",
    "DefaultRuntimeModelAdapter": "internal.runtime.providers.openai_runtime_adapter",
    "OpenAIChatRequest": "internal.runtime.providers.openai_client",
    "OpenAIChatResponse": "internal.runtime.providers.openai_client",
    "OpenAIClientPort": "internal.runtime.providers.openai_client",
    "DefaultOpenAIClient": "internal.runtime.providers.openai_client",
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
