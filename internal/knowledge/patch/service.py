"""Knowledge patch capability facade."""

from __future__ import annotations


class KnowledgePatchService:
    """Build, persist, and apply reversible knowledge changes."""

    def build(self, *, schema_change, projection_change, batch):
        raise NotImplementedError

    def apply(self, *, patch):
        raise NotImplementedError

