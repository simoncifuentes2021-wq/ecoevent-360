"use client";

import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { KpiCard } from "@/components/dashboard/KpiCard";
import { TaskStatusBadge } from "@/components/tasks/TaskStatusBadge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { getEventTasks } from "@/lib/api/tasks";
import type { Task } from "@/types/task";
import { CheckCircle, ClipboardList, Clock } from "lucide-react";

function dateTime(value?: string | null) {
  return value ? new Intl.DateTimeFormat("es-CL", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)) : "-";
}

export function ClientOperationalProgressTab({ eventId }: { eventId: string }) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await getEventTasks(eventId);
        setTasks(data.items);
      } catch (err) {
        setError(err instanceof Error ? err.message : "No se pudo cargar el avance operativo.");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [eventId]);

  const completed = tasks.filter((task) => task.status === "COMPLETED").length;
  const inProgress = tasks.filter((task) => task.status === "IN_PROGRESS").length;
  const pending = tasks.filter((task) => task.status === "PENDING").length;
  const completion = tasks.length ? Math.round((completed / tasks.length) * 100) : 0;
  const chartData = useMemo(() => ["PENDING", "IN_PROGRESS", "COMPLETED", "OBSERVED", "CANCELLED"].map((status) => ({ name: status, value: tasks.filter((task) => task.status === status).length })), [tasks]);

  const columns: DataTableColumn<Task>[] = [
    { key: "title", header: "Tarea", cell: (task) => <span className="font-semibold">{task.title}</span> },
    { key: "zone", header: "Zona", cell: (task) => task.zone?.name || "-" },
    { key: "status", header: "Estado", cell: (task) => <TaskStatusBadge status={task.status} /> },
    { key: "scheduled", header: "Programada", cell: (task) => dateTime(task.scheduled_at) },
    { key: "completed", header: "Completada", cell: (task) => dateTime(task.completed_at) }
  ];

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-4">
        <KpiCard description={`${completion}% cumplimiento`} icon={ClipboardList} title="Total tareas" value={tasks.length} />
        <KpiCard description="Finalizadas" icon={CheckCircle} title="Completadas" tone="lime" value={completed} />
        <KpiCard description="En ejecucion" icon={Clock} title="En progreso" tone="blue" value={inProgress} />
        <KpiCard description="Por ejecutar" icon={Clock} title="Pendientes" value={pending} />
      </div>
      <Card>
        <CardHeader><h3 className="font-semibold">Tareas por estado</h3></CardHeader>
        <CardContent className="h-72">
          <ResponsiveContainer height="100%" width="100%"><BarChart data={chartData}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="name" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="value" fill="#0f766e" radius={[8, 8, 0, 0]} /></BarChart></ResponsiveContainer>
        </CardContent>
      </Card>
      <DataTable columns={columns} data={tasks} emptyDescription="Aun no hay tareas visibles para este evento." emptyTitle="Sin tareas" error={error} getRowKey={(task) => task.id} loading={loading} />
    </div>
  );
}
