import { api } from "@/lib/api";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { ListResponse } from "@/types/common";
import type { LogisticsEvidence, LogisticsEvidenceStage } from "@/types/logistics-evidence";

type EvidenceTarget =
  | { logisticsOrderId: string }
  | { logisticsOrderItemId: string }
  | { purchaseRequestId: string; purchaseRequestItemId?: string | null }
  | { stockMovementId: string };

type UploadPayload = {
  stage: LogisticsEvidenceStage;
  file: File;
  notes?: string | null;
};

function targetPath(target: EvidenceTarget) {
  if ("logisticsOrderId" in target) return `/logistics-orders/${target.logisticsOrderId}/evidences`;
  if ("logisticsOrderItemId" in target) return `/logistics-order-items/${target.logisticsOrderItemId}/evidences`;
  if ("purchaseRequestId" in target) return `/purchase-requests/${target.purchaseRequestId}/evidences`;
  return `/stock/movements/${target.stockMovementId}/evidences`;
}

export function getLogisticsEvidences(target: EvidenceTarget, params: Record<string, QueryValue> = {}) {
  return api.get<ListResponse<LogisticsEvidence>>(`${targetPath(target)}${toQuery(params)}`);
}

export function getEventLogisticsEvidences(eventId: string, params: Record<string, QueryValue> = {}) {
  return api.get<ListResponse<LogisticsEvidence>>(`/events/${eventId}/logistics-evidences${toQuery(params)}`);
}

export function uploadLogisticsEvidence(target: EvidenceTarget, payload: UploadPayload) {
  const formData = new FormData();
  formData.append("evidence_stage", payload.stage);
  formData.append("file", payload.file);
  if (payload.notes) formData.append("notes", payload.notes);
  if ("purchaseRequestItemId" in target && target.purchaseRequestItemId) {
    formData.append("purchase_request_item_id", target.purchaseRequestItemId);
  }
  return api.post<LogisticsEvidence>(targetPath(target), formData);
}

export function deleteLogisticsEvidence(id: string) {
  return api.delete<void>(`/logistics-evidences/${id}`);
}
