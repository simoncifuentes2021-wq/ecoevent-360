"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { CheckCircle2, AlertTriangle } from "lucide-react";

import { cn } from "@/lib/utils";

type ToastTone = "success" | "error";

type ToastItem = {
  id: string;
  title: string;
  description?: string;
  tone: ToastTone;
};

type ToastContextValue = {
  toast: (input: Omit<ToastItem, "id">) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const toast = useCallback((input: Omit<ToastItem, "id">) => {
    const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    setItems((prev) => [...prev, { ...input, id }]);
    window.setTimeout(() => {
      setItems((prev) => prev.filter((item) => item.id !== id));
    }, 3500);
  }, []);

  const value = useMemo(() => ({ toast }), [toast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed inset-x-0 bottom-20 z-50 mx-auto flex max-w-2xl flex-col gap-2 px-4 md:bottom-6">
        {items.map((item) => (
          <div
            className={cn(
              "flex items-start gap-3 rounded-2xl border bg-white/95 p-4 text-sm shadow-xl backdrop-blur",
              item.tone === "success" && "border-emerald-200",
              item.tone === "error" && "border-rose-200"
            )}
            key={item.id}
            role="status"
          >
            <span className={cn(item.tone === "success" ? "text-emerald-700" : "text-rose-700")}>
              {item.tone === "success" ? <CheckCircle2 className="h-5 w-5" /> : <AlertTriangle className="h-5 w-5" />}
            </span>
            <div className="min-w-0">
              <p className="font-semibold text-slate-950">{item.title}</p>
              {item.description ? <p className="mt-0.5 text-slate-600">{item.description}</p> : null}
            </div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

