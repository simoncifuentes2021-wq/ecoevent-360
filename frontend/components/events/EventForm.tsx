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
import { eventStatusLabels } from "@/lib/status-labels";
import type { Client } from "@/types/client";
import type { Event, EventCreate, EventStatus, EventUpdate } from "@/types/event";

const statuses = ["QUOTE", "PLANNING", "IN_PROGRESS", "FINISHED", "REPORT_DELIVERED", "CANCELLED"] as const satisfies readonly EventStatus[];
const optionalNumber = z.preprocess((value) => (value === "" || value === null ? undefined : value), z.coerce.number().optional());

const schema = z
  .object({
    client_id: z.string().min(1, "Selecciona un cliente"),
    name: z.string().min(1, "El nombre es obligatorio"),
    event_type: z.string().optional(),
    description: z.string().optional(),
    location_name: z.string().optional(),
    address: z.string().optional(),
    city: z.string().optional(),
    region: z.string().optional(),
    country: z.string().optional(),
    latitude: optionalNumber,
    longitude: optionalNumber,
    start_date: z.string().min(1, "La fecha de inicio es obligatoria"),
    end_date: z.string().min(1, "La fecha de termino es obligatoria"),
    estimated_attendees: optionalNumber.refine((value) => value === undefined || value >= 0, "No puede ser negativo"),
    status: z.enum(statuses).or(z.literal("")).optional()
  })
  .superRefine((data, ctx) => {
    if (data.start_date && data.end_date && new Date(data.start_date) >= new Date(data.end_date)) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: "La fecha de inicio debe ser menor que la fecha de termino", path: ["end_date"] });
    }
  });

type FormValues = z.infer<typeof schema>;

type EventFormProps = {
  event?: Event;
  clients: Client[];
  onSubmit: (data: EventCreate | EventUpdate) => Promise<void>;
  cancelHref: string;
  initialClientId?: string;
  submitLabel?: string;
};

function toDatetimeLocal(value?: string | null) {
  return value ? value.slice(0, 16) : "";
}

function nullableString(value?: string | null) {
  return value?.trim() ? value.trim() : null;
}

export function EventForm({ event, clients, onSubmit, cancelHref, initialClientId, submitLabel }: EventFormProps) {
  const [apiError, setApiError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors }
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      client_id: event?.client_id || initialClientId || "",
      name: event?.name || "",
      event_type: event?.event_type || "",
      description: event?.description || "",
      location_name: event?.location_name || "",
      address: event?.address || "",
      city: event?.city || "",
      region: event?.region || "",
      country: event?.country || "Chile",
      latitude: event?.latitude ? Number(event.latitude) : undefined,
      longitude: event?.longitude ? Number(event.longitude) : undefined,
      start_date: toDatetimeLocal(event?.start_date),
      end_date: toDatetimeLocal(event?.end_date),
      estimated_attendees: event?.estimated_attendees ?? undefined,
      status: event?.status || ""
    }
  });

  async function submit(values: FormValues) {
    setApiError(null);
    setLoading(true);
    try {
      const payload: EventCreate | EventUpdate = {
        client_id: values.client_id,
        name: values.name,
        event_type: nullableString(values.event_type),
        description: nullableString(values.description),
        location_name: nullableString(values.location_name),
        address: nullableString(values.address),
        city: nullableString(values.city),
        region: nullableString(values.region),
        country: nullableString(values.country),
        latitude: values.latitude ?? null,
        longitude: values.longitude ?? null,
        start_date: values.start_date,
        end_date: values.end_date,
        estimated_attendees: values.estimated_attendees ?? null
      };
      if (values.status) {
        payload.status = values.status;
      }
      await onSubmit(payload);
    } catch (error) {
      setApiError(error instanceof ApiError ? error.message : "No pudimos guardar el evento.");
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
            <Field error={errors.client_id?.message} label="Cliente">
              <select className="h-12 w-full rounded-2xl border border-slate-200 bg-white px-4 text-sm outline-none focus:border-emerald-600 focus:ring-4 focus:ring-emerald-100" {...register("client_id")}>
                <option value="">Seleccionar cliente</option>
                {clients.map((client) => (
                  <option key={client.id} value={client.id}>
                    {client.business_name}
                  </option>
                ))}
              </select>
            </Field>
            <Field error={errors.name?.message} label="Nombre evento">
              <Input {...register("name")} placeholder="Festival Sustentable 2026" />
            </Field>
            <Field label="Tipo">
              <Input {...register("event_type")} placeholder="Festival, feria, concierto" />
            </Field>
            <Field label="Estado">
              <select className="h-12 w-full rounded-2xl border border-slate-200 bg-white px-4 text-sm outline-none focus:border-emerald-600 focus:ring-4 focus:ring-emerald-100" {...register("status")}>
                <option value="">Usar estado por defecto</option>
                {statuses.map((status) => (
                  <option key={status} value={status}>
                    {eventStatusLabels[status]}
                  </option>
                ))}
              </select>
            </Field>
            <Field error={errors.start_date?.message} label="Inicio">
              <Input type="datetime-local" {...register("start_date")} />
            </Field>
            <Field error={errors.end_date?.message} label="Termino">
              <Input type="datetime-local" {...register("end_date")} />
            </Field>
            <Field error={errors.estimated_attendees?.message} label="Asistentes estimados">
              <Input min={0} type="number" {...register("estimated_attendees")} />
            </Field>
          </div>
          <details className="rounded-lg border border-slate-200 bg-slate-50/60 p-4">
            <summary className="cursor-pointer text-sm font-bold text-slate-800">Información logística avanzada</summary>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <Field label="Ubicación">
                <Input {...register("location_name")} placeholder="Parque, estadio o recinto" />
              </Field>
              <Field label="Dirección">
                <Input {...register("address")} />
              </Field>
              <Field label="Ciudad">
                <Input {...register("city")} />
              </Field>
              <Field label="Región">
                <Input {...register("region")} />
              </Field>
              <Field label="País">
                <Input {...register("country")} />
              </Field>
              <Field label="Latitud">
                <Input step="0.000001" type="number" {...register("latitude")} />
              </Field>
              <Field label="Longitud">
                <Input step="0.000001" type="number" {...register("longitude")} />
              </Field>
              <div className="md:col-span-2">
                <Field label="Descripción">
                  <textarea
                    className="min-h-28 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none transition focus:border-emerald-600 focus:ring-4 focus:ring-emerald-100"
                    {...register("description")}
                  />
                </Field>
              </div>
            </div>
          </details>
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
