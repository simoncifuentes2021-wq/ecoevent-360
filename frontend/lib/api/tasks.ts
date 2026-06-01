import { api } from "@/lib/api";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { ListResponse } from "@/types/common";
import type { Task, TaskComplete, TaskCreate, TaskStatus, TaskUpdate } from "@/types/task";

function normalizeList(value: Task[] | ListResponse<Task>): ListResponse<Task> {
  if (Array.isArray(value)) return { items: value, total: value.length, page: 1, limit: value.length || 20 };
  return value;
}

export async function getEventTasks(eventId: string, params: Record<string, QueryValue> = {}) {
  const response = await api.get<Task[] | ListResponse<Task>>(`/events/${eventId}/tasks${toQuery(params)}`);
  return normalizeList(response);
}

export function getTask(taskId: string) {
  return api.get<Task>(`/tasks/${taskId}`);
}

export function createTask(eventId: string, data: TaskCreate) {
  return api.post<Task>(`/events/${eventId}/tasks`, data);
}

export function updateTask(taskId: string, data: TaskUpdate) {
  return api.patch<Task>(`/tasks/${taskId}`, data);
}

export function changeTaskStatus(taskId: string, status: TaskStatus) {
  return api.patch<Task>(`/tasks/${taskId}/status`, { status });
}

export function completeTask(taskId: string, data: TaskComplete = {}) {
  return api.patch<Task>(`/tasks/${taskId}/complete`, data);
}

export async function getMyTasks(params: Record<string, QueryValue> = {}) {
  const response = await api.get<Task[] | ListResponse<Task>>(`/me/tasks${toQuery(params)}`);
  return normalizeList(response);
}
