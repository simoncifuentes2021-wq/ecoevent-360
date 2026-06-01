"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ModalShell } from "@/components/common/ModalShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Zone, ZoneCreate, ZoneUpdate } from "@/types/zone";

const schema = z.object({
  name: z.string().min(2, "El nombre debe tener al menos 2 caracteres"),
  description: z.string().optional()
});

export function ZoneFormModal({ zone, loading, onClose, onSubmit }: { zone?: Zone | null; loading?: boolean; onClose: () => void; onSubmit: (data: ZoneCreate | ZoneUpdate) => Promise<void> }) {
  const { register, handleSubmit, formState: { errors } } = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: { name: zone?.name || "", description: zone?.description || "" }
  });

  return (
    <ModalShell title={zone ? "Editar zona" : "Crear zona"} description="Las zonas se usaran para tareas, incidencias, residuos y QR." onClose={onClose}>
      <form className="space-y-4" onSubmit={handleSubmit((values) => onSubmit({ name: values.name, description: values.description || null }))}>
        <label className="grid gap-2 text-sm font-semibold">Nombre<Input {...register("name")} />{errors.name ? <span className="text-xs text-rose-600">{errors.name.message}</span> : null}</label>
        <label className="grid gap-2 text-sm font-semibold">Descripcion<Input {...register("description")} /></label>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button disabled={loading} type="submit">{loading ? "Guardando..." : "Guardar"}</Button>
        </div>
      </form>
    </ModalShell>
  );
}
