import type { ReactNode } from "react";

import { RoleGuard } from "@/components/layout/RoleGuard";
import { WorkerBottomNav } from "@/components/worker/WorkerBottomNav";

export default function WorkerLayout({ children }: { children: ReactNode }) {
  return (
    <RoleGuard roles={["WORKER", "SUPERVISOR"]}>
      {children}
      <WorkerBottomNav />
    </RoleGuard>
  );
}
