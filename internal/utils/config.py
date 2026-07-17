"""Configuration loading for the standalone knowbase service."""

from __future__ import annotations

import os
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
    text_root: str = ".data/knowbase"


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
    default_partition: str = "CI"


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


def _str_env(name: str, default: str = "") -> str:
    return str(os.getenv(name, default) or "").strip()


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw and raw.strip() else default


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw and raw.strip() else default


def _csv_env(name: str) -> tuple[str, ...]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return ()
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def load_runtime_config(config_path: str | None) -> RuntimeConfig:
    file_cfg = _load_yaml_config(config_path)

    storage = StorageRuntimeConfig(
        backend=_str_env(
            "CIAGENT_STORAGE_BACKEND",
            str(_get_nested(file_cfg, "storage", "backend", default="es")),
        ).lower()
        or "es",
        text_root=_str_env(
            "CIAGENT_STORAGE_TEXT_ROOT",
            str(_get_nested(file_cfg, "storage", "text_root", default=".data/knowbase")),
        )
        or ".data/knowbase",
    )

    web = WebRuntimeConfig(
        ui=WebUIRuntimeConfig(
            enabled=_bool_env(
                "CIAGENT_WEB_UI_ENABLED",
                bool(_get_nested(file_cfg, "web", "ui", "enabled", default=True)),
            ),
            mode=_str_env(
                "CIAGENT_WEB_UI_MODE",
                str(_get_nested(file_cfg, "web", "ui", "mode", default="build")),
            ).lower()
            or "build",
            auto_build=_bool_env(
                "CIAGENT_WEB_UI_AUTO_BUILD",
                bool(_get_nested(file_cfg, "web", "ui", "auto_build", default=True)),
            ),
            dist_dir=_str_env(
                "CIAGENT_WEB_UI_DIST_DIR",
                str(_get_nested(file_cfg, "web", "ui", "dist_dir", default="")),
            ),
            dev_host=_str_env(
                "CIAGENT_WEB_UI_DEV_HOST",
                str(_get_nested(file_cfg, "web", "ui", "dev_host", default="127.0.0.1")),
            ),
            dev_port=_int_env(
                "CIAGENT_WEB_UI_DEV_PORT",
                int(_get_nested(file_cfg, "web", "ui", "dev_port", default=5173)),
            ),
        )
    )

    startup = StartupRuntimeConfig(
        api_server=ApiServerRuntimeConfig(
            host=_str_env(
                "CIAGENT_API_HOST",
                str(_get_nested(file_cfg, "startup", "api", "host", default="0.0.0.0")),
            ),
            port=_int_env(
                "CIAGENT_API_PORT",
                int(_get_nested(file_cfg, "startup", "api", "port", default=8000)),
            ),
        ),
        default_partition=_str_env(
            "CIAGENT_KNOWBASE_DEFAULT_PARTITION",
            str(_get_nested(file_cfg, "startup", "default_partition", default="CI")),
        ),
    )

    es = KnowbaseElasticsearchConfig(
        url=_str_env("CIAGENT_KNOWBASE_ES_URL", str(_get_nested(file_cfg, "es", "url", default=""))),
        api_key=_str_env("CIAGENT_KNOWBASE_ES_API_KEY", str(_get_nested(file_cfg, "es", "api_key", default=""))),
        partitions_index=_str_env(
            "CIAGENT_KNOWBASE_PARTITIONS_INDEX",
            str(_get_nested(file_cfg, "es", "partitions_index", default="ci_knowbase_partitions_v1")),
        ),
        cases_index=_str_env(
            "CIAGENT_KNOWBASE_CASES_INDEX",
            str(_get_nested(file_cfg, "es", "cases_index", default="ci_knowbase_cases_v1")),
        ),
        agent_runs_index=_str_env(
            "CIAGENT_KNOWBASE_AGENT_RUNS_INDEX",
            str(_get_nested(file_cfg, "es", "agent_runs_index", default="ci_knowbase_agent_runs_v1")),
        ),
        run_steps_index=_str_env(
            "CIAGENT_KNOWBASE_RUN_STEPS_INDEX",
            str(_get_nested(file_cfg, "es", "run_steps_index", default="ci_knowbase_run_steps_v1")),
        ),
        run_artifacts_index=_str_env(
            "CIAGENT_KNOWBASE_RUN_ARTIFACTS_INDEX",
            str(_get_nested(file_cfg, "es", "run_artifacts_index", default="ci_knowbase_run_artifacts_v1")),
        ),
        partition_semantic_index_index=_str_env(
            "CIAGENT_KNOWBASE_PARTITION_SEMANTIC_INDEX_INDEX",
            str(_get_nested(file_cfg, "es", "partition_semantic_index_index", default="ci_knowbase_partition_semantic_index_v1")),
        ),
        partition_facet_schemas_index=_str_env(
            "CIAGENT_KNOWBASE_PARTITION_FACET_SCHEMAS_INDEX",
            str(_get_nested(file_cfg, "es", "partition_facet_schemas_index", default="ci_knowbase_partition_facet_schemas_v1")),
        ),
        partition_facet_index_index=_str_env(
            "CIAGENT_KNOWBASE_PARTITION_FACET_INDEX_INDEX",
            str(_get_nested(file_cfg, "es", "partition_facet_index_index", default="ci_knowbase_partition_facet_index_v1")),
        ),
        event_records_index=_str_env(
            "CIAGENT_KNOWBASE_EVENT_RECORDS_INDEX",
            str(_get_nested(file_cfg, "es", "event_records_index", default="ci_knowbase_event_records_v1")),
        ),
        verify_certs=_bool_env(
            "CIAGENT_KNOWBASE_ES_VERIFY_CERTS",
            bool(_get_nested(file_cfg, "es", "verify_certs", default=True)),
        ),
    )

    embedding = KnowbaseEmbeddingConfig(
        provider=_str_env(
            "CIAGENT_KNOWBASE_EMBEDDING_PROVIDER",
            str(_get_nested(file_cfg, "embedding", "provider", default="openai_compatible")),
        ),
        model_name=_str_env(
            "CIAGENT_KNOWBASE_EMBEDDING_MODEL",
            str(_get_nested(file_cfg, "embedding", "model_name", default="")),
        ),
        endpoint=_str_env(
            "CIAGENT_KNOWBASE_EMBEDDING_ENDPOINT",
            str(_get_nested(file_cfg, "embedding", "endpoint", default="")),
        ),
        base_url=_str_env(
            "CIAGENT_KNOWBASE_EMBEDDING_BASE_URL",
            str(_get_nested(file_cfg, "embedding", "base_url", default="")),
        ),
        api_key=_str_env(
            "CIAGENT_KNOWBASE_EMBEDDING_API_KEY",
            str(_get_nested(file_cfg, "embedding", "api_key", default="")),
        ),
        dimensions=_int_env(
            "CIAGENT_KNOWBASE_EMBEDDING_DIMENSIONS",
            int(_get_nested(file_cfg, "embedding", "dimensions", default=0)),
        ),
        query_prefix=_str_env(
            "CIAGENT_KNOWBASE_EMBEDDING_QUERY_PREFIX",
            str(_get_nested(file_cfg, "embedding", "query_prefix", default="search_query: ")),
        ),
        document_prefix=_str_env(
            "CIAGENT_KNOWBASE_EMBEDDING_DOCUMENT_PREFIX",
            str(_get_nested(file_cfg, "embedding", "document_prefix", default="search_document: ")),
        ),
        timeout_seconds=_int_env(
            "CIAGENT_KNOWBASE_EMBEDDING_TIMEOUT_SECONDS",
            int(_get_nested(file_cfg, "embedding", "timeout_seconds", default=30)),
        ),
    )

    logging_config = LoggingConfig(
        level=_str_env("CIAGENT_LOG_LEVEL", str(_get_nested(file_cfg, "logging", "level", default="INFO"))),
        json_format=_bool_env(
            "CIAGENT_LOG_JSON",
            bool(_get_nested(file_cfg, "logging", "json_format", default=False)),
        ),
    )

    llm_config = LLMRuntimeConfig(
        provider=_str_env("CIAGENT_LEAD_AGENT_PROVIDER", str(_get_nested(file_cfg, "llm", "provider", default="openai"))),
        model=_str_env("CIAGENT_LEAD_AGENT_MODEL", str(_get_nested(file_cfg, "llm", "model", default="gpt-4o-mini"))),
        temperature=_float_env(
            "CIAGENT_LEAD_AGENT_TEMPERATURE",
            float(_get_nested(file_cfg, "llm", "temperature", default=0.0)),
        ),
        max_output_tokens=_int_env(
            "CIAGENT_LEAD_AGENT_MAX_OUTPUT_TOKENS",
            int(_get_nested(file_cfg, "llm", "max_output_tokens", default=1200)),
        ),
        timeout_seconds=_int_env(
            "CIAGENT_LEAD_AGENT_TIMEOUT_SECONDS",
            int(_get_nested(file_cfg, "llm", "timeout_seconds", default=60)),
        ),
        openai_api_key=_str_env("OPENAI_API_KEY", str(_get_nested(file_cfg, "llm", "openai", "api_key", default=""))) or None,
        openai_base_url=_str_env("OPENAI_BASE_URL", str(_get_nested(file_cfg, "llm", "openai", "base_url", default=""))) or None,
    )

    missing: list[str] = []
    if storage.backend == "es":
        if not es.url:
            missing.append("CIAGENT_KNOWBASE_ES_URL")
        if not es.api_key:
            missing.append("CIAGENT_KNOWBASE_ES_API_KEY")
    if not startup.default_partition:
        missing.append("CIAGENT_KNOWBASE_DEFAULT_PARTITION")
    if not embedding.endpoint and not embedding.base_url:
        missing.append("CIAGENT_KNOWBASE_EMBEDDING_ENDPOINT or CIAGENT_KNOWBASE_EMBEDDING_BASE_URL")
    if not llm_config.openai_api_key:
        missing.append("OPENAI_API_KEY")
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
