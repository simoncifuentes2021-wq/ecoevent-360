import { api } from "@/lib/api";
import { getStoredToken } from "@/lib/auth";
import { API_URL } from "@/lib/constants";
import type { FormQrCode, FormQrCreate } from "@/types/formQr";

export function getFormQrCodes(formId: string) {
  return api.get<FormQrCode[]>(`/forms/${formId}/qr`);
}

export function createFormQrCode(formId: string, data: FormQrCreate) {
  return api.post<FormQrCode>(`/forms/${formId}/qr`, data);
}

export function deleteFormQrCode(qrId: string) {
  return api.delete<void>(`/form-qr/${qrId}`);
}

export async function downloadFormQrCode(qr: FormQrCode) {
  const token = getStoredToken();
  const response = await fetch(`${API_URL}/form-qr/${qr.id}/download`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {}
  });
  if (!response.ok) throw new Error("No se pudo descargar el QR.");
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${qr.label || "qr"}.png`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
