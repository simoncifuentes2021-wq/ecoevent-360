"use client";

import { useEffect, useState } from "react";

import { getStoredToken } from "@/lib/auth";
import { API_ORIGIN, API_URL } from "@/lib/constants";

function authenticatedUrl(value: string) {
  if (value.startsWith("/api/")) return `${API_ORIGIN}${value}`;
  const path = value.startsWith("/") ? value : `/${value}`;
  return `${API_URL}${path}`;
}

export function usePrivateFileUrl(value: string) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let objectUrl: string | null = null;

    async function load() {
      try {
        setError(null);
        const token = getStoredToken();
        const response = await fetch(authenticatedUrl(value), {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          signal: controller.signal
        });
        if (!response.ok) throw new Error(`No se pudo abrir el archivo (${response.status}).`);
        objectUrl = URL.createObjectURL(await response.blob());
        setUrl(objectUrl);
      } catch (reason) {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : "No se pudo abrir el archivo.");
        }
      }
    }

    void load();
    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [value]);

  return { url, error };
}
