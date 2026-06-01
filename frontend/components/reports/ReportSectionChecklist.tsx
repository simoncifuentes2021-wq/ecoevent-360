import { AlertTriangle, CheckCircle, CircleDashed } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { ReportSectionStatus } from "@/types/report";

export function ReportSectionChecklist({ sections }: { sections: ReportSectionStatus[] }) {
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {sections.map((section) => {
        const Icon = section.status === "complete" ? CheckCircle : section.status === "partial" ? CircleDashed : AlertTriangle;
        return (
          <div className="flex gap-3 rounded-2xl border border-slate-200 bg-white p-4" key={section.key}>
            <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ${section.status === "complete" ? "bg-emerald-50 text-emerald-700" : section.status === "partial" ? "bg-amber-50 text-amber-700" : "bg-slate-100 text-slate-500"}`}>
              <Icon className="h-5 w-5" />
            </span>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h4 className="font-semibold text-slate-950">{section.label}</h4>
                <Badge tone={section.status === "complete" ? "success" : section.status === "partial" ? "warning" : "neutral"}>
                  {section.status === "complete" ? "Con datos" : section.status === "partial" ? "Parcial" : "Sin datos"}
                </Badge>
              </div>
              <p className="mt-1 text-sm text-slate-600">{section.description}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
