import type { EventForm } from "@/types/eventForm";

export function slugifyPublicPathSegment(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function publicFormLinkSlug(publicSlug: string, title?: string): string {
  const match = publicSlug.match(/^(.+)-(\d+)$/);
  if (!match) return publicSlug;
  const ordinal = Number(match[2]);
  if (!Number.isSafeInteger(ordinal) || ordinal < 2) return publicSlug;
  const titleSlug = title ? slugifyPublicPathSegment(title) : "";
  if (titleSlug && titleSlug !== match[1]) return publicSlug;
  return match[1];
}

export function publicFormPath(form: Pick<EventForm, "public_slug" | "public_path_context_slug" | "public_path_slug" | "title" | "event_name" | "session_name">): string {
  const linkSlug = form.public_path_slug || publicFormLinkSlug(form.public_slug, form.title);
  const contextSlug = form.public_path_context_slug
    || (form.session_name ? slugifyPublicPathSegment(form.session_name) : "")
    || (form.event_name ? slugifyPublicPathSegment(form.event_name) : "");
  return contextSlug ? `/f/${contextSlug}/${linkSlug}` : `/f/${linkSlug}`;
}
