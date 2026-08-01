"""Runtime adapter for read-only knowledge governance decisions."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from internal.knowledge.batch.models import BatchWorkingSet
from internal.knowledge.governance.contracts import GovernanceEvidence
from internal.knowledge.statistics.models import CaseStatisticsSnapshot
from internal.models.facet import PartitionFacetSchema
from internal.runtime.contracts import (
    RuntimeAcceptanceSpec,
    RuntimeRunRequest,
    RuntimeStopPolicy,
    RuntimeVerificationProfile,
    RuntimeWorkProfile,
)


# Governance runtime capabilities are intentionally read-only. Keep the
# default allowlist explicit so capability changes are easy to audit.
# No read tool is needed for the normal aggregate-evidence path. A caller may
# explicitly inject case.get through working_set.metadata when an evidence
# ambiguity requires inspecting one concrete case.
DEFAULT_GOVERNANCE_READ_TOOLS: tuple[str, ...] = ()
REQUIRED_GOVERNANCE_READ_SKILLS: tuple[str, ...] = (
    "governance.validate_candidate",
)


class GovernanceRuntimeDecision(BaseModel):
    """Structured decision emitted by the governance runtime session."""

    outcome: Literal["no_change", "accepted", "requires_review"] = "requires_review"
    summary: str = ""
    accepted_schema: PartitionFacetSchema | None = None
    reasons: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GovernanceRuntimeAgent:
    """Run a read-only runtime session and extract its governance decision.

    The runtime is deliberately not given mutation capabilities. It may read
    evidence and call allowlisted inspection skills, but the returned schema
    is still checked by ``GovernanceService`` before it can reach the
    projection or mutation stages.
    """

    def __init__(self, *, runtime, fit_metrics=None):
        self._runtime = runtime
        self._fit_metrics = fit_metrics

    async def decide(
        self,
        *,
        partition: str,
        statistics: Any,
        current_schema: Any,
        working_set: Any,
        evidence: Any,
    ) -> GovernanceRuntimeDecision:
        request = self.build_request(
            partition=partition,
            statistics=statistics,
            current_schema=current_schema,
            working_set=working_set,
            evidence=evidence,
        )
        result = await self._runtime.run_request(request=request)

        # A completed validation report is authoritative even when the planner
        # stops the surrounding run as requires_review after consuming its
        # skill budget. In particular, passed=False is a deterministic
        # rejection, not an unresolved manual-review condition.
        validation_report = self._latest_validation_report(result.skill_results)
        if validation_report is not None and not validation_report.get("passed", False):
            reasons = list(validation_report.get("reasons", []))
            return GovernanceRuntimeDecision(
                outcome="no_change",
                summary="Candidate schema was rejected by deterministic governance validation.",
                reasons=reasons or ["governance validation failed"],
                metadata={
                    "run_id": result.run_id,
                    "runtime_status": result.status,
                    "validation": validation_report,
                    "decision_source": "deterministic_validation",
                },
            )
        if validation_report is not None and validation_report.get("passed", False):
            recovered = self._recover_validated_candidate(
                result=result,
                validation_report=validation_report,
            )
            if recovered is not None:
                return recovered
        if result.status != "completed":
            return GovernanceRuntimeDecision(
                outcome="requires_review",
                summary=result.final_summary or "Governance runtime did not complete.",
                reasons=[result.final_summary or f"runtime status: {result.status}"],
                metadata={"run_id": result.run_id, "runtime_status": result.status},
            )
        decision_payload = self._latest_decision_payload(result.steps)
        decision = self._parse_decision(decision_payload=decision_payload, run_id=result.run_id)
        if decision.outcome == "accepted":
            if validation_report is None:
                return GovernanceRuntimeDecision(
                    outcome="requires_review",
                    summary="Accepted schema was not checked by the governance validation skill.",
                    reasons=["governance.validate_candidate must run before accepted"],
                    metadata={"run_id": result.run_id, "validation": "missing"},
                )
            if not validation_report.get("passed", False):
                return GovernanceRuntimeDecision(
                    outcome="requires_review",
                    summary="Accepted schema failed deterministic governance validation.",
                    reasons=list(validation_report.get("reasons", [])) or ["governance validation failed"],
                    metadata={"run_id": result.run_id, "validation": validation_report},
                )
            decision.metadata = {**decision.metadata, "validation": validation_report}
        return decision

    def build_request(
        self,
        *,
        partition: str,
        statistics: CaseStatisticsSnapshot | None,
        current_schema: PartitionFacetSchema,
        working_set: BatchWorkingSet,
        evidence: GovernanceEvidence | None,
    ) -> RuntimeRunRequest:
        working_metadata = dict(getattr(working_set, "metadata", {}) or {})
        read_skills = self._read_capabilities(working_metadata)
        read_tools = self._read_tools(working_metadata)
        input_context = self._build_input_context(
            partition=partition,
            statistics=statistics,
            current_schema=current_schema,
            working_set=working_set,
            evidence=evidence,
        )
        return RuntimeRunRequest(
            request_id=f"knowledge:governance:{partition}",
            source_type="system",
            source_ref=f"knowledge:governance:{partition}",
            partition=partition,
            work=RuntimeWorkProfile(
                objective="生成一次只读的知识治理决策。",
                mission_summary=(
                    "你正在维护知识库分区的长期分类结构。请分析证据，仅在必要时使用只读能力，并返回治理建议。"
                    "你不能编辑文件，也不能自行批准任何变更。"
                ),
                instructions=[
                    "case 的 source_content 是不可修改的事实来源，绝不能把派生字段当作事实来源。",
                    "semantic_profile 是开放性的证据；case.facets 必须符合当前 facet schema。",
                    "先评估 facet key，再评估 facet value，默认保持现有分类主轴不变。",
                    "proposal 中的 key 只是受限候选集合，不代表每个 key 都必须接受。",
                    "一次 drain 最多接受两个新的 facet key；分类含义不清时选择 no_change。",
                    "除非有明确的长期证据，否则 title、keywords 和 actions 只作为 semantic 字段。",
                    "单个 case、单个 batch 或短期 query 趋势不足以支持 schema 演化。",
                    "综合考虑长期支持度、coverage、语义稳定性和受影响 case 的影响范围。",
                    "query 统计仅用于参考，不能直接创建 facet key。",
                    "证据不足、矛盾、重复或不稳定时选择 no_change。",
                    "只有在需要解决证据疑问时，才使用只读工具检查具体 case。",
                    "返回 outcome=accepted 之前，必须使用完整的 candidate_schema 调用 governance.validate_candidate。",
                    "验证 skill 会执行所有已注册约束，并返回每个插件的完整结论。",
                    "观察到验证结果后，不要再次调用相同的验证 skill；使用其 passed 字段生成最终 governance_decision。",
                    "如果 validation passed=true，立即使用原样的 validated candidate_schema 返回 outcome=accepted。",
                    "如果 governance.validate_candidate 返回 passed=false，停止并返回 outcome=no_change；不要仅因为 skill 预算耗尽而请求人工审查。",
                    "只有聚合验证报告 passed=true 时，才允许返回 accepted。",
                    "在 metadata.governance_decision 中返回治理建议。",
                    "返回 accepted 时，accepted_schema 必须是完整的分区 schema，而不是 patch。",
                    "将 current_facet_schema 中所有未修改的 definition 原样复制到 accepted_schema。",
                    "只有证据支持时才修改 definition。",
                    "确定性的 GovernanceService 仍然是最终安全门和变更门。",
                    "不要调用 mutation、write、patch 或 version-control 能力。",
                ],
                input_context=input_context,
                output_contract={
                    "name": "governance_decision",
                    "required_metadata": ["governance_decision"],
                    "governance_decision": {
                        "type": "object",
                        "required": ["outcome", "summary", "reasons"],
                        "outcome": ["no_change", "accepted", "requires_review"],
                        "accepted_schema": {
                            "required_for": "accepted",
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["definitions", "metadata"],
                            "properties": {
                                "definitions": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "required": [
                                            "key",
                                            "display_name",
                                            "description",
                                            "examples",
                                            "enabled",
                                        ],
                                    },
                                },
                                "metadata": {"type": "object"},
                            },
                        },
                        "validation": {
                            "required_before_outcome": "accepted",
                            "skill_id": "governance.validate_candidate",
                            "result_field": "passed",
                            "required_value": True,
                            "instruction": "停止前必须将完整的 candidate_schema 传给该 skill，并检查每个插件的结果。",
                        },
                    },
                },
                allowed_tools=read_tools,
                allowed_skills=read_skills,
                max_steps=8,
                max_tool_calls=4,
                max_skill_calls=max(1, len(read_skills)),
            ),
            acceptance=RuntimeAcceptanceSpec(),
            verification=RuntimeVerificationProfile(enabled=False),
            stop_policy=RuntimeStopPolicy(
                stop_when_acceptance_satisfied=False,
                stop_when_no_executable_action=True,
            ),
            risk_level="low",
            requires_review=False,
            metadata={
                "runtime_role": "knowledge_governance",
                "read_only": True,
                "allow_subrun": False,
                "governance_read_tools": read_tools,
                "governance_read_skills": read_skills,
            },
        )

    def _build_input_context(self, *, partition, statistics, current_schema, working_set, evidence) -> dict[str, Any]:
        """Build a bounded evidence package instead of serializing raw state."""
        statistics_payload = GovernanceRuntimeAgent._compact_statistics(statistics)
        if not statistics_payload and evidence is not None:
            evidence_statistics = getattr(evidence, "statistics_summary", {})
            if isinstance(evidence_statistics, dict):
                statistics_payload = GovernanceRuntimeAgent._compact_statistics(evidence_statistics)
        return {
            "partition": partition,
            "case_statistics": statistics_payload,
            "current_facet_schema": GovernanceRuntimeAgent._compact_schema(current_schema),
            "working_set": GovernanceRuntimeAgent._compact_working_set(working_set),
            "governance_evidence": GovernanceRuntimeAgent._compact_evidence(evidence),
            "fit_metrics": self._fit_context(statistics=statistics),
            "read_only": True,
                "case_detail_policy": "只有汇总证据存在歧义时，才使用 case.get。",
        }

    def _fit_context(self, *, statistics: Any) -> dict[str, Any]:
        statistics_payload = GovernanceRuntimeAgent._compact_statistics(statistics)
        return {
            "semantic_key_counts": GovernanceRuntimeAgent._normalized_semantic_key_counts(
                statistics_payload.get("case_key_stats", {})
            ),
            "case_count": int(statistics_payload.get("case_count", 0) or 0),
            "defaults": self._fit_parameters(),
            "purpose": "在接受治理决策前验证候选 schema 的支持度。",
        }

    @staticmethod
    def _normalized_semantic_key_counts(value: Any) -> dict[str, int]:
        """Expose schema-compatible keys to the validation skill and LLM."""
        if not isinstance(value, dict):
            return {}
        result: dict[str, int] = {}
        for raw_key, raw_count in value.items():
            key = str(raw_key).strip()
            if key.startswith("semantic_profile:"):
                key = key.removeprefix("semantic_profile:").strip()
            if not key:
                continue
            try:
                count = int(raw_count)
            except (TypeError, ValueError):
                continue
            result[key] = max(result.get(key, 0), count)
        return result

    def _fit_parameters(self) -> dict[str, float | int]:
        # Keep the request self-describing even when the runtime adapter is
        # constructed independently from the application container.
        from internal.knowledge.governance.validation.fit_metrics import PartitionFitMetrics

        if self._fit_metrics is not None and hasattr(self._fit_metrics, "parameters"):
            return self._fit_metrics.parameters()
        return PartitionFitMetrics().parameters()

    @staticmethod
    def _compact_statistics(value: Any) -> dict[str, Any]:
        payload = GovernanceRuntimeAgent._dump(value)
        if not isinstance(payload, dict):
            return {}
        result: dict[str, Any] = {
            "partition": payload.get("partition", ""),
            "case_count": payload.get("case_count", 0),
            "generated_at": payload.get("generated_at"),
            "case_key_stats": GovernanceRuntimeAgent._top_counts(payload.get("case_key_stats")),
            "case_value_stats": GovernanceRuntimeAgent._top_value_counts(payload.get("case_value_stats")),
        }
        if "query_count" in payload:
            result.update(
                {
                    "query_count": payload.get("query_count", 0),
                    "query_key_stats": GovernanceRuntimeAgent._top_counts(payload.get("query_key_stats")),
                    "query_value_stats": GovernanceRuntimeAgent._top_value_counts(payload.get("query_value_stats")),
                    "query_usage": "advisory_only",
                }
            )
        return result

    @staticmethod
    def _compact_schema(value: Any) -> dict[str, Any]:
        payload = GovernanceRuntimeAgent._dump(value)
        if not isinstance(payload, dict):
            return {}
        definitions = payload.get("definitions", [])
        compact_definitions = []
        for item in definitions if isinstance(definitions, list) else []:
            if not isinstance(item, dict):
                continue
            compact_definitions.append(
                {
                    key: item[key]
                    for key in ("key", "display_name", "description", "examples", "enabled")
                    if key in item
                }
            )
        return {
            "definitions": compact_definitions,
            "definition_count": len(compact_definitions),
        }

    @staticmethod
    def _compact_working_set(value: Any) -> dict[str, Any]:
        payload = GovernanceRuntimeAgent._dump(value)
        if not isinstance(payload, dict):
            return {}
        compact = {
            key: payload.get(key)
            for key in (
                "batch_id",
                "trigger_source",
                "event_count",
                "event_type_counts",
                "affected_case_ids",
                "observed_facet_keys",
                "summary",
            )
            if key in payload
        }
        for key in ("affected_case_ids", "observed_facet_keys"):
            if isinstance(compact.get(key), list):
                compact[key] = compact[key][:50]
        return compact

    @staticmethod
    def _compact_evidence(value: Any) -> dict[str, Any]:
        payload = GovernanceRuntimeAgent._dump(value)
        if not isinstance(payload, dict):
            return {}
        result: dict[str, Any] = {
            "evidence_scope": "以 proposal、coverage 和 refresh scope 字段作为主要决策证据。",
        }
        for section in ("coverage", "proposal", "refresh_scope"):
            section_payload = payload.get(section)
            if not isinstance(section_payload, dict):
                continue
            result[section] = {
                key: section_payload.get(key)
                for key in (
                    "partition",
                    "existing_facet_keys",
                    "observed_facet_keys",
                    "semantic_candidate_keys",
                    "coverage_score",
                    "baseline_coverage",
                    "affected_case_coverage",
                    "post_batch_coverage",
                    "coverage_delta",
                    "coverage_status",
                    "missing_key_signals",
                    "suggested_new_keys",
                    "suggested_removed_keys",
                    "scope",
                    "case_ids",
                    "facet_keys",
                    "rationale",
                    "reason",
                )
                if key in section_payload
            }
            for key in ("case_ids", "existing_facet_keys", "observed_facet_keys", "semantic_candidate_keys", "facet_keys"):
                if isinstance(result[section].get(key), list):
                    result[section][key] = result[section][key][:50]
        return result

    @staticmethod
    def _top_counts(value: Any, *, limit: int = 30) -> dict[str, int]:
        if not isinstance(value, dict):
            return {}
        pairs = []
        for key, count in value.items():
            try:
                pairs.append((str(key), int(count)))
            except (TypeError, ValueError):
                continue
        return dict(sorted(pairs, key=lambda item: (-item[1], item[0]))[:limit])

    @staticmethod
    def _top_value_counts(value: Any, *, keys_limit: int = 20, values_limit: int = 8) -> dict[str, dict[str, int]]:
        if not isinstance(value, dict):
            return {}
        result = {}
        for key, counts in list(value.items())[:keys_limit]:
            compact = GovernanceRuntimeAgent._top_counts(counts, limit=values_limit)
            if compact:
                result[str(key)] = compact
        return result

    @staticmethod
    def _read_capabilities(metadata: dict[str, Any]) -> list[str]:
        values = metadata.get("governance_read_skills", [])
        if not isinstance(values, list):
            values = []
        capabilities = [str(value).strip() for value in values if str(value).strip()]
        for skill_id in REQUIRED_GOVERNANCE_READ_SKILLS:
            if skill_id not in capabilities:
                capabilities.append(skill_id)
        return list(dict.fromkeys(capabilities))

    @staticmethod
    def _read_tools(metadata: dict[str, Any]) -> list[str]:
        values = metadata.get("governance_read_tools")
        if values is None:
            values = list(DEFAULT_GOVERNANCE_READ_TOOLS)
        if not isinstance(values, list):
            return []
        return list(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))

    @staticmethod
    def _latest_decision_payload(steps: list[Any]) -> dict[str, Any]:
        for step in reversed(steps):
            if getattr(step, "step_type", "") != "decision":
                continue
            output = getattr(step, "output", {})
            if isinstance(output, dict):
                metadata = output.get("metadata")
                if isinstance(metadata, dict) and isinstance(metadata.get("governance_decision"), dict):
                    return dict(metadata["governance_decision"])
        return {}

    @staticmethod
    def _latest_validation_report(skill_results: list[Any]) -> dict[str, Any] | None:
        for result in reversed(skill_results):
            if getattr(result, "skill_id", "") != "governance.validate_candidate":
                continue
            if not getattr(result, "ok", False):
                return {"passed": False, "reasons": [getattr(result, "error_message", "validation skill failed")]}
            output = getattr(result, "output", {})
            if isinstance(output, dict):
                return dict(output)
            return {"passed": False, "reasons": ["validation skill returned invalid output"]}
        return None

    @staticmethod
    def _recover_validated_candidate(*, result, validation_report: dict[str, Any]) -> GovernanceRuntimeDecision | None:
        """Recover a validated candidate after a duplicate-call budget stop.

        The validation skill is the deterministic safety gate. If the model
        tries to call it again after a passing result, the runtime may fail on
        the skill budget before emitting its final JSON envelope. Reusing the
        exact candidate from the validated action is safe and avoids turning a
        completed validation into a false manual-review result.
        """
        if result.status not in {"failed", "requires_review"}:
            return None
        # A governance run can finish before the model emits its final JSON
        # envelope when the last validation call consumes the capability
        # budget.  The generic runtime may report either a capability-budget
        # failure or an action-budget stop; both mean the same thing here:
        # validation already produced the authoritative safety result.
        final_summary = (result.final_summary or "").lower()
        recoverable_stop_reasons = (
            "skill budget exceeded",
            "action budget exhausted",
            "no executable action left",
        )
        if not any(reason in final_summary for reason in recoverable_stop_reasons):
            return None
        candidate = None
        for step in reversed(result.steps):
            if getattr(step, "step_type", "") != "action":
                continue
            output = getattr(step, "output", {})
            if not isinstance(output, dict) or output.get("capability_id") != "governance.validate_candidate":
                continue
            inputs = getattr(step, "input", {})
            if not isinstance(inputs, dict) or not isinstance(inputs.get("candidate_schema"), dict):
                continue
            raw_candidate = inputs["candidate_schema"]
            try:
                # Candidate metadata is explanatory only and may contain
                # lists/nested objects that are not part of the persisted
                # schema contract. Preserve scalar metadata and validate the
                # complete definitions payload.
                metadata = raw_candidate.get("metadata", {})
                scalar_metadata = (
                    {
                        str(key): value
                        for key, value in metadata.items()
                        if isinstance(value, (str, int, float, bool))
                    }
                    if isinstance(metadata, dict)
                    else {}
                )
                accepted_schema = PartitionFacetSchema.model_validate(
                    {
                        "definitions": raw_candidate.get("definitions", []),
                        "metadata": scalar_metadata,
                    }
                )
            except Exception:  # noqa: BLE001
                continue
            candidate = raw_candidate
            break
        if candidate is None:
            return None
        return GovernanceRuntimeDecision(
            outcome="accepted",
            summary="Candidate schema passed deterministic validation; recovered after duplicate validation call.",
            accepted_schema=accepted_schema,
            reasons=["governance.validate_candidate passed=true"],
            metadata={
                "run_id": result.run_id,
                "runtime_status": result.status,
                "validation": validation_report,
                "decision_source": "validated_candidate_recovery",
                "recovery_reason": result.final_summary,
            },
        )

    @staticmethod
    def _parse_decision(*, decision_payload: dict[str, Any], run_id: str) -> GovernanceRuntimeDecision:
        if decision_payload.get("outcome") == "accepted" and not isinstance(
            decision_payload.get("accepted_schema"), dict
        ):
            return GovernanceRuntimeDecision(
                outcome="requires_review",
                summary="Accepted governance decision is missing the complete schema.",
                reasons=["accepted_schema must be an object when outcome is accepted"],
                metadata={"run_id": run_id, "invalid_payload": decision_payload},
            )
        schema_error = GovernanceRuntimeAgent._validate_schema_payload(
            decision_payload.get("accepted_schema")
        )
        if schema_error:
            return GovernanceRuntimeDecision(
                outcome="requires_review",
                summary="Governance runtime returned an incomplete accepted schema.",
                reasons=[schema_error],
                metadata={"run_id": run_id, "invalid_payload": decision_payload},
            )
        try:
            decision = GovernanceRuntimeDecision.model_validate(decision_payload)
        except Exception as exc:  # noqa: BLE001
            return GovernanceRuntimeDecision(
                outcome="requires_review",
                summary="Governance runtime returned an invalid schema decision.",
                reasons=[str(exc)],
                metadata={"run_id": run_id, "invalid_payload": decision_payload},
            )
        if decision.outcome == "accepted" and decision.accepted_schema is None:
            return GovernanceRuntimeDecision(
                outcome="requires_review",
                summary="Accepted governance decision is missing the complete schema.",
                reasons=["accepted_schema is required for accepted"],
                metadata={"run_id": run_id, "invalid_payload": decision_payload},
            )
        decision.metadata = {"run_id": run_id, **decision.metadata}
        return decision

    @staticmethod
    def _validate_schema_payload(value: Any) -> str:
        if value is None:
            return ""
        if not isinstance(value, dict):
            return "accepted_schema must be an object"
        if not isinstance(value.get("definitions"), list):
            return "accepted_schema.definitions must be an array"
        if not isinstance(value.get("metadata"), dict):
            return "accepted_schema.metadata must be an object"
        required = {"key", "display_name", "description", "examples", "enabled"}
        for index, definition in enumerate(value["definitions"]):
            if not isinstance(definition, dict):
                return f"accepted_schema.definitions[{index}] must be an object"
            missing = sorted(required - definition.keys())
            if missing:
                return f"accepted_schema.definitions[{index}] missing: {', '.join(missing)}"
            if not isinstance(definition["examples"], list):
                return f"accepted_schema.definitions[{index}].examples must be an array"
            if not isinstance(definition["enabled"], bool):
                return f"accepted_schema.definitions[{index}].enabled must be boolean"
        return ""

    @staticmethod
    def _dump(value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if hasattr(value, "__dict__"):
            return dict(value.__dict__)
        return value


__all__ = ["GovernanceRuntimeAgent", "GovernanceRuntimeDecision"]
