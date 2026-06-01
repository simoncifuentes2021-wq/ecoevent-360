"use client";

import type { ReactNode } from "react";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { LoadingState } from "@/components/common/LoadingState";
import { defaultRouteForRole } from "@/lib/auth";
import { useAuth } from "@/hooks/useAuth";
import type { UserRole } from "@/types/roles";

export function RoleGuard({ children, roles }: { children: ReactNode; roles?: UserRole[] }) {
  const router = useRouter();
  const { user, loading, isAuthenticated } = useAuth();

  useEffect(() => {
    if (loading) return;
    if (!isAuthenticated || !user) {
      router.replace("/login");
      return;
    }
    if (roles && !roles.includes(user.role)) {
      router.replace(defaultRouteForRole(user.role));
    }
  }, [isAuthenticated, loading, roles, router, user]);

  if (loading || !isAuthenticated || !user) {
    return <LoadingState label="Validando sesion..." />;
  }

  if (roles && !roles.includes(user.role)) {
    return <LoadingState label="Redirigiendo..." />;
  }

  return children;
}
