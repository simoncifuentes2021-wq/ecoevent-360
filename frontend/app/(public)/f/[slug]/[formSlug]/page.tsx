import type { Metadata } from "next";

import { PublicFormPage } from "@/components/public-forms/PublicFormPage";
import { publicFormMetadata } from "@/lib/publicFormMetadata";

export const dynamic = "force-dynamic";

export function generateMetadata({ params }: { params: { slug: string; formSlug: string } }): Promise<Metadata> {
  return publicFormMetadata(params.formSlug, `/f/${params.slug}/${params.formSlug}`, params.slug);
}

export default function ShowPublicFormRoute({ params }: { params: { formSlug: string } }) {
  return <PublicFormPage slug={params.formSlug} />;
}
