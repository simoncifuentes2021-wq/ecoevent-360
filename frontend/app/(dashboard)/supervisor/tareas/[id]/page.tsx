import { redirect } from "next/navigation";

export default function SupervisorTaskDetailPage({ params }: { params: { id: string } }) {
  redirect(`/worker/tareas/${params.id}`);
}
