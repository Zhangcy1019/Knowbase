"""List partition-scoped case documents."""

from __future__ import annotations

from datetime import datetime, timezone

from internal.models.tool import ToolCall, ToolResult, ToolSpec
from internal.ports import CaseReadPort


class ListCasesTool:
    def __init__(self, *, repository: CaseReadPort):
        self._repository = repository
        self._spec = ToolSpec(
            tool_id="case.list",
            title="List Cases",
            description="List cases for one partition.",
            input_schema={
                "type": "object",
                "additionalProperties": False,
                "required": ["partition"],
                "properties": {
                    "partition": {"type": "string", "description": "Partition name whose cases should be listed."},
                },
            },
            examples=[
                {"inputs": {"partition": "CI"}},
            ],
            usage_notes=[
                "Use this tool to inspect the current working case set before deciding on write actions.",
            ],
            argument_binding_hints={
                "partition": "request.partition",
            },
        )

    @property
    def spec(self) -> ToolSpec:
        return self._spec

    def execute(self, call: ToolCall) -> ToolResult:
        started_at = datetime.now(timezone.utc)
        partition = str(call.inputs.get("partition") or call.partition).strip()
        documents = [] if not partition else self._repository.list_by_partition(partition)
        return ToolResult(
            call_id=call.call_id,
            tool_id=call.tool_id,
            ok=bool(partition),
            output={"cases": [item.model_dump(mode="json") for item in documents]},
            error_message="" if partition else "partition is required",
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
        )
