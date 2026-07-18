"""Knowbase-specific Elasticsearch client factory helpers."""

from __future__ import annotations

from internal.connectors.es.client import BaseElasticsearchClient, ElasticsearchConfig
from internal.utils.config import KnowbaseElasticsearchConfig


def build_knowbase_es_client(
    *,
    es_config: KnowbaseElasticsearchConfig,
    index_name: str,
) -> tuple[BaseElasticsearchClient, str]:
    url = es_config.url.strip()
    api_key = es_config.api_key.strip()
    resolved_index_name = index_name.strip()
    verify_certs = bool(es_config.verify_certs)

    if not url:
        raise RuntimeError("Knowbase repositories require es.url")
    if not api_key:
        raise RuntimeError("Knowbase repositories require es.api_key")
    if not resolved_index_name:
        raise RuntimeError("Knowbase repositories require a non-empty index_name")

    client = BaseElasticsearchClient(
        ElasticsearchConfig(
            url=url,
            api_key=api_key,
            index=resolved_index_name,
            verify_certs=verify_certs,
        )
    )
    return client, resolved_index_name
