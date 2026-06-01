import { redirect } from "next/navigation";

export default function SupervisorUploadEvidencePage({ searchParams }: { searchParams: Record<string, string | string[] | undefined> }) {
  const params = new URLSearchParams();
  for (const key of ["event_id", "task_id", "incident_id"]) {
    const value = searchParams[key];
    if (typeof value === "string" && value) params.set(key, value);
  }
  redirect(`/worker/subir-evidencia${params.size ? `?${params.toString()}` : ""}`);
}
