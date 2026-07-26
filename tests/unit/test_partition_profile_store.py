"""Partition profile persistence invariants.

Run:
    cd /home/zcy/Project/knowbase
    python3 -m unittest tests.unit.test_partition_profile_store
"""

from datetime import datetime, timedelta, timezone
import unittest

from internal.domain.partition.store import PartitionProfileStore
from internal.models import PartitionFacetDefinition, PartitionFacetSchema
from internal.models.facet import PartitionFacetSchemaDocument


class _SchemaRepository:
    def __init__(self, document: PartitionFacetSchemaDocument) -> None:
        self.document = document
        self.upsert_count = 0

    def get(self, partition_name: str):
        return self.document if self.document.partition_name == partition_name else None

    def upsert(self, document):
        self.upsert_count += 1
        self.document = document
        return document


class _UnusedRepository:
    pass


class PartitionProfileStoreTest(unittest.TestCase):
    def test_save_same_schema_is_a_no_op(self) -> None:
        created_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        updated_at = datetime.now(timezone.utc)
        schema = PartitionFacetSchema(
            definitions=[PartitionFacetDefinition(key="domain")],
            metadata={"version": 1},
        )
        repository = _SchemaRepository(
            PartitionFacetSchemaDocument(
                partition_name="CI",
                facet_schema=schema,
                created_at=created_at,
                updated_at=updated_at,
            )
        )
        store = PartitionProfileStore(
            facet_index_repository=_UnusedRepository(),
            facet_schema_repository=repository,
            semantic_index_repository=_UnusedRepository(),
        )

        result = store.save_facet_schema(partition_name="CI", facet_schema=schema)

        self.assertIs(result, repository.document)
        self.assertEqual(result.updated_at, updated_at)
        self.assertEqual(repository.upsert_count, 0)


if __name__ == "__main__":
    unittest.main()
