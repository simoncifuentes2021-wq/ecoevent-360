"use client";

import { PlayCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { TaskStatus } from "@/types/task";

export function ChangeTaskStatusButton({ status, onChange }: { status: TaskStatus; onChange: (status: TaskStatus) => void }) {
  if (status !== "PENDING") return null;
  return <Button type="button" onClick={() => onChange("IN_PROGRESS")}><PlayCircle className="h-4 w-4" />Iniciar</Button>;
}
