"use client";

import { FileText } from "lucide-react";

import { Button } from "@/components/ui/button";

export function GenerateReportButton({ onClick }: { onClick: () => void }) {
  return <Button onClick={onClick} type="button"><FileText className="h-4 w-4" />Generar reporte final</Button>;
}
