"""Skill for rebuilding a case and its derived retrieval artifacts."""

from __future__ import annotations

from datetime import datetime, timezone

from internal.infrastructure.ai.embedding_contracts import EmbeddingProvider
from internal.models import KnowbaseCaseDocument, KnowbaseCaseDraft
from internal.knowledge.capability.skills.action import SkillAction
from internal.models.skill import SkillInvocation, SkillResult, SkillSpec
from internal.models.skill_context import SkillExecutionContext
from internal.ports import (
    CaseFacetResolutionPort,
    CaseRepositoryPort,
    CaseRepresentationPort,
    CaseSemanticProfilePort,
    CaseSummaryPort,
    PartitionLookupPort,
)
from internal.knowledge.capability.skills.case.payloads import RebuildCasePayload
from internal.utils.logger import get_logger

logger = get_logger(__name__)


class RebuildCaseSkill:
    """Recompute one case and all derived projections."""

    def __init__(
        self,
        *,
        case_repository: CaseRepositoryPort,
        partition_service: PartitionLookupPort,
        summary_extractor: CaseSummaryPort,
        semantic_profile_extractor: CaseSemanticProfilePort,
        facet_resolver: CaseFacetResolutionPort,
        ingestor: CaseRepresentationPort,
        embedding_provider: EmbeddingProvider | None = None,
    ):
        self._case_repository = case_repository
        self._partition_service = partition_service
        self._summary_extractor = summary_extractor
        self._semantic_profile_extractor = semantic_profile_extractor
        self._facet_resolver = facet_resolver
        self._ingestor = ingestor
        if embedding_provider is None:
            raise ValueError("RebuildCaseSkill requires an explicit embedding_provider")
        self._embedding_provider = embedding_provider
        self._spec = SkillSpec(
            skill_id="case.rebuild_case",
            title="Rebuild Case",
            description="Recompute one case and its derived fields.",
            execution_mode="deterministic",
            side_effect_scope="single_resource",
            input_schema={
                "type": "object",
                "additionalProperties": False,
                "required": ["case_id"],
                "properties": {
                    "case_id": {"type": "string", "description": "Target case id to rebuild."},
                    "partition": {"type": "string", "description": "Owning partition when available."},
                    "force": {"type": "boolean", "description": "Force rebuild even when no changes are detected."},
                },
            },
            examples=[
                {"inputs": {"case_id": "case-123", "partition": "CI", "force": False}},
            ],
            usage_notes=[
                "Use this skill when summary, semantic profile, facets, or embeddings need a full refresh.",
            ],
            argument_binding_hints={
                "case_id": "input_context.case_id",
                "partition": "request.partition",
            },
        )

    @property
    def spec(self) -> SkillSpec:
        return self._spec

    def execute(self, invocation: SkillInvocation, *, context: SkillExecutionContext | None = None) -> SkillResult:
        started_at = datetime.now(timezone.utc)
        execution_context = context or SkillExecutionContext(partition=invocation.partition)
        action = SkillAction(
            action_type="rebuild",
            target_type="case",
            target_id=str(invocation.inputs.get("case_id", "")),
            payload={k: v for k, v in invocation.inputs.items() if isinstance(v, (str, list, dict))},
        )
        result = self._execute_action(action, context=execution_context)
        return SkillResult(
            invocation_id=invocation.invocation_id,
            skill_id=invocation.skill_id,
            ok=True,
            updated_objects=[str(item) for item in result.get("updated_objects", [])],
            output=result,
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
        )

    def _execute_action(self, action: SkillAction, *, context: SkillExecutionContext) -> dict[str, object]:
        payload = RebuildCasePayload.model_validate(
            {
                "partition": context.partition or str(action.payload.get("partition", "")),
                **action.payload,
            }
        )
        document = self._case_repository.get(payload.case_id)
        if document is None:
            raise ValueError(f"case not found: {payload.case_id}")

        partition = self._partition_service.get_partition(document.partition)
        if partition is None:
            raise ValueError(f"partition not found: {document.partition}")
        facet_definitions = self._partition_service.list_facet_definitions(document.partition)

        logger.info("Executing rebuild_case for %s:%s (force=%s)", context.partition, payload.case_id, payload.force)

        summary_text = self._summary_extractor.extract_sync(title=document.title, source_content=document.source_content)
        semantic_profile = self._semantic_profile_extractor.extract_sync(
            title=document.title,
            source_content=document.source_content,
            facet_definitions=facet_definitions,
        )
        facets = self._facet_resolver.project_from_semantic_profile(
            semantic_profile=semantic_profile,
            facet_definitions=facet_definitions,
        )
        updated = document.model_copy(
            update={
                "summary_text": summary_text,
                "semantic_profile": semantic_profile,
                "facets": facets,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._enrich_case_document(updated)
        self._case_repository.upsert(updated)
        return {
            "updated_objects": [payload.case_id],
            "reasoning_summary": f"rebuild_case completed for {context.partition}:{payload.case_id}",
            "facets": facets,
        }

    def _enrich_case_document(self, document: KnowbaseCaseDocument) -> None:
        draft = KnowbaseCaseDraft(
            partition=document.partition,
            title=document.title,
            source_content=document.source_content,
            source_refs=document.source_refs,
            summary_text=document.summary_text,
            semantic_profile=document.semantic_profile,
            metadata=document.metadata,
            facets=document.facets,
        )
        document.search_text = self._ingestor.build_search_text(draft=draft)
        document.search_vector = []
        document.content_vector = []
        if not document.search_text.strip():
            return
        try:
            document.search_vector = self._embedding_provider.embed_documents([document.search_text])[0]
            content_text = self._ingestor.build_content_text(draft=draft)
            if content_text.strip():
                document.content_vector = self._embedding_provider.embed_documents([content_text])[0]
        except Exception as exc:  # pragma: no cover - operational path
            logger.warning(
                "Rebuild case failed to refresh embeddings",
                extra={"case_id": document.case_id, "partition": document.partition, "error": str(exc)},
            )
