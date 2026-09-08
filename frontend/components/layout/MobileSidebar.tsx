"use client";

import { Menu, X } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Sidebar } from "@/components/layout/Sidebar";
import type { AuthUser } from "@/types/auth";

export function MobileSidebar({ user }: { user: AuthUser }) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function closeWithEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }

    window.addEventListener("keydown", closeWithEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", closeWithEscape);
    };
  }, [open]);

  return (
    <>
      <Button
        aria-controls="mobile-navigation"
        aria-expanded={open}
        aria-label="Abrir menú"
        className="h-10 w-10 p-0 md:hidden"
        onClick={() => setOpen(true)}
        type="button"
        variant="secondary"
      >
        <Menu className="h-4 w-4" />
      </Button>
      {open ? (
        <div className="fixed inset-0 z-50 h-[100dvh] overflow-hidden md:hidden">
          <button
            aria-label="Cerrar menú"
            className="absolute inset-0 bg-slate-950/45"
            onClick={() => setOpen(false)}
            type="button"
          />
          <div
            aria-label="Menú principal"
            aria-modal="true"
            className="relative h-[100dvh] w-[min(20rem,calc(100vw-2.5rem))] overflow-hidden pb-[env(safe-area-inset-bottom)] pt-[env(safe-area-inset-top)] shadow-2xl"
            id="mobile-navigation"
            role="dialog"
          >
            <button
              aria-label="Cerrar menú"
              className="absolute right-3 top-[max(0.75rem,env(safe-area-inset-top))] z-10 grid h-10 w-10 place-items-center rounded-full border bg-white text-slate-700 shadow-sm"
              onClick={() => setOpen(false)}
              type="button"
            >
              <X className="h-5 w-5" />
            </button>
            <Sidebar onNavigate={() => setOpen(false)} user={user} />
          </div>
        </div>
      ) : null}
    </>
  );
}
