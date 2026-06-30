import type { UserRole } from "@/types/roles";

export function isAdminRole(role?: UserRole | null) {
  return role === "SUPER_ADMIN" || role === "ADMIN";
}

export function canManageCatalogs(role?: UserRole | null) {
  return isAdminRole(role);
}

export function canManageClients(role?: UserRole | null) {
  return isAdminRole(role);
}

export function canManageUsers(role?: UserRole | null) {
  return isAdminRole(role);
}

export function canManageServices(role?: UserRole | null) {
  return isAdminRole(role);
}

export function canManageEvents(role?: UserRole | null) {
  return isAdminRole(role);
}

export function canCreateSuperAdmin(role?: UserRole | null) {
  return role === "SUPER_ADMIN";
}

export function canDeleteCriticalData(role?: UserRole | null) {
  return role === "SUPER_ADMIN";
}

export function canOperateEvent(role?: UserRole | null) {
  return role === "SUPER_ADMIN" || role === "ADMIN" || role === "SUPERVISOR";
}

export function isLogisticsOperator(role?: UserRole | null) {
  return role === "LOGISTICS_OPERATOR";
}

export function canViewLogisticsOrders(role?: UserRole | null) {
  return isAdminRole(role) || role === "SUPERVISOR" || role === "LOGISTICS_OPERATOR";
}

export function canManageLogisticsOrders(role?: UserRole | null) {
  return isAdminRole(role) || role === "SUPERVISOR" || role === "LOGISTICS_OPERATOR";
}

export function canCreateLogisticsOrder(role?: UserRole | null) {
  return isAdminRole(role) || role === "SUPERVISOR";
}

export function canManageEventServices(role?: UserRole | null) {
  return isAdminRole(role);
}

export function canManageZones(role?: UserRole | null) {
  return role === "SUPER_ADMIN" || role === "ADMIN" || role === "SUPERVISOR";
}

export function canManageStaff(role?: UserRole | null) {
  return role === "SUPER_ADMIN" || role === "ADMIN" || role === "SUPERVISOR";
}

export function canAssignStaff(role?: UserRole | null) {
  return canManageStaff(role);
}

export function canManageTasks(role?: UserRole | null) {
  return role === "SUPER_ADMIN" || role === "ADMIN" || role === "SUPERVISOR";
}

export function canCompleteTask(role?: UserRole | null) {
  return role === "SUPER_ADMIN" || role === "ADMIN" || role === "SUPERVISOR" || role === "WORKER";
}

export function canViewOperationalTabs(role?: UserRole | null) {
  return role === "SUPER_ADMIN" || role === "ADMIN" || role === "SUPERVISOR" || role === "CLIENT";
}

export function canUseWorkerActions(role?: UserRole | null) {
  return role === "WORKER" || role === "SUPERVISOR";
}

export function canViewIncidents(role?: UserRole | null) {
  return Boolean(role);
}

export function canCreateIncident(role?: UserRole | null) {
  return role === "SUPER_ADMIN" || role === "ADMIN" || role === "SUPERVISOR" || role === "WORKER";
}

export function canEditIncident(role?: UserRole | null) {
  return role === "SUPER_ADMIN" || role === "ADMIN" || role === "SUPERVISOR";
}

export function canAssignIncident(role?: UserRole | null) {
  return canEditIncident(role);
}

export function canResolveIncident(role?: UserRole | null) {
  return role === "SUPER_ADMIN" || role === "ADMIN" || role === "SUPERVISOR" || role === "WORKER";
}

export function canCloseIncident(role?: UserRole | null) {
  return role === "SUPER_ADMIN" || role === "ADMIN" || role === "SUPERVISOR";
}

export function canViewEvidences(role?: UserRole | null) {
  return Boolean(role);
}

export function canUploadEvidence(role?: UserRole | null) {
  return role === "SUPER_ADMIN" || role === "ADMIN" || role === "SUPERVISOR" || role === "WORKER";
}

export function canDeleteEvidence(role?: UserRole | null) {
  return role === "SUPER_ADMIN" || role === "ADMIN" || role === "SUPERVISOR";
}

export function canUseWorkerIncidentActions(role?: UserRole | null) {
  return role === "WORKER" || role === "SUPERVISOR";
}

export function canUseWorkerEvidenceActions(role?: UserRole | null) {
  return role === "WORKER" || role === "SUPERVISOR";
}

export function canViewWaste(role?: UserRole | null) {
  return Boolean(role);
}

export function canCreateWasteRecord(role?: UserRole | null) {
  return role === "SUPER_ADMIN" || role === "ADMIN" || role === "SUPERVISOR" || role === "WORKER";
}

export function canEditWasteRecord(role?: UserRole | null) {
  return role === "SUPER_ADMIN" || role === "ADMIN" || role === "SUPERVISOR";
}

export function canDeleteWasteRecord(role?: UserRole | null) {
  return role === "SUPER_ADMIN" || role === "ADMIN";
}

export function canManageWasteTypes(role?: UserRole | null) {
  return isAdminRole(role);
}

export function canUseWorkerWasteActions(role?: UserRole | null) {
  return role === "WORKER" || role === "SUPERVISOR";
}

export const canViewCarbon = (role?: UserRole | null) => Boolean(role);
export const canCreateCarbonRecord = (role?: UserRole | null) => role === "SUPER_ADMIN" || role === "ADMIN" || role === "SUPERVISOR";
export const canEditCarbonRecord = canCreateCarbonRecord;
export const canDeleteCarbonRecord = (role?: UserRole | null) => role === "SUPER_ADMIN" || role === "ADMIN";
export const canManageCarbonFactors = (role?: UserRole | null) => isAdminRole(role);
export const canViewOperationalConsumption = (role?: UserRole | null) => Boolean(role);
export const canCreateOperationalConsumption = (role?: UserRole | null) => role === "SUPER_ADMIN" || role === "ADMIN" || role === "SUPERVISOR";
export const canEditOperationalConsumption = canCreateOperationalConsumption;
export const canDeleteOperationalConsumption = (role?: UserRole | null) => role === "SUPER_ADMIN" || role === "ADMIN";
export const canUseWorkerConsumptionActions = (role?: UserRole | null) => role === "WORKER" || role === "SUPERVISOR";

export const canViewSurveys = (role?: UserRole | null) => role === "SUPER_ADMIN" || role === "ADMIN" || role === "SUPERVISOR" || role === "CLIENT";
export const canCreateSurvey = (role?: UserRole | null) => role === "SUPER_ADMIN" || role === "ADMIN" || role === "SUPERVISOR";
export const canEditSurvey = canCreateSurvey;
export const canCloseSurvey = canCreateSurvey;
export const canImportSurveyCsv = canCreateSurvey;
export const canViewSurveyResponses = (role?: UserRole | null) => canViewSurveys(role);
export const canViewSurveySummary = (role?: UserRole | null) => canViewSurveys(role);
export const canManageSurveyQr = canCreateSurvey;
export const canViewEventDashboard = (role?: UserRole | null) => role === "SUPER_ADMIN" || role === "ADMIN" || role === "SUPERVISOR" || role === "CLIENT";
export const canViewAdminDashboard = (role?: UserRole | null) => isAdminRole(role);
export const canViewClientDashboard = (role?: UserRole | null) => role === "CLIENT";
export const canViewWorkerDashboard = (role?: UserRole | null) => role === "WORKER" || role === "SUPERVISOR";

export const canViewReports = (role?: UserRole | null) => role === "SUPER_ADMIN" || role === "ADMIN" || role === "SUPERVISOR" || role === "CLIENT";
export const canGenerateReports = (role?: UserRole | null) => isAdminRole(role);
export const canDownloadReports = (role?: UserRole | null) => canViewReports(role);
export const canDeleteReports = (role?: UserRole | null) => isAdminRole(role);
export const canMarkReportDelivered = (role?: UserRole | null) => isAdminRole(role);
export const canViewReportPreview = (role?: UserRole | null) => role === "SUPER_ADMIN" || role === "ADMIN" || role === "SUPERVISOR";

export const canViewClientEvents = (role?: UserRole | null) => role === "CLIENT";
export const canViewClientEventDetail = (role?: UserRole | null) => role === "CLIENT";
export const canViewClientReports = (role?: UserRole | null) => role === "CLIENT";
export const canViewClientIndicators = (role?: UserRole | null) => role === "CLIENT";
export const canDownloadClientReports = (role?: UserRole | null) => role === "CLIENT";
export const canClientReportIncident = (_role?: UserRole | null) => false;
