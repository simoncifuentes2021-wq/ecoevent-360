"use client";

import { LogOut } from "lucide-react";

import { RoleBadge } from "@/components/common/RoleBadge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";

export function UserMenu() {
  const { user, logout } = useAuth();
  if (!user) return null;

  return (
    <div className="flex items-center gap-3">
      <div className="hidden text-right sm:block">
        <p className="text-sm font-semibold">{user.full_name}</p>
        <p className="text-xs text-muted-foreground">{user.email}</p>
      </div>
      <RoleBadge role={user.role} />
      <Button className="h-9 px-3" onClick={logout} type="button" variant="ghost">
        <LogOut className="h-4 w-4" />
        <span className="hidden lg:inline">Salir</span>
      </Button>
    </div>
  );
}
