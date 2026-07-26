"""Partition versioning and lock unit tests."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from internal.infrastructure.coordination import PartitionMutationLock
from internal.infrastructure.version_control.git import GitRepository
from internal.versioning import PartitionVersioningManager


class PartitionVersioningTest(unittest.TestCase):
    def test_partition_paths_are_isolated_and_validated(self) -> None:
        with TemporaryDirectory() as directory:
            manager = PartitionVersioningManager(local_root=Path(directory))

            self.assertEqual(
                manager.partition_root("CI"),
                Path(directory).resolve() / "partitions" / "CI",
            )
            with self.assertRaises(ValueError):
                manager.partition_root("../outside")

    def test_mutation_lock_writes_and_removes_operation_metadata(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with PartitionMutationLock(local_root=root, partition="CI", operation_id="op-1"):
                metadata = root / "locks" / "CI.json"
                self.assertTrue(metadata.exists())
                self.assertIn('"operation_id": "op-1"', metadata.read_text(encoding="utf-8"))
            self.assertFalse(metadata.exists())

    def test_startup_validation_rejects_dirty_existing_partition(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            manager = PartitionVersioningManager(local_root=root)
            repository = GitRepository(root=manager.partition_root("CI"))
            repository.initialize()
            (manager.partition_root("CI") / "dirty.json").write_text("{}\n", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "uncommitted changes"):
                manager.initialize_existing_partitions(["CI"])


if __name__ == "__main__":
    unittest.main()
