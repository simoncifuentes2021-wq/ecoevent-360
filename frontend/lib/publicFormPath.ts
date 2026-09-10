import type { EventForm } from "@/types/eventForm";

export function slugifyPublicPathSegment(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function publicFormPath(form: Pick<EventForm, "public_slug" | "session_name">): string {
  const showSlug = form.session_name ? slugifyPublicPathSegment(form.session_name) : "";
  return showSlug ? `/f/${showSlug}/${form.public_slug}` : `/f/${form.public_slug}`;
}
