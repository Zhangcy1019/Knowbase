"""OpenAI-compatible remote embedding provider."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Protocol

import requests

from internal.utils.logger import get_logger


logger = get_logger(__name__)


@dataclass(frozen=True)
class EmbeddingConfig:
    provider: str = "openai_compatible"
    model_name: str = ""
    endpoint: str = ""
    base_url: str = ""
    api_key: str = ""
    dimensions: int = 0
    query_prefix: str = "search_query: "
    document_prefix: str = "search_document: "
    timeout_seconds: int = 30


class EmbeddingProvider(Protocol):
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, text: str) -> list[float]:
        ...


class OpenAICompatibleEmbeddingProvider:
    """Call a remote OpenAI-compatible embeddings service via HTTP."""

    def __init__(self, config: EmbeddingConfig):
        self._config = config
        self._endpoint = self._resolve_endpoint(config)
        self.dimensions = max(0, int(config.dimensions))
        self._session = requests.Session()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        prefixed = [self._prefix_document(text) for text in texts]
        payload = self._build_payload(prefixed)
        response = self._post_embeddings(payload)
        return self._parse_embeddings_response(response, expected_count=len(prefixed))

    def embed_query(self, text: str) -> list[float]:
        payload = self._build_payload(self._prefix_query(text))
        response = self._post_embeddings(payload)
        vectors = self._parse_embeddings_response(response, expected_count=1)
        return vectors[0]

    @staticmethod
    def _resolve_endpoint(config: EmbeddingConfig) -> str:
        if config.endpoint.strip():
            return config.endpoint.strip()

        base_url = config.base_url.strip().rstrip("/")
        if not base_url:
            raise RuntimeError(
                "Knowbase embeddings require CIAGENT_KNOWBASE_EMBEDDING_ENDPOINT "
                "or CIAGENT_KNOWBASE_EMBEDDING_BASE_URL"
            )
        if base_url.endswith("/embeddings"):
            return base_url
        if base_url.endswith("/v1"):
            return f"{base_url}/embeddings"
        return f"{base_url}/v1/embeddings"

    def _build_payload(self, input_value: str | list[str]) -> dict[str, Any]:
        payload: dict[str, Any] = {"input": input_value}
        if self._config.model_name.strip():
            payload["model"] = self._config.model_name.strip()
        return payload

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._config.api_key.strip():
            headers["Authorization"] = f"Bearer {self._config.api_key.strip()}"
        return headers

    def _post_embeddings(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._session.post(
                self._endpoint,
                json=payload,
                headers=self._build_headers(),
                timeout=self._config.timeout_seconds,
            )
        except requests.RequestException as exc:
            logger.exception(
                "Embedding request failed",
                extra={"endpoint": self._endpoint, "error": str(exc)},
            )
            raise RuntimeError(f"Embedding request failed: {exc}") from exc

        if response.status_code >= 400:
            body = response.text[:500]
            logger.error(
                "Embedding service returned error",
                extra={"endpoint": self._endpoint, "status_code": response.status_code, "body": body},
            )
            raise RuntimeError(f"Embedding service error {response.status_code}: {body}")

        try:
            data = response.json()
        except ValueError as exc:
            logger.exception("Embedding service returned invalid JSON", extra={"endpoint": self._endpoint})
            raise RuntimeError("Embedding service returned invalid JSON") from exc
        if not isinstance(data, dict):
            raise RuntimeError("Embedding service returned a non-object JSON payload")
        return data

    def _parse_embeddings_response(self, response: dict[str, Any], *, expected_count: int) -> list[list[float]]:
        raw_items = response.get("data")
        if not isinstance(raw_items, list):
            raise RuntimeError("Embedding service response missing 'data' list")
        items = sorted(
            (item for item in raw_items if isinstance(item, dict)),
            key=lambda item: int(item.get("index", 0)),
        )
        if len(items) != expected_count:
            raise RuntimeError(
                f"Embedding response count mismatch: expected {expected_count}, got {len(items)}"
            )
        vectors = [self._coerce_vector(item.get("embedding")) for item in items]
        return vectors

    def _prefix_document(self, text: str) -> str:
        text = text.strip()
        return f"{self._config.document_prefix}{text}" if text else self._config.document_prefix.strip()

    def _prefix_query(self, text: str) -> str:
        text = text.strip()
        return f"{self._config.query_prefix}{text}" if text else self._config.query_prefix.strip()

    def _coerce_vector(self, vector: Any) -> list[float]:
        if not isinstance(vector, list):
            raise RuntimeError("Embedding service response missing embedding vector")
        normalized = [float(value) for value in vector]
        if self.dimensions <= 0:
            self.dimensions = len(normalized)
            return normalized
        if len(normalized) != self.dimensions:
            raise RuntimeError(
                f"Embedding dimension mismatch: expected {self.dimensions}, got {len(normalized)}"
            )
        return normalized


def load_embedding_config_from_env() -> EmbeddingConfig:
    return EmbeddingConfig(
        provider=str(os.getenv("CIAGENT_KNOWBASE_EMBEDDING_PROVIDER") or "openai_compatible").strip()
        or "openai_compatible",
        model_name=str(os.getenv("CIAGENT_KNOWBASE_EMBEDDING_MODEL") or "").strip(),
        endpoint=str(os.getenv("CIAGENT_KNOWBASE_EMBEDDING_ENDPOINT") or "").strip(),
        base_url=str(os.getenv("CIAGENT_KNOWBASE_EMBEDDING_BASE_URL") or "").strip(),
        api_key=str(os.getenv("CIAGENT_KNOWBASE_EMBEDDING_API_KEY") or "").strip(),
        dimensions=int(str(os.getenv("CIAGENT_KNOWBASE_EMBEDDING_DIMENSIONS") or "0").strip() or "0"),
        query_prefix=str(os.getenv("CIAGENT_KNOWBASE_EMBEDDING_QUERY_PREFIX") or "search_query: "),
        document_prefix=str(os.getenv("CIAGENT_KNOWBASE_EMBEDDING_DOCUMENT_PREFIX") or "search_document: "),
        timeout_seconds=int(str(os.getenv("CIAGENT_KNOWBASE_EMBEDDING_TIMEOUT_SECONDS") or "30").strip() or "30"),
    )


@lru_cache(maxsize=1)
def create_embedding_provider() -> EmbeddingProvider:
    config = load_embedding_config_from_env()
    if config.provider != "openai_compatible":
        raise RuntimeError(f"Unsupported knowledge embedding provider: {config.provider}")
    return OpenAICompatibleEmbeddingProvider(config)
