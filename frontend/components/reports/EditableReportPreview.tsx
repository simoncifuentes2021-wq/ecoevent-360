"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronUp, Lock, Maximize2, Redo2, RotateCcw, Undo2, Unlock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getReportLayoutOverrides, resetReportLayoutOverride, saveReportLayoutOverride } from "@/lib/api/reports";
import type { ReportLayoutOverride, ReportPagePlan } from "@/types/report";

const cleanOverride = (elementKey: string): ReportLayoutOverride => ({ element_key: elementKey, page_key: null, x_offset: 0, y_offset: 0, width_scale: 1, height_scale: 1, rotation: 0, z_index: 0, locked: false, visible: true });
type HistoryEntry = { before?: ReportLayoutOverride; after?: ReportLayoutOverride };

export function EditableReportPreview({ reportId, html, plan, onSelectSection, onSaved }: { reportId: string; html: string; plan?: ReportPagePlan; onSelectSection: (key: string) => void; onSaved: () => Promise<void> }) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const overridesRef = useRef<Record<string, ReportLayoutOverride>>({});
  const [overrides, setOverrides] = useState<Record<string, ReportLayoutOverride>>({});
  const [selected, setSelected] = useState<string>();
  const [editing, setEditing] = useState(false);
  const [zoom, setZoom] = useState(55);
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [future, setFuture] = useState<HistoryEntry[]>([]);
  const pages = plan?.pages || [];

  const loadOverrides = useCallback(async () => {
    const items = await getReportLayoutOverrides(reportId);
    const next = Object.fromEntries(items.map(item => [item.element_key, item]));
    overridesRef.current = next;
    setOverrides(next);
  }, [reportId]);
  useEffect(() => { void loadOverrides(); }, [loadOverrides]);

  const commit = useCallback(async (after: ReportLayoutOverride, before?: ReportLayoutOverride, remember = true) => {
    setBusy(true);
    try {
      const saved = await saveReportLayoutOverride(reportId, after);
      const next = { ...overridesRef.current, [saved.element_key]: saved };
      overridesRef.current = next; setOverrides(next);
      if (remember) { setHistory(items => [...items, { before, after: saved }]); setFuture([]); }
      await onSaved();
    } finally { setBusy(false); }
  }, [onSaved, reportId]);

  const remove = useCallback(async (elementKey: string, remember = true) => {
    const before = overridesRef.current[elementKey];
    setBusy(true);
    try {
      await resetReportLayoutOverride(reportId, elementKey);
      const next = { ...overridesRef.current }; delete next[elementKey];
      overridesRef.current = next; setOverrides(next);
      if (remember) { setHistory(items => [...items, { before }]); setFuture([]); }
      await onSaved();
    } finally { setBusy(false); }
  }, [onSaved, reportId]);

  const decorate = useCallback(() => {
    const doc = iframeRef.current?.contentDocument;
    if (!doc) return;
    doc.getElementById("report-position-editor")?.remove();
    if (!editing) return;
    const style = doc.createElement("style");
    style.id = "report-position-editor";
    style.textContent = `[data-report-element-key]{cursor:move!important;outline:1px dashed rgba(5,150,105,.7);outline-offset:2px}[data-report-element-key][data-editor-selected="true"]{outline:3px solid #059669!important;outline-offset:3px}.report-resize-handle{position:absolute!important;right:-8px!important;bottom:-8px!important;width:16px!important;height:16px!important;border:2px solid white!important;background:#059669!important;border-radius:3px!important;z-index:2147483647!important;cursor:nwse-resize!important}`;
    doc.head.appendChild(style);
    const nodes = Array.from(doc.querySelectorAll<HTMLElement>("[data-report-element-key]"));
    nodes.forEach(node => {
      const key = node.dataset.reportElementKey!;
      node.dataset.editorSelected = String(key === selected);
      node.querySelector(":scope > .report-resize-handle")?.remove();
      node.onclick = event => { event.preventDefault(); event.stopPropagation(); setSelected(key); };
      node.onpointerdown = event => {
        if ((event.target as HTMLElement).classList.contains("report-resize-handle")) return;
        const current = overridesRef.current[key] || cleanOverride(key);
        if (current.locked) { setSelected(key); return; }
        event.preventDefault(); event.stopPropagation(); setSelected(key);
        const startX = event.clientX; const startY = event.clientY; const original = node.style.transform;
        const move = (pointer: PointerEvent) => { node.style.transform = `${original} translate(${pointer.clientX - startX}px,${pointer.clientY - startY}px)`; };
        const up = (pointer: PointerEvent) => {
          doc.removeEventListener("pointermove", move); doc.removeEventListener("pointerup", up);
          const after = { ...current, x_offset: current.x_offset + pointer.clientX - startX, y_offset: current.y_offset + pointer.clientY - startY };
          void commit(after, overridesRef.current[key]);
        };
        doc.addEventListener("pointermove", move); doc.addEventListener("pointerup", up);
      };
      if (key === selected && !(overridesRef.current[key]?.locked)) {
        const handle = doc.createElement("span"); handle.className = "report-resize-handle";
        handle.onpointerdown = event => {
          event.preventDefault(); event.stopPropagation();
          const current = overridesRef.current[key] || cleanOverride(key);
          const rect = node.getBoundingClientRect(); const startX = event.clientX; const startY = event.clientY; const original = node.style.transform;
          const move = (pointer: PointerEvent) => { const sx = Math.max(.1, (rect.width + pointer.clientX - startX) / rect.width); const sy = Math.max(.1, (rect.height + pointer.clientY - startY) / rect.height); node.style.transform = `${original} scale(${sx},${sy})`; };
          const up = (pointer: PointerEvent) => {
            doc.removeEventListener("pointermove", move); doc.removeEventListener("pointerup", up);
            const after = { ...current, width_scale: Math.max(.1, Math.min(5, current.width_scale * (rect.width + pointer.clientX - startX) / rect.width)), height_scale: Math.max(.1, Math.min(5, current.height_scale * (rect.height + pointer.clientY - startY) / rect.height)) };
            void commit(after, overridesRef.current[key]);
          };
          doc.addEventListener("pointermove", move); doc.addEventListener("pointerup", up);
        };
        node.appendChild(handle);
      }
    });
  }, [commit, editing, selected]);
  useEffect(() => { decorate(); }, [decorate, html]);

  async function patchSelected(patch: Partial<ReportLayoutOverride>) { if (!selected) return; const before = overridesRef.current[selected]; await commit({ ...(before || cleanOverride(selected)), ...patch }, before); }
  async function resetAll() { setBusy(true); try { await resetReportLayoutOverride(reportId); overridesRef.current = {}; setOverrides({}); setHistory([]); setFuture([]); setSelected(undefined); await onSaved(); } finally { setBusy(false); } }
  async function undo() { const entry = history.at(-1); if (!entry) return; setHistory(items => items.slice(0, -1)); setFuture(items => [...items, entry]); if (entry.before) await commit(entry.before, entry.after, false); else if (entry.after) await remove(entry.after.element_key, false); }
  async function redo() { const entry = future.at(-1); if (!entry) return; setFuture(items => items.slice(0, -1)); setHistory(items => [...items, entry]); if (entry.after) await commit(entry.after, entry.before, false); else if (entry.before) await remove(entry.before.element_key, false); }
  const current = selected ? overrides[selected] || cleanOverride(selected) : undefined;
  const changeZoom = (next: number) => setZoom(Math.min(100, Math.max(30, next)));
  const goPage = (number: number, sectionKey?: string) => { if (sectionKey) onSelectSection(sectionKey); iframeRef.current?.contentWindow?.scrollTo({ top: (number - 1) * 1123, behavior: "smooth" }); };

  return <div className="sticky top-24 max-h-[calc(100vh-7rem)] overflow-auto rounded-2xl bg-slate-200 p-3" data-testid="live-a4-preview"><div className="mb-3 flex flex-wrap items-center gap-2 rounded-xl bg-white p-2 shadow-sm"><button type="button" aria-label="Alejar vista previa" className="h-8 rounded-lg border px-3 font-bold" onClick={() => changeZoom(zoom - 10)}>−</button><input aria-label="Zoom de vista previa" type="range" min="30" max="100" step="5" value={zoom} onChange={event => changeZoom(Number(event.target.value))} className="min-w-20 flex-1"/><button type="button" aria-label="Acercar vista previa" className="h-8 rounded-lg border px-3 font-bold" onClick={() => changeZoom(zoom + 10)}>+</button><output className="w-12 text-center text-xs font-bold">{zoom}%</output><Button size="sm" variant={editing ? "primary" : "secondary"} onClick={() => { setEditing(value => !value); setSelected(undefined); }}><Maximize2 className="h-4 w-4"/>{editing ? "Terminar edición" : "Editar posiciones"}</Button></div>{editing ? <div className="mb-3 rounded-xl border border-emerald-200 bg-white p-2"><div className="flex flex-wrap gap-1"><Button size="sm" variant="ghost" disabled={busy || !history.length} onClick={() => void undo()}><Undo2 className="h-4 w-4"/>Deshacer</Button><Button size="sm" variant="ghost" disabled={busy || !future.length} onClick={() => void redo()}><Redo2 className="h-4 w-4"/>Rehacer</Button>{current ? <><Button size="sm" variant="ghost" disabled={busy} onClick={() => void patchSelected({ locked: !current.locked })}>{current.locked ? <Unlock className="h-4 w-4"/> : <Lock className="h-4 w-4"/>}{current.locked ? "Desbloquear" : "Bloquear"}</Button><Button size="sm" variant="ghost" disabled={busy} onClick={() => void patchSelected({ z_index: current.z_index + 1 })}><ChevronUp className="h-4 w-4"/>Adelante</Button><Button size="sm" variant="ghost" disabled={busy} onClick={() => void patchSelected({ z_index: current.z_index - 1 })}><ChevronDown className="h-4 w-4"/>Atrás</Button><Button size="sm" variant="ghost" disabled={busy} onClick={() => void remove(current.element_key)}><RotateCcw className="h-4 w-4"/>Restablecer elemento</Button></> : null}<Button size="sm" variant="ghost" className="ml-auto text-red-700" disabled={busy || !Object.keys(overrides).length} onClick={() => void resetAll()}>Restablecer todo</Button></div><p className="mt-2 px-2 text-xs text-slate-600">Selecciona un KPI, gráfico o imagen del reporte. Arrastra para mover y usa el control verde para redimensionar. Los datos y el diseño profesional se conservan.</p>{selected ? <p className="mt-1 truncate px-2 text-[10px] font-mono text-emerald-800">{selected}</p> : null}</div> : null}<div className="mb-3 flex gap-2 overflow-x-auto" aria-label="Páginas del reporte">{pages.map(page => <button key={page.number} className="shrink-0 rounded-lg bg-white px-3 py-2 text-left text-xs shadow-sm" onClick={() => goPage(page.number, page.section_keys[0])}><b>{page.number}</b> {page.title}</button>)}</div>{html ? <div className="overflow-auto rounded-lg bg-slate-300 p-3"><div className="mx-auto" style={{ width: `${794 * zoom / 100}px`, height: `${1123 * zoom / 100}px` }}><iframe ref={iframeRef} onLoad={decorate} title="Vista previa exacta y editable del reporte" sandbox="allow-same-origin" srcDoc={html} className="origin-top-left border-0 bg-white shadow-xl" style={{ width: "794px", height: "1123px", transform: `scale(${zoom / 100})` }}/></div></div> : <div className="grid aspect-[210/297] place-items-center bg-white text-sm text-slate-500">Preparando vista previa editorial…</div>}</div>;
}
