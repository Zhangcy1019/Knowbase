"""Case-skill payload models."""

from __future__ import annotations

from pydantic import BaseModel


class RebuildCasePayload(BaseModel):
    """Rebuild one case and its derived fields from the current document snapshot."""

    partition: str
    case_id: str
    force: bool = False


class RefreshCaseFacetsPayload(BaseModel):
    """Re-evaluate one case's resolved facets from the current document snapshot."""

    partition: str
    case_id: str
    force: bool = False
