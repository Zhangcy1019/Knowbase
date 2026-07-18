"""Persistence backend factory."""

from __future__ import annotations

from internal.infrastructure.persistence.es import build_es_persistence_bundle
from internal.infrastructure.persistence.local import build_local_persistence_bundle
from internal.infrastructure.persistence.types import PersistenceBundle
from internal.utils.config import RuntimeConfig


def build_persistence_bundle(*, runtime_cfg: RuntimeConfig) -> PersistenceBundle:
    backend = runtime_cfg.storage.backend.strip().lower()
    if backend == "es":
        return build_es_persistence_bundle(runtime_cfg=runtime_cfg)
    if backend == "local":
        return build_local_persistence_bundle(runtime_cfg=runtime_cfg)
    raise ValueError(f"unsupported storage backend: {runtime_cfg.storage.backend}")
