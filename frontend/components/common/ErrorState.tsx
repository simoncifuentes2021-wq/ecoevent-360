import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";

export function ErrorState({
  title = "No se pudo cargar",
  message,
  onRetry
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="rounded-lg border border-rose-200 bg-rose-50 p-5 text-rose-900">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5" />
        <div>
          <p className="font-semibold">{title}</p>
          <p className="mt-1 text-sm text-rose-700">{message}</p>
          {onRetry ? (
            <Button className="mt-4" type="button" variant="secondary" onClick={onRetry}>
              Reintentar
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
