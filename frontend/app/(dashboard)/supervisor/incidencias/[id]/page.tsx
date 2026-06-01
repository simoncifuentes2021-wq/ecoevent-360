import { redirect } from "next/navigation";

export default function SupervisorIncidentDetailPage({ params }: { params: { id: string } }) {
  redirect(`/worker/incidencias/${params.id}`);
}
