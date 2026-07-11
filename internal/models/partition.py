"""Partition-level schemas for knowbase."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class PartitionDocument(BaseModel):
    """One high-level knowbase partition/domain."""

    partition_name: str
    scenario_description: str = ""
    status: Literal["active", "disabled", "archived"] = "active"
    created_at: datetime
    updated_at: datetime
