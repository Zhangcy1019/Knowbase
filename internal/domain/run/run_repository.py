"""Repository for agent runs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from internal.connectors.es.client import BaseElasticsearchClient
from _es import build_knowbase_es_client
from internal.models.run import AgentRun


class AgentRunRepository:
    """Persist agent runs into a dedicated index."""

    def __init__(self, *, client: BaseElasticsearchClient, index_name: str):
        self._client = client
        self._index_name = index_name

    @classmethod
    def from_env(cls) -> "AgentRunRepository":
        client, index_name = build_knowbase_es_client(
            index_env="CIAGENT_KNOWBASE_AGENT_RUNS_INDEX",
            default_index="ci_knowbase_agent_runs_v1",
        )
        return cls(client=client, index_name=index_name)

    def create_index(self) -> dict[str, Any]:
        if self._client.index_exists(index=self._index_name):
            return {"acknowledged": True, "index": self._index_name, "created": False}
        return self._client.create_index(index=self._index_name, body=self.build_index_mapping())

    def save(self, run: AgentRun) -> AgentRun:
        now = datetime.now(timezone.utc)
        persisted = run.model_copy(
            update={
                "run_id": run.run_id or f"run-{int(now.timestamp() * 1000)}",
                "created_at": run.created_at or now,
                "updated_at": now,
            }
        )
        self._client.index_document(
            index=self._index_name,
            doc_id=persisted.run_id,
            document=persisted.model_dump(mode="json"),
            refresh="wait_for",
        )
        return persisted

    def get(self, run_id: str) -> AgentRun | None:
        if not self._client.document_exists(index=self._index_name, doc_id=run_id):
            return None
        response = self._client.get_document(index=self._index_name, doc_id=run_id)
        return AgentRun.model_validate(response.get("_source") or {})

    def list(self, *, partition: str = "", status: str = "") -> list[AgentRun]:
        filters: list[dict[str, Any]] = []
        if partition:
            filters.append({"term": {"partition": partition}})
        if status:
            filters.append({"term": {"status": status}})
        query: dict[str, Any] = {"bool": {"filter": filters}} if filters else {"match_all": {}}
        response = self._client.search_raw(
            index=self._index_name,
            body={"size": 200, "query": query, "sort": [{"created_at": {"order": "desc"}}]},
        )
        return [AgentRun.model_validate(hit.get("_source") or {}) for hit in response.get("hits", {}).get("hits", [])]

    def delete(self, run_id: str) -> None:
        self._client.delete_document(index=self._index_name, doc_id=run_id, refresh="wait_for")

    @staticmethod
    def build_index_mapping() -> dict[str, Any]:
        return {
            "mappings": {
                "properties": {
                    "run_id": {"type": "keyword"},
                    "partition": {"type": "keyword"},
                    "agent_id": {"type": "keyword"},
                    "mode": {"type": "keyword"},
                    "status": {"type": "keyword"},
                    "source_type": {"type": "keyword"},
                    "source_event_type": {"type": "keyword"},
                    "source_event_id": {"type": "keyword"},
                    "source_ref": {"type": "keyword"},
                    "objective": {"type": "text"},
                    "reasoning_summary": {"type": "text"},
                    "final_summary": {"type": "text"},
                    "planning_context": {"type": "flattened"},
                    "tool_whitelist": {"type": "keyword"},
                    "skill_whitelist": {"type": "keyword"},
                    "step_count": {"type": "integer"},
                    "tool_call_count": {"type": "integer"},
                    "skill_call_count": {"type": "integer"},
                    "max_steps": {"type": "integer"},
                    "max_tool_calls": {"type": "integer"},
                    "max_skill_calls": {"type": "integer"},
                    "risk_level": {"type": "keyword"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                    "finished_at": {"type": "date"},
                }
            }
        }
