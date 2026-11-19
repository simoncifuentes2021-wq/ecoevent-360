import { PublicVolunteerRegistrationPage } from "@/components/volunteers/PublicVolunteerPages";

export default function Page({ params }: { params: { slug: string } }) {
  return <PublicVolunteerRegistrationPage slug={params.slug} />;
}
