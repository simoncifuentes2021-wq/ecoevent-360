import { API_URL } from "@/lib/constants";
import { clearSession, getStoredToken } from "@/lib/auth";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
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
    try {
      const data = (await response.json()) as { detail?: unknown };
      if (typeof data.detail === "string") detail = data.detail;
      if (Array.isArray(data.detail)) detail = "La solicitud contiene datos invalidos.";
    } catch {
      detail = "No se pudo completar la solicitud.";
    }
    throw new ApiError(response.status, detail);
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
