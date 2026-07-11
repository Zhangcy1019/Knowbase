"""Case draft builder skeleton."""

from __future__ import annotations

from internal.models import IngestRequest, KnowbaseCaseDraft, KnowbaseCaseMetadata


class KnowbaseCaseDraftBuilder:
    """Build a minimal case draft from ingest input."""

    def build(self, request: IngestRequest) -> KnowbaseCaseDraft:
        return KnowbaseCaseDraft(
            partition=request.partition_name,
            title=request.title,
            source_content=request.source_content,
            source_refs=request.source_refs,
            metadata=KnowbaseCaseMetadata(author=request.author, source=request.source),
        )
