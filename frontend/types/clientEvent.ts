import type { CarbonSummary } from "@/types/carbon";
import type { Event } from "@/types/event";
import type { EventService } from "@/types/eventService";
import type { EventDashboard } from "@/types/dashboard";
import type { Report } from "@/types/report";
import type { SurveySummary } from "@/types/survey";
import type { WasteSummary } from "@/types/waste";

export type ClientEventDetail = {
  event?: Event;
  services: EventService[];
  dashboard?: EventDashboard;
  waste_summary?: WasteSummary;
  carbon_summary?: CarbonSummary;
  surveys_summary?: SurveySummary;
  reports: Report[];
};

export type ClientEventTab = {
  key: string;
  label: string;
  visible: boolean;
  count?: number;
};
