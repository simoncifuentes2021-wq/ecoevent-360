"use client";

import PublicFormPage from "../page";

export default function ShowPublicFormPage({ params }: { params: { slug: string; formSlug: string } }) {
  return <PublicFormPage params={{ slug: params.formSlug }} />;
}
