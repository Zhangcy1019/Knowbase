"""Observation-layer semantic candidate models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class CaseSemanticCandidate:
    """One extracted semantic candidate from one case."""

    case_id: str = ""
    partition: str = ""
    key: str = ""
    canonical_key: str = ""
    value: str = ""
    canonical_value: str = ""
    confidence: float = 0.0
    evidence_spans: list[dict[str, object]] = field(default_factory=list)
    source_excerpt_hash: str = ""
    extraction_version: str = ""
    observed_at: str = ""
    batch_id: str = ""
