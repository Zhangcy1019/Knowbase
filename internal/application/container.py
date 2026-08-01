"""Dependency assembly for the integrated Knowbase application."""

from __future__ import annotations

from dataclasses import dataclass

from internal.api import KnowbaseRouteDeps
from internal.application.indices import ensure_indices
from internal.application.modules import build_ingest_service, build_query_flow, build_runtime_module
from internal.application.providers import build_core_providers, build_ingest_providers
from internal.application.registries import build_skill_registry
from internal.runtime.skills import SkillRuntime
from internal.runtime.tools import ToolRuntime
from internal.utils.config import RuntimeConfig


@dataclass(slots=True)
class KnowbaseAppContainer:
    """Assembled service graph for one app instance."""

    route_deps: KnowbaseRouteDeps


def build_app_container(*, runtime_cfg: RuntimeConfig) -> KnowbaseAppContainer:
    core = build_core_providers(runtime_cfg=runtime_cfg)
    ingest = build_ingest_providers(runtime_cfg=runtime_cfg)
    skill_registry = build_skill_registry(
        runtime_cfg=runtime_cfg,
        case_repository=core.case_repository,
        partition_service=core.partition_service,
    )
    skill_runtime = SkillRuntime(registry=skill_registry)
    # The primary runtime starts with no capabilities. Individual owners,
    # such as knowledge governance, create an isolated capability scope.
    tool_runtime = ToolRuntime()
    runtime_module = build_runtime_module(
        runtime_cfg=runtime_cfg,
        core=core,
        tool_runtime=tool_runtime,
        skill_runtime=skill_runtime,
    )
    ingest_service = build_ingest_service(core=core, ingest=ingest)
    query_flow = build_query_flow(core=core)
    ensure_indices(core=core)

    return KnowbaseAppContainer(
        route_deps=KnowbaseRouteDeps(
            partition_service=core.partition_service,
            partition_schema_suggester=core.partition_schema_suggester,
            case_repository=core.case_repository,
            case_write_service=core.case_write_service,
            runtime_service=runtime_module.runtime_service,
            event_publisher=core.event_publisher,
            event_backlog_service=runtime_module.event_backlog_service,
            event_worker=runtime_module.event_worker,
            skill_runtime=skill_runtime,
            ingest_service=ingest_service,
            query_flow=query_flow,
            statistics_service=core.statistics_service,
            query_statistics_service=core.query_statistics_service,
            decision_service=core.decision_service,
            task_queue=core.task_queue,
        )
    )
