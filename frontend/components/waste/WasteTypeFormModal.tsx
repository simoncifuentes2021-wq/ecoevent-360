"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ModalShell } from "@/components/common/ModalShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { WasteType, WasteTypeCreate, WasteTypeUpdate } from "@/types/waste";

const schema = z.object({
  name: z.string().min(1, "El nombre es obligatorio"),
  description: z.string().optional(),
  is_recyclable: z.boolean().optional()
});

export function WasteTypeFormModal({ item, loading, onClose, onSubmit }: { item?: WasteType | null; loading?: boolean; onClose: () => void; onSubmit: (data: WasteTypeCreate | WasteTypeUpdate) => Promise<void> }) {
  const { register, handleSubmit, formState: { errors } } = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: { name: item?.name || "", description: item?.description || "", is_recyclable: item?.is_recyclable ?? false }
  });
  return (
    <ModalShell title={item ? "Editar tipo" : "Crear tipo"} description="Catalogo ambiental de clasificacion de residuos." onClose={onClose}>
      <form className="space-y-4" onSubmit={handleSubmit((values) => onSubmit({ ...values, description: values.description || null }))}>
        <label className="grid gap-2 text-sm font-semibold">Nombre<Input {...register("name")} />{errors.name ? <span className="text-xs text-rose-600">{errors.name.message}</span> : null}</label>
        <label className="grid gap-2 text-sm font-semibold">Descripcion<Input {...register("description")} /></label>
        <label className="flex items-center gap-2 text-sm font-semibold"><input className="h-4 w-4" type="checkbox" {...register("is_recyclable")} />Es reciclable</label>
        <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button><Button disabled={loading} type="submit">{loading ? "Guardando..." : "Guardar"}</Button></div>
      </form>
    </ModalShell>
  );
}
