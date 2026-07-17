"""Persistence backend assembly for knowbase."""

from internal.infrastructure.persistence.factory import build_persistence_bundle
from internal.infrastructure.persistence.types import PersistenceBundle

__all__ = [
    "PersistenceBundle",
    "build_persistence_bundle",
]
