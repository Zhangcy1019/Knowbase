from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from internal.infrastructure.persistence.local import StatisticsSnapshotRepository
from internal.knowledge.statistics import (
    CaseObservation,
    CaseSupportQuery,
    StatisticsAggregator,
    StatisticsObservationNormalizer,
    StatisticsReader,
    StatisticsStore,
    StatisticsSupportFilter,
    StatisticsWriter,
)


class KnowledgeStatisticsTest(unittest.TestCase):
    def _build_writer(self, root: Path) -> tuple[StatisticsWriter, StatisticsStore]:
        snapshot_store = StatisticsStore(repository=StatisticsSnapshotRepository(root))
        writer = StatisticsWriter(
            snapshot_store=snapshot_store,
            normalizer=StatisticsObservationNormalizer(),
            aggregator=StatisticsAggregator(),
        )
        return writer, snapshot_store

    def test_incremental_and_full_rebuild_have_same_result(self) -> None:
        with TemporaryDirectory() as directory:
            writer, store = self._build_writer(Path(directory))
            observations = [
                CaseObservation(
                    observation_id="observation-1",
                    partition="ci",
                    source_id="case-1",
                    facets={"Area": ["Build", "Build"]},
                ),
                CaseObservation(
                    observation_id="observation-2",
                    partition="ci",
                    source_id="case-2",
                    facets={"area": ["Release"]},
                ),
            ]
            for observation in observations:
                writer.append_case_observation(observation=observation)

            incremental = store.load(partition="ci")
            rebuilt = writer.rebuild_partition_statistics(partition="ci", observations=observations)

            self.assertIsNotNone(incremental)
            self.assertEqual(incremental.case_key_stats, rebuilt.case_key_stats)
            self.assertEqual(incremental.value_stats, rebuilt.value_stats)
            self.assertEqual(incremental.case_support_index, rebuilt.case_support_index)

    def test_duplicate_observation_is_idempotent(self) -> None:
        with TemporaryDirectory() as directory:
            writer, store = self._build_writer(Path(directory))
            observation = CaseObservation(
                observation_id="observation-1",
                partition="ci",
                source_id="case-1",
                facets={"area": ["build"]},
            )
            writer.append_case_observation(observation=observation)
            writer.append_case_observation(observation=observation)

            snapshot = store.load(partition="ci")
            self.assertEqual(snapshot.case_count, 1)
            self.assertEqual(snapshot.value_stats["facet:area"]["build"], 1)

    def test_support_query_matches_multiple_filters(self) -> None:
        with TemporaryDirectory() as directory:
            writer, store = self._build_writer(Path(directory))
            writer.append_case_observation(
                observation=CaseObservation(
                    observation_id="observation-1",
                    partition="ci",
                    source_id="case-1",
                    facets={"area": ["build"]},
                    semantic_profile={"network": ["disabled"]},
                )
            )
            reader = StatisticsReader(store=store)
            query = CaseSupportQuery(
                filters=[
                    StatisticsSupportFilter(field="facet", key="area", values=["build"]),
                    StatisticsSupportFilter(field="semantic_profile", key="network", values=["disabled"]),
                ]
            )

            self.assertEqual(reader.find_supporting_cases(partition="ci", query=query), ["case-1"])

    def test_replace_and_remove_update_snapshot(self) -> None:
        with TemporaryDirectory() as directory:
            writer, store = self._build_writer(Path(directory))
            old = CaseObservation(
                observation_id="observation-1",
                partition="ci",
                source_id="case-1",
                facets={"area": ["build"]},
            )
            new = old.model_copy(update={"facets": {"area": ["release"]}})
            writer.append_case_observation(observation=old)
            writer.replace_case_observation(old_observation=old, new_observation=new)
            snapshot = store.load(partition="ci")
            self.assertEqual(snapshot.case_support_index, {"facet:area:release": ["case-1"]})
            writer.remove_observation(observation=new)
            self.assertEqual(store.load(partition="ci").case_count, 0)


if __name__ == "__main__":
    unittest.main()
