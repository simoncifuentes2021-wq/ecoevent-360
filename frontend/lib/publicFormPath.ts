import type { EventForm } from "@/types/eventForm";

export function slugifyPublicPathSegment(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function publicFormPath(form: Pick<EventForm, "public_slug" | "event_name" | "session_name">): string {
  const showSlug = form.session_name ? slugifyPublicPathSegment(form.session_name) : "";
  if (showSlug) return `/f/${showSlug}/${form.public_slug}`;
  const eventSlug = form.event_name ? slugifyPublicPathSegment(form.event_name) : "";
  return eventSlug ? `/f/${eventSlug}/${form.public_slug}` : `/f/${form.public_slug}`;
}
