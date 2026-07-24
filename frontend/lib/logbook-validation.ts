import type { LogbookItem, LogbookResponse } from "@/types/logbook";

export type LogbookRequirement = { itemId: string; itemTitle: string; sectionTitle: string };

export type LogbookValidationSummary = {
  totalItems: number;
  answeredItems: number;
  unansweredItems: number;
  optionalUnansweredItems: number;
  pendingRequiredResponses: LogbookRequirement[];
  pendingComments: LogbookRequirement[];
  pendingEvidences: LogbookRequirement[];
  pendingFailureEvidences: LogbookRequirement[];
  failedItems: number;
  evidenceCount: number;
  complete: boolean;
};

export function isAnswered(response?: LogbookResponse): boolean {
  if (!response || response.result_status === "PENDING") return false;
  if (response.is_not_applicable) return true;
  if (response.boolean_value !== undefined && response.boolean_value !== null) return true;
  if (response.numeric_value !== undefined && response.numeric_value !== null) return true;
  if (typeof response.text_value === "string" && response.text_value.trim() !== "") return true;
  if (typeof response.selected_option_id === "string" && response.selected_option_id !== "") return true;
  return response.result_status === "COMPLETED"
    && response.evidences.some((evidence) => !evidence.deleted_at);
}

export function validateLogbook(
  sections: Array<{ title: string; items: LogbookItem[] }>,
  responses: Map<string, LogbookResponse>,
): LogbookValidationSummary {
  const pendingRequiredResponses: LogbookRequirement[] = [];
  const pendingComments: LogbookRequirement[] = [];
  const pendingEvidences: LogbookRequirement[] = [];
  const pendingFailureEvidences: LogbookRequirement[] = [];
  let totalItems = 0;
  let answeredItems = 0;
  let optionalUnansweredItems = 0;
  let failedItems = 0;
  let evidenceCount = 0;

  for (const section of sections) {
    for (const item of section.items) {
      totalItems += 1;
      const response = responses.get(item.id);
      const answered = isAnswered(response);
      const entry = { itemId: item.id, itemTitle: item.title, sectionTitle: section.title };
      if (answered) answeredItems += 1;
      else if (item.is_required) pendingRequiredResponses.push(entry);
      else optionalUnansweredItems += 1;
      if (!response) continue;

      if (response.result_status === "FAILED") failedItems += 1;
      const activeEvidences = response.evidences.filter((evidence) => !evidence.deleted_at).length;
      evidenceCount += activeEvidences;
      if (
        response.result_status === "FAILED"
        && item.require_comment_on_failure
        && !response.comment?.trim()
      ) pendingComments.push(entry);
      const minimum = Math.max(1, item.min_evidences);
      if (item.evidence_policy === "REQUIRED" && activeEvidences < minimum) {
        pendingEvidences.push(entry);
      }
      if (
        item.evidence_policy === "REQUIRED_ON_FAILURE"
        && response.result_status === "FAILED"
        && activeEvidences < minimum
      ) pendingFailureEvidences.push(entry);
    }
  }

  return {
    totalItems,
    answeredItems,
    unansweredItems: totalItems - answeredItems,
    optionalUnansweredItems,
    pendingRequiredResponses,
    pendingComments,
    pendingEvidences,
    pendingFailureEvidences,
    failedItems,
    evidenceCount,
    complete: [
      pendingRequiredResponses,
      pendingComments,
      pendingEvidences,
      pendingFailureEvidences,
    ].every((items) => items.length === 0),
  };
}
