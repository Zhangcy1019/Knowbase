"""Git workspace and versioning integration tests.

Run:
    cd /home/zcy/Project/knowbase
    python3 -m unittest tests.integration.infrastructure.version_control.test_git_repository
"""

from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
import unittest

from internal.application.versioning import VersionCommitCoordinator
from internal.infrastructure.version_control.git import GitRepository


class GitRepositoryIntegrationTest(unittest.TestCase):
    def test_initialize_creates_workspace_repository_and_initial_revision(self) -> None:
        with TemporaryDirectory() as directory:
            repository = GitRepository(root=Path(directory))

            revision = repository.initialize()

            self.assertTrue(revision)
            self.assertTrue((Path(directory) / ".git").exists())
            self.assertTrue(repository.status().clean)

            second_revision = repository.initialize()
            self.assertEqual(second_revision, revision)

    def test_initialize_baselines_existing_files(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            existing = root / "cases" / "case-1.json"
            existing.parent.mkdir(parents=True)
            existing.write_text("{}\n", encoding="utf-8")

            repository = GitRepository(root=root)
            revision = repository.initialize()

            self.assertTrue(revision)
            self.assertTrue(repository.status().clean)
            tracked = subprocess.run(
                ["git", "ls-files", "cases/case-1.json"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(tracked, "cases/case-1.json")

    def test_existing_dirty_repository_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            repository = GitRepository(root=root)
            repository.initialize()
            (root / "dirty.json").write_text("{}\n", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "uncommitted changes"):
                repository.initialize()

    def test_commit_status_diff_and_restore(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            repository = GitRepository(root=root)
            repository.initialize()
            document = root / "cases" / "case-1.json"
            document.parent.mkdir(parents=True)
            document.write_text('{"title":"before"}\n', encoding="utf-8")

            first_commit = repository.commit(
                message="ingest: add or update case case-1",
                paths=["cases/case-1.json"],
            )
            self.assertTrue(first_commit.revision)
            self.assertTrue(repository.status().clean)

            document.write_text('{"title":"after"}\n', encoding="utf-8")
            self.assertFalse(repository.status().clean)
            self.assertIn('"after"', repository.diff(paths=["cases/case-1.json"]))

            repository.restore(
                revision=first_commit.revision,
                paths=["cases/case-1.json"],
            )
            self.assertEqual(document.read_text(encoding="utf-8"), '{"title":"before"}\n')

    def test_commit_without_changes_is_idempotent(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            repository = GitRepository(root=root)
            initial_revision = repository.initialize()
            document = root / "knowledge_statistics" / "ci" / "snapshot.json"
            document.parent.mkdir(parents=True)
            document.write_text("{}\n", encoding="utf-8")
            committed = repository.commit(message="knowledge: update partition ci", paths=["knowledge_statistics/ci/snapshot.json"])

            result = repository.commit(message="knowledge: update partition ci", paths=["knowledge_statistics/ci/snapshot.json"])

            self.assertNotEqual(committed.revision, initial_revision)
            self.assertEqual(result.revision, committed.revision)
            self.assertEqual(result.paths, [])

    def test_coordinator_rejects_dirty_workspace_before_governance(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            repository = GitRepository(root=root)
            repository.initialize()
            (root / "uncommitted.txt").write_text("dirty\n", encoding="utf-8")
            coordinator = VersionCommitCoordinator(version_control=repository)

            with self.assertRaisesRegex(RuntimeError, "clean working tree"):
                coordinator.begin_governance()

    def test_initialize_rejects_workspace_nested_in_parent_repository(self) -> None:
        with TemporaryDirectory() as directory:
            parent = Path(directory)
            subprocess.run(["git", "init"], cwd=parent, check=True, capture_output=True)
            subprocess.run(
                [
                    "git", "-c", "user.name=parent", "-c", "user.email=parent@local",
                    "commit", "--allow-empty", "-m", "parent",
                ],
                cwd=parent,
                check=True,
                capture_output=True,
            )
            nested = parent / "workspace"

            with self.assertRaisesRegex(RuntimeError, "inside another Git repository"):
                GitRepository(root=nested).initialize()


if __name__ == "__main__":
    unittest.main()
