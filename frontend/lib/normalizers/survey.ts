import type { CSVImportResult, SurveyResponse, SurveySummary } from "@/types/survey";

function asNumber(value: unknown, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function buckets(value: unknown): Array<{ name: string; value: number }> {
  if (Array.isArray(value)) {
    return value.map((item) => ({
      name: String(item.name ?? item.label ?? item.key ?? item.zone ?? "Sin dato"),
      value: asNumber(item.value ?? item.count ?? item.total)
    }));
  }
  if (value && typeof value === "object") {
    return Object.entries(value).map(([name, count]) => ({ name, value: asNumber(count) }));
  }
  return [];
}

export function normalizeSurveySummary(raw: unknown): SurveySummary {
  const data = raw && typeof raw === "object" ? raw as Record<string, unknown> : {};
  return {
    total_responses: asNumber(data.total_responses ?? data.total),
    average_rating: asNumber(data.average_rating ?? data.avg_general_rating),
    recommendation_rate: asNumber(data.recommendation_rate ?? data.recommendation_percentage),
    cleaning_positive_rate: asNumber(data.cleaning_positive_rate ?? data.avg_cleanliness_rating),
    bathroom_positive_rate: asNumber(data.bathroom_positive_rate ?? data.avg_bathroom_rating),
    saw_recycling_points_rate: asNumber(data.saw_recycling_points_rate),
    recycling_action_rate: asNumber(data.recycling_action_rate),
    main_problems: buckets(data.main_problems),
    transport_modes: buckets(data.transport_modes),
    responses_by_zone: buckets(data.responses_by_zone),
    rating_distribution: buckets(data.rating_distribution ?? data.ratings),
    comments_sample: Array.isArray(data.comments_sample) ? data.comments_sample.map(String) : []
  };
}

export function normalizeSurveyResponses(raw: SurveyResponse[] | { items?: SurveyResponse[]; data?: SurveyResponse[] }) {
  if (Array.isArray(raw)) return raw;
  return raw.items ?? raw.data ?? [];
}

export function normalizeImportResult(raw: unknown): CSVImportResult {
  const data = raw && typeof raw === "object" ? raw as CSVImportResult : {};
  return {
    imported_rows: data.imported_rows ?? 0,
    skipped_rows: data.skipped_rows ?? 0,
    duplicated_rows: data.duplicated_rows ?? 0,
    errors: data.errors ?? [],
    message: data.message ?? "CSV importado correctamente."
  };
}

export function formatSurveyRate(value: number) {
  return `${Math.round(value)}%`;
}

export function formatSurveyRating(value: number) {
  return value ? value.toFixed(1) : "0.0";
}

export function mapBooleanAnswer(value: unknown) {
  if (value === true || value === "true" || value === "SI" || value === "Sí" || value === "si") return "Si";
  if (value === false || value === "false" || value === "NO" || value === "no") return "No";
  return "Sin dato";
}

export function getTopSurveyProblem(summary: SurveySummary) {
  return summary.main_problems.slice().sort((a, b) => b.value - a.value)[0]?.name || "Sin dato";
}

export function getTopTransportMode(summary: SurveySummary) {
  return summary.transport_modes.slice().sort((a, b) => b.value - a.value)[0]?.name || "Sin dato";
}
