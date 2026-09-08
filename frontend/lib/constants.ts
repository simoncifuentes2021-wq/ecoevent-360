export const APP_NAME = "EcoEvent 360";

// Port 8000 can be retained by an orphaned Windows reload worker during local
// development. The actively managed local backend runs on 8001.
const localApiUrl = "http://localhost:8001/api/v1";
const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

export const API_URL =
  configuredApiUrl ?? (process.env.NODE_ENV === "production" ? "" : localApiUrl);

export const API_ORIGIN = API_URL.replace(/\/api\/v\d+$/, "");
