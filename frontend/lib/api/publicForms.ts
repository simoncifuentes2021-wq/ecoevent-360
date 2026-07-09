import { api } from "@/lib/api";
import type { FormResponseSubmit, FormSubmitResult, PublicEventForm } from "@/types/eventForm";

export function getPublicForm(slug: string, lang?: string | null) {
  const query = lang ? `?lang=${encodeURIComponent(lang)}` : "";
  return api.get<PublicEventForm>(`/public/forms/${slug}${query}`, { auth: false });
}

export function submitPublicForm(slug: string, data: FormResponseSubmit) {
  return api.post<FormSubmitResult>(`/public/forms/${slug}/submit`, data, { auth: false });
}
