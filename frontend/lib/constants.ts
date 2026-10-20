export const APP_NAME = "Greenway App";

// The local backend launched for this workspace listens on port 8002.
const localApiUrl = "http://127.0.0.1:8002/api/v1";
const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
const usesLocalBackend = !configuredApiUrl || /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?\/api\/v\d+$/.test(configuredApiUrl);

export const API_URL =
  process.env.NODE_ENV !== "production" && usesLocalBackend
    ? "/api/v1"
    : configuredApiUrl ?? (process.env.NODE_ENV === "production" ? "" : localApiUrl);

export const API_ORIGIN = API_URL.replace(/\/api\/v\d+$/, "");
