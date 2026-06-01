"use client";

import type { ReactNode } from "react";

export function ModalShell({
  title,
  description,
  children,
  onClose
}: {
  title: string;
  description?: string;
  children: ReactNode;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-3 sm:p-4">
      <div className="max-h-[90vh] w-full max-w-xl overflow-y-auto overflow-x-hidden rounded-3xl border border-slate-200 bg-white p-5 shadow-2xl sm:p-6">
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-slate-950">{title}</h2>
            {description ? <p className="mt-1 text-sm text-slate-600">{description}</p> : null}
          </div>
          <button className="rounded-full px-3 py-1 text-xl text-slate-400 hover:bg-slate-100" onClick={onClose} type="button">
            ×
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
