"""Product-layer facade for knowbase."""

from importlib import import_module

_EXPORTS = {
    "KnowbaseCommitService": "product.ingest",
    "KnowbaseIngestService": "product.ingest",
    "KnowbaseIngestValidator": "product.ingest",
    "KnowbaseQueryFlow": "product.query",
    "KnowbaseQueryPlanner": "product.query",
    "KnowbaseQuerySemanticProfileExtractor": "product.query",
    "KnowbaseQueryService": "product.query",
    "KnowbaseRanking": "product.query",
    "QueryNormalizer": "product.query",
    "build_query_search_representation": "product.query",
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
    "KnowbaseCommitService",
    "KnowbaseIngestService",
    "KnowbaseIngestValidator",
    "KnowbaseQueryFlow",
    "KnowbaseQueryPlanner",
    "KnowbaseQuerySemanticProfileExtractor",
    "KnowbaseQueryService",
    "KnowbaseRanking",
    "QueryNormalizer",
    "build_query_search_representation",
]
