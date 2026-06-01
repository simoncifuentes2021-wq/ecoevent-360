import { redirect } from "next/navigation";

export default function SupervisorReportIncidentPage({ searchParams }: { searchParams: Record<string, string | string[] | undefined> }) {
  const params = new URLSearchParams();
  const eventId = searchParams.event_id;
  if (typeof eventId === "string" && eventId) params.set("event_id", eventId);
  redirect(`/worker/reportar-incidencia${params.size ? `?${params.toString()}` : ""}`);
}
