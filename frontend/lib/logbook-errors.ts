import { ApiError } from "@/lib/api";

const translations: Array<[RegExp, string]> = [
  [/evidence required/i, "Debes adjuntar la fotografía requerida antes de continuar."],
  [/required item missing/i, "Debes responder todos los ítems obligatorios antes de continuar."],
  [/only the participant can edit responses/i, "Sólo el participante asignado puede editar estas respuestas."],
  [/forbidden|not authorized|permission|insufficient role/i, "No tienes permiso para realizar esta acción en esta bitácora."],
  [/invalid participant|event staff|belong to event/i, "El participante seleccionado ya no pertenece al equipo habilitado para este evento."],
  [/comment.*required|required.*comment/i, "Debes agregar un comentario para explicar este incumplimiento."],
  [/version|conflict|modified by another/i, "Esta respuesta fue modificada por otro participante. Recarga la información antes de guardar nuevamente."],
  [/duplicate|already exists|already created/i, "Esta acción ya fue realizada y no puede duplicarse."],
  [/submitted assignments are locked|cannot be submitted|only submitted assignments/i, "El estado de la bitácora cambió. Actualiza la información antes de continuar."],
  [/not applicable is not allowed/i, "Este ítem no permite marcar la opción No aplica."],
  [/numeric value is required/i, "Ingresa un número válido antes de guardar."],
  [/invalid option/i, "Selecciona una opción válida."],
  [/validation error|revisa los campos marcados/i, "Revisa los campos marcados e inténtalo nuevamente."],
];

export function logbookError(
  reason: unknown,
  fallback = "Ocurrió un problema al procesar la solicitud. Inténtalo nuevamente.",
) {
  const raw = reason instanceof ApiError ? reason.detail : reason instanceof Error ? reason.message : "";
  for (const [pattern, message] of translations) {
    if (pattern.test(raw)) return message;
  }
  if (reason instanceof ApiError && reason.status === 401) {
    return "Tu sesión venció. Inicia sesión nuevamente.";
  }
  if (reason instanceof ApiError && reason.status === 403) {
    return "No tienes permiso para realizar esta acción en esta bitácora.";
  }
  if (reason instanceof ApiError && reason.status === 409) {
    return "La información cambió mientras trabajabas. Actualiza la bitácora antes de intentarlo nuevamente.";
  }
  if (reason instanceof ApiError && reason.status === 422) {
    return "Revisa los datos y requisitos pendientes antes de continuar.";
  }
  if (reason instanceof ApiError && reason.status >= 500) {
    return "El servidor no pudo completar la acción. Inténtalo nuevamente.";
  }
  if (reason instanceof TypeError || /failed to fetch|network|timeout|load failed/i.test(raw)) {
    return "No fue posible comunicarse con el servidor. Revisa tu conexión e inténtalo nuevamente.";
  }
  return fallback;
}
