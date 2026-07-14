"""Runtime primitives for knowbase."""

from __future__ import annotations

from importlib import import_module

_EXPORTS = {
    "RuntimeRunRequest": "runtime.contracts",
    "RuntimeAction": "runtime.contracts",
    "RuntimeDecision": "runtime.contracts",
    "RuntimeObservation": "runtime.contracts",
    "RuntimeMemorySnapshot": "runtime.contracts",
    "RuntimeTurnInput": "runtime.contracts",
    "RuntimeRunResult": "runtime.contracts",
    "RuntimeRunState": "runtime.state",
    "KnowbaseRuntimeService": "runtime.service",
    "RuntimeExecutor": "runtime.executor",
    "RuntimeAgentPort": "runtime.agent",
    "DeterministicRuntimeAgent": "runtime.agent",
    "RuntimeActionExecutor": "runtime.action_executor",
    "RuntimeLoopEngine": "runtime.engine",
    "RuntimeMemoryManager": "runtime.memory",
    "RuntimePolicy": "runtime.policy",
    "RuntimeTerminationPolicy": "runtime.termination",
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
    "RuntimeRunRequest",
    "RuntimeAction",
    "RuntimeDecision",
    "RuntimeObservation",
    "RuntimeMemorySnapshot",
    "RuntimeTurnInput",
    "RuntimeRunResult",
    "RuntimeRunState",
    "KnowbaseRuntimeService",
    "RuntimeExecutor",
    "RuntimeAgentPort",
    "DeterministicRuntimeAgent",
    "RuntimeActionExecutor",
    "RuntimeLoopEngine",
    "RuntimeMemoryManager",
    "RuntimePolicy",
    "RuntimeTerminationPolicy",
]
