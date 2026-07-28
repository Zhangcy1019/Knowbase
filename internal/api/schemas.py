from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from internal.models import (
    CaseFacetProfile,
    CaseSemanticProfile,
    EventRecordStatus,
    KnowbaseCaseMetadata,
    KnowbaseEventType,
    PartitionFacetDefinition,
    PartitionFacetSchema,
    PartitionDocument,
)


class PartitionUpsertRequest(BaseModel):
    """Create or update one knowbase partition."""

    partition_name: str = Field(min_length=1)
    status: str = "active"
    scenario_description: str = ""


class PartitionSchemaEntryResponse(BaseModel):
    key: str
    value: str


class PartitionSchemaSuggestionRequest(BaseModel):
    partition_name: str = Field(min_length=1)
    scenario_description: str = ""
    current_facet_definitions: list[PartitionFacetDefinitionRequest] = Field(default_factory=list)
    cautious_update: bool = False


class PartitionSchemaSuggestionResponse(BaseModel):
    suggested_facets: list[PartitionSchemaEntryResponse] = Field(default_factory=list)
    rationale: str = ""
    should_update_existing: bool = True


class PartitionFacetDefinitionRequest(BaseModel):
    key: str
    display_name: str = ""
    description: str = ""
    examples: list[str] = Field(default_factory=list)
    enabled: bool = True


class PartitionFacetSchemaUpsertRequest(BaseModel):
    definitions: list[PartitionFacetDefinitionRequest] = Field(default_factory=list)
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)


class PartitionFacetSchemaResponse(BaseModel):
    partition_name: str
    facet_schema: PartitionFacetSchema = Field(default_factory=PartitionFacetSchema)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class GetCaseResponse(BaseModel):
    """Case lookup response."""

    case: dict[str, Any]


class CaseCreateRequest(BaseModel):
    partition: str = Field(min_length=1)
    title: str = ""
    source_content: str = ""
    source_refs: list[str] = Field(default_factory=list)
    summary_text: str = ""
    semantic_profile: CaseSemanticProfile = Field(default_factory=CaseSemanticProfile)
    metadata: KnowbaseCaseMetadata = Field(default_factory=KnowbaseCaseMetadata)
    facets: CaseFacetProfile = Field(default_factory=CaseFacetProfile)


class CaseUpdateRequest(BaseModel):
    title: str | None = None
    source_content: str | None = None
    source_refs: list[str] | None = None
    summary_text: str | None = None
    semantic_profile: CaseSemanticProfile | None = None
    metadata: KnowbaseCaseMetadata | None = None
    facets: CaseFacetProfile | None = None
    raw_text: str | None = None
    case_detail: str | None = None


class CreateResourceResponse(BaseModel):
    created_type: str
    created_id: str
    partition: str
    detail: dict[str, Any] = Field(default_factory=dict)


class RuntimeRunActionView(BaseModel):
    action_name: str
    action_type: str
    target_type: str
    target_id: str = ""
    summary: str = ""


class RuntimeRunSummary(BaseModel):
    run_id: str = ""
    partition: str
    agent_id: str
    mode: str
    status: str
    requires_review: bool = False
    source_type: str
    source_event_type: KnowbaseEventType | str = ""
    source_ref: str = ""
    objective: str = ""
    reasoning_summary: str = ""
    step_count: int = 0
    tool_call_count: int = 0
    skill_call_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    finished_at: datetime | None = None


class RuntimeRunDetail(RuntimeRunSummary):
    final_summary: str = ""
    planning_context: dict[str, Any] = Field(default_factory=dict)
    tool_whitelist: list[str] = Field(default_factory=list)
    skill_whitelist: list[str] = Field(default_factory=list)
    max_steps: int = 0
    max_tool_calls: int = 0
    max_skill_calls: int = 0
    risk_level: str = ""
    actions: list[RuntimeRunActionView] = Field(default_factory=list)


class RuntimeRunStepResponse(BaseModel):
    step_id: str = ""
    run_id: str
    index: int = 0
    step_type: str
    name: str = ""
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    summary: str = ""
    created_at: datetime | None = None


class RuntimeRunArtifactResponse(BaseModel):
    artifact_id: str = ""
    run_id: str
    artifact_type: str
    title: str = ""
    content: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RuntimeTraceTurnResponse(BaseModel):
    turn_index: int = 0
    decision_step: RuntimeRunStepResponse | None = None
    decision_artifact: RuntimeRunArtifactResponse | None = None
    planner_context_artifact: RuntimeRunArtifactResponse | None = None
    llm_prompt_artifact: RuntimeRunArtifactResponse | None = None
    llm_response_artifact: RuntimeRunArtifactResponse | None = None
    action_steps: list[RuntimeRunStepResponse] = Field(default_factory=list)
    tool_calls: list[RuntimeRunStepResponse] = Field(default_factory=list)
    tool_results: list[RuntimeRunStepResponse] = Field(default_factory=list)
    skill_calls: list[RuntimeRunStepResponse] = Field(default_factory=list)
    skill_results: list[RuntimeRunStepResponse] = Field(default_factory=list)
    errors: list[RuntimeRunStepResponse] = Field(default_factory=list)


class RuntimeTraceReplayResponse(BaseModel):
    run: RuntimeRunDetail
    request_artifact: RuntimeRunArtifactResponse | None = None
    turns: list[RuntimeTraceTurnResponse] = Field(default_factory=list)
    steps: list[RuntimeRunStepResponse] = Field(default_factory=list)
    artifacts: list[RuntimeRunArtifactResponse] = Field(default_factory=list)


class EventRecordResponse(BaseModel):
    event_id: str = ""
    event_type: KnowbaseEventType | str
    partition: str = ""
    resource_type: str = ""
    resource_id: str = ""
    status: EventRecordStatus
    priority: int = 100
    next_retry_at: datetime | None = None
    last_run_at: datetime | None = None
    run_id: str = ""
    attempt_count: int = 0
    error_message: str = ""
    occurred_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PartitionTaskResponse(BaseModel):
    task_id: str
    partition: str
    kind: str
    payload: dict[str, Any] = Field(default_factory=dict)
    status: str
    attempt_count: int = 0
    error_message: str = ""
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class KnowledgeDrainSummaryResponse(BaseModel):
    """One persisted Knowledge governance attempt for the console."""

    decision_id: str
    runtime_run_id: str = ""
    partition: str
    batch_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    base_revision: str = ""
    applied_revision: str = ""
    mutation_plan_id: str = ""
    change_count: int = 0
    schema_changed: bool = False
    requires_review: bool = False
    error_message: str = ""


class KnowledgeDrainDetailResponse(KnowledgeDrainSummaryResponse):
    """Full persisted Knowledge decision payload for debugging and audit."""

    input: dict[str, Any]
    stages: dict[str, Any] = Field(default_factory=dict)
    outcome: dict[str, Any]
    execution: dict[str, Any] | None = None
    status_history: list[dict[str, Any]] = Field(default_factory=list)
    reviewer: str | None = None
    review_reason: str | None = None
    supersedes_decision_id: str | None = None


class KnowledgeReviewActionRequest(BaseModel):
    """Manual action applied to a Knowledge decision waiting for review."""

    action: Literal["approve", "discard", "retry"]
    reviewer: str = "manual"
    reason: str = ""


class KnowledgeOverviewResponse(BaseModel):
    """Compact current Knowledge state for the page header."""

    partition: str
    case_count: int = 0
    facet_key_count: int = 0
    pending_decision_count: int = 0
    last_drain_at: datetime | None = None


class QueryStatisticsResponse(BaseModel):
    """Query-derived signals kept separate from the partition knowledge schema."""

    partition: str
    generated_at: datetime | None = None
    query_count: int = 0
    query_key_stats: dict[str, int] = Field(default_factory=dict)
    query_value_stats: dict[str, dict[str, int]] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CaseStatisticsResponse(BaseModel):
    """Current case-derived statistics used by Knowledge inspection surfaces."""

    partition: str
    generated_at: datetime | None = None
    case_count: int = 0
    case_key_stats: dict[str, int] = Field(default_factory=dict)
    case_value_stats: dict[str, dict[str, int]] = Field(default_factory=dict)


class MaintenanceActionResponse(BaseModel):
    action: str
    ok: bool = True
    summary: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class PartitionMaintenanceRequest(BaseModel):
    partition: str = Field(min_length=1)
    limit: int = 20


class ResourceMaintenanceRequest(BaseModel):
    partition: str = Field(min_length=1)


OverviewGraphMode = Literal["facet-case"]
OverviewNodeType = Literal["facet", "case"]


class OverviewGraphNode(BaseModel):
    id: str
    type: OverviewNodeType
    label: str
    facet: str = ""
    status: str = ""
    dirty: bool = False
    meta: dict[str, Any] = Field(default_factory=dict)


class OverviewGraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relation: str


class OverviewGraphStats(BaseModel):
    facet_count: int = 0
    case_count: int = 0


class OverviewGraphResponse(BaseModel):
    partition: PartitionDocument
    mode: OverviewGraphMode
    nodes: list[OverviewGraphNode] = Field(default_factory=list)
    edges: list[OverviewGraphEdge] = Field(default_factory=list)
    stats: OverviewGraphStats = Field(default_factory=OverviewGraphStats)


class OverviewDocumentDetailResponse(BaseModel):
    id: str
    type: OverviewNodeType
    title: str
    partition: str
    facet: str = ""
    raw_text: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    content: dict[str, Any] = Field(default_factory=dict)
