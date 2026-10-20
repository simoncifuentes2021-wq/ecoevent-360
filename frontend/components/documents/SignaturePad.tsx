"use client";

import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";

function clearCanvas(canvas: HTMLCanvasElement, context: CanvasRenderingContext2D) {
  // Drawing uses a device-pixel-ratio transform, while canvas.width/height are
  // already physical pixels. Clear under the identity transform so the whole
  // backing bitmap is erased on high-DPI screens too.
  context.save();
  context.setTransform(1, 0, 0, 1, 0, 0);
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.restore();
}

// Capture only the ink (plus a little breathing room), so later resizing can
// scale the actual signature uniformly instead of stretching the whole pad.
function captureInk(canvas: HTMLCanvasElement) {
  const context = canvas.getContext("2d");
  if (!context) return null;
  const { width, height } = canvas;
  const pixels = context.getImageData(0, 0, width, height).data;
  let left = width;
  let top = height;
  let right = -1;
  let bottom = -1;

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      if (pixels[(y * width + x) * 4 + 3] > 8) {
        left = Math.min(left, x);
        top = Math.min(top, y);
        right = Math.max(right, x);
        bottom = Math.max(bottom, y);
      }
    }
  }
  if (right < left || bottom < top) return null;

  // The API validates uploaded PNGs as at least 20×10 px. A larger minimum
  // margin keeps a flat/short handwritten stroke above that limit after crop.
  const padding = Math.max(12, Math.round(Math.min(width, height) * 0.025));
  left = Math.max(0, left - padding);
  top = Math.max(0, top - padding);
  right = Math.min(width - 1, right + padding);
  bottom = Math.min(height - 1, bottom + padding);
  const cropped = document.createElement("canvas");
  cropped.width = right - left + 1;
  cropped.height = bottom - top + 1;
  cropped.getContext("2d")?.drawImage(
    canvas,
    left,
    top,
    cropped.width,
    cropped.height,
    0,
    0,
    cropped.width,
    cropped.height,
  );
  return cropped;
}

export function SignaturePad({
  onChange,
  label = "Dibuja tu firma",
  disabled = false,
  resetToken = 0,
}: {
  onChange: (signatureDataUrl: string) => void;
  label?: string;
  disabled?: boolean;
  resetToken?: number;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;
  const hasInk = useRef(false);
  const drawing = useRef(false);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (!expanded) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setExpanded(false);
    };
    window.addEventListener("keydown", closeOnEscape);

    // Some mobile browsers allow orientation locking only after a user gesture
    // and while the page is fullscreen. The expanded pad remains usable if not.
    const orientation = window.screen.orientation;
    return () => {
      window.removeEventListener("keydown", closeOnEscape);
      orientation.unlock?.();
    };
  }, [expanded]);

  function enterExpanded() {
    setExpanded(true);
    const container = containerRef.current;
    if (!container?.requestFullscreen) return;
    void container.requestFullscreen().then(() => {
      const orientation = window.screen.orientation as ScreenOrientation & {
        lock?: (orientation: "landscape") => Promise<void>;
      };
      return orientation.lock?.("landscape").catch(() => undefined);
    }).catch(() => undefined);
  }

  function exitExpanded() {
    setExpanded(false);
    if (document.fullscreenElement) void document.exitFullscreen().catch(() => undefined);
  }

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const resize = () => {
      const bounds = canvas.getBoundingClientRect();
      if (!bounds.width || !bounds.height) return;
      const previous = hasInk.current ? captureInk(canvas) : null;
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(bounds.width * ratio);
      canvas.height = Math.round(bounds.height * ratio);
      const context = canvas.getContext("2d");
      if (!context) return;
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      context.lineWidth = 2.6;
      context.lineCap = "round";
      context.lineJoin = "round";
      context.strokeStyle = "#12211f";
      if (previous) {
        // Fit by a single uniform scale and center the ink. This keeps the
        // signature's proportions when moving between portrait and landscape.
        const scale = Math.min(
          (bounds.width * ratio) / previous.width,
          (bounds.height * ratio) / previous.height,
        );
        const drawWidth = (previous.width * scale) / ratio;
        const drawHeight = (previous.height * scale) / ratio;
        context.drawImage(
          previous,
          (bounds.width - drawWidth) / 2,
          (bounds.height - drawHeight) / 2,
          drawWidth,
          drawHeight,
        );
        const updatedInk = captureInk(canvas);
        if (updatedInk) onChangeRef.current(updatedInk.toDataURL("image/png"));
      }
    };
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    resize();
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) return;
    clearCanvas(canvas, context);
    hasInk.current = false;
    drawing.current = false;
  }, [resetToken]);

  function point(event: React.PointerEvent<HTMLCanvasElement>) {
    const bounds = event.currentTarget.getBoundingClientRect();
    return { x: event.clientX - bounds.left, y: event.clientY - bounds.top };
  }

  function start(event: React.PointerEvent<HTMLCanvasElement>) {
    if (disabled) return;
    const canvas = event.currentTarget;
    const context = canvas.getContext("2d");
    if (!context) return;
    event.preventDefault();
    canvas.setPointerCapture(event.pointerId);
    const position = point(event);
    context.beginPath();
    context.moveTo(position.x, position.y);
    context.lineTo(position.x + 0.1, position.y + 0.1);
    context.stroke();
    drawing.current = true;
    hasInk.current = true;
  }

  function move(event: React.PointerEvent<HTMLCanvasElement>) {
    if (disabled || !drawing.current) return;
    const context = event.currentTarget.getContext("2d");
    if (!context) return;
    event.preventDefault();
    const position = point(event);
    context.lineTo(position.x, position.y);
    context.stroke();
  }

  function finish() {
    if (!drawing.current) return;
    drawing.current = false;
    const canvas = canvasRef.current;
    if (canvas && hasInk.current) {
      const ink = captureInk(canvas);
      if (ink) onChange(ink.toDataURL("image/png"));
    }
  }

  function clear() {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) return;
    clearCanvas(canvas, context);
    hasInk.current = false;
    drawing.current = false;
    onChange("");
  }

  return <div ref={containerRef} className={expanded ? "fixed inset-0 z-[100] flex flex-col bg-slate-50 p-4 sm:p-6" : "space-y-2"}>
    <div className="flex items-center justify-between gap-3">
      <div>
        <p className="text-sm font-semibold text-slate-800">{label}</p>
        {expanded && <p className="mt-1 text-xs text-slate-500">Gira el teléfono horizontalmente para tener más espacio.</p>}
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <Button type="button" size="sm" variant="secondary" disabled={disabled} onClick={clear}>Borrar firma</Button>
        <Button type="button" size="sm" variant="secondary" onClick={expanded ? exitExpanded : enterExpanded}>
          {expanded ? "Volver al documento" : "Firmar en pantalla completa"}
        </Button>
      </div>
    </div>
    <canvas
      ref={canvasRef}
      aria-label={label}
      className={`${expanded ? "min-h-0 flex-1" : "h-36"} w-full rounded-xl border-2 border-dashed border-slate-300 bg-white touch-none ${disabled ? "cursor-not-allowed opacity-60" : "cursor-crosshair"}`}
      onPointerDown={start}
      onPointerMove={move}
      onPointerUp={finish}
      onPointerCancel={finish}
      onLostPointerCapture={finish}
    />
    <p className="text-xs text-slate-500">Usa el dedo, un lápiz digital o el mouse. No subas una foto de tu firma.</p>
    {expanded && <div className="flex justify-end"><Button type="button" onClick={exitExpanded}>Listo</Button></div>}
  </div>;
}
