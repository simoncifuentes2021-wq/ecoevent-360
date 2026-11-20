import type { EventForm } from "@/types/eventForm";

export function slugifyPublicPathSegment(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function publicFormLinkSlug(publicSlug: string): string {
  const match = publicSlug.match(/^(.+)-(\d+)$/);
  if (!match) return publicSlug;
  let ordinal = Number(match[2]);
  if (!Number.isSafeInteger(ordinal) || ordinal < 2) return publicSlug;
  let code = "";
  while (ordinal > 0) {
    ordinal -= 1;
    code = String.fromCharCode((ordinal % 26) + 97) + code;
    ordinal = Math.floor(ordinal / 26);
  }
  return `${match[1]}-formulario-${code}`;
}

export function publicFormPath(form: Pick<EventForm, "public_slug" | "event_name" | "session_name">): string {
  const linkSlug = publicFormLinkSlug(form.public_slug);
  const showSlug = form.session_name ? slugifyPublicPathSegment(form.session_name) : "";
  if (showSlug) return `/f/${showSlug}/${linkSlug}`;
  const eventSlug = form.event_name ? slugifyPublicPathSegment(form.event_name) : "";
  return eventSlug ? `/f/${eventSlug}/${linkSlug}` : `/f/${linkSlug}`;
}
