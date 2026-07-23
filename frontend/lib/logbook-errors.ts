import { ApiError } from "@/lib/api";

const translations: Array<[RegExp, string]> = [
  [/evidence required/i, "Debes adjuntar la evidencia requerida antes de continuar."],
  [/only the participant can edit responses/i, "Sólo el participante asignado puede editar estas respuestas."],
  [/forbidden|not authorized|permission/i, "No tienes permiso para realizar esta acción en esta bitácora."],
  [/invalid participant|event staff|belong to event/i, "El participante seleccionado ya no pertenece al equipo de este evento."],
  [/comment.*required|required.*comment/i, "Debes escribir un comentario para continuar."],
  [/version|conflict|modified by another/i, "Esta respuesta fue modificada por otro participante. Recarga la información antes de intentarlo nuevamente."],
  [/duplicate|already exists|already created/i, "Esta acción ya fue realizada y no puede duplicarse."],
  [/validation error/i, "Revisa los campos marcados e inténtalo nuevamente."],
];

export function logbookError(reason: unknown, fallback = "No se pudo completar la acción.") {
  const raw = reason instanceof Error ? reason.message : "";
  for (const [pattern, message] of translations) {
    if (pattern.test(raw)) return message;
  }
  if (reason instanceof ApiError && reason.status >= 500) {
    return "El servidor no pudo completar la acción. Inténtalo nuevamente.";
  }
  return raw && !/(token|storage_key|traceback|jwt)/i.test(raw) ? raw : fallback;
}
