import { SupervisorLogbookDetail } from "@/components/logbooks/SupervisorLogbookDetail";

export default function Page({ params }: { params: { id: string } }) {
  return <SupervisorLogbookDetail id={params.id} />;
}
