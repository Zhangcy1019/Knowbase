"""Configuration loading for the standalone knowbase service."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class LoggingConfig:
    level: str = "INFO"
    json_format: bool = False


@dataclass(frozen=True)
class LLMRuntimeConfig:
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_output_tokens: int = 1200
    timeout_seconds: int = 60
    openai_api_key: str | None = None
    openai_base_url: str | None = None


@dataclass(frozen=True)
class KnowbaseElasticsearchConfig:
    url: str
    api_key: str
    partitions_index: str
    cases_index: str
    agent_runs_index: str
    run_steps_index: str
    run_artifacts_index: str
    partition_semantic_index_index: str
    partition_facet_schemas_index: str
    partition_facet_index_index: str
    event_records_index: str
    verify_certs: bool = True


@dataclass(frozen=True)
class KnowbaseEmbeddingConfig:
    provider: str = "openai_compatible"
    model_name: str = ""
    endpoint: str = ""
    base_url: str = ""
    api_key: str = ""
    dimensions: int = 0
    query_prefix: str = "search_query: "
    document_prefix: str = "search_document: "
    timeout_seconds: int = 30


@dataclass(frozen=True)
class StorageRuntimeConfig:
    backend: str = "es"
    local_root: str = ".data/knowbase"


@dataclass(frozen=True)
class WebUIRuntimeConfig:
    enabled: bool = True
    mode: str = "build"
    auto_build: bool = True
    dist_dir: str = ""
    dev_host: str = "127.0.0.1"
    dev_port: int = 5173


@dataclass(frozen=True)
class WebRuntimeConfig:
    ui: WebUIRuntimeConfig


@dataclass(frozen=True)
class ApiServerRuntimeConfig:
    host: str = "0.0.0.0"
    port: int = 8000


@dataclass(frozen=True)
class StartupRuntimeConfig:
    api_server: ApiServerRuntimeConfig


@dataclass(frozen=True)
class RuntimeConfig:
    storage: StorageRuntimeConfig
    web: WebRuntimeConfig
    startup: StartupRuntimeConfig
    es: KnowbaseElasticsearchConfig
    embedding: KnowbaseEmbeddingConfig
    logging: LoggingConfig
    llm: LLMRuntimeConfig


def _load_yaml_config(config_path: str | None) -> dict[str, Any]:
    if not config_path:
        return {}
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"config file not found: {config_path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("config root must be a mapping object")
    return data


def _get_nested(config: dict[str, Any], *keys: str, default: Any = None) -> Any:
    value: Any = config
    for key in keys:
        if not isinstance(value, dict):
            return default
        value = value.get(key)
        if value is None:
            return default
    return value


def load_runtime_config(config_path: str | None) -> RuntimeConfig:
    file_cfg = _load_yaml_config(config_path)

    storage = StorageRuntimeConfig(
        backend=str(_get_nested(file_cfg, "storage", "backend", default="es")).strip().lower() or "es",
        local_root=str(_get_nested(file_cfg, "storage", "local_root", default=".data/knowbase")).strip()
        or ".data/knowbase",
    )

    web = WebRuntimeConfig(
        ui=WebUIRuntimeConfig(
            enabled=bool(_get_nested(file_cfg, "web", "ui", "enabled", default=True)),
            mode=str(_get_nested(file_cfg, "web", "ui", "mode", default="build")).strip().lower() or "build",
            auto_build=bool(_get_nested(file_cfg, "web", "ui", "auto_build", default=True)),
            dist_dir=str(_get_nested(file_cfg, "web", "ui", "dist_dir", default="")).strip(),
            dev_host=str(_get_nested(file_cfg, "web", "ui", "dev_host", default="127.0.0.1")).strip(),
            dev_port=int(_get_nested(file_cfg, "web", "ui", "dev_port", default=5173)),
        )
    )

    startup = StartupRuntimeConfig(
        api_server=ApiServerRuntimeConfig(
            host=str(_get_nested(file_cfg, "startup", "api", "host", default="0.0.0.0")).strip(),
            port=int(_get_nested(file_cfg, "startup", "api", "port", default=8000)),
        ),
    )

    es = KnowbaseElasticsearchConfig(
        url=str(_get_nested(file_cfg, "es", "url", default="")).strip(),
        api_key=str(_get_nested(file_cfg, "es", "api_key", default="")).strip(),
        partitions_index=str(_get_nested(file_cfg, "es", "partitions_index", default="knowbase_partitions_v1")).strip(),
        cases_index=str(_get_nested(file_cfg, "es", "cases_index", default="knowbase_cases_v1")).strip(),
        agent_runs_index=str(_get_nested(file_cfg, "es", "agent_runs_index", default="knowbase_agent_runs_v1")).strip(),
        run_steps_index=str(_get_nested(file_cfg, "es", "run_steps_index", default="knowbase_run_steps_v1")).strip(),
        run_artifacts_index=str(_get_nested(file_cfg, "es", "run_artifacts_index", default="knowbase_run_artifacts_v1")).strip(),
        partition_semantic_index_index=str(_get_nested(file_cfg, "es", "partition_semantic_index_index", default="knowbase_partition_semantic_index_v1")).strip(),
        partition_facet_schemas_index=str(_get_nested(file_cfg, "es", "partition_facet_schemas_index", default="knowbase_partition_facet_schemas_v1")).strip(),
        partition_facet_index_index=str(_get_nested(file_cfg, "es", "partition_facet_index_index", default="knowbase_partition_facet_index_v1")).strip(),
        event_records_index=str(_get_nested(file_cfg, "es", "event_records_index", default="knowbase_event_records_v1")).strip(),
        verify_certs=bool(_get_nested(file_cfg, "es", "verify_certs", default=True)),
    )

    embedding = KnowbaseEmbeddingConfig(
        provider=str(_get_nested(file_cfg, "embedding", "provider", default="openai_compatible")).strip(),
        model_name=str(_get_nested(file_cfg, "embedding", "model_name", default="")).strip(),
        endpoint=str(_get_nested(file_cfg, "embedding", "endpoint", default="")).strip(),
        base_url=str(_get_nested(file_cfg, "embedding", "base_url", default="")).strip(),
        api_key=str(_get_nested(file_cfg, "embedding", "api_key", default="")).strip(),
        dimensions=int(_get_nested(file_cfg, "embedding", "dimensions", default=0)),
        query_prefix=str(_get_nested(file_cfg, "embedding", "query_prefix", default="search_query: ")).strip(),
        document_prefix=str(_get_nested(file_cfg, "embedding", "document_prefix", default="search_document: ")).strip(),
        timeout_seconds=int(_get_nested(file_cfg, "embedding", "timeout_seconds", default=30)),
    )

    logging_config = LoggingConfig(
        level=str(_get_nested(file_cfg, "logging", "level", default="INFO")).strip(),
        json_format=bool(_get_nested(file_cfg, "logging", "json_format", default=False)),
    )

    llm_config = LLMRuntimeConfig(
        provider=str(_get_nested(file_cfg, "llm", "provider", default="openai")).strip(),
        model=str(_get_nested(file_cfg, "llm", "model", default="gpt-4o-mini")).strip(),
        temperature=float(_get_nested(file_cfg, "llm", "temperature", default=0.0)),
        max_output_tokens=int(_get_nested(file_cfg, "llm", "max_output_tokens", default=1200)),
        timeout_seconds=int(_get_nested(file_cfg, "llm", "timeout_seconds", default=60)),
        openai_api_key=str(_get_nested(file_cfg, "llm", "openai", "api_key", default="")).strip() or None,
        openai_base_url=str(_get_nested(file_cfg, "llm", "openai", "base_url", default="")).strip() or None,
    )

    missing: list[str] = []
    if storage.backend == "es":
        if not es.url:
            missing.append("es.url")
        if not es.api_key:
            missing.append("es.api_key")
    if not embedding.endpoint and not embedding.base_url:
        missing.append("embedding.endpoint or embedding.base_url")
    if not llm_config.openai_api_key:
        missing.append("llm.openai.api_key")
    if missing:
        raise ValueError(f"missing required config values: {', '.join(missing)}")

    return RuntimeConfig(
        storage=storage,
        web=web,
        startup=startup,
        es=es,
        embedding=embedding,
        logging=logging_config,
        llm=llm_config,
    )
