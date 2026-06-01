import { ApiError, api } from "@/lib/api";
import type { WorkerDashboard } from "@/types/dashboard";

export async function getWorkerDashboard() {
  try {
    return await api.get<WorkerDashboard>("/dashboard/worker");
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

