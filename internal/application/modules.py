"""Higher-level module assembly for product, runtime, and backlog services."""

from __future__ import annotations

from dataclasses import dataclass

from internal.agents.product import AnswerSynthesisAgent
from internal.backlog.dispatch import KnowbaseBacklogDispatchService
from internal.backlog.planning import BacklogPreparationPlanner, BatchWorkingSetBuilder
from internal.backlog.queue import KnowbaseEventBacklogService
from internal.backlog.worker import KnowbaseEventWorker
from internal.ports import EventBacklogPort, EventWorkerPort, IngestUseCase, QueryUseCase, RuntimeRunPort
from internal.product.ingest.service import KnowbaseIngestService
from internal.product.ingest.validator import KnowbaseIngestValidator
from internal.product.query.flow import KnowbaseQueryFlow
from internal.product.query.normalizer import QueryNormalizer
from internal.product.query.planner import KnowbaseQueryPlanner
from internal.product.query.ranking import KnowbaseRanking
from internal.product.query.service import KnowbaseQueryService
from internal.runtime.service import KnowbaseRuntimeService
from internal.skills import SkillRuntime
from internal.tools import ToolRuntime

from internal.application.providers import CoreProviders, IngestProviders


@dataclass(slots=True)
class RuntimeModule:
    runtime_service: RuntimeRunPort
    event_backlog_service: EventBacklogPort
    event_worker: EventWorkerPort


def build_runtime_module(
    *,
    core: CoreProviders,
    tool_runtime: ToolRuntime,
    skill_runtime: SkillRuntime,
) -> RuntimeModule:
    runtime_service = KnowbaseRuntimeService(
        partition_service=core.partition_service,
        case_repository=core.case_repository,
        run_repository=core.run_repository,
        step_repository=core.step_repository,
        artifact_repository=core.artifact_repository,
        tool_runtime=tool_runtime,
        skill_runtime=skill_runtime,
    )
    event_backlog_service = KnowbaseEventBacklogService(repository=core.event_record_repository)
    dispatch_service = KnowbaseBacklogDispatchService(
        working_set_builder=BatchWorkingSetBuilder(),
        preparation_planner=BacklogPreparationPlanner(
            partition_service=core.partition_service,
            case_repository=core.case_repository,
        ),
    )
    event_worker = KnowbaseEventWorker(
        backlog_service=event_backlog_service,
        dispatch_service=dispatch_service,
        runtime_service=runtime_service,
    )
    return RuntimeModule(
        runtime_service=runtime_service,
        event_backlog_service=event_backlog_service,
        event_worker=event_worker,
    )


def build_ingest_service(
    *,
    core: CoreProviders,
    ingest: IngestProviders,
) -> IngestUseCase:
    return KnowbaseIngestService(
        validator=KnowbaseIngestValidator(),
        draft_builder=ingest.draft_builder,
        case_write_service=core.case_write_service,
        event_publisher=core.event_publisher,
        partition_service=core.partition_service,
        summary_extractor=ingest.summary_extractor,
        semantic_profile_extractor=ingest.semantic_profile_extractor,
        facet_resolver=ingest.facet_resolver,
    )


def build_query_flow(*, core: CoreProviders) -> QueryUseCase:
    query_normalizer = QueryNormalizer()
    return KnowbaseQueryFlow(
        planner=KnowbaseQueryPlanner(),
        normalizer=query_normalizer,
        query_service=KnowbaseQueryService(
            case_service=core.case_service,
            normalizer=query_normalizer,
            ranking=KnowbaseRanking(),
        ),
        partition_service=core.partition_service,
        answer_agent=AnswerSynthesisAgent(),
    )
