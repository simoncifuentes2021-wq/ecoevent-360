export const logbookStageLabels: Record<string, string> = {
  SETUP: "Montaje",
  OPENING: "Apertura",
  OPERATION: "Operación",
  CLOSING: "Cierre",
  DISMANTLING: "Desmontaje",
  OTHER: "Otra",
};

export const logbookStatusLabels: Record<string, string> = {
  DRAFT: "Borrador", ACTIVE: "Activa", ARCHIVED: "Archivada",
  PUBLISHED: "Publicada", RETIRED: "Retirada", SCHEDULED: "Programada",
  OPEN: "Abierta", IN_PROGRESS: "En progreso", UNDER_REVIEW: "En revisión",
  CHANGES_REQUESTED: "Cambios solicitados", COMPLETED: "Completada",
  PENDING: "Pendiente", SUBMITTED: "Enviada", RESUBMITTED: "Reenviada",
  APPROVED: "Aprobada", REJECTED: "Rechazada", OVERDUE: "Vencida",
  CANCELLED: "Cancelada", FAILED: "Con observaciones", NOT_APPLICABLE: "No aplica",
};

export const logbookModeLabels: Record<string, string> = {
  INDIVIDUAL: "Individual", SHARED: "Compartida",
};

export const logbookItemTypeLabels: Record<string, string> = {
  CHECKBOX: "Casilla de verificación", YES_NO: "Sí / No",
  STATUS_SELECT: "Lista de estados", NUMBER: "Número",
  SHORT_TEXT: "Texto corto", LONG_TEXT: "Texto largo",
  PHOTO: "Fotografía", CONFIRMATION: "Confirmación",
};

export const logbookEvidencePolicyLabels: Record<string, string> = {
  NONE: "Sin evidencia", OPTIONAL: "Evidencia opcional",
  REQUIRED: "Evidencia obligatoria", REQUIRED_ON_FAILURE: "Obligatoria si falla",
};

export function logbookLabel(labels: Record<string, string>, value?: string | null) {
  return value ? labels[value] ?? value : "—";
}
