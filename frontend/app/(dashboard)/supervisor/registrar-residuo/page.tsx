import { redirect } from "next/navigation";

export default function SupervisorWastePage({ searchParams }: { searchParams: Record<string, string | string[] | undefined> }) {
  const params = new URLSearchParams();
  for (const key of ["event_id", "zone_id"]) {
    const value = searchParams[key];
    if (typeof value === "string" && value) params.set(key, value);
  }
  redirect(`/worker/registrar-residuo${params.size ? `?${params.toString()}` : ""}`);
}
