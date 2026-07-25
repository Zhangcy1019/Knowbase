"""Small Git adapter used by application-level commit policies."""

from __future__ import annotations

import subprocess
from pathlib import Path

from internal.models.version_control import VersionCommit, VersionControlStatus
from internal.utils.logger import get_logger


logger = get_logger("knowbase.infrastructure.version_control.git")


class GitRepository:
    """Implement generic version-control operations for one workspace."""

    def __init__(self, *, root: Path):
        self._root = root

    def initialize(self) -> str:
        self._root.mkdir(parents=True, exist_ok=True)
        discovered_root = self._discover_root()
        if discovered_root is not None and discovered_root != self._root.resolve():
            logger.error(
                "Git workspace is nested inside another repository; startup is blocked.",
                extra={
                    "workspace": str(self._root.resolve()),
                    "repository_root": str(discovered_root),
                },
            )
            raise RuntimeError(
                f"local workspace is inside another Git repository: {self._root} "
                f"(repository root: {discovered_root})"
            )
        if discovered_root is None:
            logger.info(
                "Initializing Git workspace.",
                extra={"workspace": str(self._root.resolve())},
            )
            self._run("init")
            self._run("add", "-A")
        else:
            logger.info(
                "Using existing Git workspace.",
                extra={"workspace": str(self._root.resolve())},
            )
        try:
            self.current_revision()
        except subprocess.CalledProcessError:
            logger.info(
                "Creating initial Git workspace baseline commit.",
                extra={"workspace": str(self._root.resolve())},
            )
            self._run(
                "-c", "user.name=knowbase", "-c", "user.email=knowbase@local",
                "commit", "--allow-empty", "-m", "workspace: initialize",
            )
        status = self.status()
        if not status.clean:
            logger.error(
                "Git workspace has uncommitted changes; startup is blocked.",
                extra={
                    "workspace": str(self._root.resolve()),
                    "revision": status.revision,
                    "changed_paths": status.changed_paths,
                },
            )
            raise RuntimeError(
                "workspace Git repository has uncommitted changes: "
                + ", ".join(status.changed_paths)
            )
        return status.revision

    def _discover_root(self) -> Path | None:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=self._root,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return None
        return Path(result.stdout.strip()).resolve()

    def status(self) -> VersionControlStatus:
        revision = self.current_revision()
        output = self._run("status", "--porcelain", "--untracked-files=all")
        paths = [line[3:] for line in output.splitlines() if len(line) >= 4]
        return VersionControlStatus(clean=not paths, revision=revision, changed_paths=paths)

    def current_revision(self) -> str:
        return self._run("rev-parse", "HEAD").strip()

    def diff(self, *, paths: list[str] | None = None) -> str:
        return self._run("diff", "--", *(paths or []))

    def commit(self, *, message: str, paths: list[str]) -> VersionCommit:
        if not paths:
            raise ValueError("version-control commit requires at least one path")
        self._run("add", "--", *paths)
        staged = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=self._root,
            check=False,
        )
        if staged.returncode == 0:
            logger.info(
                "Git commit skipped because there are no changes.",
                extra={"workspace": str(self._root.resolve()), "message": message},
            )
            return VersionCommit(revision=self.current_revision(), message=message, paths=[])
        logger.info(
            "Creating Git commit.",
            extra={
                "workspace": str(self._root.resolve()),
                "message": message,
                "paths": paths,
            },
        )
        self._run("commit", "-m", message)
        revision = self.current_revision()
        logger.info(
            "Git commit created.",
            extra={"workspace": str(self._root.resolve()), "revision": revision, "message": message},
        )
        return VersionCommit(revision=revision, message=message, paths=list(paths))

    def restore(self, *, revision: str, paths: list[str]) -> None:
        if not paths:
            return
        logger.info(
            "Restoring files from Git revision.",
            extra={"workspace": str(self._root.resolve()), "revision": revision, "paths": paths},
        )
        self._run("restore", "--source", revision, "--", *paths)

    def _run(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self._root,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout


__all__ = ["GitRepository"]
