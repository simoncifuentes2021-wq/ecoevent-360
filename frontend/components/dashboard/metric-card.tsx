import { Card, CardContent } from "@/components/ui/card";

export function MetricCard({ label, value, trend }: { label: string; value: string; trend: string }) {
  return (
    <Card>
      <CardContent className="space-y-2">
        <p className="text-sm text-muted-foreground">{label}</p>
        <div className="flex items-end justify-between gap-3">
          <p className="text-3xl font-bold">{value}</p>
          <span className="rounded-sm bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-700">
            {trend}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

