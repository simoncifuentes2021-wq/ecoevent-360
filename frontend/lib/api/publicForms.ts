import { api } from "@/lib/api";
import type { FormResponseSubmit, FormSubmitResult, PublicEventForm } from "@/types/eventForm";

export function getPublicForm(slug: string, lang?: string | null) {
  const query = lang ? `?lang=${encodeURIComponent(lang)}` : "";
  return api.get<PublicEventForm>(`/public/forms/${slug}${query}`, { auth: false });
}

export function submitPublicForm(slug: string, data: FormResponseSubmit) {
  const payload = { ...data, idempotency_key: data.idempotency_key || crypto.randomUUID() };
  return api.post<FormSubmitResult>(`/public/forms/${slug}/submit`, payload, { auth: false });
}
