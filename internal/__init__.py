"""Public package interface for knowbase.

The top-level package intentionally exports only product-facing entrypoints
and a small set of core models. Internal repositories, compilers, planners,
matchers, and other implementation details should be imported from their
subpackages directly when needed.
"""

from internal.models import IngestRequest, IngestResult, KnowbaseCaseDocument, PartitionDocument, QueryAnswer, QueryRequest, QueryResult
from internal.product.ingest.service import KnowbaseIngestService
from internal.product.query.flow import KnowbaseQueryFlow
from internal.product.query.service import KnowbaseQueryService

__all__ = [
    "IngestRequest",
    "IngestResult",
    "KnowbaseCaseDocument",
    "KnowbaseIngestService",
    "KnowbaseQueryFlow",
    "KnowbaseQueryService",
    "PartitionDocument",
    "QueryAnswer",
    "QueryRequest",
    "QueryResult",
]
