import type { ReactNode } from "react";

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
  actions
}: {
  eyebrow?: string;
  title: string;
  description: string;
  action?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
      <div>
        {eyebrow ? <p className="text-sm font-semibold uppercase text-primary">{eyebrow}</p> : null}
        <h1 className="mt-1 text-3xl font-bold tracking-tight">{title}</h1>
        <p className="mt-2 max-w-2xl text-muted-foreground">{description}</p>
      </div>
      {action || actions ? <div className="shrink-0">{action || actions}</div> : null}
    </div>
  );
}
