"""Shared LLM construction helpers."""

from __future__ import annotations

from internal.utils.config import LLMRuntimeConfig


def build_langchain_openai_chat_model(*, config: LLMRuntimeConfig):
    provider = config.provider.strip().lower()
    if provider != "openai":
        raise ValueError(f"unsupported llm provider: {config.provider}")
    if not (config.openai_api_key or "").strip():
        raise ValueError("missing llm api key")
    try:
        from langchain_openai import ChatOpenAI
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("langchain_openai import failed") from exc
    return ChatOpenAI(
        model=config.model.strip() or "gpt-4o-mini",
        temperature=float(config.temperature),
        api_key=(config.openai_api_key or "").strip(),
        base_url=(config.openai_base_url or "").strip() or None,
    )
