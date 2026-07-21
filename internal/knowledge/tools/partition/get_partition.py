"""Read one partition document."""

from __future__ import annotations

from datetime import datetime, timezone

from internal.models.tool import ToolCall, ToolResult, ToolSpec
from internal.ports import PartitionLookupPort


class GetPartitionTool:
    def __init__(self, *, service: PartitionLookupPort):
        self._service = service
        self._spec = ToolSpec(
            tool_id="partition.get",
            title="Get Partition",
            description="Load one partition document by partition name.",
            input_schema={
                "type": "object",
                "additionalProperties": False,
                "required": ["partition"],
                "properties": {
                    "partition": {"type": "string", "description": "Partition name to load."},
                },
            },
            examples=[
                {"inputs": {"partition": "CI"}},
            ],
            usage_notes=[
                "Use this tool to inspect partition status and metadata before partition-scoped actions.",
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
        partition_name = str(call.inputs.get("partition") or call.partition).strip()
        document = None if not partition_name else self._service.get_partition(partition_name)
        return ToolResult(
            call_id=call.call_id,
            tool_id=call.tool_id,
            ok=document is not None,
            output={} if document is None else {"partition": document.model_dump(mode="json")},
            error_message="" if document is not None else f"partition not found: {partition_name}",
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
        )
