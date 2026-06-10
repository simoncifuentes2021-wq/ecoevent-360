export const APP_NAME = "EcoEvent 360";

const localApiUrl = "http://localhost:8000/api/v1";
const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

export const API_URL =
  configuredApiUrl ?? (process.env.NODE_ENV === "production" ? "" : localApiUrl);

export const API_ORIGIN = API_URL.replace(/\/api\/v\d+$/, "");
