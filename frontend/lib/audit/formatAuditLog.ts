import type { AuditLog } from "@/types/auditLog";

const actionLabels: Record<string, string> = {
  LOGIN_SUCCESS: "Inicio de sesion exitoso",
  LOGIN_FAILED: "Intento de inicio fallido",
  LOGOUT: "Cerro sesion",
  USER_CREATED: "Creo un usuario",
  USER_UPDATED: "Actualizo un usuario",
  USER_DEACTIVATED: "Desactivo un usuario",
  USER_ROLE_CHANGED: "Cambio el rol de un usuario",
  USER_PASSWORD_CHANGED: "Cambio una contrasena",
  CLIENT_CREATED: "Creo un cliente",
  CLIENT_UPDATED: "Actualizo un cliente",
  CLIENT_DEACTIVATED: "Desactivo un cliente",
  EVENT_CREATED: "Creo un evento",
  EVENT_UPDATED: "Actualizo un evento",
  EVENT_STATUS_CHANGED: "Cambio el estado del evento",
  EVENT_CANCELLED: "Cancelo un evento",
  SERVICE_CREATED: "Creo un servicio",
  SERVICE_UPDATED: "Actualizo un servicio",
  SERVICE_DEACTIVATED: "Desactivo un servicio",
  EVENT_SERVICE_ADDED: "Agrego un servicio al evento",
  EVENT_SERVICE_UPDATED: "Actualizo un servicio del evento",
  EVENT_SERVICE_REMOVED: "Quito un servicio del evento",
  ZONE_CREATED: "Creo una zona",
  ZONE_UPDATED: "Actualizo una zona",
  ZONE_DEACTIVATED: "Elimino una zona",
  STAFF_ASSIGNED: "Asigno personal al evento",
  STAFF_REMOVED: "Removio personal del evento",
  CREATE: "Creo un registro",
  UPDATE: "Actualizo un registro",
  DELETE: "Elimino un registro",
  COMPLETE: "Completo una tarea",
  STATUS_CHANGE: "Cambio un estado",
  RESOLVE: "Resolvio una incidencia",
  CLOSE: "Cerro una incidencia",
  CARBON_RECORD_CREATED: "Creo un registro de carbono",
  CARBON_RECORD_UPDATED: "Actualizo un registro de carbono",
  CARBON_RECORD_DELETED_OR_VOIDED: "Elimino o anulo un registro de carbono",
  FUEL_RECORD_CREATED: "Registro combustible",
  ENERGY_RECORD_CREATED: "Registro energia",
  WATER_RECORD_CREATED: "Registro agua",
  SURVEY_CREATED: "Creo una encuesta",
  SURVEY_UPDATED: "Actualizo una encuesta",
  SURVEY_CLOSED: "Cerro una encuesta",
  SURVEY_CSV_IMPORTED: "Importo respuestas CSV",
  REPORT_DOWNLOADED: "Descargo un reporte"
};

const moduleLabels: Record<string, string> = {
  auth: "Auth",
  users: "Usuarios",
  clients: "Clientes",
  events: "Eventos",
  services: "Servicios",
  zones: "Zonas",
  staff: "Personal",
  tasks: "Tareas",
  incidents: "Incidencias",
  evidences: "Evidencias",
  waste: "Residuos",
  carbon: "Huella",
  operations: "Consumos",
  surveys: "Encuestas",
  reports: "Reportes"
};

const statusLabels: Record<string, string> = {
  SUCCESS: "Exitoso",
  FAILED: "Fallido",
  DENIED: "Denegado",
  INFO: "Info"
};

export function formatAuditAction(action: string) {
  return actionLabels[action] || action.replaceAll("_", " ").toLowerCase();
}

export function formatAuditModule(module: string) {
  return moduleLabels[module] || module;
}

export function formatAuditStatus(status: string) {
  return statusLabels[status] || status;
}

export function buildAuditDescription(log: AuditLog) {
  if (log.description) return log.description;
  const actor = log.user_name || "Sistema";
  const action = formatAuditAction(log.action);
  const target = log.task_title || log.incident_title || log.zone_name || log.event_name || log.client_name || log.entity_type || "el sistema";
  return `${actor} - ${action} en ${target}.`;
}
