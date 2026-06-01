"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Plus } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { FilterSelect } from "@/components/common/FilterSelect";
import { SearchInput } from "@/components/common/SearchInput";
import { useToast } from "@/components/common/ToastProvider";
import { CompleteTaskDialog } from "@/components/tasks/CompleteTaskDialog";
import { TaskDetailPanel } from "@/components/tasks/TaskDetailPanel";
import { TaskFormModal } from "@/components/tasks/TaskFormModal";
import { TaskTable } from "@/components/tasks/TaskTable";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { getEventStaff } from "@/lib/api/staff";
import { changeTaskStatus, completeTask, createTask, getEventTasks, updateTask } from "@/lib/api/tasks";
import { getEventZones } from "@/lib/api/zones";
import { canManageTasks } from "@/lib/permissions";
import type { UserRole } from "@/types/roles";
import type { EventStaff } from "@/types/staff";
import type { Priority, Task, TaskCreate, TaskStatus, TaskUpdate } from "@/types/task";
import type { Zone } from "@/types/zone";

export function TasksTab({ eventId, role }: { eventId: string; role?: UserRole | null }) {
  const { toast } = useToast();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);
  const [staff, setStaff] = useState<EventStaff[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formTask, setFormTask] = useState<Task | null | undefined>();
  const [detailTask, setDetailTask] = useState<Task | null>(null);
  const [completeTarget, setCompleteTarget] = useState<Task | null>(null);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [zoneId, setZoneId] = useState("");
  const [assigneeId, setAssigneeId] = useState("");
  const canManage = canManageTasks(role);

  function attachStaffUsers(taskItems: Task[], staffItems: EventStaff[]) {
    const staffByUserId = new Map(staffItems.map((item) => [item.user_id, item.user]));
    return taskItems.map((task) => {
      if (!task.assigned_to || task.assignee || task.assigned_user) return task;
      const user = staffByUserId.get(task.assigned_to);
      return user ? { ...task, assignee: user } : task;
    });
  }

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [taskData, zoneData, staffData] = await Promise.all([getEventTasks(eventId), getEventZones(eventId), getEventStaff(eventId)]);
      setTasks(attachStaffUsers(taskData.items, staffData));
      setZones(zoneData);
      setStaff(staffData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar la informacion.");
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => { void load(); }, [load]);

  const filtered = useMemo(() => tasks.filter((task) => {
    const assignee = task.assignee?.full_name || task.assigned_user?.full_name || "";
    return (!q || `${task.title} ${assignee}`.toLowerCase().includes(q.toLowerCase()))
      && (!status || task.status === status)
      && (!priority || task.priority === priority)
      && (!zoneId || task.zone_id === zoneId)
      && (!assigneeId || task.assigned_to === assigneeId);
  }), [tasks, q, status, priority, zoneId, assigneeId]);

  async function save(data: TaskCreate | TaskUpdate) {
    setSaving(true);
    try {
      if (formTask) await updateTask(formTask.id, data as TaskUpdate);
      else await createTask(eventId, data as TaskCreate);
      setFormTask(undefined);
      toast({ tone: "success", title: formTask ? "Tarea actualizada" : "Tarea creada" });
      await load();
    } catch (err) {
      toast({
        tone: "error",
        title: "No se pudo guardar la tarea",
        description: err instanceof ApiError ? err.detail : "Revisa los datos e intenta nuevamente."
      });
    } finally {
      setSaving(false);
    }
  }

  async function setTaskStatus(task: Task, nextStatus: TaskStatus) {
    try {
      await changeTaskStatus(task.id, nextStatus);
      toast({ tone: "success", title: "Estado actualizado", description: task.title });
      await load();
    } catch (err) {
      toast({
        tone: "error",
        title: "No se pudo cambiar el estado",
        description: err instanceof ApiError ? err.detail : "No tienes permiso para esta transicion."
      });
    }
  }

  async function confirmComplete(observation?: string) {
    if (!completeTarget) return;
    setSaving(true);
    try {
      await completeTask(completeTarget.id, { observation });
      setCompleteTarget(null);
      toast({ tone: "success", title: "Tarea completada" });
      await load();
    } catch (err) {
      toast({
        tone: "error",
        title: "No se pudo completar la tarea",
        description: err instanceof ApiError ? err.detail : "Intenta nuevamente."
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-950">Tareas operativas</h2>
          <p className="text-sm text-slate-600">Planifica, asigna y controla trabajo por zona y responsable.</p>
        </div>
        {canManage ? <Button onClick={() => setFormTask(null)}><Plus className="h-4 w-4" />Crear tarea</Button> : null}
      </div>
      <div className="grid gap-3 lg:grid-cols-[1fr_160px_160px_180px_200px]">
        <SearchInput placeholder="Buscar tarea..." value={q} onChange={setQ} />
        <FilterSelect label="Estado" value={status} onChange={setStatus} options={[{ label: "Todos", value: "" }, { label: "Pendiente", value: "PENDING" }, { label: "En progreso", value: "IN_PROGRESS" }, { label: "Completada", value: "COMPLETED" }, { label: "Observada", value: "OBSERVED" }, { label: "Cancelada", value: "CANCELLED" }]} />
        <FilterSelect label="Prioridad" value={priority} onChange={setPriority} options={[{ label: "Todas", value: "" }, { label: "Baja", value: "LOW" }, { label: "Media", value: "MEDIUM" }, { label: "Alta", value: "HIGH" }, { label: "Critica", value: "CRITICAL" }]} />
        <FilterSelect label="Zona" value={zoneId} onChange={setZoneId} options={[{ label: "Todas", value: "" }, ...zones.map((zone) => ({ label: zone.name, value: zone.id }))]} />
        <FilterSelect label="Responsable" value={assigneeId} onChange={setAssigneeId} options={[{ label: "Todos", value: "" }, ...staff.map((item) => ({ label: item.user?.full_name || item.user_id, value: item.user_id }))]} />
      </div>
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      <TaskTable
        canManage={canManage}
        canObserveStatus={role === "SUPERVISOR"}
        canStartStatus={role !== "SUPERVISOR"}
        error={null}
        loading={loading}
        tasks={filtered}
        onComplete={setCompleteTarget}
        onEdit={setFormTask}
        onStatus={setTaskStatus}
        onView={setDetailTask}
      />
      {formTask !== undefined ? <TaskFormModal loading={saving} staff={staff} task={formTask} zones={zones} onClose={() => setFormTask(undefined)} onSubmit={save} /> : null}
      {detailTask ? <TaskDetailPanel task={detailTask} onClose={() => setDetailTask(null)} /> : null}
      {completeTarget ? <CompleteTaskDialog loading={saving} onClose={() => setCompleteTarget(null)} onConfirm={confirmComplete} /> : null}
    </div>
  );
}
