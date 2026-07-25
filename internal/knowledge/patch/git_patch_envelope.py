"""Git envelope skeleton for knowledge patches."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class GitPatchEnvelope:
    """Execution-layer wrapper around one knowledge patch."""

    patch_id: str = ""
    branch_name: str = ""
    commit_id: str = ""
    revert_target: str = ""
