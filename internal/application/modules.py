"""Higher-level module assembly for product, runtime, and backlog services."""

from __future__ import annotations

from dataclasses import dataclass

from internal.agents.product import AnswerSynthesisAgent
from internal.backlog.queue import KnowbaseEventBacklogService
from internal.backlog.worker import KnowbaseEventWorker
from internal.knowledge.service import KnowbaseKnowledgeService
from internal.knowledge.workflow import KnowledgeDrainWorkflow
from internal.knowledge.batch import BatchWorkingSetBuilder
from internal.ports import EventBacklogPort, EventWorkerPort, IngestUseCase, QueryUseCase, RuntimeRunPort
from internal.product.ingest.service import KnowbaseIngestService
from internal.product.ingest.validator import KnowbaseIngestValidator
from internal.product.query.flow import KnowbaseQueryFlow
from internal.product.query.normalizer import QueryNormalizer
from internal.product.query.planner import KnowbaseQueryPlanner
from internal.product.query.ranking import KnowbaseRanking
from internal.product.query.semantic_profile_extractor import KnowbaseQuerySemanticProfileExtractor
from internal.product.query.service import KnowbaseQueryService
from internal.runtime.llm import DefaultRuntimeDecisionGenerator, DefaultRuntimePromptBuilder
from internal.runtime.loop.turn_planner import RuntimeTurnPlanner
from internal.infrastructure.ai import DefaultOpenAIClient
from internal.runtime.llm.model_adapter import DefaultRuntimeModelAdapter
from internal.runtime.skills import SkillRuntime
from internal.runtime.service import KnowbaseRuntimeService
from internal.runtime.trace import RuntimeTraceRecorder
from internal.runtime.tools import ToolRuntime
from internal.utils.config import RuntimeConfig

from internal.application.providers import CoreProviders, IngestProviders


@dataclass(slots=True)
class RuntimeModule:
    runtime_service: RuntimeRunPort
    event_backlog_service: EventBacklogPort
    event_worker: EventWorkerPort


def build_runtime_module(
    *,
    runtime_cfg: RuntimeConfig,
    core: CoreProviders,
    tool_runtime: ToolRuntime,
    skill_runtime: SkillRuntime,
) -> RuntimeModule:
    if runtime_cfg.llm.provider.strip().lower() != "openai":
        raise ValueError(f"unsupported runtime llm provider: {runtime_cfg.llm.provider}")
    trace_recorder = RuntimeTraceRecorder(
        run_repository=core.run_repository,
        step_repository=core.step_repository,
        artifact_repository=core.artifact_repository,
    )
    openai_client = DefaultOpenAIClient(
        api_key=runtime_cfg.llm.openai_api_key or "",
        base_url=runtime_cfg.llm.openai_base_url,
        timeout_seconds=runtime_cfg.llm.timeout_seconds,
    )
    decision_generator = DefaultRuntimeDecisionGenerator(
        prompt_builder=DefaultRuntimePromptBuilder(
            model=runtime_cfg.llm.model,
            temperature=runtime_cfg.llm.temperature,
            max_output_tokens=runtime_cfg.llm.max_output_tokens,
        ),
        model_adapter=DefaultRuntimeModelAdapter(client=openai_client),
        trace_recorder=trace_recorder,
        llm_config=runtime_cfg.llm,
    )
    runtime_service = KnowbaseRuntimeService(
        partition_service=core.partition_service,
        case_repository=core.case_repository,
        run_repository=core.run_repository,
        step_repository=core.step_repository,
        artifact_repository=core.artifact_repository,
        tool_runtime=tool_runtime,
        skill_runtime=skill_runtime,
        planner=RuntimeTurnPlanner(decision_generator=decision_generator),
        trace_recorder=trace_recorder,
    )
    event_backlog_service = KnowbaseEventBacklogService(repository=core.event_record_repository)
    knowledge_workflow = KnowledgeDrainWorkflow(
        working_set_builder=BatchWorkingSetBuilder(),
        partition_service=core.partition_service,
        statistics=core.statistics_service,
        versioning=core.versioning,
        projection=core.projection_service,
        mutation_executor=core.mutation_executor,
    )
    knowledge_service = KnowbaseKnowledgeService(
        backlog_service=event_backlog_service,
        workflow=knowledge_workflow,
    )
    event_worker = KnowbaseEventWorker(
        backlog_service=event_backlog_service,
        knowledge_service=knowledge_service,
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
        statistics=core.statistics_service,
        versioning=core.versioning,
    )


def build_query_flow(*, core: CoreProviders) -> QueryUseCase:
    query_normalizer = QueryNormalizer()
    return KnowbaseQueryFlow(
        planner=KnowbaseQueryPlanner(
            semantic_profile_extractor=KnowbaseQuerySemanticProfileExtractor(llm_config=core.runtime_cfg.llm),
            embedding_provider=core.embedding_provider,
        ),
        normalizer=query_normalizer,
        query_service=KnowbaseQueryService(
            case_service=core.case_service,
            normalizer=query_normalizer,
            ranking=KnowbaseRanking(),
        ),
        partition_service=core.partition_service,
        answer_agent=AnswerSynthesisAgent(),
        statistics=core.query_statistics_service,
    )
