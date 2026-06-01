"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ModalShell } from "@/components/common/ModalShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Survey, SurveyCreate } from "@/types/survey";

const schema = z.object({
  title: z.string().min(3, "Ingresa al menos 3 caracteres."),
  description: z.string().optional(),
  google_form_url: z.string().url("Ingresa una URL valida.").optional().or(z.literal("")),
  google_sheet_url: z.string().url("Ingresa una URL valida.").optional().or(z.literal("")),
  status: z.enum(["DRAFT", "ACTIVE", "CLOSED", "ARCHIVED"]).optional(),
  opens_at: z.string().optional(),
  closes_at: z.string().optional()
}).refine((data) => !data.opens_at || !data.closes_at || new Date(data.opens_at) < new Date(data.closes_at), {
  message: "El cierre debe ser posterior a la apertura.",
  path: ["closes_at"]
});

type FormData = z.infer<typeof schema>;

export function SurveyFormModal({ survey, loading, onClose, onSubmit }: { survey?: Survey | null; loading?: boolean; onClose: () => void; onSubmit: (data: SurveyCreate) => Promise<void> | void }) {
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: survey?.title ?? "",
      description: survey?.description ?? "",
      google_form_url: survey?.google_form_url ?? "",
      google_sheet_url: survey?.google_sheet_url ?? "",
      status: survey?.status ?? "ACTIVE",
      opens_at: survey?.opens_at?.slice(0, 16) ?? "",
      closes_at: survey?.closes_at?.slice(0, 16) ?? ""
    }
  });

  return (
    <ModalShell description="Pega el enlace publico de Google Forms y, si corresponde, el enlace de respuestas en Google Sheets." title={survey ? "Editar encuesta" : "Crear encuesta"} onClose={onClose}>
      <form className="space-y-4" onSubmit={handleSubmit((data) => onSubmit({
        ...data,
        description: data.description || null,
        google_form_url: data.google_form_url || null,
        google_sheet_url: data.google_sheet_url || null,
        opens_at: data.opens_at || null,
        closes_at: data.closes_at || null
      }))}>
        <label className="block text-sm font-semibold">Titulo<Input className="mt-1" {...register("title")} /></label>
        {errors.title ? <p className="text-sm text-rose-600">{errors.title.message}</p> : null}
        <label className="block text-sm font-semibold">Descripcion<textarea className="mt-1 min-h-24 w-full rounded-md border border-slate-200 px-3 py-2 text-sm" {...register("description")} /></label>
        <label className="block text-sm font-semibold">Google Form URL<Input className="mt-1" placeholder="https://forms.gle/..." {...register("google_form_url")} /></label>
        {errors.google_form_url ? <p className="text-sm text-rose-600">{errors.google_form_url.message}</p> : null}
        <label className="block text-sm font-semibold">Google Sheet URL<Input className="mt-1" placeholder="https://docs.google.com/spreadsheets/..." {...register("google_sheet_url")} /></label>
        {errors.google_sheet_url ? <p className="text-sm text-rose-600">{errors.google_sheet_url.message}</p> : null}
        <div className="grid gap-3 md:grid-cols-3">
          <label className="block text-sm font-semibold">Estado<select className="mt-1 h-10 w-full rounded-md border border-slate-200 px-3 text-sm" {...register("status")}><option value="DRAFT">Borrador</option><option value="ACTIVE">Activa</option><option value="CLOSED">Cerrada</option><option value="ARCHIVED">Archivada</option></select></label>
          <label className="block text-sm font-semibold">Apertura<Input className="mt-1" type="datetime-local" {...register("opens_at")} /></label>
          <label className="block text-sm font-semibold">Cierre<Input className="mt-1" type="datetime-local" {...register("closes_at")} /></label>
        </div>
        {errors.closes_at ? <p className="text-sm text-rose-600">{errors.closes_at.message}</p> : null}
        <div className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800">
          Exporta respuestas desde Google Sheets con: Archivo &gt; Descargar &gt; Valores separados por comas (.csv).
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button disabled={loading} onClick={onClose} type="button" variant="secondary">Cancelar</Button>
          <Button disabled={loading} type="submit">{loading ? "Guardando..." : "Guardar"}</Button>
        </div>
      </form>
    </ModalShell>
  );
}
