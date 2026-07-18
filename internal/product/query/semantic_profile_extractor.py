"""LLM-based semantic profile extractor for one query."""

from __future__ import annotations

from textwrap import dedent
from typing import Any

from langchain_core.messages import HumanMessage

from internal.models import PartitionFacetDefinition, QuerySemanticExtractionEnvelope, QuerySemanticProfile, ensure_partition_profile_keys, resolve_partition_profile_fields
from internal.models.partition_semantic_index import PartitionSemanticIndex
from internal.utils.config import LLMRuntimeConfig
from internal.utils.logger import get_logger
from internal.utils.llm import build_langchain_openai_chat_model


class KnowbaseQuerySemanticProfileExtractor:
    """Infer a structured query semantic profile and hypothetical answer."""

    def __init__(self, *, llm_config: LLMRuntimeConfig | None = None):
        self._logger = get_logger(__name__)
        self._llm_config = llm_config
        self._model = self._build_model()

    async def extract(
        self,
        *,
        text: str,
        expanded_terms: list[str],
        facet_definitions: list[PartitionFacetDefinition] | None = None,
        semantic_index: PartitionSemanticIndex | None = None,
    ) -> tuple[QuerySemanticProfile, str]:
        normalized_text = text.strip()
        profile_fields = resolve_partition_profile_fields(facet_definitions)
        if not normalized_text:
            return QuerySemanticProfile.from_partition_schema(facet_definitions=facet_definitions), ""
        if self._model is None:
            raise RuntimeError("KnowbaseQuerySemanticProfileExtractor is unavailable: LLM model initialization failed")

        prompt = self._build_prompt(
            text=normalized_text,
            expanded_terms=expanded_terms,
            profile_fields=profile_fields,
            semantic_index=semantic_index,
        )
        structured_model = self._model.with_structured_output(QuerySemanticExtractionEnvelope)
        try:
            result = await structured_model.ainvoke([HumanMessage(content=prompt)])
        except Exception as exc:  # noqa: BLE001
            self._logger.exception(
                "Query semantic profile extraction failed",
                extra={"error": str(exc)},
            )
            raise RuntimeError(f"Query semantic profile extraction failed: {exc}") from exc
        return self._sanitize_result(result, facet_definitions=facet_definitions)

    def _build_model(self):
        if self._llm_config is None:
            self._logger.error(
                "KnowbaseQuerySemanticProfileExtractor unavailable: missing llm_config",
            )
            return None
        try:
            return build_langchain_openai_chat_model(config=self._llm_config)
        except Exception as exc:  # noqa: BLE001
            self._logger.exception(
                "KnowbaseQuerySemanticProfileExtractor unavailable: chat model initialization failed",
                extra={"error": str(exc)},
            )
            return None

    @staticmethod
    def _build_prompt(
        *,
        text: str,
        expanded_terms: list[str],
        profile_fields: dict[str, str],
        semantic_index: PartitionSemanticIndex | None,
    ) -> str:
        field_lines = "\n".join(
            f"- {key}: {description or 'semantic field enabled by the partition schema'}"
            for key, description in profile_fields.items()
        )
        semantic_index_lines = "\n".join(
            f"- {item.key}: top_values={', '.join(value.value for value in item.sample_values[:6]) or '(none)'}"
            for item in ((semantic_index.key_stats if semantic_index is not None else [])[:12])
            if item.key.strip()
        )
        instructions = dedent(
            """
            你是 Knowbase 的 Query Semantic Profile Extractor。

            目标：
            - 将用户查询改写成与 case 检索表示同构的语义轮廓。
            - 生成一个简短的 hypothetical_answer，用来模拟“如果命中正确知识，答案大概会怎么说”。
            - 当前 partition facet schema 中定义的字段，是必须优先覆盖的稳定维度。
            - 除这些稳定维度外，如果 query 本身明显表达了额外的开放语义维度，也可以补充新的 key。

            输出结构说明：
            - semantic_profile: 一个 JSON 对象，key 可以是稳定 facet key，也可以是你额外归纳出的开放语义 key；字段值必须是短语数组
            - hypothetical_answer: 用 1 到 3 句短中文或与输入同语言的短句，概括最可能命中的知识答案

            当前必须优先覆盖的稳定 facet 字段：
            {field_lines}

            当前 partition 中已经观察到的高频开放语义参考：
            {semantic_index_lines}

            约束：
            - 输出语言默认与输入保持一致。
            - 专有名词、库名、分支名、命令名保留原文，不要翻译。
            - 不要编造不存在的信息；只能根据 query 和 expanded terms 做合理补全。
            - 如果当前存在稳定 facet 字段，必须尽量为这些字段输出值；如果 query 里确实没有对应信号，也至少保留该字段并返回空数组。
            - 如果当前 partition 已经存在高频开放语义 key/value，请尽量复用这些已有表达，避免无意义地创造近义新 key。
            - 在覆盖稳定 facet 字段之后，你可以补充额外的开放语义 key，用于表达当前 schema 尚未正式收敛但对检索有帮助的维度。
            - semantic_profile 中每个字段尽量使用短语，不要使用长句。
            - 去重，避免同义重复。
            - 如果查询明显是在问排查/解决/规范，优先补全 actions、rules、constraints。
            - 如果查询明显是在问故障现象或根因，优先补全 symptoms、causes。
            - 不要输出字段解释，不要输出额外文本。
            """
        ).format(
            field_lines=field_lines or "- 当前没有稳定 facet 字段约束，你可以自由归纳语义 key",
            semantic_index_lines=semantic_index_lines or "- 当前还没有可参考的高频开放语义",
        ).strip()
        return (
            f"{instructions}\n\n"
            f"query:\n{text}\n\n"
            f"expanded_terms:\n{', '.join(term for term in expanded_terms if term)}\n"
        )

    @staticmethod
    def _sanitize_result(
        result: QuerySemanticExtractionEnvelope,
        *,
        facet_definitions: list[PartitionFacetDefinition] | None,
    ) -> tuple[QuerySemanticProfile, str]:
        raw_profile = ensure_partition_profile_keys(
            result.semantic_profile,
            facet_definitions=facet_definitions,
        )
        normalized_profile: dict[str, Any] = {}
        for key, values in raw_profile.items():
            normalized_profile[key] = KnowbaseQuerySemanticProfileExtractor._dedupe(values, limit=8)
        return (
            QuerySemanticProfile.from_partition_schema(normalized_profile, facet_definitions=facet_definitions),
            str(result.hypothetical_answer).strip(),
        )

    @staticmethod
    def _dedupe(values: object, *, limit: int) -> list[str]:
        if not isinstance(values, list):
            values = [values] if values not in (None, "") else []
        seen: set[str] = set()
        output: list[str] = []
        for value in values:
            normalized = str(value).strip()
            if not normalized:
                continue
            lowered = normalized.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            output.append(normalized)
            if len(output) >= limit:
                break
        return output
