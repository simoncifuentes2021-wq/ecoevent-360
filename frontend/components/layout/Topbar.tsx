"use client";

import { usePathname } from "next/navigation";

import { MobileSidebar } from "@/components/layout/MobileSidebar";
import { UserMenu } from "@/components/layout/UserMenu";
import type { AuthUser } from "@/types/auth";

function titleFromPath(pathname: string) {
  const parts = pathname.split("/").filter(Boolean);
  if (parts.length === 0) return "Inicio";
  return parts[parts.length - 1].replaceAll("-", " ");
}

export function Topbar({ user }: { user: AuthUser }) {
  const pathname = usePathname();
  const title = titleFromPath(pathname);

  return (
    <header className="sticky top-0 z-30 border-b bg-background/88 px-4 py-3 backdrop-blur md:px-8">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <MobileSidebar user={user} />
          <div>
            <p className="text-xs font-medium uppercase text-muted-foreground">EcoEvent 360</p>
            <h1 className="capitalize text-lg font-bold md:text-xl">{title}</h1>
          </div>
        </div>
        <UserMenu />
      </div>
    </header>
  );
}
