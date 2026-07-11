"""Registry assembly helpers for tools and skills."""

from __future__ import annotations

from internal.domain.case.facet_resolver import KnowbaseCaseFacetResolver
from internal.domain.case.ingestor import KnowbaseCaseIngestor
from internal.domain.case.semantic_profile_extractor import KnowbaseSemanticProfileExtractor
from internal.domain.case.summary_extractor import KnowbaseCaseSummaryExtractor
from internal.ports import (
    CaseReadPort,
    CaseRepositoryPort,
    PartitionLookupPort,
)
from internal.skills import SkillRegistry
from internal.skills.case import RebuildCaseSkill, RefreshCaseFacetsSkill
from internal.skills.partition import RefreshSelectedCasesFacetsSkill
from internal.tools import GetCaseTool, GetPartitionTool, ListCasesTool, ToolRegistry


def build_skill_registry(
    *,
    case_repository: CaseRepositoryPort,
    partition_service: PartitionLookupPort,
) -> SkillRegistry:
    facet_resolver = KnowbaseCaseFacetResolver()
    summary_extractor = KnowbaseCaseSummaryExtractor()
    semantic_profile_extractor = KnowbaseSemanticProfileExtractor()
    ingestor = KnowbaseCaseIngestor()
    skill_registry = SkillRegistry()
    skill_registry.register(
        RebuildCaseSkill(
            case_repository=case_repository,
            partition_service=partition_service,
            summary_extractor=summary_extractor,
            semantic_profile_extractor=semantic_profile_extractor,
            facet_resolver=facet_resolver,
            ingestor=ingestor,
        )
    )
    skill_registry.register(
        RefreshCaseFacetsSkill(
            case_repository=case_repository,
            partition_service=partition_service,
            facet_resolver=facet_resolver,
        )
    )
    skill_registry.register(
        RefreshSelectedCasesFacetsSkill(
            case_repository=case_repository,
            partition_service=partition_service,
            facet_resolver=facet_resolver,
        )
    )
    return skill_registry


def build_tool_registry(
    *,
    case_repository: CaseReadPort,
    partition_service: PartitionLookupPort,
) -> ToolRegistry:
    tool_registry = ToolRegistry()
    tool_registry.register(GetCaseTool(repository=case_repository))
    tool_registry.register(ListCasesTool(repository=case_repository))
    tool_registry.register(GetPartitionTool(service=partition_service))
    return tool_registry
