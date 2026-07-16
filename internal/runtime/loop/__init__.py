"""Runtime loop orchestration components."""

from __future__ import annotations

from importlib import import_module

_EXPORTS = {
    "RuntimeLoopEngine": "internal.runtime.loop.engine",
    "RuntimePlannerContext": "internal.runtime.loop.planner_components",
    "RuntimePlannerObservation": "internal.runtime.loop.planner_components",
    "RuntimePlannerStopAssessment": "internal.runtime.loop.planner_components",
    "RuntimeObservationAssemblerPort": "internal.runtime.loop.planner_components",
    "RuntimeStopEvaluatorPort": "internal.runtime.loop.planner_components",
    "DefaultRuntimeObservationAssembler": "internal.runtime.loop.planner_components",
    "DefaultRuntimeStopEvaluator": "internal.runtime.loop.planner_components",
    "RuntimeTurnPlannerPort": "internal.runtime.loop.turn_planner",
    "UnconfiguredRuntimeTurnPlanner": "internal.runtime.loop.turn_planner",
    "RuntimeTurnPlanner": "internal.runtime.loop.turn_planner",
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
