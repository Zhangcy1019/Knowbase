"""Repository for run artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from internal.connectors.es.client import BaseElasticsearchClient
from _es import build_knowbase_es_client
from internal.models.run import RunArtifact


class RunArtifactRepository:
    """Persist intermediate and final run artifacts."""

    def __init__(self, *, client: BaseElasticsearchClient, index_name: str):
        self._client = client
        self._index_name = index_name

    @classmethod
    def from_env(cls) -> "RunArtifactRepository":
        client, index_name = build_knowbase_es_client(
            index_env="CIAGENT_KNOWBASE_RUN_ARTIFACTS_INDEX",
            default_index="ci_knowbase_run_artifacts_v1",
        )
        return cls(client=client, index_name=index_name)

    def create_index(self) -> dict[str, Any]:
        if self._client.index_exists(index=self._index_name):
            return {"acknowledged": True, "index": self._index_name, "created": False}
        return self._client.create_index(index=self._index_name, body=self.build_index_mapping())

    def save(self, artifact: RunArtifact) -> RunArtifact:
        now = datetime.now(timezone.utc)
        persisted = artifact.model_copy(
            update={
                "artifact_id": artifact.artifact_id or f"{artifact.run_id}:{artifact.artifact_type}:{int(now.timestamp() * 1000)}",
                "created_at": artifact.created_at or now,
                "updated_at": now,
            }
        )
        self._client.index_document(
            index=self._index_name,
            doc_id=persisted.artifact_id,
            document=persisted.model_dump(mode="json"),
            refresh="wait_for",
        )
        return persisted

    def list_for_run(self, run_id: str) -> list[RunArtifact]:
        response = self._client.search_raw(
            index=self._index_name,
            body={
                "size": 200,
                "query": {"bool": {"filter": [{"term": {"run_id": run_id}}]}},
                "sort": [{"created_at": {"order": "asc"}}],
            },
        )
        return [RunArtifact.model_validate(hit.get("_source") or {}) for hit in response.get("hits", {}).get("hits", [])]

    def delete_for_run(self, run_id: str) -> None:
        for artifact in self.list_for_run(run_id):
            self._client.delete_document(index=self._index_name, doc_id=artifact.artifact_id, refresh="wait_for")

    @staticmethod
    def build_index_mapping() -> dict[str, Any]:
        return {
            "mappings": {
                "properties": {
                    "artifact_id": {"type": "keyword"},
                    "run_id": {"type": "keyword"},
                    "artifact_type": {"type": "keyword"},
                    "title": {"type": "text"},
                    "content": {"type": "flattened"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                }
            }
        }
