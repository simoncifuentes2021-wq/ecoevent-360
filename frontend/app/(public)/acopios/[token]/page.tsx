import type { Metadata } from "next";
import { PublicWasteEntry } from "@/components/waste/PublicWasteEntry";

export const metadata: Metadata = { title: "Registro de acopio · Greenway", robots: { index: false, follow: false } };

export default function PublicWastePage({ params }: { params: { token: string } }) {
  return <>
    <link rel="manifest" href={`/acopios/${encodeURIComponent(params.token)}/manifest.webmanifest`} />
    <PublicWasteEntry token={params.token} />
  </>;
}
