"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { submitPublicForm } from "@/lib/api/publicForms";
import { publicFormCopy, publicFormFieldLabel, publicFormOptionLabel, translatePublicFormError } from "@/lib/publicFormI18n";
import type { FormSubmitResult, PublicEventForm, PublicFormField } from "@/types/eventForm";

type FieldError = { field_key: string; message: string };

export function PublicFormRenderer({ form, language }: { form: PublicEventForm; language: string }) {
  const [answers, setAnswers] = useState<Record<string, unknown>>(initialAnswers(form));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [result, setResult] = useState<FormSubmitResult | null>(null);
  const copy = publicFormCopy(language);

  function update(key: string, value: unknown) {
    setAnswers((current) => {
      const next = { ...current, [key]: value };
      if ((key === "country_residence" || key === "country_origin") && value !== "Chile") {
        delete next.residence_region;
        delete next.residence_commune;
      }
      if (key === "residence_region" && value !== "Metropolitana de Santiago") {
        delete next.residence_commune;
      }
      return next;
    });
    setFieldErrors((current) => {
      if (!current[key]) return current;
      const next = { ...current };
      delete next[key];
      return next;
    });
  }

  async function submit() {
    const nextErrors = validateAnswers(form.fields, answers, language);
    if (Object.keys(nextErrors).length) {
      setFieldErrors(nextErrors);
      setError(null);
      window.requestAnimationFrame(() => {
        document.getElementById(`field-${Object.keys(nextErrors)[0]}`)?.focus();
      });
      return;
    }

    setLoading(true);
    setError(null);
    setFieldErrors({});
    try {
      setResult(await submitPublicForm(form.public_slug, { language, answers }));
    } catch (err) {
      if (err instanceof ApiError && Array.isArray(err.rawDetail)) {
        const nextErrors = fieldErrorsFromDetail(err.rawDetail, language);
        setFieldErrors(nextErrors);
        setError(Object.keys(nextErrors).length ? null : translatePublicFormError(err.message, language));
      } else {
        setError(err instanceof Error ? translatePublicFormError(err.message, language) : copy.submitError);
      }
    } finally {
      setLoading(false);
    }
  }

  if (result) {
    return (
      <main className="px-4 py-8">
        <section className="mx-auto max-w-2xl rounded-lg bg-white p-6 text-center shadow-2xl">
          <h2 className="text-2xl font-bold text-slate-950">{copy.successTitle}</h2>
          <p className="mt-2 text-slate-600">{copy.successMessage}</p>
          {result.bike_zone_code ? (
            <div className="mt-5 rounded-lg bg-emerald-50 p-5">
              <p className="text-xs font-bold uppercase tracking-wide text-emerald-700">{copy.bikeZoneCode}</p>
              <p className="mt-1 text-3xl font-black text-emerald-800">{result.bike_zone_code}</p>
              <p className="mt-2 text-sm font-medium text-emerald-900">{copy.bikeZoneInstruction}</p>
            </div>
          ) : null}
          {result.response_code ? (
            <p className="mt-4 text-sm text-slate-500">
              {copy.responseCode}: <strong className="text-slate-700">{result.response_code}</strong>
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
          {form.fields.filter((field) => isFieldVisible(field, answers, form.fields)).map((field) => (
            <FieldControl key={field.field_key} conditionallyRequired={isFieldConditionallyRequired(field, answers, form.fields)} error={fieldErrors[field.field_key]} field={field} language={language} value={answers[field.field_key]} onChange={(value) => update(field.field_key, value)} />
          ))}
        </div>
        {error ? <p aria-live="polite" className="mt-4 rounded-md bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700">{error}</p> : null}
        <Button className="mt-6 w-full" disabled={loading} style={{ backgroundColor: form.primary_color }} type="button" onClick={submit}>
          {loading ? copy.submitting : form.submit_label}
        </Button>
      </section>
    </main>
  );
}

function FieldControl({ field, value, error, conditionallyRequired = false, language, onChange }: { field: PublicFormField; value: unknown; error?: string; conditionallyRequired?: boolean; language: string; onChange: (value: unknown) => void }) {
  const fieldId = `field-${field.field_key}`;
  const required = field.is_required || conditionallyRequired ? <span className="text-rose-600"> *</span> : null;
  const label = publicFormFieldLabel(field.field_key, field.label, language);
  return (
    <div className="block text-sm font-semibold text-slate-800">
      <label htmlFor={fieldId}>{label}{required}</label>
      {field.help_text ? <span className="mt-1 block text-xs font-normal text-slate-500">{field.help_text}</span> : null}
      <Control error={error} field={field} fieldId={fieldId} language={language} value={value} onChange={onChange} />
      {error ? <span id={`${fieldId}-error`} aria-live="polite" className="mt-1 block text-xs font-semibold text-rose-700">{error}</span> : null}
    </div>
  );
}

function isFieldVisible(field: PublicFormField, answers: Record<string, unknown>, fields: PublicFormField[]) {
  const hasCountryField = fields.some((item) => item.field_key === "country_residence" || item.field_key === "country_origin");
  const hasRegionField = fields.some((item) => item.field_key === "residence_region");
  if (!hasCountryField) {
    if (hasRegionField && field.field_key === "residence_commune") {
      return answers.residence_region === "Metropolitana de Santiago";
    }
    return true;
  }
  const country = answers.country_residence ?? answers.country_origin;
  if (field.field_key === "residence_region") return country === "Chile";
  if (field.field_key === "residence_commune") return country === "Chile" && answers.residence_region === "Metropolitana de Santiago";
  return true;
}

function isFieldConditionallyRequired(field: PublicFormField, answers: Record<string, unknown>, fields: PublicFormField[]) {
  const hasCountryField = fields.some((item) => item.field_key === "country_residence" || item.field_key === "country_origin");
  const hasRegionField = fields.some((item) => item.field_key === "residence_region");
  if (!hasCountryField) {
    return hasRegionField && field.field_key === "residence_commune" && answers.residence_region === "Metropolitana de Santiago";
  }
  const country = answers.country_residence ?? answers.country_origin;
  return (field.field_key === "residence_region" && country === "Chile")
    || (field.field_key === "residence_commune" && answers.residence_region === "Metropolitana de Santiago");
}

function Control({ field, fieldId, value, error, language, onChange }: { field: PublicFormField; fieldId: string; value: unknown; error?: string; language: string; onChange: (value: unknown) => void }) {
  const copy = publicFormCopy(language);
  const common = `mt-2 ${error ? "border-rose-400 focus:border-rose-500 focus:ring-rose-200" : ""}`;
  const readonlyClass = field.is_readonly ? "cursor-not-allowed bg-slate-50 text-slate-600" : "";
  if (field.field_type === "TEXTAREA") {
    return <textarea aria-describedby={error ? `${fieldId}-error` : undefined} aria-invalid={Boolean(error)} className={`${common} ${readonlyClass} min-h-28 w-full rounded-md border px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20`} id={fieldId} maxLength={field.max_length ?? undefined} placeholder={field.placeholder ?? ""} readOnly={field.is_readonly} value={String(value ?? "")} onChange={(event) => onChange(event.target.value)} />;
  }
  if (field.field_type === "SELECT") {
    return (
      <select aria-describedby={error ? `${fieldId}-error` : undefined} aria-invalid={Boolean(error)} className={`${common} h-11 w-full rounded-md border bg-white px-3 text-sm`} disabled={field.is_readonly} id={fieldId} value={String(value ?? "")} onChange={(event) => onChange(event.target.value)}>
        <option value="">{copy.selectPlaceholder}</option>
        {field.options.map((option) => <option key={option.value} value={option.value}>{publicFormOptionLabel(option.value, option.label, language)}</option>)}
      </select>
    );
  }
  if (field.field_type === "RADIO" || field.field_type === "YES_NO") {
    const options = field.field_type === "YES_NO" && !field.options.length
      ? [{ label: copy.yes, value: "true" }, { label: copy.no, value: "false" }]
      : field.options;
    return (
      <div aria-describedby={error ? `${fieldId}-error` : undefined} aria-invalid={Boolean(error)} className="mt-2 grid gap-2" role="radiogroup">
        {options.map((option, index) => (
          <label className="flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium" key={option.value}>
            <input checked={value === option.value || (field.field_type === "YES_NO" && value === (option.value === "true"))} disabled={field.is_readonly} id={index === 0 ? fieldId : undefined} name={fieldId} type="radio" onChange={() => onChange(field.field_type === "YES_NO" ? option.value === "true" : option.value)} />
            {field.field_type === "YES_NO" ? option.label : publicFormOptionLabel(option.value, option.label, language)}
          </label>
        ))}
      </div>
    );
  }
  if (field.field_type === "MULTI_SELECT") {
    const selected = Array.isArray(value) ? value.map(String) : [];
    return (
      <div className={`${common} grid gap-2`}>
        {field.options.map((option, index) => (
          <label className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium" key={option.value}>
            <input checked={selected.includes(option.value)} id={index === 0 ? fieldId : undefined} type="checkbox" onChange={(event) => onChange(event.target.checked ? [...selected, option.value] : selected.filter((item) => item !== option.value))} />
            {publicFormOptionLabel(option.value, option.label, language)}
          </label>
        ))}
      </div>
    );
  }
  if (field.field_type === "CHECKBOX") {
    return (
      <label className="mt-2 flex cursor-pointer items-center gap-2 rounded-md border px-3 py-3 text-sm font-medium">
        <input checked={value === true} disabled={field.is_readonly} id={fieldId} type="checkbox" onChange={(event) => onChange(event.target.checked)} />
        {field.placeholder || copy.yes}
      </label>
    );
  }
  const type = field.field_type === "EMAIL" ? "email" : field.field_type === "PHONE" ? "tel" : field.field_type === "NUMBER" || field.field_type.startsWith("RATING") ? "number" : field.field_type === "DATE" ? "date" : "text";
  return <Input aria-describedby={error ? `${fieldId}-error` : undefined} aria-invalid={Boolean(error)} className={`${common} ${readonlyClass}`} id={fieldId} max={field.max_value ? Number(field.max_value) : undefined} maxLength={field.max_length ?? undefined} min={field.min_value ? Number(field.min_value) : field.field_type === "RATING_1_5" || field.field_type === "RATING_1_7" ? 1 : undefined} placeholder={field.placeholder ?? ""} readOnly={field.is_readonly} type={type} value={String(value ?? "")} onChange={(event) => onChange(type === "number" ? event.target.value : event.target.value)} />;
}

function validateAnswers(fields: PublicFormField[], answers: Record<string, unknown>, language: string) {
  const errors: Record<string, string> = {};
  fields.filter((field) => isFieldVisible(field, answers, fields)).forEach((field) => {
    const required = field.is_required || isFieldConditionallyRequired(field, answers, fields);
    if (!required || !isEmptyAnswer(field, answers[field.field_key])) return;
    errors[field.field_key] = translatePublicFormError("Este campo es obligatorio", language);
  });
  return errors;
}

function isEmptyAnswer(field: PublicFormField, value: unknown) {
  if (field.field_type === "CHECKBOX") return value !== true;
  if (Array.isArray(value)) return value.length === 0;
  return value === undefined || value === null || String(value).trim() === "";
}

function fieldErrorsFromDetail(detail: unknown[], language: string) {
  const errors: Record<string, string> = {};
  detail.forEach((item) => {
    if (!item || typeof item !== "object") return;
    const candidate = item as Partial<FieldError>;
    if (typeof candidate.field_key === "string" && typeof candidate.message === "string") {
      errors[candidate.field_key] = translatePublicFormError(candidate.message, language);
    }
  });
  return errors;
}

function initialAnswers(form: PublicEventForm) {
  const data: Record<string, unknown> = {};
  form.fields.forEach((field) => {
    if (field.field_key === "event_name" && form.event_name) data[field.field_key] = form.event_name;
    else if (field.field_key === "venue_name" && form.venue_name) data[field.field_key] = form.venue_name;
    else if (field.placeholder && ["event_name", "venue_name"].includes(field.field_key)) data[field.field_key] = field.placeholder;
  });
  return data;
}
