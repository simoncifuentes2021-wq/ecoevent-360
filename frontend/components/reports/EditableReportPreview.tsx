"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronUp, Lock, Maximize2, Redo2, RotateCcw, Undo2, Unlock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getReportLayoutOverrides, resetReportLayoutOverride, saveReportLayoutOverride } from "@/lib/api/reports";
import type { ReportLayoutOverride, ReportPagePlan } from "@/types/report";

const cleanOverride = (elementKey: string): ReportLayoutOverride => ({ element_key: elementKey, page_key: null, x_offset: 0, y_offset: 0, width_scale: 1, height_scale: 1, box_width: null, box_height: null, rotation: 0, z_index: 0, locked: false, visible: true });
const clamp = (value: number, minimum: number, maximum: number) => Math.min(maximum, Math.max(minimum, value));
function hasSevereOverlap(node: HTMLElement, next: DOMRect, doc: Document): boolean {
  return Array.from(doc.querySelectorAll<HTMLElement>("[data-report-element-key]"))
    .filter(other => other !== node && other.closest(".page,.cover") === node.closest(".page,.cover"))
    .some(other => {
      const rect = other.getBoundingClientRect();
      const width = Math.max(0, Math.min(next.right, rect.right) - Math.max(next.left, rect.left));
      const height = Math.max(0, Math.min(next.bottom, rect.bottom) - Math.max(next.top, rect.top));
      const smallest = Math.min(next.width * next.height, rect.width * rect.height);
      return smallest > 0 && width * height / smallest > .6;
    });
}
type HistoryEntry = { before?: ReportLayoutOverride; after?: ReportLayoutOverride };
type ViewportAnchor = { x: number; y: number; elementKey?: string; elementTop?: number };

export function EditableReportPreview({ reportId, html, plan, onSelectSection, onSaved }: { reportId: string; html: string; plan?: ReportPagePlan; onSelectSection: (key: string) => void; onSaved: (refreshHtml?: boolean) => Promise<void> }) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const overridesRef = useRef<Record<string, ReportLayoutOverride>>({});
  const pendingViewportRef = useRef<ViewportAnchor>();
  const [overrides, setOverrides] = useState<Record<string, ReportLayoutOverride>>({});
  const [selected, setSelected] = useState<string>();
  const [editing, setEditing] = useState(false);
  const [zoom, setZoom] = useState(55);
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [future, setFuture] = useState<HistoryEntry[]>([]);
  const [collisionWarning, setCollisionWarning] = useState(false);
  const pages = plan?.pages || [];

  const loadOverrides = useCallback(async () => {
    const items = await getReportLayoutOverrides(reportId);
    const next = Object.fromEntries(items.map(item => [item.element_key, item]));
    overridesRef.current = next;
    setOverrides(next);
  }, [reportId]);
  useEffect(() => { void loadOverrides(); }, [loadOverrides]);

  const rememberViewport = useCallback((elementKey?: string) => {
    const frame = iframeRef.current;
    const view = frame?.contentWindow;
    const doc = frame?.contentDocument;
    if (!view || !doc) return;
    const anchor = elementKey
      ? doc.querySelector<HTMLElement>(`[data-report-element-key="${CSS.escape(elementKey)}"]`)
      : null;
    pendingViewportRef.current = {
      x: view.scrollX,
      y: view.scrollY,
      elementKey,
      elementTop: anchor?.getBoundingClientRect().top,
    };
  }, []);

  const restoreViewport = useCallback(() => {
    const saved = pendingViewportRef.current;
    const frame = iframeRef.current;
    const view = frame?.contentWindow;
    const doc = frame?.contentDocument;
    if (!saved || !view || !doc) return;
    let top = saved.y;
    if (saved.elementKey && saved.elementTop !== undefined) {
      const anchor = doc.querySelector<HTMLElement>(
        `[data-report-element-key="${CSS.escape(saved.elementKey)}"]`,
      );
      if (anchor) top = view.scrollY + anchor.getBoundingClientRect().top - saved.elementTop;
    }
    view.scrollTo({ left: saved.x, top });
  }, []);

  const refreshKeepingViewport = useCallback(async (elementKey?: string) => {
    rememberViewport(elementKey);
    await onSaved();
  }, [onSaved, rememberViewport]);

  const applySavedOverride = useCallback((item: ReportLayoutOverride) => {
    const node = iframeRef.current?.contentDocument?.querySelector<HTMLElement>(
      `[data-report-element-key="${CSS.escape(item.element_key)}"]`,
    );
    if (!node) return;
    node.style.position = "relative";
    node.style.transformOrigin = "top left";
    node.style.transform = `translate(${item.x_offset}px,${item.y_offset}px) rotate(${item.rotation}deg) scale(${item.width_scale},${item.height_scale})`;
    node.style.zIndex = String(item.z_index);
    node.style.visibility = item.visible ? "visible" : "hidden";
    if (item.box_width != null) { node.style.width = `${item.box_width}px`; node.style.maxWidth = "none"; }
    if (item.box_height != null) { node.style.height = `${item.box_height}px`; node.style.overflow = "hidden"; }
  }, []);

  const commit = useCallback(async (after: ReportLayoutOverride, before?: ReportLayoutOverride, remember = true) => {
    setBusy(true);
    try {
      const saved = await saveReportLayoutOverride(reportId, after);
      const next = { ...overridesRef.current, [saved.element_key]: saved };
      overridesRef.current = next; setOverrides(next);
      if (remember) { setHistory(items => [...items, { before, after: saved }]); setFuture([]); }
      applySavedOverride(saved);
      await onSaved(false);
    } finally { setBusy(false); }
  }, [applySavedOverride, onSaved, reportId]);

  const remove = useCallback(async (elementKey: string, remember = true) => {
    const before = overridesRef.current[elementKey];
    setBusy(true);
    try {
      await resetReportLayoutOverride(reportId, elementKey);
      const next = { ...overridesRef.current }; delete next[elementKey];
      overridesRef.current = next; setOverrides(next);
      if (remember) { setHistory(items => [...items, { before }]); setFuture([]); }
      await refreshKeepingViewport(elementKey);
    } finally { setBusy(false); }
  }, [refreshKeepingViewport, reportId]);

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
        const rect = node.getBoundingClientRect();
        const pageRect = (node.closest(".page,.cover") as HTMLElement | null)?.getBoundingClientRect();
        const delta = (pointer: PointerEvent) => ({
          x: pageRect ? clamp(pointer.clientX - startX, pageRect.left + 24 - rect.right, pageRect.right - 24 - rect.left) : pointer.clientX - startX,
          y: pageRect ? clamp(pointer.clientY - startY, pageRect.top + 24 - rect.bottom, pageRect.bottom - 24 - rect.top) : pointer.clientY - startY,
        });
        const move = (pointer: PointerEvent) => { const next = delta(pointer); node.style.transform = `${original} translate(${next.x}px,${next.y}px)`; };
        const up = (pointer: PointerEvent) => {
          doc.removeEventListener("pointermove", move); doc.removeEventListener("pointerup", up);
          const next = delta(pointer);
          const nextRect = new DOMRect(rect.x + next.x, rect.y + next.y, rect.width, rect.height);
          setCollisionWarning(hasSevereOverlap(node, nextRect, doc));
          const after = { ...current, x_offset: current.x_offset + next.x, y_offset: current.y_offset + next.y };
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
          const boxResize = node.dataset.reportResizeMode === "box";
          const move = (pointer: PointerEvent) => {
            const width = clamp(rect.width + pointer.clientX - startX, 24, 2000);
            const height = clamp(rect.height + pointer.clientY - startY, 16, 3000);
            setCollisionWarning(hasSevereOverlap(node, new DOMRect(rect.x, rect.y, width, height), doc));
            if (boxResize) { node.style.width = `${width}px`; node.style.height = `${height}px`; node.style.overflow = "hidden"; }
            else { node.style.transform = `${original} scale(${width / rect.width},${height / rect.height})`; }
          };
          const up = (pointer: PointerEvent) => {
            doc.removeEventListener("pointermove", move); doc.removeEventListener("pointerup", up);
            const width = clamp(rect.width + pointer.clientX - startX, 24, 2000);
            const height = clamp(rect.height + pointer.clientY - startY, 16, 3000);
            const after = boxResize
              ? { ...current, box_width: width, box_height: height }
              : { ...current, width_scale: clamp(current.width_scale * width / rect.width, .1, 5), height_scale: clamp(current.height_scale * height / rect.height, .1, 5) };
            void commit(after, overridesRef.current[key]);
          };
          doc.addEventListener("pointermove", move); doc.addEventListener("pointerup", up);
        };
        node.appendChild(handle);
      }
    });
  }, [commit, editing, selected]);
  useEffect(() => { decorate(); }, [decorate, html]);

  const iframeLoaded = useCallback(() => {
    decorate();
    window.requestAnimationFrame(restoreViewport);
    window.setTimeout(restoreViewport, 120);
    window.setTimeout(() => {
      restoreViewport();
      pendingViewportRef.current = undefined;
    }, 350);
  }, [decorate, restoreViewport]);

  async function patchSelected(patch: Partial<ReportLayoutOverride>) { if (!selected) return; const before = overridesRef.current[selected]; await commit({ ...(before || cleanOverride(selected)), ...patch }, before); }
  async function resetAll() { setBusy(true); try { const anchor = selected; rememberViewport(anchor); await resetReportLayoutOverride(reportId); overridesRef.current = {}; setOverrides({}); setHistory([]); setFuture([]); await onSaved(); } finally { setBusy(false); } }
  async function undo() { const entry = history.at(-1); if (!entry) return; setHistory(items => items.slice(0, -1)); setFuture(items => [...items, entry]); if (entry.before) await commit(entry.before, entry.after, false); else if (entry.after) await remove(entry.after.element_key, false); }
  async function redo() { const entry = future.at(-1); if (!entry) return; setFuture(items => items.slice(0, -1)); setHistory(items => [...items, entry]); if (entry.after) await commit(entry.after, entry.before, false); else if (entry.before) await remove(entry.before.element_key, false); }
  const current = selected ? overrides[selected] || cleanOverride(selected) : undefined;
  const changeZoom = (next: number) => setZoom(clamp(next, 30, 100));
  const goPage = (number: number, sectionKey?: string) => { if (sectionKey) onSelectSection(sectionKey); iframeRef.current?.contentWindow?.scrollTo({ top: (number - 1) * 1123, behavior: "smooth" }); };

  return <div className="sticky top-24 max-h-[calc(100vh-7rem)] overflow-auto rounded-2xl bg-slate-200 p-3" data-testid="live-a4-preview"><div className="mb-3 flex flex-wrap items-center gap-2 rounded-xl bg-white p-2 shadow-sm"><button type="button" aria-label="Alejar vista previa" className="h-8 rounded-lg border px-3 font-bold" onClick={() => changeZoom(zoom - 10)}>−</button><input aria-label="Zoom de vista previa" type="range" min="30" max="100" step="5" value={zoom} onChange={event => changeZoom(Number(event.target.value))} className="min-w-20 flex-1"/><button type="button" aria-label="Acercar vista previa" className="h-8 rounded-lg border px-3 font-bold" onClick={() => changeZoom(zoom + 10)}>+</button><output className="w-12 text-center text-xs font-bold">{zoom}%</output><Button size="sm" variant={editing ? "primary" : "secondary"} onClick={() => { setEditing(value => !value); setSelected(undefined); }}><Maximize2 className="h-4 w-4"/>{editing ? "Terminar edición" : "Editar posiciones"}</Button></div>{editing ? <div className="mb-3 rounded-xl border border-emerald-200 bg-white p-2"><div className="flex flex-wrap gap-1"><Button size="sm" variant="ghost" disabled={busy || !history.length} onClick={() => void undo()}><Undo2 className="h-4 w-4"/>Deshacer</Button><Button size="sm" variant="ghost" disabled={busy || !future.length} onClick={() => void redo()}><Redo2 className="h-4 w-4"/>Rehacer</Button>{current ? <><Button size="sm" variant="ghost" disabled={busy} onClick={() => void patchSelected({ locked: !current.locked })}>{current.locked ? <Unlock className="h-4 w-4"/> : <Lock className="h-4 w-4"/>}{current.locked ? "Desbloquear" : "Bloquear"}</Button><Button size="sm" variant="ghost" disabled={busy} onClick={() => void patchSelected({ z_index: current.z_index + 1 })}><ChevronUp className="h-4 w-4"/>Adelante</Button><Button size="sm" variant="ghost" disabled={busy} onClick={() => void patchSelected({ z_index: current.z_index - 1 })}><ChevronDown className="h-4 w-4"/>Atrás</Button><Button size="sm" variant="ghost" disabled={busy} onClick={() => void remove(current.element_key)}><RotateCcw className="h-4 w-4"/>Restablecer elemento</Button></> : null}<Button size="sm" variant="ghost" className="ml-auto text-red-700" disabled={busy || !Object.keys(overrides).length} onClick={() => void resetAll()}>Restablecer todo</Button></div><p className="mt-2 px-2 text-xs text-slate-600">Selecciona títulos, textos, indicadores, gráficos o galerías del reporte. Los textos cambian de caja y hacen reflow sin deformar la tipografía.</p>{collisionWarning ? <p role="status" className="mt-2 rounded bg-amber-50 px-2 py-1 text-xs text-amber-800">Advertencia: este elemento se superpone ampliamente con otro. Puedes conservar la superposición si es intencional.</p> : null}{selected ? <p className="mt-1 truncate px-2 text-[10px] font-mono text-emerald-800">{selected}</p> : null}</div> : null}<div className="mb-3 flex gap-2 overflow-x-auto" aria-label="Páginas del reporte">{pages.map(page => <button key={page.number} className="shrink-0 rounded-lg bg-white px-3 py-2 text-left text-xs shadow-sm" onClick={() => goPage(page.number, page.section_keys[0])}><b>{page.number}</b> {page.title}</button>)}</div>{html ? <div className="overflow-auto rounded-lg bg-slate-300 p-3"><div className="mx-auto" style={{ width: `${794 * zoom / 100}px`, height: `${1123 * zoom / 100}px` }}><iframe ref={iframeRef} onLoad={iframeLoaded} title="Vista previa exacta y editable del reporte" sandbox="allow-same-origin" srcDoc={html} className="origin-top-left border-0 bg-white shadow-xl" style={{ width: "794px", height: "1123px", transform: `scale(${zoom / 100})` }}/></div></div> : <div className="grid aspect-[210/297] place-items-center bg-white text-sm text-slate-500">Preparando vista previa editorial…</div>}</div>;
}
