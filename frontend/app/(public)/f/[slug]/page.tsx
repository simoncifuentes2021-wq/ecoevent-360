import type { Metadata } from "next";

import { PublicFormPage } from "@/components/public-forms/PublicFormPage";
import { publicFormMetadata } from "@/lib/publicFormMetadata";

export const dynamic = "force-dynamic";

export function generateMetadata({ params }: { params: { slug: string } }): Promise<Metadata> {
  return publicFormMetadata(params.slug, `/f/${params.slug}`);
}

export default function PublicFormRoute({ params }: { params: { slug: string } }) {
  return <PublicFormPage slug={params.slug} />;
}
