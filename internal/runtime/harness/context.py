"""Shared harness context objects."""

from __future__ import annotations

from dataclasses import dataclass

from internal.runtime.memory.state import RuntimeRunState


@dataclass(slots=True)
class RuntimeHarnessContext:
    """Stable context passed into harness hooks."""

    run: object
    request: object
    state: RuntimeRunState
