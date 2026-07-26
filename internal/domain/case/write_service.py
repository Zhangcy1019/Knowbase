"""Online write-path service for knowbase cases."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from internal.infrastructure.ai.embedding_contracts import EmbeddingProvider
from internal.domain.case.facet_resolver import KnowbaseCaseFacetResolver
from internal.domain.case.ingestor import KnowbaseCaseIngestor
from internal.models import CaseFacetProfile, CaseSemanticProfile, KnowbaseCaseDocument, KnowbaseCaseDraft, KnowbaseCaseMetadata
from internal.domain.partition.service import PartitionService
from internal.utils.logger import get_logger


logger = get_logger(__name__)


class KnowbaseCaseWriteService:
    """Own the online write path for case create and update requests."""

    def __init__(
        self,
        *,
        repository,
        partition_service: PartitionService,
        ingestor: KnowbaseCaseIngestor | None = None,
        facet_resolver: KnowbaseCaseFacetResolver | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        statistics=None,
        versioning_factory=None,
        task_queue=None,
        mutation_lock_factory=None,
    ):
        self._repository = repository
        self._partition_service = partition_service
        self._ingestor = ingestor or KnowbaseCaseIngestor()
        self._facet_resolver = facet_resolver or KnowbaseCaseFacetResolver()
        if embedding_provider is None:
            raise ValueError("KnowbaseCaseWriteService requires an explicit embedding_provider")
        self._embedding_provider = embedding_provider
        self._statistics = statistics
        self._versioning_factory = versioning_factory
        self._task_queue = task_queue
        self._mutation_lock_factory = mutation_lock_factory

    async def update_case_queued(self, **kwargs):
        """Serialize an update through the shared partition task queue."""
        case_id = kwargs.get("case_id", "")
        existing = self._repository.get(case_id)
        if existing is None:
            raise ValueError(f"case not found: {case_id}")
        if self._task_queue is None:
            return self.update_case(**kwargs)
        result: dict[str, object] = {}

        async def handler(_task) -> None:
            lock = self._mutation_lock_factory(existing.partition) if self._mutation_lock_factory else _NullContext()
            with lock:
                self._prepare_versioning(existing.partition)
                result["value"] = self.update_case(**kwargs)

        task = self._task_queue.enqueue(
            partition=existing.partition,
            kind="case_update",
            payload={"case_id": case_id},
            handler=handler,
        )
        await self._task_queue.wait_idle(partition=existing.partition)
        if task.status == "failed":
            raise RuntimeError(task.error_message or f"case update task failed: {case_id}")
        return result["value"]

    async def delete_case_queued(self, *, case_id: str):
        """Serialize a delete through the shared partition task queue."""
        existing = self._repository.get(case_id)
        if existing is None:
            raise ValueError(f"case not found: {case_id}")
        if self._task_queue is None:
            return self.delete_case(case_id=case_id)
        result: dict[str, object] = {}

        async def handler(_task) -> None:
            lock = self._mutation_lock_factory(existing.partition) if self._mutation_lock_factory else _NullContext()
            with lock:
                self._prepare_versioning(existing.partition)
                result["value"] = self.delete_case(case_id=case_id)

        task = self._task_queue.enqueue(
            partition=existing.partition,
            kind="case_delete",
            payload={"case_id": case_id},
            handler=handler,
        )
        await self._task_queue.wait_idle(partition=existing.partition)
        if task.status == "failed":
            raise RuntimeError(task.error_message or f"case delete task failed: {case_id}")
        return result["value"]

    def create_case(
        self,
        *,
        case_id: str | None = None,
        partition_name: str,
        title: str,
        source_content: str,
        source_refs: list[str],
        summary_text: str,
        semantic_profile: CaseSemanticProfile,
        metadata: KnowbaseCaseMetadata,
        facets: CaseFacetProfile | dict[str, list[str]] | None = None,
    ) -> KnowbaseCaseDocument:
        partition = self._partition_service.get_partition(partition_name)
        if partition is None:
            raise ValueError(f"partition not found: {partition_name}")
        facet_definitions = self._partition_service.list_facet_definitions(partition_name)
        normalized_facets = self._normalize_facets(
            facets=self._facet_resolver.normalize(
                facets=facets or {},
                facet_definitions=facet_definitions,
            )
        )
        now = datetime.now(timezone.utc)
        case_document = KnowbaseCaseDocument(
            case_id=case_id or f"case-{uuid4().hex}",
            partition=partition_name,
            created_at=now,
            updated_at=now,
            metadata=metadata,
            title=title,
            source_content=source_content,
            source_refs=source_refs,
            summary_text=summary_text,
            semantic_profile=CaseSemanticProfile.model_validate(
                semantic_profile,
            ),
            facets=normalized_facets,
        )
        self._enrich_document(case_document)
        return self._repository.upsert(case_document)

    def update_case(
        self,
        *,
        case_id: str,
        title: str | None = None,
        source_content: str | None = None,
        source_refs: list[str] | None = None,
        summary_text: str | None = None,
        semantic_profile: CaseSemanticProfile | None = None,
        metadata: KnowbaseCaseMetadata | None = None,
        facets: CaseFacetProfile | dict[str, list[str]] | None = None,
        raw_text: str | None = None,
        case_detail: str | None = None,
    ) -> tuple[KnowbaseCaseDocument, KnowbaseCaseDocument, list[str]]:
        existing = self._repository.get(case_id)
        if existing is None:
            raise ValueError(f"case not found: {case_id}")
        partition = self._partition_service.get_partition(existing.partition)
        if partition is None:
            raise ValueError(f"partition not found: {existing.partition}")
        self._prepare_versioning(existing.partition)
        facet_definitions = self._partition_service.list_facet_definitions(existing.partition)

        resolved_source_content = existing.source_content
        if source_content is not None:
            resolved_source_content = source_content
        elif case_detail is not None:
            resolved_source_content = case_detail
        elif raw_text is not None:
            resolved_source_content = raw_text

        next_title = existing.title if title is None else title
        next_source_refs = existing.source_refs if source_refs is None else source_refs
        next_summary_text = existing.summary_text if summary_text is None else summary_text
        next_semantic_profile = (
            existing.semantic_profile
            if semantic_profile is None
            else CaseSemanticProfile.model_validate(semantic_profile)
        )
        next_metadata = existing.metadata if metadata is None else metadata
        resolved_facets = CaseFacetProfile.model_validate(existing.facets)
        if facets is not None:
            resolved_facets = self._normalize_facets(facets=facets)
        changed_fields: list[str] = []
        if next_title != existing.title:
            changed_fields.append("title")
        if resolved_source_content != existing.source_content:
            changed_fields.append("source_content")
        if next_source_refs != existing.source_refs:
            changed_fields.append("source_refs")
        if next_summary_text != existing.summary_text:
            changed_fields.append("summary_text")
        if next_semantic_profile != existing.semantic_profile:
            changed_fields.append("semantic_profile")
        if next_metadata != existing.metadata:
            changed_fields.append("metadata")
        if resolved_facets != existing.facets:
            changed_fields.append("facets")

        updated = existing.model_copy(
            update={
                "title": next_title,
                "source_content": resolved_source_content,
                "source_refs": next_source_refs,
                "summary_text": next_summary_text,
                "semantic_profile": next_semantic_profile,
                "metadata": next_metadata,
                "facets": resolved_facets,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._enrich_document(updated)
        persisted = self._repository.upsert(updated)
        self._record_update(existing=existing, updated=persisted)
        return existing, persisted, changed_fields

    def delete_case(self, *, case_id: str) -> KnowbaseCaseDocument:
        """Delete a case and maintain its derived statistics and revision."""
        existing = self._repository.get(case_id)
        if existing is None:
            raise ValueError(f"case not found: {case_id}")
        self._prepare_versioning(existing.partition)
        self._repository.delete(case_id)
        try:
            self._remove_statistics(existing)
            self._commit_case(existing)
        except Exception as exc:
            logger.exception(
                "Case delete side effects failed after persistence.",
                extra={"case_id": case_id, "partition": existing.partition},
            )
            raise RuntimeError(f"case delete side effects failed for {case_id}: {exc}") from exc
        return existing

    def _record_update(self, *, existing: KnowbaseCaseDocument, updated: KnowbaseCaseDocument) -> None:
        try:
            if self._statistics is not None:
                self._statistics.replace_case_observation(
                    old_observation=self._observation(existing),
                    new_observation=self._observation(updated),
                )
            self._commit_case(updated)
        except Exception as exc:
            logger.exception(
                "Case update side effects failed after persistence.",
                extra={"case_id": updated.case_id, "partition": updated.partition},
            )
            raise RuntimeError(f"case update side effects failed for {updated.case_id}: {exc}") from exc

    def _remove_statistics(self, document: KnowbaseCaseDocument) -> None:
        if self._statistics is not None:
            self._statistics.remove_observation(observation=self._observation(document))

    def _commit_case(self, document: KnowbaseCaseDocument) -> None:
        if self._versioning_factory is not None:
            self._versioning_factory(document.partition).commit_case_ingest(
                case_id=document.case_id,
                paths=[
                    f"cases/{document.case_id}.json",
                ],
            )

    def _prepare_versioning(self, partition: str) -> None:
        if self._versioning_factory is not None:
            self._versioning_factory(partition)

    @staticmethod
    def _observation(document: KnowbaseCaseDocument):
        from internal.knowledge.statistics import CaseObservation

        return CaseObservation(
            observation_id=f"case:{document.case_id}",
            partition=document.partition,
            source_id=document.case_id,
            facets=document.facets.model_dump(),
            semantic_profile=document.semantic_profile.model_dump(),
        )

    @staticmethod
    def _normalize_facets(*, facets: CaseFacetProfile | dict[str, list[str]]) -> CaseFacetProfile:
        normalized: dict[str, list[str]] = {}
        for key, values in facets.items():
            normalized_key = str(key).strip()
            if not normalized_key:
                continue
            cleaned = [str(item).strip() for item in values if str(item).strip()]
            if cleaned:
                normalized[normalized_key] = list(dict.fromkeys(cleaned))
        return CaseFacetProfile.model_validate(normalized)

    def _enrich_document(self, document: KnowbaseCaseDocument) -> None:
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
            logger.exception(
                "Online knowbase case write failed to build embeddings",
                extra={"case_id": document.case_id, "partition": document.partition, "error": str(exc)},
            )
            raise RuntimeError(
                f"Failed to build case embedding for {document.case_id}: {exc}"
            ) from exc


class _NullContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None
