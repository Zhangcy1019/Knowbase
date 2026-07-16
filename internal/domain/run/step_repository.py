"""Repository for run steps."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from internal.connectors.es.client import BaseElasticsearchClient
from internal.connectors.es.knowbase import build_knowbase_es_client
from internal.models.run import RunStep


class RunStepRepository:
    """Persist run steps for audit and replay."""

    def __init__(self, *, client: BaseElasticsearchClient, index_name: str):
        self._client = client
        self._index_name = index_name

    @classmethod
    def from_env(cls) -> "RunStepRepository":
        client, index_name = build_knowbase_es_client(
            index_env="CIAGENT_KNOWBASE_RUN_STEPS_INDEX",
            default_index="ci_knowbase_run_steps_v1",
        )
        return cls(client=client, index_name=index_name)

    def create_index(self) -> dict[str, Any]:
        if self._client.index_exists(index=self._index_name):
            return {"acknowledged": True, "index": self._index_name, "created": False}
        return self._client.create_index(index=self._index_name, body=self.build_index_mapping())

    def save(self, step: RunStep) -> RunStep:
        now = datetime.now(timezone.utc)
        persisted = step.model_copy(
            update={
                "step_id": step.step_id or f"{step.run_id}:step:{step.index}:{int(now.timestamp() * 1000)}",
                "created_at": step.created_at or now,
            }
        )
        self._client.index_document(
            index=self._index_name,
            doc_id=persisted.step_id,
            document=persisted.model_dump(mode="json"),
            refresh="wait_for",
        )
        return persisted

    def list_for_run(self, run_id: str) -> list[RunStep]:
        response = self._client.search_raw(
            index=self._index_name,
            body={
                "size": 500,
                "query": {"bool": {"filter": [{"term": {"run_id": run_id}}]}},
                "sort": [{"index": {"order": "asc"}}, {"created_at": {"order": "asc"}}],
            },
        )
        return [RunStep.model_validate(hit.get("_source") or {}) for hit in response.get("hits", {}).get("hits", [])]

    def delete_for_run(self, run_id: str) -> None:
        for step in self.list_for_run(run_id):
            self._client.delete_document(index=self._index_name, doc_id=step.step_id, refresh="wait_for")

    @staticmethod
    def build_index_mapping() -> dict[str, Any]:
        return {
            "mappings": {
                "properties": {
                    "step_id": {"type": "keyword"},
                    "run_id": {"type": "keyword"},
                    "index": {"type": "integer"},
                    "step_type": {"type": "keyword"},
                    "name": {"type": "keyword"},
                    "input": {"type": "flattened"},
                    "output": {"type": "flattened"},
                    "summary": {"type": "text"},
                    "created_at": {"type": "date"},
                }
            }
        }
