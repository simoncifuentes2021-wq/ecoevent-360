import { ExternalLink, QrCode } from "lucide-react";

import { Button } from "@/components/ui/button";

export function QrFallbackNotice({ googleFormUrl }: { googleFormUrl?: string | null }) {
  return (
    <div className="rounded-2xl border border-dashed border-amber-300 bg-amber-50 p-4">
      <div className="flex gap-3">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-white text-amber-700"><QrCode className="h-5 w-5" /></span>
        <div>
          <h3 className="font-bold text-amber-950">QR automatico no disponible</h3>
          <p className="mt-1 text-sm text-amber-800">
            La generacion automatica de QR aun no esta disponible en el backend. Mientras tanto, puedes generar el QR desde Google Forms o usar el enlace publico.
          </p>
          {googleFormUrl ? <Button className="mt-3" onClick={() => window.open(googleFormUrl, "_blank")} type="button" variant="secondary"><ExternalLink className="h-4 w-4" />Abrir Google Form</Button> : null}
        </div>
      </div>
    </div>
  );
}
