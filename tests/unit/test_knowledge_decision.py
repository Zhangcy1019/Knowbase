"""Knowledge decision audit and review-lock tests."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from internal.knowledge.decision import (
    KnowledgeDecisionInput,
    KnowledgeDecisionOutcome,
    KnowledgeDecisionRecord,
    KnowledgeDecisionRepository,
    KnowledgeDecisionService,
)
from internal.knowledge.decision.review_lock import PartitionReviewLock


class KnowledgeDecisionTest(unittest.TestCase):
    def test_requires_review_creates_lock_and_discard_releases_it(self) -> None:
        with TemporaryDirectory() as directory:
            repository = KnowledgeDecisionRepository(local_root=Path(directory))
            lock = PartitionReviewLock(local_root=Path(directory))
            service = KnowledgeDecisionService(repository=repository, review_lock=lock)
            record = KnowledgeDecisionRecord(
                partition="CI",
                batch_id="batch-1",
                status="requires_review",
                input=KnowledgeDecisionInput(
                    statistics_snapshot={"case_count": 2},
                ),
                outcome=KnowledgeDecisionOutcome(
                    outcome="requires_review",
                    reasons=["manual review"],
                ),
            )

            service.create(record)
            self.assertEqual(lock.get(partition="CI")["decision_id"], record.decision_id)
            service.transition(decision_id=record.decision_id, status="discarded", reviewer="dev")

            self.assertIsNone(lock.get(partition="CI"))
            self.assertEqual(service.get(record.decision_id).status, "discarded")

    def test_only_one_review_decision_is_allowed_per_partition(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            repository = KnowledgeDecisionRepository(local_root=root)
            lock = PartitionReviewLock(local_root=root)
            service = KnowledgeDecisionService(repository=repository, review_lock=lock)
            service.create(KnowledgeDecisionRecord(
                partition="CI",
                batch_id="batch-1",
                status="requires_review",
                input=KnowledgeDecisionInput(),
                outcome=KnowledgeDecisionOutcome(outcome="requires_review"),
            ))

            with self.assertRaisesRegex(RuntimeError, "already has"):
                service.create(KnowledgeDecisionRecord(
                    partition="CI",
                    batch_id="batch-2",
                    status="requires_review",
                    input=KnowledgeDecisionInput(),
                    outcome=KnowledgeDecisionOutcome(outcome="requires_review"),
                ))


if __name__ == "__main__":
    unittest.main()
