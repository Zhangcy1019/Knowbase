"""High-level query orchestration for knowbase."""

from __future__ import annotations

from internal.agents.product.answer_synthesis import AnswerSynthesisAgent
from internal.models import QueryRequest, QueryResult
from internal.knowledge.statistics import QueryObservation
from uuid import uuid4
from internal.ports import PartitionProfileReadPort, PartitionReadPort
from internal.product.query.normalizer import QueryNormalizer
from internal.product.query.planner import KnowbaseQueryPlanner
from internal.product.query.service import KnowbaseQueryService
from internal.utils.logger import get_logger


logger = get_logger("knowbase.product.query.flow")


class KnowbaseQueryFlow:
    """Coordinate product-facing query operations."""

    def __init__(
        self,
        *,
        planner: KnowbaseQueryPlanner,
        normalizer: QueryNormalizer,
        query_service: KnowbaseQueryService,
        partition_service: PartitionReadPort | PartitionProfileReadPort,
        answer_agent: AnswerSynthesisAgent,
        statistics=None,
    ):
        self._planner = planner
        self._normalizer = normalizer
        self._query_service = query_service
        self._partition_service = partition_service
        self._answer_agent = answer_agent
        self._statistics = statistics

    async def run(self, request: QueryRequest) -> QueryResult:
        if not request.partition_name.strip():
            raise ValueError("query partition_name must not be empty")
        partition = self._partition_service.get_partition(request.partition_name)
        if partition is None:
            raise ValueError(f"unknown partition: {request.partition_name}")
        if partition.status != "active":
            raise ValueError(f"partition is not active: {request.partition_name}")
        facet_definitions = self._partition_service.list_facet_definitions(request.partition_name)
        semantic_index = self._partition_service.get_semantic_index(request.partition_name)
        plan = await self._planner.plan(
            request,
            facet_definitions=facet_definitions,
            semantic_index=semantic_index,
        )
        if self._statistics is not None:
            query_id = uuid4().hex
            try:
                self._statistics.record(
                    observation=QueryObservation(
                        observation_id=f"query:{query_id}",
                        partition=request.partition_name,
                        source_id=f"query:{query_id}",
                        semantic_profile=plan.semantic_profile.model_dump(),
                        metadata={"text_length": len(request.text)},
                    )
                )
            except Exception as exc:  # telemetry must not break query serving
                logger.exception(
                    "Query statistics recording failed; continuing query execution.",
                    extra={"partition": request.partition_name, "error": str(exc)},
                )
        cases = self._query_service.execute(request=request, plan=plan)
        answer = await self._answer_agent.answer(
            query=request.text,
            cases=cases,
        )
        return QueryResult(
            plan=plan,
            cases=cases,
            answer=answer,
            debug={
                "requested_size": request.size,
                "recall_size": request.recall_size,
                "returned_case_count": len(cases),
                "semantic_index_key_count": 0 if semantic_index is None else len(semantic_index.key_stats),
            },
        )
