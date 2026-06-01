import type { LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

export function KpiCard({
  title,
  value,
  description,
  icon: Icon,
  tone = "emerald"
}: {
  title: string;
  value: string | number;
  description: string;
  icon: LucideIcon;
  tone?: "emerald" | "blue" | "lime" | "slate";
}) {
  const color = {
    emerald: "bg-emerald-50 text-emerald-700",
    blue: "bg-cyan-50 text-cyan-700",
    lime: "bg-lime-50 text-lime-700",
    slate: "bg-slate-100 text-slate-700"
  }[tone];

  return (
    <Card className="overflow-hidden">
      <CardContent className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-muted-foreground">{title}</p>
          <p className="mt-2 text-3xl font-bold tracking-tight">{value}</p>
          <p className="mt-2 text-xs text-muted-foreground">{description}</p>
        </div>
        <span className={`grid h-11 w-11 shrink-0 place-items-center rounded-lg ${color}`}>
          <Icon className="h-5 w-5" />
        </span>
      </CardContent>
    </Card>
  );
}
