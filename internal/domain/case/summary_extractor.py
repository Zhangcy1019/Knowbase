"""LLM-based case summary extractor."""

from __future__ import annotations

import os
from textwrap import dedent

from langchain_core.messages import HumanMessage

from internal.utils.logger import get_logger


class KnowbaseCaseSummaryExtractor:
    """Extract a short human-readable summary from one knowledge entry."""

    def __init__(self):
        self._logger = get_logger(__name__)
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
        provider = os.getenv("CIAGENT_LEAD_AGENT_PROVIDER", "openai").strip().lower()
        if provider != "openai":
            self._logger.error(
                "KnowbaseCaseSummaryExtractor unsupported provider",
                extra={"provider": provider},
            )
            return None
        try:
            from langchain_openai import ChatOpenAI
        except Exception as exc:  # noqa: BLE001
            self._logger.exception(
                "KnowbaseCaseSummaryExtractor unavailable: langchain_openai import failed",
                extra={"error": str(exc)},
            )
            return None
        if not os.getenv("OPENAI_API_KEY"):
            self._logger.error("KnowbaseCaseSummaryExtractor unavailable: OPENAI_API_KEY missing")
            return None

        model_name = os.getenv("CIAGENT_LEAD_AGENT_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
        temperature = float(os.getenv("CIAGENT_LEAD_AGENT_TEMPERATURE", "0").strip() or "0")
        return ChatOpenAI(model=model_name, temperature=temperature)

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
