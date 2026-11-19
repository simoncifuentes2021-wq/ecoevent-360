import { FieldStaffPortal } from "@/components/volunteers/FieldStaffPortal";

export default function FieldStaffPage({ params }: { params: { eventId: string } }) {
  return <FieldStaffPortal eventId={params.eventId} />;
}
