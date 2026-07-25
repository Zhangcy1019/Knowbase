"""Knowledge patch builder skeleton."""

from __future__ import annotations


class KnowledgePatchBuilder:
    """Build batch-scoped reversible knowledge patches from schema and case deltas."""

    def build(self, *, batch, schema_patch, case_patches):
        raise NotImplementedError
