"""Generic OpenAI-style chat client for runtime providers."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from openai import OpenAI

from internal.utils.logger import get_logger


logger = get_logger("knowbase.runtime.providers.openai_client")

OpenAIResponseFormat = Literal["json_object", "json_schema"]


@dataclass(slots=True)
class OpenAIChatRequest:
    """Provider-agnostic OpenAI-style chat request."""

    model: str
    system_prompt: str = ""
    user_prompt: str = ""
    response_format: OpenAIResponseFormat = "json_object"
    response_schema: dict[str, Any] = field(default_factory=dict)
    temperature: float = 0.0
    max_output_tokens: int = 1200
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class OpenAIChatResponse:
    """Provider-agnostic OpenAI-style chat response."""

    content_text: str = ""
    content_json: dict[str, Any] = field(default_factory=dict)
    finish_reason: str = ""
    model: str = ""
    usage: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class OpenAIClientPort(Protocol):
    """Thin client port for OpenAI-style structured chat completion."""

    def create_chat(self, *, request: OpenAIChatRequest) -> OpenAIChatResponse:
        ...


class DefaultOpenAIClient:
    """OpenAI-backed structured chat client used by runtime decision generation."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str | None = None,
        timeout_seconds: int = 60,
    ):
        normalized_key = api_key.strip()
        if not normalized_key:
            raise ValueError("OpenAI client requires a non-empty api_key")
        normalized_base_url = (base_url or "").strip() or None
        self._timeout_seconds = max(1, int(timeout_seconds))
        self._client = OpenAI(
            api_key=normalized_key,
            base_url=normalized_base_url,
            timeout=float(self._timeout_seconds),
        )

    @classmethod
    def from_env(cls) -> "DefaultOpenAIClient":
        api_key = str(os.getenv("OPENAI_API_KEY") or "").strip()
        base_url = str(os.getenv("OPENAI_BASE_URL") or "").strip() or None
        timeout_seconds = int(str(os.getenv("CIAGENT_LEAD_AGENT_TIMEOUT_SECONDS") or "60").strip() or "60")
        return cls(
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )

    def create_chat(self, *, request: OpenAIChatRequest) -> OpenAIChatResponse:
        completion = self._client.chat.completions.create(
            model=request.model,
            messages=[
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            response_format=self._build_response_format(request=request),
            temperature=request.temperature,
            max_completion_tokens=max(1, int(request.max_output_tokens)),
            metadata=self._build_api_metadata(request=request) or None,
        )
        content_text = self._extract_content_text(completion=completion)
        content_json = self._extract_content_json(content_text=content_text)
        usage = {
            "input_tokens": int(getattr(getattr(completion, "usage", None), "prompt_tokens", 0) or 0),
            "output_tokens": int(getattr(getattr(completion, "usage", None), "completion_tokens", 0) or 0),
            "total_tokens": int(getattr(getattr(completion, "usage", None), "total_tokens", 0) or 0),
        }
        finish_reason = ""
        if getattr(completion, "choices", None):
            finish_reason = str(getattr(completion.choices[0], "finish_reason", "") or "")
        response = OpenAIChatResponse(
            content_text=content_text,
            content_json=content_json,
            finish_reason=finish_reason,
            model=str(getattr(completion, "model", "") or request.model),
            usage=usage,
            metadata={
                "request_model": request.model,
                "response_format": request.response_format,
            },
        )
        logger.debug(
            "OpenAI runtime chat completed.",
            extra={
                "model": response.model,
                "finish_reason": response.finish_reason,
                "usage": response.usage,
            },
        )
        return response

    def _build_response_format(self, *, request: OpenAIChatRequest) -> dict[str, Any]:
        if request.response_format == "json_schema" and request.response_schema:
            return {
                "type": "json_schema",
                "json_schema": {
                    "name": str(request.metadata.get("schema_name") or "runtime_schema"),
                    "strict": True,
                    "schema": dict(request.response_schema),
                },
            }
        return {"type": "json_object"}

    @staticmethod
    def _build_api_metadata(*, request: OpenAIChatRequest) -> dict[str, str]:
        metadata: dict[str, str] = {}
        for key, value in request.metadata.items():
            if key == "context" or value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                metadata[str(key)] = str(value)
        return metadata

    @staticmethod
    def _extract_content_text(*, completion: Any) -> str:
        if not getattr(completion, "choices", None):
            return ""
        message = getattr(completion.choices[0], "message", None)
        if message is None:
            return ""
        content = getattr(message, "content", "")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text_value = item.get("text")
                    if isinstance(text_value, str) and text_value.strip():
                        parts.append(text_value.strip())
                    continue
                text_value = getattr(item, "text", None)
                if isinstance(text_value, str) and text_value.strip():
                    parts.append(text_value.strip())
            return "\n".join(parts).strip()
        return str(content or "").strip()

    @staticmethod
    def _extract_content_json(*, content_text: str) -> dict[str, Any]:
        if not content_text:
            return {}
        try:
            payload = json.loads(content_text)
        except json.JSONDecodeError as exc:
            raise ValueError("OpenAI response is not valid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("OpenAI response JSON must be an object")
        return payload


__all__ = [
    "OpenAIResponseFormat",
    "OpenAIChatRequest",
    "OpenAIChatResponse",
    "OpenAIClientPort",
    "DefaultOpenAIClient",
]
