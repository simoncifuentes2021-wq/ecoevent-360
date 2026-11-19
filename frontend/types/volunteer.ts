import type { WasteType } from "@/types/waste";

export type ActivationStatus = "DRAFT" | "ACTIVE" | "CLOSED" | "CANCELLED" | "ARCHIVED";
export type ContributionStatus = "ACTIVE" | "VOID";

export type RecyclingActivation = {
  id: string;
  event_id: string;
  session_id: string | null;
  event_name?: string | null;
  name: string;
  description: string | null;
  location_name: string | null;
  address: string | null;
  starts_at: string;
  ends_at: string | null;
  responsible_user_id: string | null;
  status: ActivationStatus;
  capacity: number | null;
  public_slug: string;
  created_at: string;
  updated_at: string;
  volunteer_count: number;
  contribution_count: number;
  total_weight_kg: string | number;
  allowed_material_ids: string[];
};

export type RecyclableMaterial = WasteType;

export type ContributionItem = {
  id?: string;
  material_id: string;
  material_name_snapshot?: string;
  unit_snapshot?: string;
  weight_kg: string | number;
};

export type MaterialContribution = {
  id: string;
  volunteer_id: string;
  volunteer_name: string;
  volunteer_email: string | null;
  volunteer_code: string;
  activation_id: string;
  activation_name: string;
  event_id: string;
  event_name: string;
  registered_by_user_id: string | null;
  registered_by_name: string | null;
  registered_at: string;
  notes: string | null;
  total_weight_kg: string | number;
  status: ContributionStatus;
  void_reason: string | null;
  voided_at: string | null;
  email_status: "PENDING" | "SENT" | "FAILED" | "SKIPPED";
  items: ContributionItem[];
  evidence_count: number;
};

export type VolunteerListItem = {
  id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  organization: string | null;
  unique_code: string;
  status: "ACTIVE" | "INACTIVE" | "ARCHIVED";
  registered_at: string;
  activation_count: number;
  contribution_count: number;
  total_weight_kg: string | number;
};

export type VolunteerResolve = {
  id: string;
  full_name: string;
  unique_code: string;
  already_in_activation: boolean;
  total_weight_kg_in_event: string | number;
};

export type VolunteerDashboard = {
  unique_volunteers: number;
  participations: number;
  contributions: number;
  total_weight_kg: string | number;
  active_activations: number;
  average_per_volunteer_kg: string | number;
  by_date: Array<{ date: string; kg: number | string; contributions: number }>;
  by_activation: Array<{ id: string; name: string; kg: number | string; contributions: number }>;
  by_material: Array<{ material: string; kg: number | string }>;
  new_volunteers_by_date: Array<{ date: string; volunteers: number }>;
};

export type PublicActivation = {
  name: string;
  description: string | null;
  event_name: string;
  location_name: string | null;
  address: string | null;
  starts_at: string;
  ends_at: string | null;
  status: string;
  consent_text: string;
  consent_version: string;
};

export type PublicVolunteerImpact = {
  full_name: string;
  total_weight_kg: string | number;
  activation_count: number;
  contribution_count: number;
  material_totals: Record<string, string | number>;
  contributions: Array<{
    id: string;
    activation: string;
    event: string;
    registered_at: string;
    total_weight_kg: string | number;
    items: Array<{ material: string; weight_kg: string | number; unit: string }>;
    evidences: Array<{ id: string; description: string | null; file_type: string | null }>;
  }>;
};
