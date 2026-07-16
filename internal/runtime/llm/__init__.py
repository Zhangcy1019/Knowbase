"""Model-facing decision-generation components for runtime loop planning."""

from __future__ import annotations

from importlib import import_module

_EXPORTS = {
    "RuntimeDecisionPrompt": "internal.runtime.llm.prompt_builder",
    "RuntimePromptBuilderPort": "internal.runtime.llm.prompt_builder",
    "DefaultRuntimePromptBuilder": "internal.runtime.llm.prompt_builder",
    "RuntimeDecisionActionPayload": "internal.runtime.llm.decision_parser",
    "RuntimeDecisionPayload": "internal.runtime.llm.decision_parser",
    "RUNTIME_DECISION_PAYLOAD_JSON_SCHEMA": "internal.runtime.llm.decision_parser",
    "build_runtime_decision_payload_schema": "internal.runtime.llm.decision_parser",
    "RuntimeDecisionParserPort": "internal.runtime.llm.decision_parser",
    "DefaultRuntimeDecisionParser": "internal.runtime.llm.decision_parser",
    "RuntimeDecisionConstraints": "internal.runtime.llm.decisioning",
    "RuntimeProposedActionKind": "internal.runtime.llm.decisioning",
    "RuntimeProposedAction": "internal.runtime.llm.decisioning",
    "RuntimeDecisionDraft": "internal.runtime.llm.decisioning",
    "RuntimeDecisionGeneratorPort": "internal.runtime.llm.decisioning",
    "DefaultRuntimeDecisionGenerator": "internal.runtime.llm.decisioning",
    "RuntimeDecisionNormalizer": "internal.runtime.llm.decisioning",
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
