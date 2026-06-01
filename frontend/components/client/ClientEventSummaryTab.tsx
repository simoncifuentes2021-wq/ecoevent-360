"use client";

import { EventDashboardTab } from "@/components/dashboard/EventDashboardTab";

export function ClientEventSummaryTab({ eventId }: { eventId: string }) {
  return <EventDashboardTab eventId={eventId} />;
}
