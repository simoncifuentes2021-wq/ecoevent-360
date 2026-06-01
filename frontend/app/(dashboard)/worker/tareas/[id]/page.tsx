"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, ArrowLeft, Camera, CheckCircle, MapPin, PlayCircle, ShieldAlert, User } from "lucide-react";
import type { ReactNode } from "react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { useToast } from "@/components/common/ToastProvider";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { CompleteTaskDialog } from "@/components/tasks/CompleteTaskDialog";
import { PriorityBadge } from "@/components/tasks/PriorityBadge";
import { TaskStatusBadge } from "@/components/tasks/TaskStatusBadge";
import { Button } from "@/components/ui/button";
import { MobileShell } from "@/components/worker/MobileShell";
import { useAuth } from "@/hooks/useAuth";
import { ApiError } from "@/lib/api";
import { getEvent } from "@/lib/api/events";
import { getEventStaff } from "@/lib/api/staff";
import { changeTaskStatus, completeTask, getTask } from "@/lib/api/tasks";
import { getEventZones } from "@/lib/api/zones";
import type { Task } from "@/types/task";

function dateTime(value?: string | null) {
  return value ? new Intl.DateTimeFormat("es-CL", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "Sin fecha";
}

export default function WorkerTaskDetailPage({ params }: { params: { id: string } }) {
  const { toast } = useToast();
  const { user } = useAuth();
  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [completeOpen, setCompleteOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const taskData = await getTask(params.id);
      const [eventData, zoneData, staffData] = await Promise.all([
        getEvent(taskData.event_id).catch(() => null),
        getEventZones(taskData.event_id).catch(() => []),
        getEventStaff(taskData.event_id).catch(() => [])
      ]);
      const zone = taskData.zone || zoneData.find((item) => item.id === taskData.zone_id) || null;
      const staffUser = staffData.find((item) => item.user_id === taskData.assigned_to)?.user || null;
      const currentUserAssignee =
        user && taskData.assigned_to === user.id
          ? { id: user.id, full_name: user.full_name, email: user.email, role: user.role }
          : null;
      setTask({
        ...taskData,
        event: taskData.event || eventData,
        zone,
        assignee: taskData.assignee || taskData.assigned_user || staffUser || currentUserAssignee
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar la tarea.");
    } finally {
      setLoading(false);
    }
  }, [params.id, user]);

  useEffect(() => { void load(); }, [load]);

  async function startTask() {
    setSaving(true);
    try {
      await changeTaskStatus(params.id, "IN_PROGRESS");
      toast({ tone: "success", title: "Tarea iniciada" });
      await load();
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "No se pudo iniciar la tarea.";
      const message = detail.includes("SUPERVISOR can only set OBSERVED or CANCELLED")
        ? "Esta tarea no esta asignada a tu usuario supervisor o el backend aun no fue reiniciado con la ultima correccion."
        : detail;
      toast({ tone: "error", title: "No pudimos iniciar", description: message });
    } finally {
      setSaving(false);
    }
  }

  async function confirmComplete(observation?: string) {
    setSaving(true);
    try {
      if (task?.status === "PENDING") {
        await changeTaskStatus(params.id, "IN_PROGRESS");
      }
      await completeTask(params.id, { observation });
      toast({ tone: "success", title: "Tarea completada" });
      setCompleteOpen(false);
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

  if (loading) return <LoadingState label="Cargando tarea..." />;
  if (error || !task) return <ErrorState message={error || "Tarea no encontrada"} title="No pudimos cargar la tarea" onRetry={load} />;

  const isAssignedToCurrentUser = Boolean(user?.id && task.assigned_to === user.id);
  const canStartTask = task.status === "PENDING" && (user?.role === "WORKER" || isAssignedToCurrentUser);

  return (
    <RoleGuard roles={["WORKER", "SUPERVISOR"]}>
      <MobileShell title={task.title} description={task.event?.name || "Detalle de tarea operativa"}>
        <Link href="/worker/mis-tareas"><Button className="w-full" variant="secondary"><ArrowLeft className="h-4 w-4" />Volver a mis tareas</Button></Link>
        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap gap-2"><TaskStatusBadge status={task.status} /><PriorityBadge priority={task.priority} /></div>
          <p className="mt-4 text-sm leading-6 text-slate-700">{task.description || "Sin descripcion adicional."}</p>
          <div className="mt-5 grid gap-3 text-sm text-slate-700">
            <Info icon={<MapPin className="h-4 w-4" />} label="Zona" value={task.zone?.name || "Sin zona"} />
            <Info icon={<User className="h-4 w-4" />} label="Responsable" value={task.assignee?.full_name || task.assigned_user?.full_name || "Sin responsable"} />
            <Info icon={<CheckCircle className="h-4 w-4" />} label="Programada" value={dateTime(task.scheduled_at)} />
            <Info icon={<CheckCircle className="h-4 w-4" />} label="Completada" value={dateTime(task.completed_at)} />
          </div>
          {task.observation ? <div className="mt-4 rounded-2xl bg-slate-50 p-4 text-sm text-slate-700">{task.observation}</div> : null}
        </div>
        <div className="sticky bottom-3 grid gap-2 rounded-3xl border bg-white/95 p-3 shadow-xl backdrop-blur">
          {canStartTask ? <Button className="h-12" onClick={startTask}><PlayCircle className="h-5 w-5" />Iniciar tarea</Button> : null}
          {task.status === "PENDING" && user?.role === "SUPERVISOR" && !isAssignedToCurrentUser ? (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
              <p className="flex items-center gap-2 font-semibold"><AlertTriangle className="h-4 w-4" />Tarea no asignada a tu usuario</p>
              <p className="mt-1">Puedes observar o gestionar la tarea desde el evento, pero solo el responsable asignado puede iniciarla.</p>
            </div>
          ) : null}
          {task.status !== "COMPLETED" ? <Button className="h-12" variant="secondary" onClick={() => setCompleteOpen(true)}><CheckCircle className="h-5 w-5" />Completar tarea</Button> : null}
          <div className="grid grid-cols-2 gap-2">
            <Link href={`/worker/subir-evidencia?task_id=${task.id}&event_id=${task.event_id}`}><Button className="w-full" variant="ghost"><Camera className="h-4 w-4" />Evidencia</Button></Link>
            <Link href={`/worker/reportar-incidencia?event_id=${task.event_id}`}><Button className="w-full" variant="ghost"><ShieldAlert className="h-4 w-4" />Incidencia</Button></Link>
          </div>
        </div>
        {completeOpen ? <CompleteTaskDialog loading={saving} onClose={() => setCompleteOpen(false)} onConfirm={confirmComplete} /> : null}
      </MobileShell>
    </RoleGuard>
  );
}

function Info({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return <div className="flex items-center gap-2"><span className="text-emerald-700">{icon}</span><span className="font-semibold">{label}:</span><span>{value}</span></div>;
}
