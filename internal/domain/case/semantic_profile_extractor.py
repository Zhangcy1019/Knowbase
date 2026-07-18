"""LLM-based semantic profile extractor for one case or guide-like entry."""

from __future__ import annotations

from textwrap import dedent

from internal.infrastructure.ai.generation import build_openai_client, generate_structured
from internal.models.partition_semantic_index import PartitionSemanticIndex
from internal.models import CaseSemanticExtractionEnvelope, CaseSemanticProfile, PartitionFacetDefinition, ensure_partition_profile_keys, resolve_partition_profile_fields
from internal.utils.config import LLMRuntimeConfig
from internal.utils.logger import get_logger


class KnowbaseSemanticProfileExtractor:
    """Extract one structured semantic profile from title and source content."""

    def __init__(self, *, llm_config: LLMRuntimeConfig | None = None):
        self._logger = get_logger(__name__)
        self._llm_config = llm_config
        self._client = self._build_client()

    async def extract(
        self,
        *,
        title: str,
        source_content: str,
        facet_definitions: list[PartitionFacetDefinition] | None = None,
        semantic_index: PartitionSemanticIndex | None = None,
    ) -> CaseSemanticProfile:
        normalized_title = title.strip()
        normalized_content = source_content.strip()
        profile_fields = resolve_partition_profile_fields(facet_definitions)  # profile_fields: key-description
        if not normalized_title and not normalized_content:
            return CaseSemanticProfile.from_partition_schema({}, facet_definitions=facet_definitions)
        if self._client is None:
            raise RuntimeError("KnowbaseSemanticProfileExtractor is unavailable: LLM model initialization failed")

        prompt = self._build_prompt(
            title=normalized_title,
            source_content=normalized_content,
            profile_fields=profile_fields,
            facet_definitions=facet_definitions,
            semantic_index=semantic_index,
        )
        try:
            result = generate_structured(
                client=self._client,
                model=self._llm_config.model if self._llm_config is not None else "",
                temperature=self._llm_config.temperature if self._llm_config is not None else 0.0,
                max_output_tokens=self._llm_config.max_output_tokens if self._llm_config is not None else 1200,
                system_prompt="You are Knowbase case semantic profile extractor.",
                user_prompt=prompt,
                response_model=CaseSemanticExtractionEnvelope,
                metadata={"component": "case_semantic_profile_extractor"},
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.exception(
                "Semantic profile extraction failed",
                extra={"error": str(exc)},
            )
            raise RuntimeError(f"Semantic profile extraction failed: {exc}") from exc
        return self._sanitize_result(result, facet_definitions=facet_definitions)

    def extract_sync(
        self,
        *,
        title: str,
        source_content: str,
        facet_definitions: list[PartitionFacetDefinition] | None = None,
        semantic_index: PartitionSemanticIndex | None = None,
    ) -> CaseSemanticProfile:
        normalized_title = title.strip()
        normalized_content = source_content.strip()
        profile_fields = resolve_partition_profile_fields(facet_definitions)
        if not normalized_title and not normalized_content:
            return CaseSemanticProfile.from_partition_schema({}, facet_definitions=facet_definitions)
        if self._client is None:
            raise RuntimeError("KnowbaseSemanticProfileExtractor is unavailable: LLM model initialization failed")

        prompt = self._build_prompt(
            title=normalized_title,
            source_content=normalized_content,
            profile_fields=profile_fields,
            facet_definitions=facet_definitions,
            semantic_index=semantic_index,
        )
        try:
            result = generate_structured(
                client=self._client,
                model=self._llm_config.model if self._llm_config is not None else "",
                temperature=self._llm_config.temperature if self._llm_config is not None else 0.0,
                max_output_tokens=self._llm_config.max_output_tokens if self._llm_config is not None else 1200,
                system_prompt="You are Knowbase case semantic profile extractor.",
                user_prompt=prompt,
                response_model=CaseSemanticExtractionEnvelope,
                metadata={"component": "case_semantic_profile_extractor"},
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.exception(
                "Semantic profile extraction failed",
                extra={"error": str(exc)},
            )
            raise RuntimeError(f"Semantic profile extraction failed: {exc}") from exc
        return self._sanitize_result(result, facet_definitions=facet_definitions)

    def _build_client(self):
        if self._llm_config is None:
            self._logger.error(
                "KnowbaseSemanticProfileExtractor unavailable: missing llm_config",
            )
            return None
        try:
            return build_openai_client(config=self._llm_config)
        except Exception as exc:  # noqa: BLE001
            self._logger.exception(
                "KnowbaseSemanticProfileExtractor unavailable: OpenAI client initialization failed",
                extra={"error": str(exc)},
            )
            return None

    @staticmethod
    def _build_prompt(
        *,
        title: str,
        source_content: str,
        profile_fields: dict[str, str],
        facet_definitions: list[PartitionFacetDefinition] | None,
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
            你是 Knowbase 的 Case Semantic Profile Extractor。

            目标：
            - 从一条知识条目中抽取稳定的语义轮廓，供后续 facet 投影、检索和总结使用。
            - 输入既可能是故障用例，也可能是最佳实践、操作手册、规范说明。
            - 当前 partition facet schema 中定义的字段，是必须优先覆盖的稳定维度。
            - 除这些稳定维度外，如果你发现还有明显有价值的语义维度，也可以额外输出新的 key。

            输出结构说明：
            - semantic_profile: 一个 JSON 对象，key 可以是稳定 facet key，也可以是你额外归纳出的开放语义 key
            - 每个字段的值必须是数组，数组中的每一项都应当是单词级别或极短标签级别的文本，而不是句子、子句、解释或完整动作描述

            当前必须优先覆盖的稳定 facet 字段：
            {field_lines}

            当前 partition 中已经观察到的高频开放语义参考：
            {semantic_index_lines}

            约束：
            - 只提取输入中明确出现或可直接归纳出的内容，不要编造。
            - 如果当前存在稳定 facet 字段，必须尽量为这些字段输出值；如果内容里确实没有信号，也至少保留该字段并返回空数组。
            - 先阅读稳定 facet 字段的 key 和 description，理解这些字段分别要承载哪一类语义，再回到原文中抽取对应信息。
            - 如果当前 partition 已经存在高频开放语义 key/value，请尽量复用这些已有表达，避免无意义地创造近义新 key。
            - 在覆盖稳定 facet 字段之后，你可以补充额外的开放语义 key，用于表达当前 schema 尚未正式收敛但对检索有帮助的维度。
            - semantic_profile 中每个字段的值都必须尽量压缩为单词、术语、实体名、命令名或 1 到 3 个词以内的短标签。
            - 严禁输出完整句子、因果描述、操作说明、结论性陈述或超过 3 个词的长短语。
            - 如果一个字段只能提炼出较长表达，请继续抽象、压缩、归纳，优先保留最核心的关键词，而不是原句。
            - 如果原文是中文，尽量输出简短中文关键词；如果原文是英文，尽量输出简短英文关键词；专有名词、库名、命令名、分支名保持原文。
            - 每个字段优先输出可检索、可索引、可复用的标签词，不要输出自然语言说明。
            - 去重，避免同义重复。
            - 如果文档更像故障案例，优先补全 symptoms / causes / actions。
            - 如果文档更像最佳实践、手册或规范说明，统一标为 guide，优先补全 actions / rules / constraints。
            - 如果某类信息不存在，对应字段返回空数组。
            - 不要输出字段解释，不要输出额外文本。

            输出示例要求：
            - 正确示例："timeout", "network", "certificate", "rollback", "权限不足", "证书过期"
            - 错误示例："因为证书过期导致服务连接失败", "需要先检查网络再重启服务", "该问题通常出现在发布之后"
            """
        ).format(
            field_lines=field_lines or "- 当前没有稳定 facet 字段约束，你可以自由归纳语义 key",
            semantic_index_lines=semantic_index_lines or "- 当前还没有可参考的高频开放语义",
        ).strip()
        return (
            f"{instructions}\n\n"
            f"title:\n{title}\n\n"
            f"source_content:\n{source_content}\n"
        )

    @staticmethod
    def _sanitize_result(
        result: CaseSemanticExtractionEnvelope,
        *,
        facet_definitions: list[PartitionFacetDefinition] | None,
    ) -> CaseSemanticProfile:
        raw_profile = ensure_partition_profile_keys(
            result.semantic_profile,
            facet_definitions=facet_definitions,
        )
        normalized_profile: dict[str, object] = {}
        for key, raw_values in raw_profile.items():
            values = KnowbaseSemanticProfileExtractor._dedupe(raw_values, limit=8)
            normalized_profile[key] = values
        return CaseSemanticProfile.model_validate(normalized_profile)

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
