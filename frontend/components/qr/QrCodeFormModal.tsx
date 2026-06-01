"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ModalShell } from "@/components/common/ModalShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { QrCodeCreate } from "@/types/qr";
import type { Zone } from "@/types/zone";

const schema = z.object({
  label: z.string().min(2, "Ingresa al menos 2 caracteres."),
  zone_id: z.string().optional(),
  target_url: z.string().url("Ingresa una URL valida.").optional().or(z.literal(""))
});

type FormData = z.infer<typeof schema>;

export function QrCodeFormModal({ zones, loading, onClose, onSubmit }: { zones: Zone[]; loading?: boolean; onClose: () => void; onSubmit: (data: QrCodeCreate) => void | Promise<void> }) {
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({ resolver: zodResolver(schema), defaultValues: { label: "", zone_id: "", target_url: "" } });
  return (
    <ModalShell title="Crear QR de encuesta" description="Genera un QR general o asociado a una zona del evento." onClose={onClose}>
      <form className="space-y-4" onSubmit={handleSubmit((data) => onSubmit({ label: data.label, zone_id: data.zone_id || null, target_url: data.target_url || null }))}>
        <label className="block text-sm font-semibold">Etiqueta<Input className="mt-1" {...register("label")} /></label>
        {errors.label ? <p className="text-sm text-rose-600">{errors.label.message}</p> : null}
        <label className="block text-sm font-semibold">Zona<select className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3 text-sm" {...register("zone_id")}><option value="">QR general</option>{zones.map((zone) => <option key={zone.id} value={zone.id}>{zone.name}</option>)}</select></label>
        <label className="block text-sm font-semibold">URL destino opcional<Input className="mt-1" {...register("target_url")} /></label>
        {errors.target_url ? <p className="text-sm text-rose-600">{errors.target_url.message}</p> : null}
        <div className="flex justify-end gap-2">
          <Button disabled={loading} onClick={onClose} type="button" variant="secondary">Cancelar</Button>
          <Button disabled={loading} type="submit">{loading ? "Creando..." : "Crear QR"}</Button>
        </div>
      </form>
    </ModalShell>
  );
}
