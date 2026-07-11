"""Core type aliases for knowbase."""

from __future__ import annotations

from enum import Enum
from typing import Literal

KnowbaseSource = Literal["agent", "user", "system", "import"]
KnowbaseStatus = Literal["draft", "published", "archived"]
RunRiskLevel = Literal["low", "medium", "high", "critical"]
AgentRunMode = Literal["deterministic", "plan", "agent"]
AgentRunStatus = Literal["pending", "running", "completed", "failed", "cancelled"]
RuntimeRunMode = Literal["deterministic", "plan", "agent"]
AgentRuntimeStage = Literal["prepare", "execute", "finalize"]


class KnowbaseEventType(str, Enum):
    CASE_CREATED = "case.created"
    CASE_UPDATED = "case.updated"
    CASE_DELETED = "case.deleted"
    PARTITION_CASE_VOLUME_THRESHOLD_REACHED = "partition.case_volume_threshold_reached"
    PARTITION_BECAME_IDLE = "partition.became_idle"
    BACKLOG_REQUESTED = "backlog.requested"


ChangeActionType = Literal[
    "create",
    "update",
    "delete",
    "merge",
    "split",
    "rename",
    "rebuild",
    "reassign",
    "propose_patch",
]
ChangeTargetType = Literal[
    "partition",
    "case",
    "facet_schema",
    "facet_value",
    "backlog_batch",
]
