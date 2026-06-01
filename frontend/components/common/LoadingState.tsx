import { Loader2 } from "lucide-react";

export function LoadingState({ label = "Cargando informacion..." }: { label?: string }) {
  return (
    <div className="grid min-h-[220px] place-items-center rounded-lg border bg-white/80 p-8">
      <div className="flex items-center gap-3 text-sm font-medium text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin text-primary" />
        {label}
      </div>
    </div>
  );
}
