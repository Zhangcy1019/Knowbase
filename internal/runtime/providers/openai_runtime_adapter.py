"""Model-adapter contracts for runtime decision generation."""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from internal.runtime.llm.prompt_builder import RuntimeDecisionPrompt
from internal.runtime.providers.openai_client import (
    DefaultOpenAIClient,
    OpenAIChatRequest,
    OpenAIClientPort,
)


@dataclass(slots=True)
class RuntimeModelRequest:
    """Structured model request built from one runtime decision prompt."""

    model: str = ""
    system: str = ""
    instruction: str = ""
    response_schema: dict[str, Any] = field(default_factory=dict)
    temperature: float = 0.0
    max_output_tokens: int = 1200
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RuntimeModelResponse:
    """Structured model response returned to the decision parser."""

    payload: dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""
    model_name: str = ""
    finish_reason: str = ""
    usage: dict[str, int] = field(default_factory=dict)
    provider_metadata: dict[str, Any] = field(default_factory=dict)


class RuntimeModelAdapterPort(Protocol):
    """Bridge between prompt payloads and an actual model invocation."""

    def invoke(self, *, prompt: RuntimeDecisionPrompt) -> RuntimeModelResponse:
        ...


class OpenAIRuntimeModelAdapter:
    """Adapt runtime decision prompts onto a generic OpenAI-style client."""

    def __init__(self, *, client: OpenAIClientPort | None = None):
        if client is None:
            raise ValueError("OpenAIRuntimeModelAdapter requires an explicit OpenAIClientPort instance")
        self._client = client

    def invoke(self, *, prompt: RuntimeDecisionPrompt) -> RuntimeModelResponse:
        request = RuntimeModelRequest(
            model=prompt.model,
            system=prompt.system,
            instruction=self._build_instruction(prompt=prompt),
            response_schema=dict(prompt.response_schema),
            temperature=prompt.temperature,
            max_output_tokens=prompt.max_output_tokens,
            context=dict(prompt.context),
        )
        response = self._client.create_chat(
            request=OpenAIChatRequest(
                model=request.model or "gpt-5",
                system_prompt=request.system,
                user_prompt=request.instruction,
                response_format="json_schema" if request.response_schema else "json_object",
                response_schema=dict(request.response_schema),
                temperature=request.temperature,
                max_output_tokens=request.max_output_tokens,
                metadata={
                    "context": dict(request.context),
                    "schema_name": "runtime_decision_payload",
                },
            )
        )
        return RuntimeModelResponse(
            payload=dict(response.content_json),
            raw_text=response.content_text,
            model_name=response.model,
            finish_reason=response.finish_reason,
            usage=dict(response.usage),
            provider_metadata=dict(response.metadata),
        )

    @staticmethod
    def _build_instruction(*, prompt: RuntimeDecisionPrompt) -> str:
        instruction = prompt.instruction
        if prompt.response_schema:
            instruction = (
                f"{instruction}\n\n"
                "Response requirements:\n"
                "- Return a JSON object only.\n"
                "- Do not wrap the JSON in markdown fences.\n"
                f"- Follow this JSON schema:\n{json.dumps(prompt.response_schema, ensure_ascii=True, indent=2)}"
            )
        return instruction


class DefaultRuntimeModelAdapter(OpenAIRuntimeModelAdapter):
    """Default runtime adapter backed by the configured OpenAI client."""

    def __init__(self, *, client: OpenAIClientPort):
        super().__init__(client=client)

    @classmethod
    def from_env(cls) -> "DefaultRuntimeModelAdapter":
        return cls(client=DefaultOpenAIClient.from_env())


__all__ = [
    "RuntimeModelRequest",
    "RuntimeModelResponse",
    "RuntimeModelAdapterPort",
    "OpenAIRuntimeModelAdapter",
    "DefaultRuntimeModelAdapter",
]
