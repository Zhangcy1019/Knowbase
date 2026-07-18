"""Shared helpers for integration tests."""

from __future__ import annotations

import os
from pathlib import Path

from internal.utils.config import RuntimeConfig, load_runtime_config
from internal.utils.logger import configure_logging


def resolve_test_config_path() -> Path:
    return Path("config/app.test.yaml")


def load_test_runtime_config() -> RuntimeConfig:
    return load_runtime_config(str(resolve_test_config_path()))


def bootstrap_test_runtime() -> RuntimeConfig:
    runtime_cfg = load_test_runtime_config()

    os.environ.setdefault("CIAGENT_STORAGE_BACKEND", runtime_cfg.storage.backend)
    os.environ.setdefault("CIAGENT_STORAGE_LOCAL_ROOT", runtime_cfg.storage.local_root)

    os.environ.setdefault("CIAGENT_LEAD_AGENT_PROVIDER", runtime_cfg.llm.provider)
    os.environ.setdefault("CIAGENT_LEAD_AGENT_MODEL", runtime_cfg.llm.model)
    os.environ.setdefault("CIAGENT_LEAD_AGENT_TEMPERATURE", str(runtime_cfg.llm.temperature))
    os.environ.setdefault("CIAGENT_LEAD_AGENT_MAX_OUTPUT_TOKENS", str(runtime_cfg.llm.max_output_tokens))
    os.environ.setdefault("CIAGENT_LEAD_AGENT_TIMEOUT_SECONDS", str(runtime_cfg.llm.timeout_seconds))
    if runtime_cfg.llm.openai_api_key:
        os.environ.setdefault("OPENAI_API_KEY", runtime_cfg.llm.openai_api_key)
    if runtime_cfg.llm.openai_base_url:
        os.environ.setdefault("OPENAI_BASE_URL", runtime_cfg.llm.openai_base_url)

    os.environ.setdefault("CIAGENT_KNOWBASE_EMBEDDING_PROVIDER", runtime_cfg.embedding.provider)
    os.environ.setdefault("CIAGENT_KNOWBASE_EMBEDDING_MODEL", runtime_cfg.embedding.model_name)
    os.environ.setdefault("CIAGENT_KNOWBASE_EMBEDDING_ENDPOINT", runtime_cfg.embedding.endpoint)
    os.environ.setdefault("CIAGENT_KNOWBASE_EMBEDDING_BASE_URL", runtime_cfg.embedding.base_url)
    os.environ.setdefault("CIAGENT_KNOWBASE_EMBEDDING_API_KEY", runtime_cfg.embedding.api_key)
    os.environ.setdefault("CIAGENT_KNOWBASE_EMBEDDING_DIMENSIONS", str(runtime_cfg.embedding.dimensions))
    os.environ.setdefault("CIAGENT_KNOWBASE_EMBEDDING_QUERY_PREFIX", runtime_cfg.embedding.query_prefix)
    os.environ.setdefault("CIAGENT_KNOWBASE_EMBEDDING_DOCUMENT_PREFIX", runtime_cfg.embedding.document_prefix)
    os.environ.setdefault("CIAGENT_KNOWBASE_EMBEDDING_TIMEOUT_SECONDS", str(runtime_cfg.embedding.timeout_seconds))

    configure_logging(runtime_cfg.logging)
    return runtime_cfg
