"use client";

import { Button } from "@/components/ui/button";
import type { TaskStatus } from "@/types/task";

const filters: Array<{ label: string; value: "" | TaskStatus | "TODAY" }> = [
  { label: "Todas", value: "" },
  { label: "Pendientes", value: "PENDING" },
  { label: "En progreso", value: "IN_PROGRESS" },
  { label: "Completadas", value: "COMPLETED" },
  { label: "Observadas", value: "OBSERVED" },
  { label: "Hoy", value: "TODAY" }
];

export function WorkerTaskFilters({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return <div className="flex gap-2 overflow-x-auto pb-1">{filters.map((item) => <Button key={item.value || "all"} size="sm" variant={value === item.value ? "primary" : "secondary"} onClick={() => onChange(item.value)}>{item.label}</Button>)}</div>;
}
