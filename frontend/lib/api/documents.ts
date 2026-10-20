import { API_URL } from "@/lib/constants";
import { getStoredToken } from "@/lib/auth";
import { ApiError, api } from "@/lib/api";

export type DocumentPerson = {
  id: string; first_name: string; last_name: string; rut: string; email: string | null;
  phone: string | null; address: string | null; commune: string | null;
  updated_at: string; latest_employment: Record<string, unknown> | null;
};
export type ManagedDocument = {
  id: string; person_id: string; person_name: string; person_rut: string;
  employment_id: string | null; event_id: string | null; kind: "CONTRACT" | "EPP";
  status: string; title: string; data: Record<string, unknown>; epp: {
    riohs_received: boolean; eirl_completed: boolean; delivery_date: string | null;
    items: Array<{ item_code: string; label: string; received_at: string | null; returned_at: string | null; received_conformity: boolean }>;
  } | null; version: number; created_at: string; updated_at: string; completed_at: string | null;
  can_edit: boolean; has_original_pdf: boolean; has_signed_pdf: boolean;
};
export type DocumentSummary = { people: number; documents: number; pending: number; completed: number; incomplete_epp: number };
export type SignatureLink = { url: string; expires_at: string; qr_data_url: string; signature_notice: string };
export type DocumentSingleSendResult = { document: ManagedDocument; link: SignatureLink; recipient: string | null; email_sent: boolean; delivery_error: string | null };
export type DocumentPairSendResult = { recipient: string; email_sent: boolean; delivery_error: string | null; documents: ManagedDocument[]; links: SignatureLink[] };
export type DocumentEmailBatchItem = {
  id: string; contract_id: string; epp_id: string; person_name: string; email: string | null;
  status: "QUEUED" | "PROCESSING" | "SENDING" | "RETRYING" | "SENT" | "PREPARED" | "FAILED";
  attempt_count: number; error: string | null;
  result: { recipient: string | null; email_sent: boolean; delivery_error: string | null; documents: ManagedDocument[]; links: Array<{ url: string; expires_at: string }> } | null;
};
export type DocumentEmailBatch = {
  id: string; event_id: string; status: "QUEUED" | "PROCESSING" | "COMPLETED" | "COMPLETED_WITH_ERRORS";
  total: number; queued: number; processing: number; sent: number; prepared: number; failed: number;
  skipped: number; created_at: string; items: DocumentEmailBatchItem[];
};
export type DocumentContractDefaults = { employer_name: string; employer_rut: string; representative_name: string; representative_rut: string; employer_address: string; employer_commune: string; has_event_override?: boolean };
export type DocumentHistoryEntry = { id: string; action: string; description: string | null; actor: string; created_at: string; old_data: Record<string, unknown> | null; new_data: Record<string, unknown> | null; metadata: Record<string, unknown> | null };
export type RepresentativeSignatureProfile = { configured: boolean; signer_name: string | null; signer_rut: string | null; signature_data_url: string | null; captured_at: string | null };
export type EventEppTemplate = { event_id: string; items: Array<{ item_code: string; label: string }>; updated_at: string | null; draft_documents_updated?: number };
export type DocumentBatchGenerationResult = {
  event_id: string; event_name: string; workers_processed: number;
  people_created: number; people_updated: number; assignments_created: number;
  contracts_created: number; epp_documents_created: number; documents_created: number;
  documents_skipped: number; setup_warnings: string[];
  workers_failed: number;
  results: Array<{ rut: string; name: string; person_action: string; assignment_action: string; created: string[]; already_had: string[]; status: "SUCCESS" | "ERROR"; error: string | null }>;
};
export type PeopleImportResult = {
  created: number; updated: number; assignments: number;
  workers_processed: number; workers_failed: number;
  results: Array<{ rut: string; name: string; person_action: string; assignment_action: string; status: "SUCCESS" | "ERROR"; error: string | null }>;
};
export type DraftGenerationPreview = {
  event_id: string; event_name: string; workers_processed: number;
  contracts_to_create: number; epp_to_create: number; documents_to_create: number;
  documents_existing: number; setup_warnings: string[];
  results: Array<{ person_id?: string; rut: string; name: string; person_action?: string; assignment_action?: string; create: string[]; already_had: string[]; missing_data?: string[] }>;
};
export type MissingDraftGenerationResult = {
  event_id: string; event_name: string; workers_processed: number;
  contracts_created: number; epp_documents_created: number; documents_created: number;
  documents_skipped: number; setup_warnings: string[];
  results: Array<{ person_id: string; name: string; rut: string; created: string[]; already_had: string[] }>;
};
export type ExistingPersonAssignment = {
  person_id: string;
  position: string;
  area?: string | null;
  workplace?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  remuneration?: string | number | null;
};
export type ExistingPeopleAssignmentResult = {
  source_event_id: string;
  target_event_id: string;
  target_event_name: string;
  assigned: Array<{ person_id: string; name: string; rut: string; employment_id: string }>;
  already_assigned: Array<{ person_id: string; name: string; rut: string }>;
  contracts_created: number;
  epp_documents_created: number;
  documents_created: number;
  documents_skipped: number;
  setup_warnings: string[];
};

async function blobRequest(path: string, method: "GET" | "POST" = "GET") {
  const token = getStoredToken();
  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });
  if (!response.ok) throw new ApiError(response.status, "No se pudo generar o descargar el PDF.");
  return response.blob();
}

export const documentApi = {
  people: (params = "") => api.get<DocumentPerson[]>(`/documents/people${params}`),
  documents: (params = "") => api.get<ManagedDocument[]>(`/documents${params}`),
  summary: (params = "") => api.get<DocumentSummary>(`/documents/summary${params}`),
  contractDefaults: () => api.get<DocumentContractDefaults>("/documents/contract-defaults"),
  representativeSignature: () => api.get<RepresentativeSignatureProfile>("/documents/representative-signature"),
  saveRepresentativeSignature: (signature_data_url: string) => api.put<RepresentativeSignatureProfile>("/documents/representative-signature", { signature_data_url }),
  deleteRepresentativeSignature: () => api.delete<RepresentativeSignatureProfile>("/documents/representative-signature"),
  saveContractDefaults: (data: DocumentContractDefaults) => api.put<DocumentContractDefaults>("/documents/contract-defaults", data),
  eventContractDefaults: (eventId: string) => api.get<DocumentContractDefaults>(`/documents/events/${eventId}/contract-defaults`),
  saveEventContractDefaults: (eventId: string, data: DocumentContractDefaults) => api.put<DocumentContractDefaults>(`/documents/events/${eventId}/contract-defaults`, data),
  resetEventContractDefaults: (eventId: string) => api.delete<DocumentContractDefaults>(`/documents/events/${eventId}/contract-defaults`),
  personHistory: (personId: string, eventId: string) => api.get<DocumentHistoryEntry[]>(`/documents/people/${personId}/history?event_id=${encodeURIComponent(eventId)}`),
  eventEppTemplate: (eventId: string) => api.get<EventEppTemplate>(`/documents/events/${eventId}/epp-template`),
  saveEventEppTemplate: (eventId: string, items: EventEppTemplate["items"]) => api.put<EventEppTemplate>(`/documents/events/${eventId}/epp-template`, { items }),
  createPerson: (data: Record<string, unknown>) => api.post<DocumentPerson>("/documents/people", data),
  updatePerson: (id: string, data: Record<string, unknown>, eventId?: string) =>
    api.patch<DocumentPerson>(`/documents/people/${id}${eventId ? `?event_id=${encodeURIComponent(eventId)}` : ""}`, data),
  updateEmployment: (personId: string, employmentId: string, data: Record<string, unknown>, eventId?: string) =>
    api.patch<Record<string, unknown>>(`/documents/people/${personId}/employments/${employmentId}${eventId ? `?event_id=${encodeURIComponent(eventId)}` : ""}`, data),
  previewImport: (file: File) => {
    const form = new FormData(); form.append("file", file);
    return api.post<{ valid_rows: Record<string, unknown>[]; errors: Array<{ row: number; field: string; message: string }>; total_rows: number; valid_count: number; error_count: number }>("/documents/people/import/preview", form);
  },
  commitImport: (data: Record<string, unknown>) => api.post<PeopleImportResult>("/documents/people/import", data),
  importAndGenerate: (data: Record<string, unknown>) => api.post<DocumentBatchGenerationResult>("/documents/people/import-and-generate", data),
  previewImportAndGenerate: (data: Record<string, unknown>) => api.post<DraftGenerationPreview>("/documents/people/import-and-generate/preview", data),
  generateMissingDrafts: (event_id: string, person_ids: string[]) =>
    api.post<MissingDraftGenerationResult>("/documents/events/generate-missing-drafts", { event_id, person_ids }),
  previewMissingDrafts: (event_id: string, person_ids: string[]) =>
    api.post<DraftGenerationPreview>("/documents/events/preview-missing-drafts", { event_id, person_ids }),
  assignExisting: (data: { source_event_id: string; target_event_id: string; assignments: ExistingPersonAssignment[]; generate_documents: boolean }) =>
    api.post<ExistingPeopleAssignmentResult>("/documents/people/assign-existing", data),
  template: () => blobRequest("/documents/people/template"),
  eventDocumentStatus: (eventId: string) => blobRequest(`/documents/events/${eventId}/status.xlsx`),
  createDocument: (data: Record<string, unknown>) => api.post<ManagedDocument>("/documents", data),
  updateDocument: (id: string, data: Record<string, unknown>) => api.patch<ManagedDocument>(`/documents/${id}`, data),
  previewPdf: (id: string) => blobRequest(`/documents/${id}/preview`, "POST"),
  prepare: (id: string) => api.post<ManagedDocument>(`/documents/${id}/prepare`),
  send: (id: string) => api.post<DocumentSingleSendResult>(`/documents/${id}/send`),
  sendTogether: (contract_document_id: string, epp_document_id: string) => api.post<DocumentPairSendResult>("/documents/send-together", { contract_document_id, epp_document_id }),
  enqueueTogetherBatch: (data: { batch_id: string; event_id: string; pairs: Array<{ contract_document_id: string; epp_document_id: string }> }) =>
    api.post<DocumentEmailBatch>("/documents/send-together/batches", data),
  getTogetherBatch: (batchId: string) => api.get<DocumentEmailBatch>(`/documents/send-together/batches/${batchId}`),
  retryTogetherBatch: (batchId: string, item_ids: string[]) =>
    api.post<DocumentEmailBatch>(`/documents/send-together/batches/${batchId}/retry`, { item_ids }),
  newVersion: (id: string) => api.post<ManagedDocument>(`/documents/${id}/new-version`),
  cancel: (id: string) => api.post<ManagedDocument>(`/documents/${id}/cancel`),
  supervisorSign: (id: string) => api.post<ManagedDocument>(`/documents/${id}/supervisor-sign`),
  download: (id: string, signed = false) => blobRequest(`/documents/${id}/pdf${signed ? "?signed=true" : ""}`),
  publicOpen: (token: string, rut: string) => api.post<Record<string, unknown>>("/documents/public/open", { token, rut }, { auth: false }),
  resendSignedCopy: (id: string) => api.post<{ email_sent: boolean; recipient: string }>(`/documents/${id}/signed-copy`),
  publicSign: (token: string, rut: string, worker_name: string, worker_signature_data_url: string, accepted: boolean, electronic_consent: boolean, epp_acknowledgments?: { riohs_received: boolean; eirl_completed: boolean; items_reviewed: boolean; received_item_codes: string[] }) => api.post<{ status: string; email_sent: boolean; delivery_error: string | null; signature_notice: string }>("/documents/public/sign", { token, rut, worker_name, worker_signature_data_url, accepted, electronic_consent, epp_acknowledgments }, { auth: false }),
};

export async function publicPreview(token: string, rut: string) {
  const response = await fetch(`${API_URL}/documents/public/preview`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, rut }), cache: "no-store",
  });
  if (!response.ok) throw new ApiError(response.status, "No se pudo abrir el documento.");
  return response.blob();
}
