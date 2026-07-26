"""Registry assembly helpers for tools and skills."""

from __future__ import annotations

from internal.infrastructure.ai.embedding_service import create_embedding_provider
from internal.domain.case.facet_resolver import KnowbaseCaseFacetResolver
from internal.domain.case.ingestor import KnowbaseCaseIngestor
from internal.domain.case.semantic_profile_extractor import KnowbaseSemanticProfileExtractor
from internal.domain.case.summary_extractor import KnowbaseCaseSummaryExtractor
from internal.ports import (
    CaseReadPort,
    CaseRepositoryPort,
    PartitionLookupPort,
    PartitionProfileWritePort,
)
from internal.runtime.skills import SkillRegistry
from internal.knowledge.capability.skills.case import RebuildCaseSkill, RefreshCaseFacetsSkill
from internal.knowledge.capability.skills.partition import RefreshSelectedCasesFacetsSkill
from internal.runtime.tools import ToolRegistry
from internal.knowledge.capability.tools import GetCaseTool, GetPartitionTool, ListCasesTool
from internal.utils.config import RuntimeConfig


def build_skill_registry(
    *,
    runtime_cfg: RuntimeConfig,
    case_repository: CaseRepositoryPort,
    partition_service: PartitionLookupPort | PartitionProfileWritePort,
) -> SkillRegistry:
    facet_resolver = KnowbaseCaseFacetResolver()
    summary_extractor = KnowbaseCaseSummaryExtractor(llm_config=runtime_cfg.llm)
    semantic_profile_extractor = KnowbaseSemanticProfileExtractor(llm_config=runtime_cfg.llm)
    ingestor = KnowbaseCaseIngestor()
    embedding_provider = create_embedding_provider(runtime_cfg.embedding)
    skill_registry = SkillRegistry()
    skill_registry.register(
        RebuildCaseSkill(
            case_repository=case_repository,
            partition_service=partition_service,
            summary_extractor=summary_extractor,
            semantic_profile_extractor=semantic_profile_extractor,
            facet_resolver=facet_resolver,
            ingestor=ingestor,
            embedding_provider=embedding_provider,
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
