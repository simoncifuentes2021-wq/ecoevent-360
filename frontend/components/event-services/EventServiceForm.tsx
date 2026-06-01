"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { EventService, EventServiceCreate, EventServiceUpdate } from "@/types/eventService";
import type { Service } from "@/types/service";

const schema = z.object({
  service_id: z.string().min(1, "Selecciona un servicio"),
  quantity: z.coerce.number().min(0.01, "La cantidad debe ser mayor a 0"),
  unit_price: z.coerce.number().min(0, "El precio no puede ser negativo").optional(),
  notes: z.string().optional()
});

type Values = z.infer<typeof schema>;

export function EventServiceForm({
  services,
  initialData,
  loading,
  onCancel,
  onSubmit
}: {
  services: Service[];
  initialData?: EventService | null;
  loading?: boolean;
  onCancel: () => void;
  onSubmit: (data: EventServiceCreate | EventServiceUpdate) => Promise<void>;
}) {
  const { register, handleSubmit, watch, formState: { errors } } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      service_id: initialData?.service_id || "",
      quantity: initialData?.quantity || 1,
      unit_price: Number(initialData?.unit_price || 0),
      notes: initialData?.notes || ""
    }
  });
  const total = Number(watch("quantity") || 0) * Number(watch("unit_price") || 0);

  return (
    <form className="space-y-4" onSubmit={handleSubmit((values) => onSubmit({ ...values, notes: values.notes || null }))}>
      <label className="grid gap-2 text-sm font-semibold">
        Servicio
        <select className="h-12 rounded-2xl border px-4" disabled={Boolean(initialData)} {...register("service_id")}>
          <option value="">Seleccionar</option>
          {services.map((service) => <option key={service.id} value={service.id}>{service.name}</option>)}
        </select>
        {errors.service_id ? <span className="text-xs text-rose-600">{errors.service_id.message}</span> : null}
      </label>
      <div className="grid gap-3 md:grid-cols-2">
        <label className="grid gap-2 text-sm font-semibold">Cantidad<Input type="number" step="0.01" {...register("quantity")} />{errors.quantity ? <span className="text-xs text-rose-600">{errors.quantity.message}</span> : null}</label>
        <label className="grid gap-2 text-sm font-semibold">Precio unitario<Input type="number" step="0.01" {...register("unit_price")} />{errors.unit_price ? <span className="text-xs text-rose-600">{errors.unit_price.message}</span> : null}</label>
      </div>
      <label className="grid gap-2 text-sm font-semibold">Notas<Input {...register("notes")} /></label>
      <div className="rounded-2xl bg-emerald-50 p-3 text-sm font-semibold text-emerald-800">Total estimado: {total.toLocaleString("es-CL", { style: "currency", currency: "CLP" })}</div>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel}>Cancelar</Button>
        <Button disabled={loading} type="submit">{loading ? "Guardando..." : "Guardar"}</Button>
      </div>
    </form>
  );
}
