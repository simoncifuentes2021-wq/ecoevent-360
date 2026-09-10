import type { Metadata } from "next";

import type { PublicEventForm } from "@/types/eventForm";

const SITE_URL = process.env.NEXT_PUBLIC_APP_URL || "https://app.greenway.cl";
const PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL || "https://ecoevent-360.onrender.com/api/v1";
const DEFAULT_SHARE_IMAGE = "https://images.unsplash.com/photo-1501281668745-f7f57925c3b4?auto=format&fit=crop&w=1200&h=630&q=85";
const SHARE_TITLE_ACRONYMS = new Set(["co2", "qr", "wwe"]);
const SHARE_TITLE_LOWERCASE_WORDS = new Set(["de", "del", "el", "en", "la", "las", "los", "para", "y"]);

export async function publicFormMetadata(formSlug: string, publicPath: string, showSlug?: string): Promise<Metadata> {
  const form = await loadPublicForm(formSlug);
  const canonicalUrl = absoluteUrl(publicPath);
  const formTitle = form?.title?.trim() || humanizeSlug(formSlug);
  const context = form?.session_name?.trim() || form?.event_name?.trim() || (showSlug ? humanizeSlug(showSlug) : "");
  const title = context ? `${formTitle} | ${context}` : `${formTitle} | EcoEvent 360`;
  const description = form?.description?.trim()
    || (context
      ? `Completa el formulario ${formTitle} para ${context}.`
      : `Completa el formulario ${formTitle} en EcoEvent 360.`);
  const imageUrl = absoluteUrl(form?.banner_url || DEFAULT_SHARE_IMAGE);
  const images = [{ url: imageUrl, width: 1200, height: 630, alt: title }];

  return {
    title,
    description,
    alternates: { canonical: canonicalUrl },
    openGraph: {
      type: "website",
      locale: "es_CL",
      siteName: "EcoEvent 360",
      url: canonicalUrl,
      title,
      description,
      images,
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: [imageUrl],
    },
  };
}

async function loadPublicForm(slug: string): Promise<PublicEventForm | null> {
  try {
    const response = await fetch(`${PUBLIC_API_URL}/public/forms/${encodeURIComponent(slug)}?lang=es`, {
      next: { revalidate: 300 },
    });
    if (!response.ok) return null;
    return await response.json() as PublicEventForm;
  } catch {
    return null;
  }
}

function absoluteUrl(value: string): string {
  try {
    return new URL(value, SITE_URL).toString();
  } catch {
    return SITE_URL;
  }
}

function humanizeSlug(slug: string): string {
  return decodeURIComponent(slug)
    .split("-")
    .filter(Boolean)
    .map((part, index) => {
      const normalized = part.toLowerCase();
      if (SHARE_TITLE_ACRONYMS.has(normalized)) return normalized.toUpperCase();
      if (index > 0 && SHARE_TITLE_LOWERCASE_WORDS.has(normalized)) return normalized;
      return `${normalized[0].toUpperCase()}${normalized.slice(1)}`;
    })
    .join(" ");
}
