"""Read one case document by id."""

from __future__ import annotations

from datetime import datetime, timezone

from internal.models.tool import ToolCall, ToolResult, ToolSpec
from internal.ports import CaseReadPort


class GetCaseTool:
    def __init__(self, *, repository: CaseReadPort):
        self._repository = repository
        self._spec = ToolSpec(
            tool_id="case.get",
            title="Get Case",
            description="Load one case document by case id.",
            input_schema={
                "type": "object",
                "additionalProperties": False,
                "required": ["case_id"],
                "properties": {
                    "case_id": {"type": "string", "description": "Case id to load."},
                },
            },
            examples=[
                {"inputs": {"case_id": "case-123"}},
            ],
            usage_notes=[
                "Use this tool when one specific case needs inspection before a write action.",
            ],
            argument_binding_hints={
                "case_id": "input_context.case_id",
            },
        )

    @property
    def spec(self) -> ToolSpec:
        return self._spec

    def execute(self, call: ToolCall) -> ToolResult:
        started_at = datetime.now(timezone.utc)
        case_id = str(call.inputs.get("case_id") or "").strip()
        document = None if not case_id else self._repository.get(case_id)
        return ToolResult(
            call_id=call.call_id,
            tool_id=call.tool_id,
            ok=document is not None,
            output={} if document is None else {"case": document.model_dump(mode="json")},
            error_message="" if document is not None else f"case not found: {case_id}",
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
        )
