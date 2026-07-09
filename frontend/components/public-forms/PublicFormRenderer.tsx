"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { submitPublicForm } from "@/lib/api/publicForms";
import type { FormSubmitResult, PublicEventForm, PublicFormField } from "@/types/eventForm";

type FieldError = { field_key: string; message: string };

export function PublicFormRenderer({ form, language }: { form: PublicEventForm; language: string }) {
  const [answers, setAnswers] = useState<Record<string, unknown>>(initialAnswers(form.fields));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [result, setResult] = useState<FormSubmitResult | null>(null);

  function update(key: string, value: unknown) {
    setAnswers((current) => ({ ...current, [key]: value }));
    setFieldErrors((current) => {
      if (!current[key]) return current;
      const next = { ...current };
      delete next[key];
      return next;
    });
  }

  async function submit() {
    setLoading(true);
    setError(null);
    setFieldErrors({});
    try {
      setResult(await submitPublicForm(form.public_slug, { language, answers }));
    } catch (err) {
      if (err instanceof ApiError && Array.isArray(err.rawDetail)) {
        const nextErrors = fieldErrorsFromDetail(err.rawDetail);
        setFieldErrors(nextErrors);
        setError(Object.keys(nextErrors).length ? null : err.message);
      } else {
        setError(err instanceof Error ? err.message : "No se pudo enviar el formulario.");
      }
    } finally {
      setLoading(false);
    }
  }

  if (result) {
    return (
      <main className="px-4 py-8">
        <section className="mx-auto max-w-2xl rounded-lg bg-white p-6 text-center shadow-2xl">
          <h2 className="text-2xl font-bold text-slate-950">Respuesta recibida</h2>
          <p className="mt-2 text-slate-600">{result.message}</p>
          {result.bike_zone_code ? (
            <div className="mt-5 rounded-lg bg-emerald-50 p-5">
              <p className="text-xs font-bold uppercase tracking-wide text-emerald-700">Código Bike Zone</p>
              <p className="mt-1 text-3xl font-black text-emerald-800">{result.bike_zone_code}</p>
              <p className="mt-2 text-sm font-medium text-emerald-900">Usa este código para check-in y check-out.</p>
            </div>
          ) : null}
          {result.response_code ? (
            <p className="mt-4 text-sm text-slate-500">
              Código de respuesta: <strong className="text-slate-700">{result.response_code}</strong>
            </p>
          ) : null}
        </section>
      </main>
    );
  }

  return (
    <main className="px-4 py-8">
      <section className="mx-auto max-w-2xl rounded-lg bg-white p-5 shadow-2xl md:p-7">
        {form.description ? <p className="mb-5 text-sm text-slate-600">{form.description}</p> : null}
        <div className="space-y-4">
          {form.fields.map((field) => (
            <FieldControl key={field.field_key} error={fieldErrors[field.field_key]} field={field} value={answers[field.field_key]} onChange={(value) => update(field.field_key, value)} />
          ))}
        </div>
        {error ? <p className="mt-4 rounded-md bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700">{error}</p> : null}
        <Button className="mt-6 w-full" disabled={loading} style={{ backgroundColor: form.primary_color }} type="button" onClick={submit}>
          {loading ? "Enviando..." : form.submit_label}
        </Button>
      </section>
    </main>
  );
}

function FieldControl({ field, value, error, onChange }: { field: PublicFormField; value: unknown; error?: string; onChange: (value: unknown) => void }) {
  const required = field.is_required ? <span className="text-rose-600"> *</span> : null;
  return (
    <label className="block text-sm font-semibold text-slate-800">
      {field.label}{required}
      {field.help_text ? <span className="mt-1 block text-xs font-normal text-slate-500">{field.help_text}</span> : null}
      <Control error={error} field={field} value={value} onChange={onChange} />
      {error ? <span className="mt-1 block text-xs font-semibold text-rose-700">{error}</span> : null}
    </label>
  );
}

function Control({ field, value, error, onChange }: { field: PublicFormField; value: unknown; error?: string; onChange: (value: unknown) => void }) {
  const common = `mt-2 ${error ? "border-rose-400 focus:border-rose-500 focus:ring-rose-200" : ""}`;
  if (field.field_type === "TEXTAREA") {
    return <textarea className={`${common} min-h-28 w-full rounded-md border px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20`} maxLength={field.max_length ?? undefined} placeholder={field.placeholder ?? ""} value={String(value ?? "")} onChange={(event) => onChange(event.target.value)} />;
  }
  if (field.field_type === "SELECT" || field.field_type === "RADIO") {
    return (
      <select className={`${common} h-11 w-full rounded-md border bg-white px-3 text-sm`} value={String(value ?? "")} onChange={(event) => onChange(event.target.value)}>
        <option value="">Selecciona</option>
        {field.options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
      </select>
    );
  }
  if (field.field_type === "MULTI_SELECT") {
    const selected = Array.isArray(value) ? value.map(String) : [];
    return (
      <div className={`${common} grid gap-2`}>
        {field.options.map((option) => (
          <label className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium" key={option.value}>
            <input checked={selected.includes(option.value)} type="checkbox" onChange={(event) => onChange(event.target.checked ? [...selected, option.value] : selected.filter((item) => item !== option.value))} />
            {option.label}
          </label>
        ))}
      </div>
    );
  }
  if (field.field_type === "CHECKBOX" || field.field_type === "YES_NO") {
    return (
      <select className={`${common} h-11 w-full rounded-md border bg-white px-3 text-sm`} value={value === true ? "true" : value === false ? "false" : ""} onChange={(event) => onChange(event.target.value === "true")}>
        <option value="">Selecciona</option>
        <option value="true">Sí</option>
        <option value="false">No</option>
      </select>
    );
  }
  const type = field.field_type === "EMAIL" ? "email" : field.field_type === "PHONE" ? "tel" : field.field_type === "NUMBER" || field.field_type.startsWith("RATING") ? "number" : field.field_type === "DATE" ? "date" : "text";
  return <Input className={common} max={field.max_value ? Number(field.max_value) : undefined} maxLength={field.max_length ?? undefined} min={field.min_value ? Number(field.min_value) : field.field_type === "RATING_1_5" || field.field_type === "RATING_1_7" ? 1 : undefined} placeholder={field.placeholder ?? ""} type={type} value={String(value ?? "")} onChange={(event) => onChange(type === "number" ? event.target.value : event.target.value)} />;
}

function fieldErrorsFromDetail(detail: unknown[]) {
  const errors: Record<string, string> = {};
  detail.forEach((item) => {
    if (!item || typeof item !== "object") return;
    const candidate = item as Partial<FieldError>;
    if (typeof candidate.field_key === "string" && typeof candidate.message === "string") {
      errors[candidate.field_key] = candidate.message;
    }
  });
  return errors;
}

function initialAnswers(fields: PublicFormField[]) {
  const data: Record<string, unknown> = {};
  fields.forEach((field) => {
    if (field.placeholder && ["event_name", "venue_name"].includes(field.field_key)) data[field.field_key] = field.placeholder;
  });
  return data;
}
