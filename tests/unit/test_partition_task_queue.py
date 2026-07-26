import asyncio
import unittest

from internal.backlog.tasks import PartitionTaskQueue


class PartitionTaskQueueTest(unittest.TestCase):
    def test_tasks_are_fifo_per_partition_and_parallel_across_partitions(self) -> None:
        async def scenario() -> None:
            queue = PartitionTaskQueue()
            started: list[tuple[str, str]] = []
            finished: list[tuple[str, str]] = []

            async def handler(task) -> None:
                started.append((task.partition, task.task_id))
                await asyncio.sleep(0)
                finished.append((task.partition, task.task_id))

            first = queue.enqueue(partition="CI", kind="case_input", handler=handler)
            second = queue.enqueue(partition="CI", kind="knowledge_drain", handler=handler)
            other = queue.enqueue(partition="EU", kind="case_input", handler=handler)
            await asyncio.gather(queue.wait_idle(partition="CI"), queue.wait_idle(partition="EU"))
            self.assertEqual(
                [task_id for partition, task_id in started if partition == "CI"],
                [first.task_id, second.task_id],
            )
            self.assertEqual(
                [task_id for partition, task_id in finished if partition == "CI"],
                [first.task_id, second.task_id],
            )
            self.assertEqual(other.status, "completed")
            self.assertIs(queue.get(first.task_id), first)

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
