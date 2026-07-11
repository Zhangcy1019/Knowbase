"""Case ingestor skeleton."""

from __future__ import annotations

from datetime import datetime, timezone

from internal.domain.case.search_representation import build_case_content_representation, build_case_search_representation
from internal.models import KnowbaseCaseDocument, KnowbaseCaseDraft


class KnowbaseCaseIngestor:
    """Build canonical case documents from drafts."""

    def build_document(self, *, case_id: str, draft: KnowbaseCaseDraft) -> KnowbaseCaseDocument:
        now = datetime.now(timezone.utc)
        return KnowbaseCaseDocument(
            case_id=case_id,
            partition=draft.partition,
            title=draft.title,
            source_content=draft.source_content,
            source_refs=draft.source_refs,
            summary_text=draft.summary_text,
            semantic_profile=draft.semantic_profile,
            metadata=draft.metadata,
            facets=draft.facets,
            created_at=now,
            updated_at=now,
            search_text=self.build_search_text(draft=draft),
        )

    def build_search_text(self, *, draft: KnowbaseCaseDraft) -> str:
        return build_case_search_representation(draft=draft)

    def build_content_text(self, *, draft: KnowbaseCaseDraft) -> str:
        return build_case_content_representation(draft=draft)
