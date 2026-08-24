"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AlignCenterHorizontal, AlignCenterVertical, AlignEndHorizontal, AlignEndVertical, AlignHorizontalDistributeCenter, AlignStartHorizontal, AlignStartVertical, AlignVerticalDistributeCenter, ChevronDown, ChevronUp, Lock, Maximize2, Redo2, RotateCcw, Undo2, Unlock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getReportLayoutOverrides, resetReportLayoutOverride, saveReportLayoutOverride, saveReportLayoutOverrides } from "@/lib/api/reports";
import type { ReportLayoutOverride, ReportPagePlan } from "@/types/report";
import { alignItems, canEqualSize, distributeItems, equalSize, snapDelta, type AlignAction, type DistributeAction, type EditorItem, type SizeAction } from "./report-layout-editor-math";

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
type HistoryEntry = { before: ReportLayoutOverride[]; after: ReportLayoutOverride[] };
type ViewportAnchor = { x: number; y: number; elementKey?: string; elementTop?: number };

export function EditableReportPreview({ reportId, html, plan, onSelectSection, onSaved }: { reportId: string; html: string; plan?: ReportPagePlan; onSelectSection: (key: string) => void; onSaved: (refreshHtml?: boolean) => Promise<void> }) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const overridesRef = useRef<Record<string, ReportLayoutOverride>>({});
  const pendingViewportRef = useRef<ViewportAnchor>();
  const [overrides, setOverrides] = useState<Record<string, ReportLayoutOverride>>({});
  const [selected, setSelected] = useState<string[]>([]);
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
      if (remember) { setHistory(items => [...items, { before: before ? [before] : [], after: [saved] }]); setFuture([]); }
      applySavedOverride(saved);
      await onSaved(false);
    } finally { setBusy(false); }
  }, [applySavedOverride, onSaved, reportId]);

  const commitMany = useCallback(async (changes: ReportLayoutOverride[], remember = true) => {
    if (!changes.length) return;
    const before = changes.map(item => overridesRef.current[item.element_key] || cleanOverride(item.element_key));
    setBusy(true);
    try {
      const saved = await saveReportLayoutOverrides(reportId, changes);
      const next = { ...overridesRef.current };
      saved.forEach(item => { next[item.element_key] = item; applySavedOverride(item); });
      overridesRef.current = next; setOverrides(next);
      if (remember) { setHistory(items => [...items, { before, after: saved }]); setFuture([]); }
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
      if (remember) { setHistory(items => [...items, { before: before ? [before] : [], after: [] }]); setFuture([]); }
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
    style.textContent = `[data-report-element-key]{cursor:move!important;outline:1px dashed rgba(5,150,105,.7);outline-offset:2px}[data-report-element-key][data-editor-selected="true"]{outline:3px solid #059669!important;outline-offset:3px}.report-resize-handle{position:absolute!important;right:-8px!important;bottom:-8px!important;width:16px!important;height:16px!important;border:2px solid white!important;background:#059669!important;border-radius:3px!important;z-index:2147483647!important;cursor:nwse-resize!important}.report-smart-guide{position:fixed!important;pointer-events:none!important;background:#ec4899!important;z-index:2147483646!important}.report-smart-guide.x{top:0!important;bottom:0!important;width:1px!important}.report-smart-guide.y{left:0!important;right:0!important;height:1px!important}`;
    doc.head.appendChild(style);
    const nodes = Array.from(doc.querySelectorAll<HTMLElement>("[data-report-element-key]"));
    nodes.forEach(node => {
      const key = node.dataset.reportElementKey!;
      node.dataset.editorSelected = String(selected.includes(key));
      node.querySelector(":scope > .report-resize-handle")?.remove();
      node.onclick = event => { event.preventDefault(); event.stopPropagation(); setSelected(items => event.ctrlKey || event.metaKey ? (items.includes(key) ? items.filter(item => item !== key) : [...items, key]) : [key]); };
      node.onpointerdown = event => {
        if ((event.target as HTMLElement).classList.contains("report-resize-handle")) return;
        const current = overridesRef.current[key] || cleanOverride(key);
        if (current.locked) { setSelected([key]); return; }
        event.preventDefault(); event.stopPropagation();
        const activeKeys = selected.includes(key) ? selected : [key];
        if (!selected.includes(key)) setSelected([key]);
        const movable = activeKeys.filter(item => !(overridesRef.current[item]?.locked));
        const groupNodes = movable.map(item => doc.querySelector<HTMLElement>(`[data-report-element-key="${CSS.escape(item)}"]`)).filter((item): item is HTMLElement => Boolean(item));
        const originals = new Map(groupNodes.map(item => [item, item.style.transform]));
        const startX = event.clientX; const startY = event.clientY; const original = node.style.transform;
        const rect = node.getBoundingClientRect();
        const pageRect = (node.closest(".page,.cover") as HTMLElement | null)?.getBoundingClientRect();
        const delta = (pointer: PointerEvent) => ({
          x: pageRect ? clamp(pointer.clientX - startX, pageRect.left + 24 - rect.right, pageRect.right - 24 - rect.left) : pointer.clientX - startX,
          y: pageRect ? clamp(pointer.clientY - startY, pageRect.top + 24 - rect.bottom, pageRect.bottom - 24 - rect.top) : pointer.clientY - startY,
        });
        const guideCandidatesX = [pageRect?.left ?? 0, pageRect ? (pageRect.left + pageRect.right) / 2 : 397, pageRect?.right ?? 794, ...nodes.filter(item => !groupNodes.includes(item)).flatMap(item => { const r = item.getBoundingClientRect(); return [r.left, r.left + r.width / 2, r.right]; })];
        const guideCandidatesY = [pageRect?.top ?? 0, pageRect ? (pageRect.top + pageRect.bottom) / 2 : 561.5, pageRect?.bottom ?? 1123, ...nodes.filter(item => !groupNodes.includes(item)).flatMap(item => { const r = item.getBoundingClientRect(); return [r.top, r.top + r.height / 2, r.bottom]; })];
        const snapped = (pointer: PointerEvent) => { const raw = delta(pointer); const sx = snapDelta(rect.left + raw.x, guideCandidatesX); const sy = snapDelta(rect.top + raw.y, guideCandidatesY); return { x: raw.x + sx.value - (rect.left + raw.x), y: raw.y + sy.value - (rect.top + raw.y), gx: sx.guide, gy: sy.guide }; };
        const clearGuides = () => doc.querySelectorAll(".report-smart-guide").forEach(item => item.remove());
        const move = (pointer: PointerEvent) => { const next = snapped(pointer); groupNodes.forEach(item => { item.style.transform = `${originals.get(item) || ""} translate(${next.x}px,${next.y}px)`; }); clearGuides(); if (next.gx !== undefined) { const guide = doc.createElement("i"); guide.className = "report-smart-guide x"; guide.style.left = `${next.gx}px`; doc.body.appendChild(guide); } if (next.gy !== undefined) { const guide = doc.createElement("i"); guide.className = "report-smart-guide y"; guide.style.top = `${next.gy}px`; doc.body.appendChild(guide); } };
        const up = (pointer: PointerEvent) => {
          doc.removeEventListener("pointermove", move); doc.removeEventListener("pointerup", up);
          clearGuides(); const next = snapped(pointer);
          const nextRect = new DOMRect(rect.x + next.x, rect.y + next.y, rect.width, rect.height);
          setCollisionWarning(hasSevereOverlap(node, nextRect, doc));
          const changes = movable.map(item => { const value = overridesRef.current[item] || cleanOverride(item); return { ...value, x_offset: value.x_offset + next.x, y_offset: value.y_offset + next.y }; });
          void commitMany(changes);
        };
        doc.addEventListener("pointermove", move); doc.addEventListener("pointerup", up);
      };
      if (selected.length === 1 && key === selected[0] && !(overridesRef.current[key]?.locked)) {
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
  }, [commit, commitMany, editing, selected]);
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

  const selectedItems = useCallback((): EditorItem[] => selected.map(key => {
    const node = iframeRef.current?.contentDocument?.querySelector<HTMLElement>(`[data-report-element-key="${CSS.escape(key)}"]`);
    const rect = node?.getBoundingClientRect() || new DOMRect();
    return { key, rect: { left: rect.left, top: rect.top, width: rect.width, height: rect.height }, override: overridesRef.current[key] || cleanOverride(key), type: node?.dataset.reportElementType, resizeMode: node?.dataset.reportResizeMode };
  }).filter(item => !item.override.locked), [selected]);
  async function patchSelected(patch: Partial<ReportLayoutOverride>) { await commitMany(selectedItems().map(item => ({ ...item.override, ...patch }))); }
  async function resetSelected() { const keys = [...selected]; if (!keys.length) return; const before = keys.map(key => overridesRef.current[key]).filter((item): item is ReportLayoutOverride => Boolean(item)); setBusy(true); try { rememberViewport(keys[0]); await Promise.all(keys.map(key => resetReportLayoutOverride(reportId, key))); const next = { ...overridesRef.current }; keys.forEach(key => delete next[key]); overridesRef.current = next; setOverrides(next); setHistory(items => [...items, { before, after: [] }]); setFuture([]); await onSaved(); } finally { setBusy(false); } }
  async function resetAll() { setBusy(true); try { const anchor = selected[0]; rememberViewport(anchor); await resetReportLayoutOverride(reportId); overridesRef.current = {}; setOverrides({}); setHistory([]); setFuture([]); await onSaved(); } finally { setBusy(false); } }
  async function applyHistory(values: ReportLayoutOverride[]) { if (values.length) await commitMany(values, false); }
  async function undo() { const entry = history.at(-1); if (!entry) return; setHistory(items => items.slice(0, -1)); setFuture(items => [...items, entry]); await applyHistory(entry.before); for (const item of entry.after.filter(after => !entry.before.some(before => before.element_key === after.element_key))) await remove(item.element_key, false); }
  async function redo() { const entry = future.at(-1); if (!entry) return; setFuture(items => items.slice(0, -1)); setHistory(items => [...items, entry]); await applyHistory(entry.after); for (const item of entry.before.filter(before => !entry.after.some(after => after.element_key === before.element_key))) await remove(item.element_key, false); }
  async function align(action: AlignAction) { await commitMany(alignItems(selectedItems(), action)); }
  async function distribute(action: DistributeAction) { await commitMany(distributeItems(selectedItems(), action)); }
  async function size(action: SizeAction) { await commitMany(equalSize(selectedItems(), action)); }
  const current = selected.length === 1 ? overrides[selected[0]] || cleanOverride(selected[0]) : undefined;
  const unlocked = selectedItems();
  const sameSizeEnabled = canEqualSize(unlocked);
  const changeZoom = (next: number) => setZoom(clamp(next, 30, 100));
  const goPage = (number: number, sectionKey?: string) => { if (sectionKey) onSelectSection(sectionKey); iframeRef.current?.contentWindow?.scrollTo({ top: (number - 1) * 1123, behavior: "smooth" }); };

  useEffect(() => {
    if (!editing) return;
    const keydown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target?.matches("input,textarea,select,[contenteditable=true]")) return;
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") { event.preventDefault(); void (event.shiftKey ? redo() : undo()); return; }
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "y") { event.preventDefault(); void redo(); return; }
      const directions: Record<string, [number, number]> = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
      const direction = directions[event.key]; if (!direction || !selected.length) return;
      event.preventDefault(); const amount = event.shiftKey ? 10 : 1;
      void commitMany(selectedItems().map(item => ({ ...item.override, x_offset: item.override.x_offset + direction[0] * amount, y_offset: item.override.y_offset + direction[1] * amount })));
    };
    window.addEventListener("keydown", keydown); return () => window.removeEventListener("keydown", keydown);
  });

  return <div className="sticky top-24 max-h-[calc(100vh-7rem)] overflow-auto rounded-2xl bg-slate-200 p-3" data-testid="live-a4-preview">
    <div className="mb-3 flex flex-wrap items-center gap-2 rounded-xl bg-white p-2 shadow-sm"><button type="button" aria-label="Alejar vista previa" className="h-8 rounded-lg border px-3 font-bold" onClick={() => changeZoom(zoom - 10)}>−</button><input aria-label="Zoom de vista previa" type="range" min="30" max="100" step="5" value={zoom} onChange={event => changeZoom(Number(event.target.value))} className="min-w-20 flex-1"/><button type="button" aria-label="Acercar vista previa" className="h-8 rounded-lg border px-3 font-bold" onClick={() => changeZoom(zoom + 10)}>+</button><output className="w-12 text-center text-xs font-bold">{zoom}%</output><Button size="sm" variant={editing ? "primary" : "secondary"} onClick={() => { setEditing(value => !value); setSelected([]); }}><Maximize2 className="h-4 w-4"/>{editing ? "Terminar edición" : "Editar posiciones"}</Button></div>
    {editing ? <div className="mb-3 rounded-xl border border-emerald-200 bg-white p-2"><div className="flex flex-wrap gap-1">
      <Button size="sm" variant="ghost" disabled={busy || !history.length} onClick={() => void undo()}><Undo2 className="h-4 w-4"/>Deshacer</Button><Button size="sm" variant="ghost" disabled={busy || !future.length} onClick={() => void redo()}><Redo2 className="h-4 w-4"/>Rehacer</Button>
      {selected.length ? <><Button size="sm" variant="ghost" disabled={busy || !unlocked.length} onClick={() => void patchSelected({ locked: true })}><Lock className="h-4 w-4"/>Bloquear</Button><Button size="sm" variant="ghost" disabled={busy || selected.every(key => !overridesRef.current[key]?.locked)} onClick={() => void commitMany(selected.map(key => ({ ...(overridesRef.current[key] || cleanOverride(key)), locked: false })))}><Unlock className="h-4 w-4"/>Desbloquear</Button><Button size="sm" variant="ghost" disabled={busy || !unlocked.length} onClick={() => void patchSelected({ z_index: Math.max(0, ...unlocked.map(item => item.override.z_index)) + 1 })}><ChevronUp className="h-4 w-4"/>Adelante</Button><Button size="sm" variant="ghost" disabled={busy || !unlocked.length} onClick={() => void patchSelected({ z_index: Math.min(0, ...unlocked.map(item => item.override.z_index)) - 1 })}><ChevronDown className="h-4 w-4"/>Atrás</Button></> : null}
      {selected.length >= 2 ? <><Button aria-label="Alinear izquierda" size="sm" variant="ghost" onClick={() => void align("left")}><AlignStartVertical className="h-4 w-4"/></Button><Button aria-label="Centrar horizontal" size="sm" variant="ghost" onClick={() => void align("center-x")}><AlignCenterVertical className="h-4 w-4"/></Button><Button aria-label="Alinear derecha" size="sm" variant="ghost" onClick={() => void align("right")}><AlignEndVertical className="h-4 w-4"/></Button><Button aria-label="Alinear arriba" size="sm" variant="ghost" onClick={() => void align("top")}><AlignStartHorizontal className="h-4 w-4"/></Button><Button aria-label="Centrar vertical" size="sm" variant="ghost" onClick={() => void align("center-y")}><AlignCenterHorizontal className="h-4 w-4"/></Button><Button aria-label="Alinear abajo" size="sm" variant="ghost" onClick={() => void align("bottom")}><AlignEndHorizontal className="h-4 w-4"/></Button></> : null}
      {selected.length >= 3 ? <><Button aria-label="Distribuir horizontalmente" size="sm" variant="ghost" onClick={() => void distribute("horizontal")}><AlignHorizontalDistributeCenter className="h-4 w-4"/></Button><Button aria-label="Distribuir verticalmente" size="sm" variant="ghost" onClick={() => void distribute("vertical")}><AlignVerticalDistributeCenter className="h-4 w-4"/></Button></> : null}
      {selected.length >= 2 ? <><Button size="sm" variant="ghost" disabled={!sameSizeEnabled} onClick={() => void size("width")}>Igualar ancho</Button><Button size="sm" variant="ghost" disabled={!sameSizeEnabled} onClick={() => void size("height")}>Igualar alto</Button><Button size="sm" variant="ghost" disabled={!sameSizeEnabled} onClick={() => void size("both")}>Igualar tamaño</Button><Button size="sm" variant="ghost" disabled={busy} onClick={() => void resetSelected()}><RotateCcw className="h-4 w-4"/>Restablecer seleccionados</Button></> : current ? <Button size="sm" variant="ghost" disabled={busy} onClick={() => void remove(current.element_key)}><RotateCcw className="h-4 w-4"/>Restablecer elemento</Button> : null}
      <Button size="sm" variant="ghost" className="ml-auto text-red-700" disabled={busy || !Object.keys(overrides).length} onClick={() => void resetAll()}>Restablecer todo</Button></div>
      <p className="mt-2 px-2 text-xs font-semibold text-slate-700">{selected.length > 1 ? `${selected.length} elementos seleccionados` : "Ctrl/Cmd + click para seleccionar varios elementos."}</p>{collisionWarning ? <p role="status" className="mt-2 rounded bg-amber-50 px-2 py-1 text-xs text-amber-800">Advertencia: este elemento se superpone ampliamente con otro. Puedes conservar la superposición si es intencional.</p> : null}{selected.length ? <p className="mt-1 truncate px-2 text-[10px] font-mono text-emerald-800">{selected.join(", ")}</p> : null}</div> : null}
    <div className="mb-3 flex gap-2 overflow-x-auto" aria-label="Páginas del reporte">{pages.map(page => <button key={page.number} className="shrink-0 rounded-lg bg-white px-3 py-2 text-left text-xs shadow-sm" onClick={() => goPage(page.number, page.section_keys[0])}><b>{page.number}</b> {page.title}</button>)}</div>{html ? <div className="overflow-auto rounded-lg bg-slate-300 p-3"><div className="mx-auto" style={{ width: `${794 * zoom / 100}px`, height: `${1123 * zoom / 100}px` }}><iframe ref={iframeRef} onLoad={iframeLoaded} title="Vista previa exacta y editable del reporte" sandbox="allow-same-origin" srcDoc={html} className="origin-top-left border-0 bg-white shadow-xl" style={{ width: "794px", height: "1123px", transform: `scale(${zoom / 100})` }}/></div></div> : <div className="grid aspect-[210/297] place-items-center bg-white text-sm text-slate-500">Preparando vista previa editorial…</div>}
  </div>;
}
