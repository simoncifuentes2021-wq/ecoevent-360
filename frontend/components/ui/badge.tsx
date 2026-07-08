import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center whitespace-nowrap rounded-sm px-2 py-1 text-xs font-semibold",
        tone === "success" && "bg-emerald-50 text-emerald-700",
        tone === "warning" && "bg-amber-50 text-amber-700",
        tone === "danger" && "bg-rose-50 text-rose-700",
        tone === "neutral" && "bg-slate-100 text-slate-700"
      )}
    >
      {children}
    </span>
  );
}
