"""Case commit skeleton for knowbase ingest."""

from __future__ import annotations

from internal.embedding.contracts import EmbeddingProvider
from internal.domain.case.ingestor import KnowbaseCaseIngestor
from internal.models import IngestResult, KnowbaseCaseDraft
from internal.ports import CaseStorePort
from internal.utils.logger import get_logger


logger = get_logger(__name__)


class KnowbaseCommitService:
    """Persist one validated case draft."""

    def __init__(
        self,
        *,
        case_service: CaseStorePort,
        ingestor: KnowbaseCaseIngestor,
        embedding_provider: EmbeddingProvider | None = None,
    ):
        self._case_service = case_service
        self._ingestor = ingestor
        if embedding_provider is None:
            raise ValueError("KnowbaseCommitService requires an explicit embedding_provider")
        self._embedding_provider = embedding_provider

    def commit(self, *, case_id: str, draft: KnowbaseCaseDraft) -> IngestResult:
        document = self._ingestor.build_document(case_id=case_id, draft=draft)
        if not document.search_text.strip():
            raise RuntimeError(f"KnowbaseCommitService requires non-empty search_text for case {case_id}")
        try:
            document.search_vector = self._embedding_provider.embed_documents([document.search_text])[0]
            content_text = self._ingestor.build_content_text(draft=draft)
            if content_text.strip():
                document.content_vector = self._embedding_provider.embed_documents([content_text])[0]
        except Exception as exc:  # pragma: no cover - operational path
            logger.exception("Failed to build case embedding", extra={"case_id": case_id, "error": str(exc)})
            raise RuntimeError(f"Failed to build case embedding for {case_id}: {exc}") from exc
        stored = self._case_service.store(document)
        return IngestResult(case_id=stored.case_id, draft=draft)
