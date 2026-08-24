import type { ReportLayoutOverride } from "@/types/report";

export type EditorRect = { left: number; top: number; width: number; height: number };
export type EditorItem = { key: string; rect: EditorRect; override: ReportLayoutOverride; type?: string; resizeMode?: string };
export type AlignAction = "left" | "center-x" | "right" | "top" | "center-y" | "bottom";
export type DistributeAction = "horizontal" | "vertical";
export type SizeAction = "width" | "height" | "both";

const right = (item: EditorItem) => item.rect.left + item.rect.width;
const bottom = (item: EditorItem) => item.rect.top + item.rect.height;
const centerX = (item: EditorItem) => item.rect.left + item.rect.width / 2;
const centerY = (item: EditorItem) => item.rect.top + item.rect.height / 2;

export function alignItems(items: EditorItem[], action: AlignAction): ReportLayoutOverride[] {
  if (items.length < 2) return [];
  const targets = {
    left: Math.min(...items.map(item => item.rect.left)),
    "center-x": items.reduce((sum, item) => sum + centerX(item), 0) / items.length,
    right: Math.max(...items.map(right)),
    top: Math.min(...items.map(item => item.rect.top)),
    "center-y": items.reduce((sum, item) => sum + centerY(item), 0) / items.length,
    bottom: Math.max(...items.map(bottom)),
  };
  return items.map(item => {
    const horizontal = action === "left" || action === "center-x" || action === "right";
    const current = action === "left" ? item.rect.left : action === "center-x" ? centerX(item) : action === "right" ? right(item) : action === "top" ? item.rect.top : action === "center-y" ? centerY(item) : bottom(item);
    return { ...item.override, x_offset: item.override.x_offset + (horizontal ? targets[action] - current : 0), y_offset: item.override.y_offset + (horizontal ? 0 : targets[action] - current) };
  });
}

export function distributeItems(items: EditorItem[], action: DistributeAction): ReportLayoutOverride[] {
  if (items.length < 3) return [];
  const horizontal = action === "horizontal";
  const sorted = [...items].sort((a, b) => (horizontal ? centerX(a) - centerX(b) : centerY(a) - centerY(b)));
  const first = horizontal ? centerX(sorted[0]) : centerY(sorted[0]);
  const last = horizontal ? centerX(sorted.at(-1)!) : centerY(sorted.at(-1)!);
  const step = (last - first) / (sorted.length - 1);
  return sorted.map((item, index) => {
    const delta = first + step * index - (horizontal ? centerX(item) : centerY(item));
    return { ...item.override, x_offset: item.override.x_offset + (horizontal ? delta : 0), y_offset: item.override.y_offset + (horizontal ? 0 : delta) };
  });
}

export function canEqualSize(items: EditorItem[]): boolean {
  if (items.length < 2) return false;
  const categories = new Set(items.map(item => item.type === "IMAGE" ? "IMAGE" : item.type === "CHART" ? "CHART" : item.resizeMode === "box" ? "BOX" : "SCALE"));
  return categories.size === 1 && !categories.has("SCALE");
}

export function equalSize(items: EditorItem[], action: SizeAction): ReportLayoutOverride[] {
  if (!canEqualSize(items)) return [];
  const reference = items[0].rect;
  return items.map(item => ({ ...item.override, box_width: action === "height" ? item.override.box_width ?? item.rect.width : reference.width, box_height: action === "width" ? item.override.box_height ?? item.rect.height : reference.height }));
}

export function snapDelta(value: number, candidates: number[], tolerance = 6): { value: number; guide?: number } {
  let closest: number | undefined;
  let distance = tolerance + 1;
  for (const candidate of candidates) {
    const next = Math.abs(candidate - value);
    if (next <= tolerance && next < distance) { closest = candidate; distance = next; }
  }
  return closest === undefined ? { value } : { value: closest, guide: closest };
}
