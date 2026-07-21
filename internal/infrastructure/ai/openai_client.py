"""Generic OpenAI-style chat client for shared AI infrastructure."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from openai import OpenAI

from internal.utils.logger import get_logger


logger = get_logger("knowbase.infrastructure.ai.openai_client")

OpenAIResponseFormat = Literal["json_object", "json_schema"]


@dataclass(slots=True)
class OpenAIChatRequest:
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
    content_text: str = ""
    content_json: dict[str, Any] = field(default_factory=dict)
    finish_reason: str = ""
    model: str = ""
    usage: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class OpenAIClientPort(Protocol):
    def create_chat(self, *, request: OpenAIChatRequest) -> OpenAIChatResponse:
        ...

    def create_text_chat(self, *, request: OpenAIChatRequest) -> OpenAIChatResponse:
        ...


class DefaultOpenAIClient:
    """OpenAI-backed structured chat client."""

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
        normalized_base_url = self._normalize_base_url(base_url)
        self._timeout_seconds = max(1, int(timeout_seconds))
        self._client = OpenAI(
            api_key=normalized_key,
            base_url=normalized_base_url,
            timeout=float(self._timeout_seconds),
        )

    def create_chat(self, *, request: OpenAIChatRequest) -> OpenAIChatResponse:
        completion = self._create_completion(request=request, include_response_format=True)
        content_text = self._extract_content_text(completion=completion)
        try:
            content_json = self._extract_content_json(content_text=content_text)
        except ValueError:
            content_json = self._repair_content_json(request=request, content_text=content_text)
        return self._build_response(
            completion=completion,
            request=request,
            content_text=content_text,
            content_json=content_json,
        )

    def create_text_chat(self, *, request: OpenAIChatRequest) -> OpenAIChatResponse:
        completion = self._create_completion(request=request, include_response_format=False)
        content_text = self._extract_content_text(completion=completion)
        return self._build_response(
            completion=completion,
            request=request,
            content_text=content_text,
            content_json={},
        )

    def _create_completion(self, *, request: OpenAIChatRequest, include_response_format: bool) -> Any:
        request_kwargs: dict[str, Any] = {
            "model": request.model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "temperature": request.temperature,
            "max_completion_tokens": max(1, int(request.max_output_tokens)),
            "metadata": self._build_api_metadata(request=request) or None,
        }
        if include_response_format:
            request_kwargs["response_format"] = self._build_response_format(request=request)
        return self._client.chat.completions.create(**request_kwargs)

    def _build_response(
        self,
        *,
        completion: Any,
        request: OpenAIChatRequest,
        content_text: str,
        content_json: dict[str, Any],
    ) -> OpenAIChatResponse:
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
            "OpenAI chat completed.",
            extra={
                "model": response.model,
                "finish_reason": response.finish_reason,
                "usage": response.usage,
                "native_response_format": "json_object",
            },
        )
        return response

    @staticmethod
    def _normalize_base_url(base_url: str | None) -> str | None:
        normalized = (base_url or "").strip().rstrip("/")
        if not normalized:
            return None
        for suffix in (
            "/chat/completions",
            "/v1/chat/completions",
            "/completions",
        ):
            if normalized.endswith(suffix):
                trimmed = normalized[: -len(suffix)].rstrip("/")
                if suffix.startswith("/v1/"):
                    return f"{trimmed}/v1" if trimmed else "/v1"
                return trimmed or None
        return normalized

    def _build_response_format(self, *, request: OpenAIChatRequest) -> dict[str, Any]:
        del request
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
        normalized_text = DefaultOpenAIClient._normalize_structured_response_text(content_text)
        try:
            payload = json.loads(normalized_text)
        except json.JSONDecodeError as exc:
            candidate = DefaultOpenAIClient._extract_first_json_object(normalized_text)
            if candidate is None:
                raise ValueError(f"OpenAI response is not valid JSON: {normalized_text[:240]!r}") from exc
            try:
                payload = json.loads(candidate)
            except json.JSONDecodeError as nested_exc:
                raise ValueError(f"OpenAI response is not valid JSON: {normalized_text[:240]!r}") from nested_exc
        if not isinstance(payload, dict):
            raise ValueError("OpenAI response JSON must be an object")
        return payload

    @staticmethod
    def _normalize_structured_response_text(content_text: str) -> str:
        normalized = DefaultOpenAIClient._strip_think_tags(content_text.strip())
        normalized = DefaultOpenAIClient._strip_markdown_code_fence(normalized)
        return normalized.strip()

    @staticmethod
    def _strip_markdown_code_fence(content_text: str) -> str:
        normalized = content_text.strip()
        fence_match = re.search(r"```(?:json)?\s*(.*?)```", normalized, flags=re.DOTALL | re.IGNORECASE)
        if fence_match is not None:
            fenced_body = fence_match.group(1).strip()
            if fenced_body:
                return fenced_body
        if not normalized.startswith("```"):
            return normalized
        lines = normalized.splitlines()
        if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1]).strip()
        return normalized

    @staticmethod
    def _strip_think_tags(content_text: str) -> str:
        normalized = re.sub(r"<think>.*?</think>", "", content_text, flags=re.DOTALL | re.IGNORECASE).strip()
        if normalized:
            return normalized
        return content_text.strip()

    @staticmethod
    def _extract_first_json_object(content_text: str) -> str | None:
        start = content_text.find("{")
        if start < 0:
            return None
        depth = 0
        in_string = False
        escape = False
        for index in range(start, len(content_text)):
            char = content_text[index]
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
                continue
            if char == "{":
                depth += 1
                continue
            if char == "}":
                depth -= 1
                if depth == 0:
                    return content_text[start : index + 1]
        return None

    def _repair_content_json(self, *, request: OpenAIChatRequest, content_text: str) -> dict[str, Any]:
        logger.warning(
            "Structured response was not valid JSON. Attempting one repair pass.",
            extra={
                "model": request.model,
                "response_format": request.response_format,
            },
        )
        repair_prompt = self._build_json_repair_prompt(
            broken_text=content_text,
            response_schema=request.response_schema,
        )
        repair_response = self.create_text_chat(
            request=OpenAIChatRequest(
                model=request.model,
                system_prompt=(
                    "You repair malformed model outputs into valid JSON. "
                    "Return only one valid JSON object. "
                    "Do not include explanations, markdown, or think tags."
                ),
                user_prompt=repair_prompt,
                response_format="json_object",
                temperature=0.0,
                max_output_tokens=max(256, min(int(request.max_output_tokens), 1200)),
                metadata={
                    **dict(request.metadata),
                    "repair_pass": "true",
                },
            )
        )
        return self._extract_content_json(content_text=repair_response.content_text)

    @staticmethod
    def _build_json_repair_prompt(*, broken_text: str, response_schema: dict[str, Any]) -> str:
        schema_text = json.dumps(response_schema, ensure_ascii=True, indent=2) if response_schema else "{}"
        return (
            "Repair the following malformed output into one valid JSON object.\n"
            "Requirements:\n"
            "- Return JSON only.\n"
            "- Preserve the intended fields and values when possible.\n"
            "- If the text is truncated, complete the smallest valid JSON object that matches the schema.\n"
            "- Keep strings concise.\n\n"
            f"Schema:\n{schema_text}\n\n"
            f"Malformed output:\n{broken_text}"
        )


__all__ = [
    "OpenAIResponseFormat",
    "OpenAIChatRequest",
    "OpenAIChatResponse",
    "OpenAIClientPort",
    "DefaultOpenAIClient",
]
