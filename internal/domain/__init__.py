"""Domain-layer facade for knowbase."""

from importlib import import_module

_EXPORTS = {
    "KnowbaseCaseDraftBuilder": "internal.domain.case",
    "KnowbaseCaseIngestor": "internal.domain.case",
    "KnowbaseCaseRetriever": "internal.domain.case",
    "KnowbaseCaseService": "internal.domain.case",
    "KnowbaseCaseSummaryExtractor": "internal.domain.case",
    "KnowbaseCaseWriteService": "internal.domain.case",
    "KnowbaseSemanticProfileExtractor": "internal.domain.case",
    "build_case_content_representation": "internal.domain.case",
    "build_case_search_representation": "internal.domain.case",
    "PartitionService": "internal.domain.partition",
    "KnowbaseEventInboxService": "internal.domain.event",
    "KnowbaseEventPublisher": "internal.domain.event",
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
    "KnowbaseCaseDraftBuilder",
    "KnowbaseCaseIngestor",
    "KnowbaseCaseRetriever",
    "KnowbaseCaseService",
    "KnowbaseCaseSummaryExtractor",
    "KnowbaseCaseWriteService",
    "KnowbaseEventInboxService",
    "KnowbaseEventPublisher",
    "KnowbaseSemanticProfileExtractor",
    "build_case_content_representation",
    "build_case_search_representation",
    "PartitionService",
]
