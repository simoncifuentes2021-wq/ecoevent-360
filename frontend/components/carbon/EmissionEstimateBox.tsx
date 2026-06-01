import { Calculator } from "lucide-react";

import { formatKgCO2e } from "@/lib/normalizers/carbon";

export function EmissionEstimateBox({ activityValue, factorValue }: { activityValue: number; factorValue: number }) {
  const estimate = Number(activityValue || 0) * Number(factorValue || 0);
  return <div className="flex items-start gap-3 rounded-2xl bg-emerald-50 p-4 text-sm text-emerald-900"><Calculator className="mt-0.5 h-5 w-5" /><div><p className="font-bold">Estimacion previa: {formatKgCO2e(estimate)}</p><p className="mt-1">El valor oficial depende del calculo y validacion del backend.</p></div></div>;
}
