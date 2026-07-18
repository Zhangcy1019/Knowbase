"""Shared text and structured generation helpers."""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from internal.infrastructure.ai.openai_client import DefaultOpenAIClient, OpenAIChatRequest
from internal.utils.config import LLMRuntimeConfig


StructuredOutputT = TypeVar("StructuredOutputT", bound=BaseModel)


def generate_text(
    *,
    client: DefaultOpenAIClient,
    model: str,
    temperature: float,
    max_output_tokens: int,
    system_prompt: str,
    user_prompt: str,
    metadata: dict[str, object] | None = None,
) -> str:
    response = client.create_chat(
        request=OpenAIChatRequest(
            model=model.strip() or "gpt-4o-mini",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format="json_object",
            temperature=float(temperature),
            max_output_tokens=max(1, int(max_output_tokens)),
            metadata=dict(metadata or {}),
        )
    )
    return str(response.content_text or "").strip()


def generate_structured(
    *,
    client: DefaultOpenAIClient,
    model: str,
    temperature: float,
    max_output_tokens: int,
    system_prompt: str,
    user_prompt: str,
    response_model: type[StructuredOutputT],
    metadata: dict[str, object] | None = None,
) -> StructuredOutputT:
    response = client.create_chat(
        request=OpenAIChatRequest(
            model=model.strip() or "gpt-4o-mini",
            system_prompt=system_prompt,
            user_prompt=_build_structured_user_prompt(
                user_prompt=user_prompt,
                response_model=response_model,
            ),
            response_format="json_object",
            temperature=float(temperature),
            max_output_tokens=max(1, int(max_output_tokens)),
            metadata={
                **dict(metadata or {}),
                "schema_name": response_model.__name__,
            },
        )
    )
    return response_model.model_validate(response.content_json)


def _build_structured_user_prompt(*, user_prompt: str, response_model: type[StructuredOutputT]) -> str:
    schema_text = response_model.model_json_schema()
    return (
        f"{user_prompt}\n\n"
        "输出要求:\n"
        "- 只返回一个 JSON object。\n"
        "- 不要输出 markdown code fence。\n"
        "- 不要输出 <think>、解释、前言或尾注。\n"
        f"- 严格满足这个 JSON schema:\n{schema_text}"
    )


def build_openai_client(*, config: LLMRuntimeConfig) -> DefaultOpenAIClient:
    provider = config.provider.strip().lower()
    if provider != "openai":
        raise ValueError(f"unsupported llm provider: {config.provider}")
    if not (config.openai_api_key or "").strip():
        raise ValueError("missing llm api key")
    return DefaultOpenAIClient(
        api_key=(config.openai_api_key or "").strip(),
        base_url=(config.openai_base_url or "").strip() or None,
        timeout_seconds=config.timeout_seconds,
    )


__all__ = ["generate_text", "generate_structured", "build_openai_client"]
