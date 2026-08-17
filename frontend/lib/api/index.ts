import { API_URL } from "@/lib/constants";
import { clearSession, getStoredToken } from "@/lib/auth";
import { chileLocalToIso } from "@/lib/chile-time";

export class ApiError extends Error {
  status: number;
  detail: string;
  rawDetail: unknown;

  constructor(status: number, detail: string, rawDetail?: unknown) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.rawDetail = rawDetail;
  }
}

type ApiOptions = RequestInit & {
  auth?: boolean;
};

export function sanitizeChileDateTimes(value: unknown): unknown {
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?$/.test(value)) {
    return chileLocalToIso(value);
  }
  if (Array.isArray(value)) return value.map(sanitizeChileDateTimes);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([key, entry]) => [key, sanitizeChileDateTimes(entry)]));
  }
  return value;
}

export function normalizeApiDateTimes(value: unknown): unknown {
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?$/.test(value)) {
    return `${value}Z`;
  }
  if (Array.isArray(value)) return value.map(normalizeApiDateTimes);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([key, entry]) => [key, normalizeApiDateTimes(entry)]));
  }
  return value;
}

const jsonBody = (body: unknown) => JSON.stringify(sanitizeChileDateTimes(body ?? {}));

async function request<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const token = options.auth === false ? null : getStoredToken();
  const headers = new Headers(options.headers);

  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });

  // A request made with an expired token can finish after a successful login.
  // Only clear the session when the rejected token is still the active one.
  if (response.status === 401 && token && getStoredToken() === token) {
    clearSession();
    if (typeof window !== "undefined" && window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
  }

  if (!response.ok) {
    let detail = `Error ${response.status}`;
    let rawDetail: unknown = undefined;
    try {
      const data = (await response.json()) as { detail?: unknown };
      rawDetail = data.detail;
      if (typeof data.detail === "string") detail = data.detail;
      if (
        data.detail &&
        typeof data.detail === "object" &&
        "message" in data.detail &&
        typeof data.detail.message === "string"
      ) {
        detail = data.detail.message;
      }
      if (Array.isArray(data.detail)) detail = "Revisa los campos marcados.";
    } catch {
      detail = "No se pudo completar la solicitud.";
    }
    throw new ApiError(response.status, detail, rawDetail);
  }

  if (response.status === 204) return undefined as T;
  return normalizeApiDateTimes(await response.json()) as T;
}

export const api = {
  get: <T>(path: string, options?: ApiOptions) => request<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body?: unknown, options?: ApiOptions) =>
    request<T>(path, {
      ...options,
      method: "POST",
      body: body instanceof FormData ? body : jsonBody(body)
    }),
  patch: <T>(path: string, body?: unknown, options?: ApiOptions) =>
    request<T>(path, {
      ...options,
      method: "PATCH",
      body: body instanceof FormData ? body : jsonBody(body)
    }),
  put: <T>(path: string, body?: unknown, options?: ApiOptions) =>
    request<T>(path, {
      ...options,
      method: "PUT",
      body: body instanceof FormData ? body : jsonBody(body)
    }),
  delete: <T>(path: string, options?: ApiOptions) =>
    request<T>(path, { ...options, method: "DELETE" })
};
