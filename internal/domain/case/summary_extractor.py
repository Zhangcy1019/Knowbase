"""LLM-based case summary extractor."""

from __future__ import annotations

import re
from textwrap import dedent

from internal.infrastructure.ai.generation import build_openai_client, generate_text
from internal.utils.config import LLMRuntimeConfig
from internal.utils.logger import get_logger


class KnowbaseCaseSummaryExtractor:
    """Extract a short human-readable summary from one knowledge entry."""

    def __init__(self, *, llm_config: LLMRuntimeConfig | None = None):
        self._logger = get_logger(__name__)
        self._llm_config = llm_config
        self._client = self._build_client()

    async def extract(self, *, title: str, source_content: str) -> str:
        normalized_title = title.strip()
        normalized_content = source_content.strip()
        if not normalized_title and not normalized_content:
            return ""
        if self._client is None:
            raise RuntimeError("KnowbaseCaseSummaryExtractor is unavailable: LLM model initialization failed")

        prompt = self._build_prompt(title=normalized_title, source_content=normalized_content)
        try:
            result = generate_text(
                client=self._client,
                model=self._llm_config.model if self._llm_config is not None else "",
                temperature=self._llm_config.temperature if self._llm_config is not None else 0.0,
                max_output_tokens=self._llm_config.max_output_tokens if self._llm_config is not None else 1200,
                system_prompt="You are Knowbase case summary extractor.",
                user_prompt=prompt,
                metadata={"component": "case_summary_extractor"},
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.exception(
                "Case summary extraction failed",
                extra={"error": str(exc)},
            )
            raise RuntimeError(f"Case summary extraction failed: {exc}") from exc
        return self._sanitize_result(result)

    def extract_sync(self, *, title: str, source_content: str) -> str:
        normalized_title = title.strip()
        normalized_content = source_content.strip()
        if not normalized_title and not normalized_content:
            return ""
        if self._client is None:
            raise RuntimeError("KnowbaseCaseSummaryExtractor is unavailable: LLM model initialization failed")

        prompt = self._build_prompt(title=normalized_title, source_content=normalized_content)
        try:
            result = generate_text(
                client=self._client,
                model=self._llm_config.model if self._llm_config is not None else "",
                temperature=self._llm_config.temperature if self._llm_config is not None else 0.0,
                max_output_tokens=self._llm_config.max_output_tokens if self._llm_config is not None else 1200,
                system_prompt="You are Knowbase case summary extractor.",
                user_prompt=prompt,
                metadata={"component": "case_summary_extractor"},
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.exception(
                "Case summary extraction failed",
                extra={"error": str(exc)},
            )
            raise RuntimeError(f"Case summary extraction failed: {exc}") from exc
        return self._sanitize_result(result)

    def _build_client(self):
        if self._llm_config is None:
            self._logger.error(
                "KnowbaseCaseSummaryExtractor unavailable: missing llm_config",
            )
            return None
        try:
            return build_openai_client(config=self._llm_config)
        except Exception as exc:  # noqa: BLE001
            self._logger.exception(
                "KnowbaseCaseSummaryExtractor unavailable: OpenAI client initialization failed",
                extra={"error": str(exc)},
            )
            return None

    @staticmethod
    def _build_prompt(*, title: str, source_content: str) -> str:
        instructions = dedent(
            """
            你是 Knowbase 的 Case Summary Extractor。

            目标：
            - 根据标题和正文，为一条知识条目生成简短 summary。

            约束：
            - summary 应该是 1 到 3 句，尽量短。
            - 保持与输入相同语言。
            - 优先概括主题、核心问题或核心做法。
            - 不要输出标题，不要输出项目符号，不要输出解释性前缀。
            - 不要输出思考过程、推理过程、<think> 标签、分析说明或中间草稿。
            - 直接输出最终 summary 正文，不要输出任何 XML/HTML/Markdown 包裹。
            """
        ).strip()
        return (
            f"{instructions}\n\n"
            f"title:\n{title}\n\n"
            f"source_content:\n{source_content}\n"
        )

    @staticmethod
    def _sanitize_result(value: object) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        text = re.sub(r"<think\b[^>]*>[\s\S]*?</think>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<thinking\b[^>]*>[\s\S]*?</thinking>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"```[\s\S]*?```", " ", text)
        text = re.sub(r"^\s*(analysis|reasoning|thoughts?)\s*:\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return ""
        if text.startswith("<") and ">" in text:
            text = re.sub(r"^<[^>]+>\s*", "", text).strip()
        return text[:500].strip()
