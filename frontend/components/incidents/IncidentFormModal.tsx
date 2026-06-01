"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ModalShell } from "@/components/common/ModalShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Incident, IncidentCreate, IncidentUpdate } from "@/types/incident";
import type { EventStaff } from "@/types/staff";
import type { Zone } from "@/types/zone";

const schema = z.object({
  title: z.string().min(3, "El titulo debe tener al menos 3 caracteres"),
  description: z.string().min(5, "La descripcion debe tener al menos 5 caracteres"),
  incident_type: z.enum(["SANITARY", "WASTE", "CLEANING", "ENVIRONMENTAL", "SAFETY", "OTHER"]),
  priority: z.enum(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
  zone_id: z.string().optional(),
  assigned_to: z.string().optional()
});

export function IncidentFormModal({ incident, zones, staff, loading, onClose, onSubmit }: { incident?: Incident | null; zones: Zone[]; staff: EventStaff[]; loading?: boolean; onClose: () => void; onSubmit: (data: IncidentCreate | IncidentUpdate) => Promise<void> }) {
  const { register, handleSubmit, formState: { errors } } = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: incident?.title || "",
      description: incident?.description || "",
      incident_type: incident?.incident_type || incident?.type || "OTHER",
      priority: incident?.priority || "MEDIUM",
      zone_id: incident?.zone_id || "",
      assigned_to: incident?.assigned_to || ""
    }
  });

  return (
    <ModalShell title={incident ? "Editar incidencia" : "Crear incidencia"} description="Registra un problema operativo y asigna seguimiento." onClose={onClose}>
      <form className="space-y-4" onSubmit={handleSubmit((values) => onSubmit({ ...values, zone_id: values.zone_id || null, assigned_to: values.assigned_to || null }))}>
        <label className="grid gap-2 text-sm font-semibold">Titulo<Input {...register("title")} />{errors.title ? <span className="text-xs text-rose-600">{errors.title.message}</span> : null}</label>
        <label className="grid gap-2 text-sm font-semibold">Descripcion<textarea className="min-h-24 rounded-2xl border px-4 py-3" {...register("description")} />{errors.description ? <span className="text-xs text-rose-600">{errors.description.message}</span> : null}</label>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="grid gap-2 text-sm font-semibold">Tipo<select className="h-12 rounded-2xl border px-4" {...register("incident_type")}><option value="SANITARY">Sanitaria</option><option value="WASTE">Residuos</option><option value="CLEANING">Limpieza</option><option value="ENVIRONMENTAL">Ambiental</option><option value="SAFETY">Seguridad</option><option value="OTHER">Otra</option></select></label>
          <label className="grid gap-2 text-sm font-semibold">Prioridad<select className="h-12 rounded-2xl border px-4" {...register("priority")}><option value="LOW">Baja</option><option value="MEDIUM">Media</option><option value="HIGH">Alta</option><option value="CRITICAL">Critica</option></select></label>
          <label className="grid gap-2 text-sm font-semibold">Zona<select className="h-12 rounded-2xl border px-4" {...register("zone_id")}><option value="">Sin zona</option>{zones.map((zone) => <option key={zone.id} value={zone.id}>{zone.name}</option>)}</select></label>
          <label className="grid gap-2 text-sm font-semibold">Responsable<select className="h-12 rounded-2xl border px-4" {...register("assigned_to")}><option value="">Sin asignar</option>{staff.map((item) => <option key={item.user_id} value={item.user_id}>{item.user?.full_name || item.user_id}</option>)}</select></label>
        </div>
        <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button><Button disabled={loading} type="submit">{loading ? "Guardando..." : "Guardar"}</Button></div>
      </form>
    </ModalShell>
  );
}
