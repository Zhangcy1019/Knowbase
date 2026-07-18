"""LLM-assisted partition facet-schema suggestion service."""

from __future__ import annotations

from textwrap import dedent

from pydantic import BaseModel, Field

from internal.infrastructure.ai.generation import build_openai_client, generate_structured
from internal.models.facet import PartitionFacetDefinition
from internal.models.semantic_profile import resolve_partition_profile_fields
from internal.utils.config import LLMRuntimeConfig
from internal.utils.logger import get_logger


class SuggestedPartitionFacet(BaseModel):
    key: str
    value: str


class PartitionSchemaSuggestion(BaseModel):
    suggested_facets: list[SuggestedPartitionFacet] = Field(default_factory=list)
    rationale: str = ""
    should_update_existing: bool = True


class PartitionSchemaSuggester:
    """Generate partition facet suggestions from scenario description and current config."""

    def __init__(self, *, llm_config: LLMRuntimeConfig | None = None) -> None:
        self._logger = get_logger(__name__)
        self._llm_config = llm_config
        self._client = None

    def suggest(
        self,
        *,
        partition_name: str,
        scenario_description: str,
        current_facet_definitions: list[PartitionFacetDefinition] | None = None,
        cautious_update: bool = False,
    ) -> PartitionSchemaSuggestion:
        if self._client is None:
            self._client = self._build_client()
        if self._client is None:
            raise RuntimeError("PartitionSchemaSuggester is unavailable: LLM model initialization failed")

        current_fields = resolve_partition_profile_fields(current_facet_definitions)
        prompt = self._build_prompt(
            partition_name=partition_name,
            scenario_description=scenario_description,
            current_fields=current_fields,
            cautious_update=cautious_update,
        )
        try:
            return generate_structured(
                client=self._client,
                model=self._llm_config.model if self._llm_config is not None else "",
                temperature=self._llm_config.temperature if self._llm_config is not None else 0.0,
                max_output_tokens=self._llm_config.max_output_tokens if self._llm_config is not None else 1200,
                system_prompt="You are Knowbase partition facet schema designer.",
                user_prompt=prompt,
                response_model=PartitionSchemaSuggestion,
                metadata={"component": "partition_schema_suggester"},
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.exception(
                "Partition schema suggestion failed",
                extra={"partition_name": partition_name, "error": str(exc)},
            )
            raise RuntimeError(f"Partition schema suggestion failed: {exc}") from exc

    def _build_client(self):
        if self._llm_config is None:
            self._logger.error("PartitionSchemaSuggester unavailable: missing llm_config")
            return None
        try:
            return build_openai_client(config=self._llm_config)
        except Exception as exc:  # noqa: BLE001
            self._logger.exception(
                "PartitionSchemaSuggester unavailable: OpenAI client initialization failed",
                extra={"error": str(exc)},
            )
            return None

    @staticmethod
    def _build_prompt(
        *,
        partition_name: str,
        scenario_description: str,
        current_fields: dict[str, str],
        cautious_update: bool,
    ) -> str:
        current_lines = "\n".join(
            f"- {key}: {field_description or 'existing semantic dimension'}"
            for key, field_description in current_fields.items()
        )
        mode_text = (
            "当前是在修改既有配置。请优先保持现有字段稳定，仅在场景定义明显变化时才建议增删改。"
            if cautious_update
            else "当前是在创建新分区。请根据场景定义提出一组清晰、稳定、可复用的 facet 字段。"
        )
        instructions = dedent(
            """
            你是 Knowbase 的 Partition Facet Schema Designer。

            目标：
            - 根据分区场景说明，为 semantic profile 设计一组 stable facets。
            - 这些字段首先要服务分类、筛选、检索和聚合，而不是做抽象概念分析。
            - 优先设计能稳定支撑分类与检索的字段，而不是停留在宽泛、上位的概念层面。
            - 每个字段都要用简洁 description 说明该字段应该承载什么信息。

            规则：
            - 建议 4 到 8 个字段。
            - key 使用 snake_case。
            - value 是这个字段的中文说明，简洁明确。
            - 字段要彼此正交，尽量避免同义重复字段。
            - 不要优先输出过于元、过于抽象、难以直接分类的字段，比如 type、scope、category、level、abstraction_level，除非场景里确实没有更具体的业务维度。
            - 不要输出 content_type 之类全局固定字段，除非场景确实需要。
            - 如果是修改既有配置，默认尽量延续当前字段，只在必要时调整。

            输出要求：
            - suggested_facets: 直接给出建议字段列表。
            - rationale: 简短说明为什么这样设计，以及与当前字段相比是否有调整。
            - should_update_existing: 如果当前配置已经足够好且不建议变更，返回 false；否则返回 true。
            """
        ).strip()
        return (
            f"{instructions}\n\n"
            f"{mode_text}\n\n"
            f"partition_name:\n{partition_name.strip() or '-'}\n\n"
            f"scenario_description:\n{scenario_description.strip() or '-'}\n\n"
            f"current_schema_fields:\n{current_lines or '- no existing fields'}\n"
        )
