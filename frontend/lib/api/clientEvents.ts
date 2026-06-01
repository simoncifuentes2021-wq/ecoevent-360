import { getCarbonRecords, getCarbonSummary } from "@/lib/api/carbon";
import { getEventDashboard } from "@/lib/api/dashboards";
import { getEventEvidences } from "@/lib/api/evidences";
import { getEvent, getEvents } from "@/lib/api/events";
import { getEventServices } from "@/lib/api/eventServices";
import { getEventIncidents } from "@/lib/api/incidents";
import { getEventReports } from "@/lib/api/reports";
import { getEventSurveys } from "@/lib/api/surveys";
import { getEventTasks } from "@/lib/api/tasks";
import { getWasteRecords, getWasteSummary } from "@/lib/api/waste";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { Event } from "@/types/event";

export function getClientEvents(params: Record<string, QueryValue> = {}) {
  return getEvents(params);
}

export function getClientEvent(eventId: string) {
  return getEvent(eventId);
}

export function getClientEventDashboard(eventId: string) {
  return getEventDashboard(eventId);
}

export function getClientEventReports(eventId: string) {
  return getEventReports(eventId);
}

export async function getClientEventFullReadModel(eventId: string) {
  const [event, dashboard, services, tasks, incidents, evidences, wasteSummary, wasteRecords, carbonSummary, carbonRecords, surveys, reports] = await Promise.allSettled([
    getEvent(eventId),
    getEventDashboard(eventId),
    getEventServices(eventId),
    getEventTasks(eventId),
    getEventIncidents(eventId),
    getEventEvidences(eventId),
    getWasteSummary(eventId),
    getWasteRecords(eventId),
    getCarbonSummary(eventId),
    getCarbonRecords(eventId),
    getEventSurveys(eventId),
    getEventReports(eventId)
  ]);

  return {
    event: event.status === "fulfilled" ? event.value : undefined,
    dashboard: dashboard.status === "fulfilled" ? dashboard.value : undefined,
    services: services.status === "fulfilled" ? services.value : [],
    tasks: tasks.status === "fulfilled" ? tasks.value.items : [],
    incidents: incidents.status === "fulfilled" ? incidents.value.items : [],
    evidences: evidences.status === "fulfilled" ? evidences.value.items : [],
    wasteSummary: wasteSummary.status === "fulfilled" ? wasteSummary.value : null,
    wasteRecords: wasteRecords.status === "fulfilled" ? wasteRecords.value.items : [],
    carbonSummary: carbonSummary.status === "fulfilled" ? carbonSummary.value : null,
    carbonRecords: carbonRecords.status === "fulfilled" ? carbonRecords.value.items : [],
    surveys: surveys.status === "fulfilled" ? surveys.value.items : [],
    reports: reports.status === "fulfilled" ? reports.value.items : []
  };
}
