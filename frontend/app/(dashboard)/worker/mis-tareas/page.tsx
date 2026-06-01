"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { useToast } from "@/components/common/ToastProvider";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { CompleteTaskDialog } from "@/components/tasks/CompleteTaskDialog";
import { WorkerTaskCard } from "@/components/tasks/WorkerTaskCard";
import { WorkerTaskFilters } from "@/components/tasks/WorkerTaskFilters";
import { Input } from "@/components/ui/input";
import { MobileShell } from "@/components/worker/MobileShell";
import { ApiError } from "@/lib/api";
import { changeTaskStatus, completeTask, getMyTasks } from "@/lib/api/tasks";
import type { Task } from "@/types/task";

function isToday(value?: string | null) {
  if (!value) return false;
  const date = new Date(value);
  const now = new Date();
  return date.toDateString() === now.toDateString();
}

export default function WorkerTasksPage() {
  const { toast } = useToast();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [filter, setFilter] = useState("");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [completeTarget, setCompleteTarget] = useState<Task | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getMyTasks({ page: 1, limit: 100 });
      setTasks(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar la informacion.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const filtered = useMemo(() => tasks.filter((task) => {
    if (filter === "TODAY") return isToday(task.scheduled_at);
    if (!filter) return true;
    return task.status === filter;
  }).filter((task) => {
    const term = query.trim().toLowerCase();
    if (!term) return true;
    return (
      task.title.toLowerCase().includes(term) ||
      (task.event?.name || "").toLowerCase().includes(term) ||
      (task.zone?.name || "").toLowerCase().includes(term)
    );
  }), [filter, query, tasks]);

  async function startTask(task: Task) {
    setSaving(true);
    try {
      await changeTaskStatus(task.id, "IN_PROGRESS");
      toast({ tone: "success", title: "Tarea iniciada", description: task.title });
      await load();
    } catch (err) {
      const message = err instanceof ApiError ? err.detail : "No se pudo iniciar la tarea.";
      toast({ tone: "error", title: "No pudimos iniciar", description: message });
    } finally {
      setSaving(false);
    }
  }

  async function confirmComplete(observation?: string) {
    if (!completeTarget) return;
    setSaving(true);
    try {
      if (completeTarget.status === "PENDING") {
        await changeTaskStatus(completeTarget.id, "IN_PROGRESS");
      }
      await completeTask(completeTarget.id, { observation });
      toast({ tone: "success", title: "Tarea completada", description: completeTarget.title });
      setCompleteTarget(null);
      await load();
    } catch (err) {
      const status = err instanceof ApiError ? err.status : null;
      const detail = err instanceof ApiError ? err.detail : "No se pudo completar la tarea.";
      const friendly =
        status === 403 ? "No tienes permisos para completar esta tarea." :
        status === 404 ? "La tarea ya no existe o fue reasignada." :
        status === 409 ? "La tarea cambio de estado. Actualiza y reintenta." :
        status === 400 ? "Revisa la observacion e intenta nuevamente." :
        detail;
      toast({ tone: "error", title: "No pudimos completar", description: friendly });
    } finally {
      setSaving(false);
    }
  }

  return (
    <RoleGuard roles={["WORKER", "SUPERVISOR"]}>
      <MobileShell title="Mis tareas" description="Revisa, inicia y completa tu trabajo en terreno.">
        <Input placeholder="Buscar por titulo, evento o zona..." value={query} onChange={(e) => setQuery(e.target.value)} />
        <WorkerTaskFilters value={filter} onChange={setFilter} />
        {loading ? <LoadingState label="Cargando tareas..." /> : null}
        {error ? <ErrorState message={error} onRetry={load} /> : null}
        {!loading && !error && filtered.length === 0 ? <EmptyState title="No tienes tareas asignadas por ahora" description="Cuando el supervisor te asigne trabajo, aparecera aqui." /> : null}
        <div className="space-y-3">
          {filtered.map((task) => <WorkerTaskCard key={task.id} task={task} onComplete={setCompleteTarget} onStart={startTask} />)}
        </div>
        {completeTarget ? <CompleteTaskDialog loading={saving} onClose={() => setCompleteTarget(null)} onConfirm={confirmComplete} /> : null}
      </MobileShell>
    </RoleGuard>
  );
}
