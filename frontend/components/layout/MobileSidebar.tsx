"use client";

import { Menu } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Sidebar } from "@/components/layout/Sidebar";
import type { AuthUser } from "@/types/auth";

export function MobileSidebar({ user }: { user: AuthUser }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button className="h-9 px-3 md:hidden" onClick={() => setOpen(true)} type="button" variant="secondary">
        <Menu className="h-4 w-4" />
      </Button>
      {open ? (
        <div className="fixed inset-0 z-50 md:hidden">
          <button
            aria-label="Cerrar menu"
            className="absolute inset-0 bg-slate-950/45"
            onClick={() => setOpen(false)}
            type="button"
          />
          <div className="relative h-full w-72">
            <Sidebar onNavigate={() => setOpen(false)} user={user} />
          </div>
        </div>
      ) : null}
    </>
  );
}
