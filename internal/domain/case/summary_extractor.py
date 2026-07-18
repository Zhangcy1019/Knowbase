"""LLM-based case summary extractor."""

from __future__ import annotations

from textwrap import dedent

from langchain_core.messages import HumanMessage

from internal.utils.config import LLMRuntimeConfig
from internal.utils.logger import get_logger
from internal.utils.llm import build_langchain_openai_chat_model


class KnowbaseCaseSummaryExtractor:
    """Extract a short human-readable summary from one knowledge entry."""

    def __init__(self, *, llm_config: LLMRuntimeConfig | None = None):
        self._logger = get_logger(__name__)
        self._llm_config = llm_config
        self._model = self._build_model()

    async def extract(self, *, title: str, source_content: str) -> str:
        normalized_title = title.strip()
        normalized_content = source_content.strip()
        if not normalized_title and not normalized_content:
            return ""
        if self._model is None:
            raise RuntimeError("KnowbaseCaseSummaryExtractor is unavailable: LLM model initialization failed")

        prompt = self._build_prompt(title=normalized_title, source_content=normalized_content)
        try:
            result = await self._model.ainvoke([HumanMessage(content=prompt)])
        except Exception as exc:  # noqa: BLE001
            self._logger.exception(
                "Case summary extraction failed",
                extra={"error": str(exc)},
            )
            raise RuntimeError(f"Case summary extraction failed: {exc}") from exc
        return self._sanitize_result(getattr(result, "content", result))

    def extract_sync(self, *, title: str, source_content: str) -> str:
        normalized_title = title.strip()
        normalized_content = source_content.strip()
        if not normalized_title and not normalized_content:
            return ""
        if self._model is None:
            raise RuntimeError("KnowbaseCaseSummaryExtractor is unavailable: LLM model initialization failed")

        prompt = self._build_prompt(title=normalized_title, source_content=normalized_content)
        try:
            result = self._model.invoke([HumanMessage(content=prompt)])
        except Exception as exc:  # noqa: BLE001
            self._logger.exception(
                "Case summary extraction failed",
                extra={"error": str(exc)},
            )
            raise RuntimeError(f"Case summary extraction failed: {exc}") from exc
        return self._sanitize_result(getattr(result, "content", result))

    def _build_model(self):
        if self._llm_config is None:
            self._logger.error(
                "KnowbaseCaseSummaryExtractor unavailable: missing llm_config",
            )
            return None
        try:
            return build_langchain_openai_chat_model(config=self._llm_config)
        except Exception as exc:  # noqa: BLE001
            self._logger.exception(
                "KnowbaseCaseSummaryExtractor unavailable: chat model initialization failed",
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
        return " ".join(text.split())[:500].strip()
