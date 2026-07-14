"""Runtime-config loading and environment projection for the app entrypoint."""

from __future__ import annotations

import os

from internal.utils.config import RuntimeConfig, load_runtime_config


def load_runtime_config_from_env() -> RuntimeConfig | None:
    config_path = (
        os.getenv("KNOWBASE_CONFIG_PATH")
        or os.getenv("CIAGENT_CONFIG_PATH")
        or "config/app.yaml"
    )
    try:
        runtime_cfg = load_runtime_config(config_path)
    except Exception:
        return None
    apply_runtime_config_to_env(runtime_cfg)
    return runtime_cfg


def apply_runtime_config_to_env(runtime_cfg: RuntimeConfig) -> None:
    os.environ.setdefault("CIAGENT_LEAD_AGENT_PROVIDER", runtime_cfg.llm.provider)
    os.environ.setdefault("CIAGENT_LEAD_AGENT_MODEL", runtime_cfg.llm.model)
    os.environ.setdefault("CIAGENT_LEAD_AGENT_TEMPERATURE", str(runtime_cfg.llm.temperature))
    if runtime_cfg.llm.openai_api_key:
        os.environ.setdefault("OPENAI_API_KEY", runtime_cfg.llm.openai_api_key)
    if runtime_cfg.llm.openai_base_url:
        os.environ.setdefault("OPENAI_BASE_URL", runtime_cfg.llm.openai_base_url)

    os.environ.setdefault("CIAGENT_KNOWBASE_ES_URL", runtime_cfg.es.url)
    os.environ.setdefault("CIAGENT_KNOWBASE_ES_API_KEY", runtime_cfg.es.api_key)
    os.environ.setdefault("CIAGENT_KNOWBASE_ES_VERIFY_CERTS", str(runtime_cfg.es.verify_certs).lower())
    os.environ.setdefault("CIAGENT_KNOWBASE_PARTITIONS_INDEX", runtime_cfg.es.partitions_index)
    os.environ.setdefault("CIAGENT_KNOWBASE_CASES_INDEX", runtime_cfg.es.cases_index)
    os.environ.setdefault("CIAGENT_KNOWBASE_AGENT_RUNS_INDEX", runtime_cfg.es.agent_runs_index)
    os.environ.setdefault("CIAGENT_KNOWBASE_RUN_STEPS_INDEX", runtime_cfg.es.run_steps_index)
    os.environ.setdefault("CIAGENT_KNOWBASE_RUN_ARTIFACTS_INDEX", runtime_cfg.es.run_artifacts_index)
    os.environ.setdefault(
        "CIAGENT_KNOWBASE_PARTITION_SEMANTIC_INDEX_INDEX",
        runtime_cfg.es.partition_semantic_index_index,
    )
    os.environ.setdefault(
        "CIAGENT_KNOWBASE_PARTITION_FACET_SCHEMAS_INDEX",
        runtime_cfg.es.partition_facet_schemas_index,
    )
    os.environ.setdefault(
        "CIAGENT_KNOWBASE_PARTITION_FACET_INDEX_INDEX",
        runtime_cfg.es.partition_facet_index_index,
    )
    os.environ.setdefault("CIAGENT_KNOWBASE_EVENT_RECORDS_INDEX", runtime_cfg.es.event_records_index)

    os.environ.setdefault("CIAGENT_KNOWBASE_DEFAULT_PARTITION", runtime_cfg.startup.default_partition)
    os.environ.setdefault("CIAGENT_KNOWBASE_EMBEDDING_PROVIDER", runtime_cfg.embedding.provider)
    os.environ.setdefault("CIAGENT_KNOWBASE_EMBEDDING_MODEL", runtime_cfg.embedding.model_name)
    os.environ.setdefault("CIAGENT_KNOWBASE_EMBEDDING_ENDPOINT", runtime_cfg.embedding.endpoint)
    os.environ.setdefault("CIAGENT_KNOWBASE_EMBEDDING_BASE_URL", runtime_cfg.embedding.base_url)
    os.environ.setdefault("CIAGENT_KNOWBASE_EMBEDDING_API_KEY", runtime_cfg.embedding.api_key)
    os.environ.setdefault("CIAGENT_KNOWBASE_EMBEDDING_DIMENSIONS", str(runtime_cfg.embedding.dimensions))
    os.environ.setdefault("CIAGENT_KNOWBASE_EMBEDDING_QUERY_PREFIX", runtime_cfg.embedding.query_prefix)
    os.environ.setdefault(
        "CIAGENT_KNOWBASE_EMBEDDING_DOCUMENT_PREFIX",
        runtime_cfg.embedding.document_prefix,
    )
    os.environ.setdefault(
        "CIAGENT_KNOWBASE_EMBEDDING_TIMEOUT_SECONDS",
        str(runtime_cfg.embedding.timeout_seconds),
    )
    os.environ.setdefault("KNOWBASE_UI_DEV_HOST", runtime_cfg.web.ui.dev_host)
    os.environ.setdefault("KNOWBASE_UI_DEV_PORT", str(runtime_cfg.web.ui.dev_port))
    proxy_host = runtime_cfg.startup.api_server.host
    if proxy_host in {"0.0.0.0", "::"}:
        proxy_host = "127.0.0.1"
    os.environ.setdefault(
        "KNOWBASE_API_PROXY_TARGET",
        f"http://{proxy_host}:{runtime_cfg.startup.api_server.port}",
    )
