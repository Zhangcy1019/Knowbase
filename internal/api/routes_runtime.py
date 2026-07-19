from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

from internal.models import AgentRun, EventRecord, RunArtifact, RunStep, SkillExecutionContext, SkillInvocation

from .deps import KnowbaseRouteDeps
from .schemas import (
    EventRecordResponse,
    MaintenanceActionResponse,
    PartitionMaintenanceRequest,
    ResourceMaintenanceRequest,
    RuntimeRunActionView,
    RuntimeRunArtifactResponse,
    RuntimeRunDetail,
    RuntimeRunStepResponse,
    RuntimeRunSummary,
    RuntimeTraceReplayResponse,
    RuntimeTraceTurnResponse,
)


def _to_event_record_response(record: EventRecord) -> EventRecordResponse:
    return EventRecordResponse(
        event_id=record.event_id,
        event_type=record.event_type,
        partition=record.partition,
        resource_type=record.resource_type,
        resource_id=record.resource_id,
        status=record.status,
        priority=record.priority,
        policy_id=record.policy_id,
        ready_at=record.ready_at,
        next_retry_at=record.next_retry_at,
        last_run_at=record.last_run_at,
        run_id=record.run_id,
        batch_key=record.batch_key,
        attempt_count=record.attempt_count,
        error_message=record.error_message,
        occurred_at=record.occurred_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
        metadata=record.metadata,
    )


def _invocation_to_action_view(invocation_payload: dict[str, object]) -> RuntimeRunActionView:
    skill_id = str(invocation_payload.get("skill_id") or "")
    inputs = invocation_payload.get("inputs")
    input_map = inputs if isinstance(inputs, dict) else {}
    return RuntimeRunActionView(
        action_name=skill_id,
        action_type=skill_id.split(".")[-1] if skill_id else "",
        target_type=skill_id.split(".")[0] if skill_id else "",
        target_id=str(
            input_map.get("case_id")
            or ",".join(str(item) for item in input_map.get("case_ids", []) if isinstance(item, (str, int, float)))
            or input_map.get("target_id")
            or input_map.get("facet_key")
            or input_map.get("facet_value")
            or ""
        ),
        summary=skill_id,
    )


def _batch_work_item_to_action_view(work_item_payload: dict[str, object]) -> RuntimeRunActionView:
    skill_id = str(work_item_payload.get("skill_id") or "")
    inputs = work_item_payload.get("inputs")
    input_map = inputs if isinstance(inputs, dict) else {}
    return RuntimeRunActionView(
        action_name=skill_id or str(work_item_payload.get("work_item_id") or "batch_work_item"),
        action_type=skill_id.split(".")[-1] if skill_id else "batch_work_item",
        target_type=str(work_item_payload.get("target_type") or (skill_id.split(".")[0] if skill_id else "")),
        target_id=str(
            work_item_payload.get("target_id")
            or input_map.get("case_id")
            or ",".join(str(item) for item in input_map.get("case_ids", []) if isinstance(item, (str, int, float)))
            or input_map.get("facet_key")
            or input_map.get("facet_value")
            or input_map.get("target_id")
            or ""
        ),
        summary=str(work_item_payload.get("summary") or skill_id or "batch work item"),
    )


def _to_run_summary(run: AgentRun) -> RuntimeRunSummary:
    return RuntimeRunSummary(
        run_id=run.run_id,
        partition=run.partition,
        agent_id=run.agent_id,
        mode=run.mode,
        status=run.status,
        requires_review=run.requires_review,
        source_type=run.source_type,
        source_event_type=run.source_event_type,
        source_ref=run.source_ref,
        objective=run.objective,
        reasoning_summary=run.reasoning_summary,
        step_count=run.step_count,
        tool_call_count=run.tool_call_count,
        skill_call_count=run.skill_call_count,
        created_at=run.created_at,
        updated_at=run.updated_at,
        finished_at=run.finished_at,
    )


def _to_run_detail(run: AgentRun, artifacts: list[RunArtifact]) -> RuntimeRunDetail:
    action_artifacts = [artifact for artifact in artifacts if artifact.artifact_type == "execute_invocations"]
    decision_artifacts = [artifact for artifact in artifacts if artifact.artifact_type == "decision"]
    actions: list[RuntimeRunActionView] = []
    seen_action_keys: set[tuple[str, str, str]] = set()

    def append_action(action: RuntimeRunActionView) -> None:
        key = (action.action_name, action.target_type, action.target_id)
        if key in seen_action_keys:
            return
        seen_action_keys.add(key)
        actions.append(action)

    for artifact in action_artifacts:
        invocations = artifact.content.get("invocations")
        if isinstance(invocations, list):
            for item in invocations:
                if isinstance(item, dict):
                    append_action(_invocation_to_action_view(item))
    for artifact in decision_artifacts:
        decision_actions = artifact.content.get("actions")
        if not isinstance(decision_actions, list):
            continue
        for item in decision_actions:
            if not isinstance(item, dict):
                continue
            skill_id = str(item.get("skill_id") or "")
            tool_id = str(item.get("tool_id") or "")
            kind = str(item.get("kind") or "")
            title = str(item.get("title") or skill_id or tool_id or kind or "runtime_action")
            inputs = item.get("inputs")
            input_map = inputs if isinstance(inputs, dict) else {}
            append_action(
                RuntimeRunActionView(
                    action_name=title,
                    action_type=kind,
                    target_type=skill_id.split(".")[0] if skill_id else (tool_id.split(".")[0] if tool_id else ""),
                    target_id=str(
                        input_map.get("case_id")
                        or ",".join(
                            str(case_id) for case_id in input_map.get("case_ids", []) if isinstance(case_id, (str, int, float))
                        )
                        or input_map.get("target_id")
                        or input_map.get("facet_key")
                        or input_map.get("facet_value")
                        or ""
                    ),
                    summary=str(item.get("summary") or title),
                )
            )
    return RuntimeRunDetail(
        **_to_run_summary(run).model_dump(mode="json"),
        final_summary=run.final_summary,
        planning_context=run.planning_context,
        tool_whitelist=run.tool_whitelist,
        skill_whitelist=run.skill_whitelist,
        max_steps=run.max_steps,
        max_tool_calls=run.max_tool_calls,
        max_skill_calls=run.max_skill_calls,
        risk_level=run.risk_level,
        actions=actions,
    )


def _to_run_step_response(step: RunStep) -> RuntimeRunStepResponse:
    return RuntimeRunStepResponse(
        step_id=step.step_id,
        run_id=step.run_id,
        index=step.index,
        step_type=step.step_type,
        name=step.name,
        input=step.input,
        output=step.output,
        summary=step.summary,
        created_at=step.created_at,
    )


def _to_run_artifact_response(artifact: RunArtifact) -> RuntimeRunArtifactResponse:
    return RuntimeRunArtifactResponse(
        artifact_id=artifact.artifact_id,
        run_id=artifact.run_id,
        artifact_type=artifact.artifact_type,
        title=artifact.title,
        content=artifact.content,
        created_at=artifact.created_at,
        updated_at=artifact.updated_at,
    )


def _to_trace_turn_response(turn) -> RuntimeTraceTurnResponse:
    return RuntimeTraceTurnResponse(
        turn_index=turn.turn_index,
        decision_step=None if turn.decision_step is None else _to_run_step_response(turn.decision_step),
        decision_artifact=None if turn.decision_artifact is None else _to_run_artifact_response(turn.decision_artifact),
        planner_context_artifact=(
            None if turn.planner_context_artifact is None else _to_run_artifact_response(turn.planner_context_artifact)
        ),
        llm_prompt_artifact=None if turn.llm_prompt_artifact is None else _to_run_artifact_response(turn.llm_prompt_artifact),
        llm_response_artifact=(
            None if turn.llm_response_artifact is None else _to_run_artifact_response(turn.llm_response_artifact)
        ),
        action_steps=[_to_run_step_response(step) for step in turn.action_steps],
        tool_calls=[_to_run_step_response(step) for step in turn.tool_calls],
        tool_results=[_to_run_step_response(step) for step in turn.tool_results],
        skill_calls=[_to_run_step_response(step) for step in turn.skill_calls],
        skill_results=[_to_run_step_response(step) for step in turn.skill_results],
        errors=[_to_run_step_response(step) for step in turn.errors],
    )


async def _execute_maintenance_skill(
    *,
    deps: KnowbaseRouteDeps,
    partition: str,
    skill_id: str,
    inputs: dict[str, object],
) -> MaintenanceActionResponse:
    result = deps.skill_runtime.execute(
        SkillInvocation(
            invocation_id=f"manual:{skill_id}:{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            skill_id=skill_id,
            partition=partition,
            inputs=inputs,
            metadata={"source": "maintenance"},
        ),
        context=SkillExecutionContext(
            partition=partition,
            agent_id="maintenance.console",
            metadata={"source": "maintenance"},
        ),
    )
    return MaintenanceActionResponse(
        action=skill_id,
        ok=result.ok,
        summary=result.error_message if not result.ok else str(result.output.get("reasoning_summary") or skill_id),
        details={
            "updated_objects": result.updated_objects,
            "output": result.output,
        },
    )


def register_runtime_routes(app: FastAPI, *, deps: KnowbaseRouteDeps) -> None:
    @app.get("/api/knowbase/runtime/backlog", response_model=list[EventRecordResponse])
    async def list_backlog_events(
        partition: str = "",
        status: str = "",
        event_type: str = "",
    ) -> list[EventRecordResponse]:
        records = deps.event_backlog_service.list_events(
            partition=partition,
            status=status,
            event_type=event_type,
        )
        return [_to_event_record_response(item) for item in records]

    @app.get("/api/knowbase/runtime/backlog/{event_id}", response_model=EventRecordResponse)
    async def get_backlog_event(event_id: str) -> EventRecordResponse:
        record = deps.event_backlog_service.get_event(event_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"backlog event not found: {event_id}")
        return _to_event_record_response(record)

    @app.post("/api/knowbase/runtime/backlog/{event_id}/requeue", response_model=EventRecordResponse)
    async def requeue_backlog_event(event_id: str) -> EventRecordResponse:
        try:
            record = deps.event_backlog_service.requeue_event(event_id=event_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _to_event_record_response(record)

    @app.delete("/api/knowbase/runtime/backlog/{event_id}")
    async def delete_backlog_event(event_id: str) -> dict[str, str]:
        existing = deps.event_backlog_service.get_event(event_id)
        if existing is None:
            raise HTTPException(status_code=404, detail=f"backlog event not found: {event_id}")
        deps.event_backlog_service.delete_event(event_id)
        return {"deleted_type": "backlog_event", "deleted_id": event_id}

    @app.post("/api/knowbase/runtime/maintenance/drain-backlog", response_model=MaintenanceActionResponse)
    async def drain_backlog(req: PartitionMaintenanceRequest) -> MaintenanceActionResponse:
        result = await deps.event_worker.run_once(partition=req.partition, limit=req.limit, trigger_source="manual")
        runtime_result = result.runtime_result
        return MaintenanceActionResponse(
            action="drain_backlog",
            ok=result.failed_count == 0,
            summary=f"Attempted {result.attempted_count} backlog event(s), completed {result.completed_count}, failed {result.failed_count}.",
            details={
                "partition": req.partition,
                "batch_id": result.batch_id,
                "attempted_count": result.attempted_count,
                "completed_count": result.completed_count,
                "failed_count": result.failed_count,
                "event_ids": result.event_ids,
                "run_id": "" if runtime_result is None else runtime_result.run_id,
                "run_status": "" if runtime_result is None else runtime_result.status,
                "requires_review": False if runtime_result is None else runtime_result.requires_review,
            },
        )

    @app.post("/api/knowbase/runtime/maintenance/rebuild-case/{case_id}", response_model=MaintenanceActionResponse)
    async def rebuild_case(case_id: str, req: ResourceMaintenanceRequest) -> MaintenanceActionResponse:
        return await _execute_maintenance_skill(
            deps=deps,
            partition=req.partition,
            skill_id="partition.refresh_selected_cases_facets",
            inputs={"partition": req.partition, "case_ids": [case_id], "target_facet_keys": []},
        )

    @app.get("/api/knowbase/runtime/runs", response_model=list[RuntimeRunSummary])
    async def list_runtime_runs(partition: str = "", status: str = "") -> list[RuntimeRunSummary]:
        runs = deps.runtime_service.list_runs(partition=partition, status=status)
        return [_to_run_summary(run) for run in runs]

    @app.get("/api/knowbase/runtime/runs/{run_id}", response_model=RuntimeRunDetail)
    async def get_runtime_run(run_id: str) -> RuntimeRunDetail:
        run = deps.runtime_service.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"runtime run not found: {run_id}")
        return _to_run_detail(run, deps.runtime_service.list_artifacts(run_id))

    @app.get("/api/knowbase/runtime/runs/{run_id}/steps", response_model=list[RuntimeRunStepResponse])
    async def list_runtime_run_steps(run_id: str) -> list[RuntimeRunStepResponse]:
        run = deps.runtime_service.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"runtime run not found: {run_id}")
        return [_to_run_step_response(step) for step in deps.runtime_service.list_steps(run_id)]

    @app.get("/api/knowbase/runtime/runs/{run_id}/artifacts", response_model=list[RuntimeRunArtifactResponse])
    async def list_runtime_run_artifacts(run_id: str) -> list[RuntimeRunArtifactResponse]:
        run = deps.runtime_service.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"runtime run not found: {run_id}")
        return [_to_run_artifact_response(artifact) for artifact in deps.runtime_service.list_artifacts(run_id)]

    @app.get("/api/knowbase/runtime/runs/{run_id}/trace", response_model=RuntimeTraceReplayResponse)
    async def get_runtime_run_trace(run_id: str) -> RuntimeTraceReplayResponse:
        replay = deps.runtime_service.get_trace_replay(run_id)
        if replay is None:
            raise HTTPException(status_code=404, detail=f"runtime run trace not found: {run_id}")
        return RuntimeTraceReplayResponse(
            run=_to_run_detail(replay.run, replay.artifacts),
            request_artifact=(
                None if replay.request_artifact is None else _to_run_artifact_response(replay.request_artifact)
            ),
            turns=[_to_trace_turn_response(turn) for turn in replay.turns],
            steps=[_to_run_step_response(step) for step in replay.steps],
            artifacts=[_to_run_artifact_response(artifact) for artifact in replay.artifacts],
        )

    @app.delete("/api/knowbase/runtime/runs/{run_id}")
    async def delete_runtime_run(run_id: str) -> dict[str, str]:
        deps.runtime_service.delete_run(run_id)
        return {"deleted_type": "runtime_run", "deleted_id": run_id}
