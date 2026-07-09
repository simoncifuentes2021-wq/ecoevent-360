import { api } from "@/lib/api";

export type BikeZoneRecord = {
  id: string;
  code: string;
  status: "REGISTERED" | "CHECKED_IN" | "CHECKED_OUT";
  check_in_at?: string | null;
  check_out_at?: string | null;
};

export function verifyBikeZoneCode(code: string) {
  return api.get<BikeZoneRecord>(`/bike-zone/verify/${code}`);
}

export function checkInBikeZone(code: string) {
  return api.patch<BikeZoneRecord>(`/bike-zone/verify/${code}/check-in`, {});
}

export function checkOutBikeZone(code: string) {
  return api.patch<BikeZoneRecord>(`/bike-zone/verify/${code}/check-out`, {});
}
