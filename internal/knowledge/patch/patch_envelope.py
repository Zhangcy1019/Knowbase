"""Knowledge patch execution envelope."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PatchEnvelope:
    """Execution metadata for one Knowledge patch."""

    patch_id: str = ""
    base_revision: str = ""
    applied_revision: str = ""
    revert_target: str = ""
