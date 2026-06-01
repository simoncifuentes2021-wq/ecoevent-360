"use client";

import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import type { ReactNode } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ErrorState } from "@/components/common/ErrorState";
import { FormActions } from "@/components/common/FormActions";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import type { Service, ServiceCreate, ServiceUpdate } from "@/types/service";

const schema = z.object({
  name: z.string().min(1, "El nombre es obligatorio"),
  category: z.string().optional(),
  description: z.string().optional(),
  unit: z.string().optional(),
  base_price: z.coerce.number().min(0, "El precio no puede ser negativo").optional(),
  is_active: z.boolean().optional()
});

type FormValues = z.infer<typeof schema>;

type ServiceFormProps = {
  service?: Service;
  onSubmit: (data: ServiceCreate | ServiceUpdate) => Promise<void>;
  cancelHref: string;
  submitLabel?: string;
};

export function ServiceForm({ service, onSubmit, cancelHref, submitLabel }: ServiceFormProps) {
  const [apiError, setApiError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors }
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: service?.name || "",
      category: service?.category || "",
      description: service?.description || "",
      unit: service?.unit || "",
      base_price: Number(service?.base_price || 0),
      is_active: service?.is_active ?? true
    }
  });

  async function submit(values: FormValues) {
    setApiError(null);
    setLoading(true);
    try {
      await onSubmit({
        ...values,
        category: values.category || null,
        description: values.description || null,
        unit: values.unit || null,
        base_price: values.base_price ?? 0
      });
    } catch (error) {
      setApiError(error instanceof ApiError ? error.message : "No pudimos guardar el servicio.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardContent className="pt-6">
        {apiError ? <ErrorState message={apiError} title="Error al guardar" /> : null}
        <form className="mt-4 space-y-5" onSubmit={handleSubmit(submit)}>
          <div className="grid gap-4 md:grid-cols-2">
            <Field error={errors.name?.message} label="Nombre">
              <Input {...register("name")} placeholder="Baños químicos premium" />
            </Field>
            <Field error={errors.category?.message} label="Categoria">
              <Input {...register("category")} placeholder="Sanitario" />
            </Field>
            <Field error={errors.unit?.message} label="Unidad">
              <Input {...register("unit")} placeholder="unidad, jornada, kg" />
            </Field>
            <Field error={errors.base_price?.message} label="Precio base">
              <Input min={0} step="0.01" type="number" {...register("base_price")} />
            </Field>
          </div>
          <Field error={errors.description?.message} label="Descripcion">
            <textarea
              className="min-h-28 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none transition focus:border-emerald-600 focus:ring-4 focus:ring-emerald-100"
              {...register("description")}
              placeholder="Describe el servicio, alcance y condiciones generales."
            />
          </Field>
          {service ? (
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <input className="h-4 w-4 rounded border-slate-300 text-emerald-700" type="checkbox" {...register("is_active")} />
              Servicio activo
            </label>
          ) : null}
          <FormActions cancelHref={cancelHref} loading={loading} submitLabel={submitLabel} />
        </form>
      </CardContent>
    </Card>
  );
}

function Field({ label, error, children }: { label: string; error?: string; children: ReactNode }) {
  return (
    <label className="space-y-2 text-sm font-semibold text-slate-700">
      <span>{label}</span>
      {children}
      {error ? <p className="text-sm font-medium text-rose-600">{error}</p> : null}
    </label>
  );
}
