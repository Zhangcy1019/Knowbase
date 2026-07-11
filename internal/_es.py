"""Shared Elasticsearch helpers for knowbase repositories."""

from __future__ import annotations

import os

from internal.connectors.es.client import BaseElasticsearchClient, ElasticsearchConfig


def build_knowbase_es_client(*, index_env: str, default_index: str) -> tuple[BaseElasticsearchClient, str]:
    url = str(os.getenv("CIAGENT_KNOWBASE_ES_URL") or "").strip()
    api_key = str(os.getenv("CIAGENT_KNOWBASE_ES_API_KEY") or "").strip()
    index_name = str(os.getenv(index_env) or default_index).strip() or default_index
    verify_certs = str(os.getenv("CIAGENT_KNOWBASE_ES_VERIFY_CERTS") or "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    if not url:
        raise RuntimeError("Knowbase repositories require CIAGENT_KNOWBASE_ES_URL")
    if not api_key:
        raise RuntimeError("Knowbase repositories require CIAGENT_KNOWBASE_ES_API_KEY")

    client = BaseElasticsearchClient(
        ElasticsearchConfig(
            url=url,
            api_key=api_key,
            index=index_name,
            verify_certs=verify_certs,
        )
    )
    return client, index_name
