import { api } from "@/lib/api";
import { toQuery } from "@/lib/api/query";
import type { EnvironmentalAction, EnvironmentalActionInput, EnvironmentalMethodology, EnvironmentalSummary } from "@/types/environmental";

export const getEnvironmentalSummary = (eventId: string, sessionId?: string) => api.get<EnvironmentalSummary>(`/events/${eventId}/environmental-impact/summary${toQuery({ session_id: sessionId })}`);
export const getEnvironmentalActions = (eventId: string, sessionId?: string) => api.get<{items: EnvironmentalAction[]; total: number}>(`/events/${eventId}/environmental-actions${toQuery({ session_id: sessionId })}`);
export const createEnvironmentalAction = (eventId: string, data: EnvironmentalActionInput) => api.post<EnvironmentalAction>(`/events/${eventId}/environmental-actions`, data);
export const updateEnvironmentalAction = (eventId: string, actionId: string, data: Partial<EnvironmentalActionInput>) => api.patch<EnvironmentalAction>(`/events/${eventId}/environmental-actions/${actionId}`, data);
export const deleteEnvironmentalAction = (eventId: string, actionId: string) => api.delete<void>(`/events/${eventId}/environmental-actions/${actionId}`);
export const calculateEnvironmentalAction = (eventId: string, actionId: string) => api.post<EnvironmentalAction>(`/events/${eventId}/environmental-actions/${actionId}/calculate`, {});
export const getEnvironmentalMethodologies = () => api.get<EnvironmentalMethodology[]>("/environmental-impact/methodologies");
export const getEnvironmentalEquivalences = () => api.get<Array<{id: string; name: string; metric_source: string; factor: string; unit: string; source: string; year: number; is_active: boolean}>>("/environmental-impact/equivalences");
