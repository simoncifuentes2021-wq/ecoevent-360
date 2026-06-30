"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMemo } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ModalShell } from "@/components/common/ModalShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { EventStaff, EventStaffCreate } from "@/types/staff";
import type { User } from "@/types/user";

const schema = z.object({
  user_id: z.string().min(1, "Selecciona una persona"),
  role_in_event: z.string().min(1, "Indica el rol en el evento"),
  shift_start: z.string().optional(),
  shift_end: z.string().optional()
}).superRefine((data, ctx) => {
  if (data.shift_start && data.shift_end && new Date(data.shift_start) >= new Date(data.shift_end)) {
    ctx.addIssue({ code: z.ZodIssueCode.custom, message: "El inicio debe ser menor que el fin", path: ["shift_end"] });
  }
});

export function AssignStaffModal({ users, assigned, loading, onClose, onSubmit }: { users: User[]; assigned: EventStaff[]; loading?: boolean; onClose: () => void; onSubmit: (data: EventStaffCreate) => Promise<void> }) {
  const assignedIds = useMemo(() => new Set(assigned.map((item) => item.user_id)), [assigned]);
  const options = users.filter((user) => user.is_active && (user.role === "WORKER" || user.role === "SUPERVISOR" || user.role === "LOGISTICS_OPERATOR") && !assignedIds.has(user.id));
  const { register, handleSubmit, formState: { errors } } = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: { role_in_event: "Operativo" }
  });

  return (
    <ModalShell title="Asignar personal" description="Selecciona personal operativo activo para el evento." onClose={onClose}>
      <form className="space-y-4" onSubmit={handleSubmit((values) => onSubmit({ ...values, shift_start: values.shift_start || null, shift_end: values.shift_end || null }))}>
        <label className="grid gap-2 text-sm font-semibold">Persona
          <select className="h-12 rounded-2xl border px-4" {...register("user_id")}>
            <option value="">Seleccionar</option>
            {options.map((user) => <option key={user.id} value={user.id}>{user.full_name} - {user.role}</option>)}
          </select>
          {options.length === 0 ? (
            <span className="rounded-2xl bg-amber-50 p-3 text-xs font-medium text-amber-800">
              No hay personal operativo activo disponible para este cliente/evento. Crea usuarios operativos o revisa que no esten ya asignados.
            </span>
          ) : null}
          {errors.user_id ? <span className="text-xs text-rose-600">{errors.user_id.message}</span> : null}
        </label>
        <label className="grid gap-2 text-sm font-semibold">Rol dentro del evento<Input {...register("role_in_event")} />{errors.role_in_event ? <span className="text-xs text-rose-600">{errors.role_in_event.message}</span> : null}</label>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="grid gap-2 text-sm font-semibold">Inicio turno<Input type="datetime-local" {...register("shift_start")} /></label>
          <label className="grid gap-2 text-sm font-semibold">Fin turno<Input type="datetime-local" {...register("shift_end")} />{errors.shift_end ? <span className="text-xs text-rose-600">{errors.shift_end.message}</span> : null}</label>
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button disabled={loading} type="submit">{loading ? "Asignando..." : "Asignar"}</Button>
        </div>
      </form>
    </ModalShell>
  );
}
