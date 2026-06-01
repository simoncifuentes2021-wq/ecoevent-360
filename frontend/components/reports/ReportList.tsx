"use client";

import { ReportCard } from "@/components/reports/ReportCard";
import { ReportTable } from "@/components/reports/ReportTable";
import type { Report } from "@/types/report";

export function ReportList(props: {
  reports: Report[];
  loading?: boolean;
  error?: string | null;
  canDelete?: boolean;
  canDeliver?: boolean;
  onView: (report: Report) => void;
  onDelete: (report: Report) => void;
  onDeliver: (report: Report) => void;
}) {
  return (
    <div>
      <div className="grid gap-3 md:hidden">
        {props.reports.map((report) => <ReportCard key={report.id} report={report} canDelete={props.canDelete} canDeliver={props.canDeliver} onDelete={props.onDelete} onDeliver={props.onDeliver} onView={props.onView} />)}
      </div>
      <div className="hidden md:block">
        <ReportTable {...props} />
      </div>
    </div>
  );
}
