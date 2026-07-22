"""Deterministic acceptance checks for runtime verification."""

from __future__ import annotations

from pathlib import Path

from internal.runtime.memory.state import RuntimeRunState


class RuntimeDeterministicVerifier:
    """Evaluate whether a runtime request has actually satisfied its acceptance checks."""

    def is_satisfied(self, *, request, state: RuntimeRunState) -> bool:
        del state
        completion_checks = list(request.acceptance.completion_checks)
        if not completion_checks:
            return True
        file_path = str(request.work.input_context.get("file_path") or "").strip()
        file_text = self._read_file_text(file_path)
        for item in completion_checks:
            check = str(item).strip()
            if not check:
                continue
            if not self._evaluate_check(check=check, file_text=file_text):
                return False
        return True

    @staticmethod
    def _read_file_text(file_path: str) -> str:
        if not file_path:
            return ""
        path = Path(file_path).expanduser()
        if not path.exists() or not path.is_file():
            return ""
        return path.read_text(encoding="utf-8")

    @staticmethod
    def _evaluate_check(*, check: str, file_text: str) -> bool:
        lowered = check.lower()
        stripped = file_text.strip()
        if lowered == "file starts with summary:":
            return stripped.startswith("Summary:")
        if lowered == "file contains body:":
            return "Body:" in file_text
        if lowered == "original content is preserved under body:":
            if "Body:" not in file_text:
                return False
            body = file_text.split("Body:", 1)[1]
            return bool(body.strip())
        if lowered == "summary line contains non-prefix content":
            if not stripped.startswith("Summary:"):
                return False
            first_line = stripped.splitlines()[0].strip()
            return len(first_line) > len("Summary:")
        return True
