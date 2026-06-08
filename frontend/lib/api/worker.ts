import { api } from "@/lib/api";
import type { WorkerDashboard } from "@/types/dashboard";

export async function getWorkerDashboard() {
  return api.get<WorkerDashboard>("/dashboard/worker");
}
