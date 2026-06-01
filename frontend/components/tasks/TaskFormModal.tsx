"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ModalShell } from "@/components/common/ModalShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { EventStaff } from "@/types/staff";
import type { Task, TaskCreate, TaskUpdate } from "@/types/task";
import type { Zone } from "@/types/zone";

const schema = z.object({
  title: z.string().min(3, "El titulo debe tener al menos 3 caracteres"),
  description: z.string().optional(),
  zone_id: z.string().optional(),
  assigned_to: z.string().optional(),
  priority: z.enum(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
  scheduled_at: z.string().optional()
});

export function TaskFormModal({ task, zones, staff, loading, onClose, onSubmit }: { task?: Task | null; zones: Zone[]; staff: EventStaff[]; loading?: boolean; onClose: () => void; onSubmit: (data: TaskCreate | TaskUpdate) => Promise<void> }) {
  const { register, handleSubmit, formState: { errors } } = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: task?.title || "",
      description: task?.description || "",
      zone_id: task?.zone_id || "",
      assigned_to: task?.assigned_to || "",
      priority: task?.priority || "MEDIUM",
      scheduled_at: task?.scheduled_at ? task.scheduled_at.slice(0, 16) : ""
    }
  });

  return (
    <ModalShell title={task ? "Editar tarea" : "Crear tarea"} description="Asigna trabajo operativo por zona, responsable y prioridad." onClose={onClose}>
      <form className="space-y-4" onSubmit={handleSubmit((values) => onSubmit({
        title: values.title,
        description: values.description || null,
        zone_id: values.zone_id || null,
        assigned_to: values.assigned_to || null,
        priority: values.priority,
        scheduled_at: values.scheduled_at || null
      }))}>
        <label className="grid min-w-0 gap-2 text-sm font-semibold">Titulo<Input className="min-w-0" {...register("title")} />{errors.title ? <span className="text-xs text-rose-600">{errors.title.message}</span> : null}</label>
        <label className="grid min-w-0 gap-2 text-sm font-semibold">Descripcion<Input className="min-w-0" {...register("description")} /></label>
        <div className="grid min-w-0 gap-4 sm:grid-cols-2">
          <label className="grid min-w-0 gap-2 text-sm font-semibold">Zona
            <select className="h-12 min-w-0 w-full rounded-2xl border bg-white px-4 outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" {...register("zone_id")}>
              <option value="">Sin zona</option>
              {zones.map((zone) => <option key={zone.id} value={zone.id}>{zone.name}</option>)}
            </select>
          </label>
          <label className="grid min-w-0 gap-2 text-sm font-semibold">Responsable
            <select className="h-12 min-w-0 w-full rounded-2xl border bg-white px-4 outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" {...register("assigned_to")}>
              <option value="">Sin asignar</option>
              {staff.map((item) => <option key={item.user_id} value={item.user_id}>{item.user?.full_name || item.user_id}</option>)}
            </select>
          </label>
          <label className="grid min-w-0 gap-2 text-sm font-semibold">Prioridad
            <select className="h-12 min-w-0 w-full rounded-2xl border bg-white px-4 outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" {...register("priority")}>
              <option value="LOW">Baja</option><option value="MEDIUM">Media</option><option value="HIGH">Alta</option><option value="CRITICAL">Critica</option>
            </select>
          </label>
          <label className="grid min-w-0 gap-2 text-sm font-semibold">Programada<Input className="min-w-0" type="datetime-local" {...register("scheduled_at")} /></label>
        </div>
        <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end"><Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button><Button disabled={loading} type="submit">{loading ? "Guardando..." : "Guardar"}</Button></div>
      </form>
    </ModalShell>
  );
}
