"use client";

import { AlertTriangle, CheckCircle, Eye, Pencil, PlayCircle, XCircle } from "lucide-react";

import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { PriorityBadge } from "@/components/tasks/PriorityBadge";
import { TaskStatusBadge } from "@/components/tasks/TaskStatusBadge";
import { Button } from "@/components/ui/button";
import type { Task, TaskStatus } from "@/types/task";

function dateTime(value?: string | null) {
  return value ? new Intl.DateTimeFormat("es-CL", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)) : "-";
}

export function TaskTable({
  tasks,
  loading,
  error,
  canManage,
  canStartStatus = true,
  canObserveStatus = false,
  onView,
  onEdit,
  onStatus,
  onComplete
}: {
  tasks: Task[];
  loading?: boolean;
  error?: string | null;
  canManage: boolean;
  canStartStatus?: boolean;
  canObserveStatus?: boolean;
  onView: (task: Task) => void;
  onEdit: (task: Task) => void;
  onStatus: (task: Task, status: TaskStatus) => void;
  onComplete: (task: Task) => void;
}) {
  const columns: DataTableColumn<Task>[] = [
    { key: "title", header: "Tarea", cell: (task) => <span className="font-semibold">{task.title}</span> },
    { key: "zone", header: "Zona", cell: (task) => task.zone?.name || "-" },
    { key: "assignee", header: "Responsable", cell: (task) => task.assignee?.full_name || task.assigned_user?.full_name || "Sin asignar" },
    { key: "status", header: "Estado", cell: (task) => <TaskStatusBadge status={task.status} /> },
    { key: "priority", header: "Prioridad", cell: (task) => <PriorityBadge priority={task.priority} /> },
    { key: "scheduled", header: "Programada", cell: (task) => dateTime(task.scheduled_at) },
    { key: "completed", header: "Completada", cell: (task) => dateTime(task.completed_at) }
  ];

  return (
    <DataTable
      actions={(task) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="secondary" onClick={() => onView(task)}><Eye className="h-4 w-4" /></Button>
          {canManage ? <Button size="sm" variant="secondary" onClick={() => onEdit(task)}><Pencil className="h-4 w-4" /></Button> : null}
          {canManage && canStartStatus && task.status === "PENDING" ? <Button size="sm" variant="ghost" onClick={() => onStatus(task, "IN_PROGRESS")}><PlayCircle className="h-4 w-4" /></Button> : null}
          {canManage && canObserveStatus && task.status !== "COMPLETED" && task.status !== "OBSERVED" && task.status !== "CANCELLED" ? <Button size="sm" variant="ghost" onClick={() => onStatus(task, "OBSERVED")}><AlertTriangle className="h-4 w-4" /></Button> : null}
          {canManage && canObserveStatus && task.status !== "COMPLETED" && task.status !== "CANCELLED" ? <Button size="sm" variant="ghost" onClick={() => onStatus(task, "CANCELLED")}><XCircle className="h-4 w-4" /></Button> : null}
          {canManage && task.status !== "COMPLETED" ? <Button size="sm" variant="ghost" onClick={() => onComplete(task)}><CheckCircle className="h-4 w-4" /></Button> : null}
        </div>
      )}
      columns={columns}
      data={tasks}
      emptyDescription="Crea tareas para coordinar el trabajo en terreno por zona y responsable."
      emptyTitle="Sin tareas"
      error={error}
      getRowKey={(task) => task.id}
      loading={loading}
    />
  );
}
