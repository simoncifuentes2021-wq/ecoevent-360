import { PublicVolunteerImpactPage } from "@/components/volunteers/PublicVolunteerPages";

export default function Page({ params }: { params: { token: string } }) {
  return <PublicVolunteerImpactPage token={params.token} />;
}
