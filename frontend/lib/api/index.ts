import { API_URL } from "@/lib/constants";
import { clearSession, getStoredToken } from "@/lib/auth";

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

async function request<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const token = options.auth === false ? null : getStoredToken();
  const headers = new Headers(options.headers);

  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (response.status === 401) {
    clearSession();
    if (typeof window !== "undefined") window.location.href = "/login";
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
  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string, options?: ApiOptions) => request<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body?: unknown, options?: ApiOptions) =>
    request<T>(path, {
      ...options,
      method: "POST",
      body: body instanceof FormData ? body : JSON.stringify(body ?? {})
    }),
  patch: <T>(path: string, body?: unknown, options?: ApiOptions) =>
    request<T>(path, {
      ...options,
      method: "PATCH",
      body: body instanceof FormData ? body : JSON.stringify(body ?? {})
    }),
  delete: <T>(path: string, options?: ApiOptions) =>
    request<T>(path, { ...options, method: "DELETE" })
};
