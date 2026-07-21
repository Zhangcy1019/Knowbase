"""Runtime injected-task integration test with a real configured LLM.

Run:
    cd /home/zcy/Project/knowbase
    python3 -m unittest tests.integration.runtime.test_runtime_injected_file_task_with_llm
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from internal.models import AgentRun, RunArtifact, RunStep
from internal.models.skill import SkillInvocation, SkillResult, SkillSpec
from internal.models.skill_context import SkillExecutionContext
from internal.runtime.contracts import RuntimeRunRequest, RuntimeWorkProfile
from internal.runtime.llm import DefaultRuntimeDecisionGenerator, DefaultRuntimePromptBuilder
from internal.runtime.loop.turn_planner import RuntimeTurnPlanner
from internal.runtime.llm.model_adapter import DefaultRuntimeModelAdapter
from internal.runtime.service import KnowbaseRuntimeService
from internal.runtime.skills import SkillRuntime
from internal.runtime.skills.registry import SkillRegistry
from internal.runtime.tools import ToolRuntime
from internal.runtime.trace import RuntimeTraceRecorder
from internal.runtime.verification.profile import RuntimeVerificationProfile
from internal.infrastructure.ai import DefaultOpenAIClient
from tests.integration.runtime.llm.test_decision_generator import _TEST_RUNTIME_CONFIG, _has_openai_env


class _InMemoryRunRepository:
    def __init__(self) -> None:
        self._runs: dict[str, AgentRun] = {}

    def save(self, run: AgentRun) -> AgentRun:
        now = datetime.now(timezone.utc)
        persisted = run.model_copy(
            update={
                "run_id": run.run_id or f"run-{int(now.timestamp() * 1000)}",
                "created_at": run.created_at or now,
                "updated_at": now,
            }
        )
        self._runs[persisted.run_id] = persisted
        return persisted

    def get(self, run_id: str) -> AgentRun | None:
        return self._runs.get(run_id)

    def list(self, *, partition: str = "", status: str = "") -> list[AgentRun]:
        items = list(self._runs.values())
        if partition:
            items = [item for item in items if item.partition == partition]
        if status:
            items = [item for item in items if item.status == status]
        return sorted(items, key=lambda item: item.created_at or datetime.min.replace(tzinfo=timezone.utc))

    def delete(self, run_id: str) -> None:
        self._runs.pop(run_id, None)


class _InMemoryRunStepRepository:
    def __init__(self) -> None:
        self._steps: dict[str, list[RunStep]] = {}

    def save(self, step: RunStep) -> RunStep:
        now = datetime.now(timezone.utc)
        persisted = step.model_copy(
            update={
                "step_id": step.step_id or f"{step.run_id}:step:{step.index}:{int(now.timestamp() * 1000)}",
                "created_at": step.created_at or now,
            }
        )
        self._steps.setdefault(persisted.run_id, []).append(persisted)
        return persisted

    def list_for_run(self, run_id: str) -> list[RunStep]:
        return list(self._steps.get(run_id, []))

    def delete_for_run(self, run_id: str) -> None:
        self._steps.pop(run_id, None)


class _InMemoryRunArtifactRepository:
    def __init__(self) -> None:
        self._artifacts: dict[str, list[RunArtifact]] = {}

    def save(self, artifact: RunArtifact) -> RunArtifact:
        now = datetime.now(timezone.utc)
        persisted = artifact.model_copy(
            update={
                "artifact_id": artifact.artifact_id
                or f"{artifact.run_id}:{artifact.artifact_type}:{int(now.timestamp() * 1000)}",
                "created_at": artifact.created_at or now,
                "updated_at": now,
            }
        )
        self._artifacts.setdefault(persisted.run_id, []).append(persisted)
        return persisted

    def list_for_run(self, run_id: str) -> list[RunArtifact]:
        return list(self._artifacts.get(run_id, []))

    def delete_for_run(self, run_id: str) -> None:
        self._artifacts.pop(run_id, None)


class _StaticPartitionService:
    @staticmethod
    def get_partition(partition: str):
        return {"partition": partition, "status": "active"} if partition.strip() else None


class _RewriteSummaryBodySkill:
    @property
    def spec(self) -> SkillSpec:
        return SkillSpec(
            skill_id="document.rewrite_summary_body",
            title="Rewrite Summary Body",
            description="Rewrite a local text file into Summary/Body structure.",
            execution_mode="deterministic",
            side_effect_scope="single_resource",
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "summary_prefix": {"type": "string"},
                },
                "required": ["file_path"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "content_preview": {"type": "string"},
                },
            },
            examples=[
                {
                    "file_path": "/tmp/knowledge_note.txt",
                    "summary_prefix": "Summary:",
                }
            ],
            usage_notes=[
                "Reuse the exact file path from runtime input_context when available.",
                "Read the source file and generate the summary content from the body before rewriting.",
            ],
            argument_binding_hints={
                "file_path": "input_context.file_path",
                "summary_prefix": "input_context.summary_prefix",
            },
        )

    def execute(self, invocation: SkillInvocation, *, context: SkillExecutionContext | None = None) -> SkillResult:
        started_at = datetime.now(timezone.utc)
        file_path = Path(str(invocation.inputs.get("file_path", "")).strip())
        summary_prefix = str(invocation.inputs.get("summary_prefix") or "Summary:").strip() or "Summary:"
        original = file_path.read_text(encoding="utf-8").strip()
        lines = [line.strip() for line in original.splitlines() if line.strip()]
        summary_body = lines[0].rstrip(".") if lines else "No content"
        rewritten = f"{summary_prefix} {summary_body}\n\nBody:\n{original}\n"
        file_path.write_text(rewritten, encoding="utf-8")
        return SkillResult(
            invocation_id=invocation.invocation_id,
            skill_id=invocation.skill_id,
            ok=True,
            updated_objects=[str(file_path)],
            output={
                "file_path": str(file_path),
                "content_preview": rewritten[:160],
            },
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
        )


class _VerifySummaryBodySkill:
    @property
    def spec(self) -> SkillSpec:
        return SkillSpec(
            skill_id="document.verify_summary_body",
            title="Verify Summary Body",
            description="Verify that a rewritten local text file satisfies Summary/Body expectations.",
            execution_mode="deterministic",
            side_effect_scope="read_only",
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "source_text": {"type": "string"},
                },
                "required": ["file_path"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "passed": {"type": "boolean"},
                    "summary": {"type": "string"},
                    "issues": {"type": "array", "items": {"type": "string"}},
                    "retryable": {"type": "boolean"},
                    "repair_prompt": {"type": "string"},
                },
            },
            examples=[
                {
                    "file_path": "/tmp/knowledge_note.txt",
                    "source_text": "Original body line one.\nOriginal body line two.",
                }
            ],
            usage_notes=[
                "Read the current file content and compare it to the original source text.",
                "Return only structured verification fields in the skill output.",
            ],
            argument_binding_hints={
                "file_path": "input_context.file_path",
                "source_text": "input_context.verification_source_text",
            },
        )

    def execute(self, invocation: SkillInvocation, *, context: SkillExecutionContext | None = None) -> SkillResult:
        started_at = datetime.now(timezone.utc)
        file_path = Path(str(invocation.inputs.get("file_path", "")).strip())
        source_text = str(invocation.inputs.get("source_text") or "").strip()
        current = file_path.read_text(encoding="utf-8")
        lines = current.splitlines()
        summary_line = lines[0].strip() if lines else ""
        issues: list[str] = []
        passed = True

        if not summary_line.startswith("Summary: "):
            passed = False
            issues.append("summary line must start with 'Summary: ' and contain content")
        elif summary_line == "Summary:" or not summary_line.removeprefix("Summary:").strip():
            passed = False
            issues.append("summary line is missing non-prefix content")
        if "\n\nBody:\n" not in current:
            passed = False
            issues.append("body section is missing")
        if source_text and source_text not in current:
            passed = False
            issues.append("original source text is not preserved in body")

        summary = "Verification passed." if passed else "Verification failed."
        repair_prompt = ""
        if not passed:
            repair_prompt = "Rewrite the file so Summary contains a concise issue line and Body preserves the original text."
        return SkillResult(
            invocation_id=invocation.invocation_id,
            skill_id=invocation.skill_id,
            ok=True,
            output={
                "passed": passed,
                "summary": summary,
                "issues": issues,
                "retryable": not passed,
                "repair_prompt": repair_prompt,
            },
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
        )


@unittest.skipUnless(
    _has_openai_env(),
    "Set llm.openai.api_key in config/app.test.yaml to run runtime injected-task LLM integration tests.",
)
class RuntimeInjectedFileTaskWithLLMIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        print(
            f"[runtime.injected_task.llm] test={self._testMethodName} "
            f"model={_TEST_RUNTIME_CONFIG.llm.model} "
            f"base_url={os.getenv('KNOWBASE_LLM_OPENAI_BASE_URL', '') or '<default>'}",
            flush=True,
        )

    def _build_service(self) -> KnowbaseRuntimeService:
        run_repository = _InMemoryRunRepository()
        step_repository = _InMemoryRunStepRepository()
        artifact_repository = _InMemoryRunArtifactRepository()
        trace_recorder = RuntimeTraceRecorder(
            run_repository=run_repository,
            step_repository=step_repository,
            artifact_repository=artifact_repository,
        )
        openai_client = DefaultOpenAIClient(
            api_key=_TEST_RUNTIME_CONFIG.llm.openai_api_key or "",
            base_url=_TEST_RUNTIME_CONFIG.llm.openai_base_url,
            timeout_seconds=_TEST_RUNTIME_CONFIG.llm.timeout_seconds,
        )
        decision_generator = DefaultRuntimeDecisionGenerator(
            prompt_builder=DefaultRuntimePromptBuilder(
                model=_TEST_RUNTIME_CONFIG.llm.model,
                temperature=_TEST_RUNTIME_CONFIG.llm.temperature,
                max_output_tokens=_TEST_RUNTIME_CONFIG.llm.max_output_tokens,
            ),
            model_adapter=DefaultRuntimeModelAdapter(client=openai_client),
            trace_recorder=trace_recorder,
            llm_config=_TEST_RUNTIME_CONFIG.llm,
        )
        skill_registry = SkillRegistry()
        skill_registry.register(_RewriteSummaryBodySkill())
        skill_registry.register(_VerifySummaryBodySkill())
        return KnowbaseRuntimeService(
            partition_service=_StaticPartitionService(),
            case_repository=None,
            run_repository=run_repository,
            step_repository=step_repository,
            artifact_repository=artifact_repository,
            tool_runtime=ToolRuntime(),
            skill_runtime=SkillRuntime(registry=skill_registry),
            planner=RuntimeTurnPlanner(decision_generator=decision_generator),
            trace_recorder=trace_recorder,
        )

    def test_runtime_run_request_can_inject_file_rewrite_task_with_llm(self) -> None:
        service = self._build_service()
        with tempfile.TemporaryDirectory(prefix="knowbase-runtime-file-task-llm-") as tempdir:
            file_path = Path(tempdir) / "knowledge_note.txt"
            file_path.write_text(
                "Buildbarn access fails in Guangzhou.\n"
                "Kylin network may be disabled.\n"
                "A local .bazelrc override may also break FlashBuild.",
                encoding="utf-8",
            )
            before = file_path.read_text(encoding="utf-8")
            print(
                "[runtime.injected_task.llm] before\n"
                f"path={file_path}\n"
                f"{before}",
                flush=True,
            )

            request = RuntimeRunRequest(
                request_id="req-runtime-file-rewrite-llm",
                source_type="manual",
                source_ref="integration:file-rewrite:llm",
                partition="CI",
                work=RuntimeWorkProfile(
                    objective="Rewrite a local note into a Summary + Body document.",
                    mission_summary="Use the allowed runtime skill to rewrite the target file in place.",
                    instructions=[
                        "Rewrite the target file in place.",
                        "Use the allowed skill to derive a concise single-line summary from the file content.",
                        "Preserve the original content under a Body section.",
                        "Do not stop before the file has actually been rewritten.",
                        "After the file has been rewritten once, stop with no more actions.",
                    ],
                    capability_hints=[
                        {
                            "kind": "execution_requirement",
                            "summary": "A write action is required; stopping before the file changes is invalid.",
                        }
                    ],
                    input_context={
                        "file_path": str(file_path),
                        "file_kind": "plain_text",
                        "desired_output_format": "Summary + Body",
                        "summary_prefix": "Summary:",
                    },
                    allowed_skills=["document.rewrite_summary_body"],
                    allowed_tools=[],
                    max_steps=16,
                    max_tool_calls=0,
                    max_skill_calls=4,
                ),
                acceptance={
                    "completion_checks": [
                        "file starts with Summary:",
                        "summary line contains non-prefix content",
                        "file contains Body:",
                        "original content is preserved under Body:",
                    ],
                    "max_retries": 0,
                },
                verification=RuntimeVerificationProfile(
                    enabled=True,
                    mode="subrun",
                    objective="Verify whether the rewritten file satisfies the requested Summary + Body structure.",
                    instructions=[
                        "Use the allowed verification skill exactly once to inspect the rewritten file.",
                        "Pass the concrete file_path from input_context to the verification skill.",
                        "After the verification skill returns, stop with no further actions.",
                        "Do not call the rewrite skill during verification.",
                    ],
                    prompt=(
                        "Judge whether the rewritten document is clearer than the source and whether the "
                        "Summary line accurately captures the primary issue from the source without losing the "
                        "original body content."
                    ),
                    allowed_skills=["document.verify_summary_body"],
                    max_steps=16,
                    max_skill_calls=4,
                    max_retries=0,
                    require_acceptance=True,
                ),
                stop_policy={"stop_when_acceptance_satisfied": True},
                risk_policy={"risk_level": "low"},
                risk_level="low",
                requires_review=False,
                metadata={"runtime_mode": "execution"},
            )

            result = asyncio.run(service.run_request(request=request))
            updated = file_path.read_text(encoding="utf-8")
            print(
                "[runtime.injected_task.llm] after\n"
                f"path={file_path}\n"
                f"{updated}",
                flush=True,
            )
            print(
                "[runtime.injected_task.llm] result "
                f"run_id={result.run_id} status={result.status} "
                f"applied_actions={result.applied_actions} "
                f"skill_results={[item.model_dump(mode='json') for item in result.skill_results]} "
                f"steps={[item.step_type for item in result.steps]}",
                flush=True,
            )
            if result.status != "completed":
                print(
                    "[runtime.injected_task.llm] failure "
                    f"final_summary={result.final_summary!r} reasoning_summary={result.reasoning_summary!r}",
                    flush=True,
                )

            self.assertEqual(result.status, "completed")
            self.assertTrue(result.run_id)
            self.assertFalse(result.requires_review)
            self.assertEqual(len(result.skill_results), 1)
            self.assertTrue(result.skill_results[0].ok)
            self.assertEqual(len(result.applied_actions), 1)
            self.assertIn("Summary:", updated)
            self.assertNotIn("Summary:\n", updated)
            self.assertIn("Body:", updated)
            self.assertIn("Buildbarn access fails in Guangzhou.", updated)

            trace = service.get_trace_replay(result.run_id)
            self.assertIsNotNone(trace)
            assert trace is not None
            self.assertEqual(len(trace.turns), 1)
            self.assertTrue(any(step.step_type == "decision" for step in trace.steps))
            self.assertTrue(any(step.step_type == "skill_call" for step in trace.steps))
            self.assertTrue(any(step.step_type == "skill_result" for step in trace.steps))
            self.assertTrue(
                any(
                    observation.kind == "verification_subrun"
                    and str(observation.payload.get("status", "")) == "completed"
                    for turn in trace.turns
                    for observation in turn.observations
                )
            )

            runs = service.list_runs(partition="CI")
            self.assertEqual(len(runs), 2)
            child_runs = [item for item in runs if item.run_id != result.run_id]
            self.assertEqual(len(child_runs), 1)
            child_run = child_runs[0]
            self.assertEqual(child_run.status, "completed")
            self.assertIn(":subrun:verification", child_run.run_id)

            child_trace = service.get_trace_replay(child_run.run_id)
            self.assertIsNotNone(child_trace)
            assert child_trace is not None
            self.assertGreaterEqual(len(child_trace.turns), 1)
            self.assertTrue(any(step.step_type == "decision" for step in child_trace.steps))
            self.assertTrue(any(step.step_type == "skill_call" for step in child_trace.steps))
            self.assertTrue(any(step.step_type == "skill_result" for step in child_trace.steps))


if __name__ == "__main__":
    unittest.main()
