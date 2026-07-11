"""Domain-layer facade for knowbase."""

from importlib import import_module

_EXPORTS = {
    "KnowbaseCaseDraftBuilder": "domain.case",
    "KnowbaseCaseIngestor": "domain.case",
    "KnowbaseCaseRepository": "domain.case",
    "KnowbaseCaseRetriever": "domain.case",
    "KnowbaseCaseService": "domain.case",
    "KnowbaseCaseSummaryExtractor": "domain.case",
    "KnowbaseCaseWriteService": "domain.case",
    "KnowbaseSemanticProfileExtractor": "domain.case",
    "build_case_content_representation": "domain.case",
    "build_case_search_representation": "domain.case",
    "PartitionRepository": "domain.partition",
    "PartitionService": "domain.partition",
    "EventRecordRepository": "domain.event",
    "KnowbaseEventInboxService": "domain.event",
    "KnowbaseEventPublisher": "domain.event",
    "AgentRunRepository": "domain.run",
    "RunArtifactRepository": "domain.run",
    "RunStepRepository": "domain.run",
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
    "AgentRunRepository",
    "EventRecordRepository",
    "KnowbaseCaseDraftBuilder",
    "KnowbaseCaseIngestor",
    "KnowbaseCaseRepository",
    "KnowbaseCaseRetriever",
    "KnowbaseCaseService",
    "KnowbaseCaseSummaryExtractor",
    "KnowbaseCaseWriteService",
    "KnowbaseEventInboxService",
    "KnowbaseEventPublisher",
    "KnowbaseSemanticProfileExtractor",
    "build_case_content_representation",
    "build_case_search_representation",
    "PartitionRepository",
    "PartitionService",
    "RunArtifactRepository",
    "RunStepRepository",
]
