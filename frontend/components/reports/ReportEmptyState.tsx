import { FileText } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";

export function ReportEmptyState() {
  return <EmptyState icon={<FileText className="h-10 w-10" />} title="Aun no hay reportes disponibles" description="Genera el reporte final cuando la informacion operacional, ambiental y de formularios este lista." />;
}
