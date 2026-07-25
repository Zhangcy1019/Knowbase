"""Facet schema analysis and convergence capability."""

from internal.knowledge.facet_governance.circuit_breaker import KnowledgeCircuitBreaker
from internal.knowledge.facet_governance.facet_key_convergence import FacetKeyConvergencePlanner
from internal.knowledge.facet_governance.fit_metrics import PartitionFitMetrics
from internal.knowledge.facet_governance.freeze_policy import FacetFreezePolicy
from internal.knowledge.facet_governance.facet_governance_service import FacetGovernanceService
from internal.knowledge.facet_governance.metrics import FacetGovernanceMetrics
from internal.knowledge.facet_governance.models import (
    FacetGovernanceResult,
    PartitionFacetCoverageAssessment,
    PartitionFacetSchemaProposal,
    PartitionRebuildRecommendation,
)

__all__ = [
    "FacetFreezePolicy",
    "FacetKeyConvergencePlanner",
    "KnowledgeCircuitBreaker",
    "PartitionFitMetrics",
    "FacetGovernanceService",
    "FacetGovernanceMetrics",
    "FacetGovernanceResult",
    "PartitionFacetCoverageAssessment",
    "PartitionFacetSchemaProposal",
    "PartitionRebuildRecommendation",
]
