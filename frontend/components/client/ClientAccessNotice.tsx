import { ShieldCheck } from "lucide-react";

export function ClientAccessNotice() {
  return (
    <div className="rounded-2xl border border-emerald-100 bg-emerald-50 p-4 text-sm text-emerald-900">
      <div className="flex gap-3">
        <ShieldCheck className="h-5 w-5 shrink-0" />
        <p>Estas viendo informacion en modo cliente. Las acciones administrativas y datos internos del equipo operativo permanecen ocultos.</p>
      </div>
    </div>
  );
}
