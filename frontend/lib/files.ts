import { API_ORIGIN } from "@/lib/constants";

export function fileUrl(value: string) {
  if (value.startsWith("http://") || value.startsWith("https://")) return value;
  const normalized = value.startsWith("/") ? value : `/${value}`;
  return `${API_ORIGIN}${normalized}`;
}
