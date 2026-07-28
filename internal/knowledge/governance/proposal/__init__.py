"""Pluggable deterministic schema-proposal discovery."""

from internal.knowledge.governance.proposal.contracts import (
    GovernanceProposalContext,
    GovernanceProposalConflict,
    GovernanceProposalPlugin,
    GovernanceProposalPluginResult,
    GovernanceProposalReport,
    has_effective_schema_proposal,
)
from internal.knowledge.governance.proposal.pipeline import GovernanceProposalPipeline
from internal.knowledge.governance.proposal.models import PartitionFacetSchemaProposal
from internal.knowledge.governance.proposal.plugins import (
    FacetKeyDemotionProposal,
    SemanticKeyPromotionProposal,
)

__all__ = [
    "FacetKeyDemotionProposal",
    "GovernanceProposalContext",
    "GovernanceProposalConflict",
    "GovernanceProposalPipeline",
    "GovernanceProposalPlugin",
    "GovernanceProposalPluginResult",
    "GovernanceProposalReport",
    "PartitionFacetSchemaProposal",
    "has_effective_schema_proposal",
    "SemanticKeyPromotionProposal",
]
