import { ReportBuilder } from "@/components/reports/ReportBuilder";

export default function ReportEditorPage({ params }: { params: { reportId: string } }) {
  return <ReportBuilder reportId={params.reportId} />;
}
