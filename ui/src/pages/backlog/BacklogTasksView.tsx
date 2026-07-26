import { useEffect, useState } from "react";

import { listBacklogTasks, type PartitionTaskResponse } from "../../shared/api";

import { BacklogTaskDetailPanel } from "./BacklogTaskDetailPanel";
import {
  BacklogTasksList,
  type TaskFilter,
} from "./BacklogTasksList";

export function BacklogTasksView({ activePartition }: { activePartition: string | null }) {
  const [tasks, setTasks] = useState<PartitionTaskResponse[]>([]);
  const [statusFilter, setStatusFilter] = useState<TaskFilter>("all");
  const [selectedTaskId, setSelectedTaskId] = useState("");
  const [loadingTasks, setLoadingTasks] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    let cancelled = false;
    if (!activePartition?.trim()) {
      setTasks([]);
      setSelectedTaskId("");
      setErrorMessage("");
      setLoadingTasks(false);
      return () => {
        cancelled = true;
      };
    }

    setLoadingTasks(true);
    setErrorMessage("");
    listBacklogTasks({ partition: activePartition })
      .then((items) => {
        if (cancelled) {
          return;
        }
        setTasks(items);
        setSelectedTaskId((current) => (
          current && items.some((item) => item.task_id === current)
            ? current
            : items[0]?.task_id ?? ""
        ));
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        setTasks([]);
        setSelectedTaskId("");
        setErrorMessage(error instanceof Error ? error.message : "Failed to load backlog tasks.");
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingTasks(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [activePartition]);

  const selectedTask = tasks.find((task) => task.task_id === selectedTaskId) ?? null;

  return (
    <section className="backlog-workbench">
      <BacklogTasksList
        activePartition={activePartition}
        tasks={tasks}
        selectedTaskId={selectedTaskId}
        statusFilter={statusFilter}
        loading={loadingTasks}
        errorMessage={errorMessage}
        onSelectTask={setSelectedTaskId}
        onChangeFilter={setStatusFilter}
      />
      <BacklogTaskDetailPanel task={selectedTask} />
    </section>
  );
}
