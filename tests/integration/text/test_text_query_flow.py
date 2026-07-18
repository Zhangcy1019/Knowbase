"""Text-backend query/search integration tests.

Run:
    cd knowbase
    python3 -m unittest tests.integration.text.test_text_query_flow
"""

from __future__ import annotations

import asyncio
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from internal.application.modules import build_ingest_service
from internal.application.providers import IngestProviders, build_core_providers
from internal.domain.case.draft_builder import KnowbaseCaseDraftBuilder
from internal.domain.case.facet_resolver import KnowbaseCaseFacetResolver
from internal.domain.case.ingestor import KnowbaseCaseIngestor
from internal.models import (
    IngestRequest,
    PartitionFacetDefinition,
    PartitionFacetSchema,
    QueryAnswer,
    QueryPlan,
    QueryRequest,
)
from internal.models.semantic_profile import QuerySemanticProfile
from internal.product.query.flow import KnowbaseQueryFlow
from internal.product.query.normalizer import QueryNormalizer
from internal.product.query.ranking import KnowbaseRanking
from internal.product.query.service import KnowbaseQueryService
from tests.integration.support import load_test_runtime_config

from tests.integration.text.test_text_minimal_flow import (
    _NoopEmbeddingProvider,
    _StaticSemanticProfileExtractor,
    _StaticSummaryExtractor,
    TextMinimalFlowIntegrationTest,
)


class _StaticQueryPlanner:
    async def plan(
        self,
        request: QueryRequest,
        *,
        facet_definitions=None,
        semantic_index=None,
    ) -> QueryPlan:
        _ = facet_definitions, semantic_index
        profile_payload = {"domain": ["tax"]} if "tax" in request.text.lower() else {}
        return QueryPlan(
            normalized_text=request.text.strip(),
            semantic_profile=QuerySemanticProfile.model_validate(profile_payload),
            hypothetical_answer="",
            search_representation=request.text.strip(),
            embedding=[],
            expanded_terms=["tax"] if "tax" in request.text.lower() else [],
            facet_filters=[],
        )


class _StaticAnswerAgent:
    async def answer(self, *, query: str, cases: list) -> QueryAnswer:
        top_case_id = cases[0].case_id if cases else ""
        return QueryAnswer(
            answer=f"Top case for query '{query}' is {top_case_id}".strip(),
            citations=[top_case_id] if top_case_id else [],
            confidence=0.9 if top_case_id else 0.0,
            reasoning_summary="Deterministic test answer.",
        )


class TextQueryFlowIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self._runtime_cfg = load_test_runtime_config()
        self._root = Path(self._runtime_cfg.storage.text_root).expanduser()
        shutil.rmtree(self._root, ignore_errors=True)
        self._root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        pass

    def test_text_backend_query_flow_returns_ranked_cases(self) -> None:
        core = self._build_core()
        self._create_partition(core=core, partition_name="CI")
        core.partition_service.save_facet_schema(
            partition_name="CI",
            facet_schema=PartitionFacetSchema(
                definitions=[
                    PartitionFacetDefinition(key="domain", display_name="Domain", enabled=True),
                ]
            ),
        )

        ingest_service = self._build_ingest_service(core=core)
        with patch("internal.domain.case.write_service.create_embedding_provider", return_value=_NoopEmbeddingProvider()):
            asyncio.run(
                ingest_service.ingest(
                    IngestRequest(
                        partition_name="CI",
                        title="Tax update memo",
                        source_content="This memo covers tax policy updates and filing obligations.",
                        source_refs=["doc://tax-memo"],
                        author="integration-test",
                        source="user",
                    )
                )
            )
            asyncio.run(
                ingest_service.ingest(
                    IngestRequest(
                        partition_name="CI",
                        title="Claims handbook",
                        source_content="This handbook explains claims workflow and document review.",
                        source_refs=["doc://claims-handbook"],
                        author="integration-test",
                        source="user",
                    )
                )
            )

        partition_cases = core.case_repository.list_by_partition("CI")
        self.assertEqual(len(partition_cases), 2)

        core.partition_service.refresh_semantic_index(partition_name="CI", case_documents=partition_cases)
        core.partition_service.refresh_facet_index(partition_name="CI", case_documents=partition_cases)

        query_flow = KnowbaseQueryFlow(
            planner=_StaticQueryPlanner(),
            normalizer=QueryNormalizer(),
            query_service=KnowbaseQueryService(
                case_service=core.case_service,
                normalizer=QueryNormalizer(),
                ranking=KnowbaseRanking(),
            ),
            partition_service=core.partition_service,
            answer_agent=_StaticAnswerAgent(),
        )

        result = asyncio.run(
            query_flow.run(
                QueryRequest(
                    text="tax policy updates",
                    partition_name="CI",
                    size=2,
                    recall_size=5,
                )
            )
        )

        self.assertIsNotNone(result.plan)
        self.assertEqual(len(result.cases), 1)
        self.assertEqual(result.cases[0].title, "Tax update memo")
        self.assertEqual(result.answer.citations, [result.cases[0].case_id])
        self.assertIn("tax", result.plan.expanded_terms)
        self.assertEqual(result.debug.get("returned_case_count"), 1)
        self.assertEqual(result.debug.get("semantic_index_key_count"), 3)

    def _build_core(self):
        return build_core_providers(runtime_cfg=self._runtime_cfg)

    def _build_ingest_service(self, *, core):
        ingest = IngestProviders(
            draft_builder=KnowbaseCaseDraftBuilder(),
            ingestor=KnowbaseCaseIngestor(),
            summary_extractor=_StaticSummaryExtractor(),
            semantic_profile_extractor=_StaticSemanticProfileExtractor(),
            facet_resolver=KnowbaseCaseFacetResolver(),
        )
        return build_ingest_service(core=core, ingest=ingest)

    @staticmethod
    def _create_partition(*, core, partition_name: str) -> None:
        TextMinimalFlowIntegrationTest._create_partition(core=core, partition_name=partition_name)


if __name__ == "__main__":
    unittest.main()
