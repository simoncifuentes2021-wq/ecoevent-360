"use client";

import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { usePathname } from "next/navigation";

import { LoadingState } from "@/components/common/LoadingState";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { useAuth } from "@/hooks/useAuth";
import { defaultRouteForRole } from "@/lib/auth";

export function AppLayout({ children }: { children: ReactNode }) {
  const { user, loading, isAuthenticated } = useAuth();
  const pathname = usePathname();

  if (loading || !isAuthenticated || !user) {
    return <LoadingState label="Preparando tu espacio de trabajo..." />;
  }

  const allowedPrefixes =
    user.role === "WORKER" ? ["/worker"] :
    user.role === "CLIENT" ? ["/client"] :
    user.role === "SUPERVISOR" ? ["/supervisor", "/worker", "/alerts"] :
    user.role === "LOGISTICS_OPERATOR" ? ["/logistica"] :
    ["/admin", "/reports", "/settings", "/alerts", "/worker"];

  if (!allowedPrefixes.some((prefix) => pathname.startsWith(prefix))) {
    if (typeof window !== "undefined") window.location.href = defaultRouteForRole(user.role);
    return <LoadingState label="Redirigiendo..." />;
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,#e8fff4_0,#f6f8fb_35%,#eef3f6_100%)] md:grid md:grid-cols-[18rem_1fr]">
      <div className="hidden md:block">
        <Sidebar user={user} />
      </div>
      <div className="min-w-0">
        <Topbar user={user} />
        <motion.main
          animate={{ opacity: 1, y: 0 }}
          className="px-4 py-5 md:px-8 md:py-7"
          initial={{ opacity: 0, y: 8 }}
          transition={{ duration: 0.22 }}
        >
          {children}
        </motion.main>
      </div>
    </div>
  );
}
