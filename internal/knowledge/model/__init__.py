"""Primary knowledge-domain models for schema convergence."""

from internal.knowledge.model.mutation_plan import KnowledgeMutationPlan
from internal.knowledge.model.semantic_candidate import CaseSemanticCandidate
from internal.knowledge.model.semantic_index import PartitionSemanticIndex

__all__ = [
    "CaseSemanticCandidate",
    "KnowledgeMutationPlan",
    "PartitionSemanticIndex",
]
