"""Primary knowledge-domain models for schema convergence."""

from internal.knowledge.model.case_facet_patch import CaseFacetPatch
from internal.knowledge.model.facet_schema_patch import PartitionFacetSchemaPatch
from internal.knowledge.model.knowledge_patch import KnowledgePatch
from internal.knowledge.model.semantic_candidate import CaseSemanticCandidate
from internal.knowledge.model.semantic_index import PartitionSemanticIndex

__all__ = [
    "CaseFacetPatch",
    "CaseSemanticCandidate",
    "KnowledgePatch",
    "PartitionFacetSchemaPatch",
    "PartitionSemanticIndex",
]
