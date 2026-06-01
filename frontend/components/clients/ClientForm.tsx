"use client";

import { useRef, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import type { ReactNode } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ErrorState } from "@/components/common/ErrorState";
import { FormActions } from "@/components/common/FormActions";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import type { Client, ClientCreate, ClientUpdate } from "@/types/client";

const clientSchema = z.object({
  business_name: z.string().min(1, "La razón social es obligatoria"),
  rut: z.string().optional(),
  contact_name: z.string().optional(),
  contact_email: z.string().email("Email inválido").optional().or(z.literal("")),
  contact_phone: z.string().optional(),
  address: z.string().optional(),
  industry: z.string().optional(),
  notes: z.string().optional()
});

type ClientFormValues = z.infer<typeof clientSchema>;

export function ClientForm({
  initialData,
  client,
  onSubmit,
  cancelHref,
  submitLabel
}: {
  initialData?: Client;
  client?: Client;
  onSubmit: (data: ClientCreate | ClientUpdate) => Promise<void>;
  cancelHref: string;
  submitLabel?: string;
}) {
  const [apiError, setApiError] = useState<string | null>(null);
  const [submitLocked, setSubmitLocked] = useState(false);
  const submitLockRef = useRef(false);
  const formData = initialData || client;
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting }
  } = useForm<ClientFormValues>({
    resolver: zodResolver(clientSchema),
    defaultValues: {
      business_name: formData?.business_name ?? "",
      rut: formData?.rut ?? "",
      contact_name: formData?.contact_name ?? "",
      contact_email: formData?.contact_email ?? "",
      contact_phone: formData?.contact_phone ?? "",
      address: formData?.address ?? "",
      industry: formData?.industry ?? "",
      notes: formData?.notes ?? ""
    }
  });

  async function submit(values: ClientFormValues) {
    if (submitLockRef.current) return;
    submitLockRef.current = true;
    setSubmitLocked(true);
    setApiError(null);
    try {
      await onSubmit({
        ...values,
        contact_email: values.contact_email || null
      });
    } catch (error) {
      submitLockRef.current = false;
      setSubmitLocked(false);
      setApiError(error instanceof ApiError ? error.detail : "No se pudo guardar el cliente.");
    }
  }

  const saving = isSubmitting || submitLocked;

  return (
    <Card>
      <CardContent>
        <form className="space-y-5" onSubmit={handleSubmit(submit)}>
          {apiError ? <ErrorState message={apiError} /> : null}
          <div className="grid gap-4 md:grid-cols-2">
            <Field error={errors.business_name?.message} label="Razón social">
              <Input disabled={saving} {...register("business_name")} />
            </Field>
            <Field label="RUT">
              <Input disabled={saving} {...register("rut")} />
            </Field>
            <Field label="Contacto">
              <Input disabled={saving} {...register("contact_name")} />
            </Field>
            <Field error={errors.contact_email?.message} label="Email">
              <Input disabled={saving} type="email" {...register("contact_email")} />
            </Field>
            <Field label="Teléfono">
              <Input disabled={saving} {...register("contact_phone")} />
            </Field>
            <Field label="Industria">
              <Input disabled={saving} {...register("industry")} />
            </Field>
            <Field label="Dirección">
              <Input disabled={saving} {...register("address")} />
            </Field>
            <Field label="Notas">
              <Input disabled={saving} {...register("notes")} />
            </Field>
          </div>
          <FormActions cancelHref={cancelHref} loading={saving} loadingLabel={submitLabel === "Crear cliente" ? "Creando cliente..." : "Guardando cambios..."} submitLabel={submitLabel} />
        </form>
      </CardContent>
    </Card>
  );
}

function Field({ label, error, children }: { label: string; error?: string; children: ReactNode }) {
  return (
    <label className="grid gap-2 text-sm font-medium">
      {label}
      {children}
      {error ? <span className="text-xs text-rose-600">{error}</span> : null}
    </label>
  );
}
