"""Shared context objects passed across the runtime harness."""

from __future__ import annotations

from dataclasses import dataclass

from internal.runtime.contracts import RuntimeTurnInput
from internal.runtime.memory import RuntimeWorkingMemory
from internal.runtime.session import RuntimeLoopState, RuntimeSession


@dataclass(slots=True)
class RuntimeAgentContext:
    """Full runtime context exposed to one agent turn."""

    session: RuntimeSession
    loop_state: RuntimeLoopState
    memory: RuntimeWorkingMemory
    turn_input: RuntimeTurnInput
