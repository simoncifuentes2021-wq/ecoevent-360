import { api } from "@/lib/api";
import type { ListResponse } from "@/types/common";
import type { ShowOperationalSummary, ShowStaffAssignment, ShowStaffInput } from "@/types/showOperations";

export function getShowStaff(sessionId: string) {
  return api.get<ListResponse<ShowStaffAssignment>>(`/event-sessions/${sessionId}/staff`);
}

export function assignShowStaff(sessionId: string, data: ShowStaffInput) {
  return api.post<ShowStaffAssignment>(`/event-sessions/${sessionId}/staff`, data);
}

export function updateShowStaff(assignmentId: string, data: Omit<ShowStaffInput, "event_staff_id">) {
  return api.patch<ShowStaffAssignment>(`/event-session-staff/${assignmentId}`, data);
}

export function removeShowStaff(assignmentId: string) {
  return api.delete<void>(`/event-session-staff/${assignmentId}`);
}

export function getShowOperationalSummary(sessionId: string) {
  return api.get<ShowOperationalSummary>(`/event-sessions/${sessionId}/operations/summary`);
}
