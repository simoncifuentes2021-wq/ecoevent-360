"use client";

import { useCallback, useEffect, useState } from "react";
import { CalendarDays, CheckCircle2, ExternalLink, Link2Off, Loader2, RefreshCw, ShieldCheck, TriangleAlert } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api";

type CalendarStatus = {
  configured: boolean;
  missing_configuration: string[];
  connected: boolean;
  account_email: string | null;
  connected_at: string | null;
};

const callbackMessages: Record<string, { tone: string; message: string }> = {
  connected: { tone: "success", message: "Google Calendar quedó conectado correctamente." },
  cancelled: { tone: "warning", message: "No se conectó la cuenta. Puedes intentarlo cuando quieras." },
  invalid_state: { tone: "error", message: "La autorización expiró o no se pudo validar. Inicia la conexión nuevamente." },
  invalid_client: { tone: "error", message: "Google rechazó el ID o el secreto del cliente. Revisa que ambos pertenezcan al mismo cliente OAuth de tipo Aplicación web." },
  missing_refresh_token: { tone: "error", message: "Google no entregó autorización para mantener la conexión. Quita el acceso de EcoEvent en tu cuenta de Google y vuelve a conectar con el consentimiento completo." },
  oauth_error: { tone: "error", message: "Google rechazó el intercambio de autorización. Revisa la dirección de retorno y vuelve a intentarlo." },
  error: { tone: "error", message: "Google no pudo completar la conexión. Revisa la configuración e inténtalo otra vez." }
};

function SettingsContent() {
  const [status, setStatus] = useState<CalendarStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ tone: string; message: string } | null>(null);

  const loadStatus = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setStatus(await api.get<CalendarStatus>("/integrations/google-calendar/status"));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo consultar la conexión.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadStatus();
    const result = new URLSearchParams(window.location.search).get("google_calendar");
    if (result && callbackMessages[result]) {
      setNotice(callbackMessages[result]);
      window.history.replaceState({}, "", "/settings");
    }
  }, [loadStatus]);

  async function connect() {
    setBusy(true);
    setError(null);
    try {
      const result = await api.post<{ authorization_url: string }>("/integrations/google-calendar/connect");
      window.location.assign(result.authorization_url);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo iniciar la conexión.");
      setBusy(false);
    }
  }

  async function disconnect() {
    if (!window.confirm("¿Desconectar Google Calendar? Las invitaciones ya enviadas seguirán en los calendarios de las personas.")) return;
    setBusy(true);
    setError(null);
    try {
      await api.delete("/integrations/google-calendar/connection");
      setNotice({ tone: "success", message: "La cuenta de Google Calendar quedó desconectada." });
      await loadStatus();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo desconectar la cuenta.");
    } finally {
      setBusy(false);
    }
  }

  const apiBase = process.env.NEXT_PUBLIC_API_URL?.replace(/\/api\/v\d+\/?$/, "") || "http://127.0.0.1:8002";

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Sistema" title="Configuración" description="Administra las conexiones de EcoEvent 360. Solo el Super Admin puede vincular estas cuentas." />

      {notice ? <div className={`rounded-xl border p-4 text-sm ${notice.tone === "success" ? "border-emerald-200 bg-emerald-50 text-emerald-900" : notice.tone === "warning" ? "border-amber-200 bg-amber-50 text-amber-950" : "border-rose-200 bg-rose-50 text-rose-900"}`}>{notice.message}</div> : null}
      {error ? <ErrorState message={error} onRetry={() => void loadStatus()} /> : null}

      <Card className="overflow-hidden">
        <div className="flex flex-col gap-5 border-b bg-gradient-to-r from-emerald-50 via-white to-white p-6 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex gap-4">
            <span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-emerald-100 text-emerald-800"><CalendarDays className="h-6 w-6" /></span>
            <div>
              <h2 className="text-lg font-semibold">Google Calendar</h2>
              <p className="mt-1 max-w-2xl text-sm text-muted-foreground">Usa el calendario de la cuenta conectada como organizador para las invitaciones del personal asignado a eventos.</p>
            </div>
          </div>
          {status?.connected ? (
            <Button variant="secondary" disabled={busy} onClick={() => void disconnect()}>{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Link2Off className="h-4 w-4" />}Desconectar cuenta</Button>
          ) : (
            <Button disabled={busy || loading || !status?.configured} onClick={() => void connect()}>{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ExternalLink className="h-4 w-4" />}Conectar Google Calendar</Button>
          )}
        </div>

        <CardContent className="space-y-5">
          {loading ? <LoadingState label="Consultando conexión..." /> : null}
          {!loading && status ? <>
            <div className={`flex items-start gap-3 rounded-xl border p-4 ${status.connected ? "border-emerald-200 bg-emerald-50/70" : "border-slate-200 bg-slate-50"}`}>
              {status.connected ? <CheckCircle2 className="mt-0.5 h-5 w-5 text-emerald-700" /> : <ShieldCheck className="mt-0.5 h-5 w-5 text-slate-500" />}
              <div className="min-w-0">
                <p className="font-medium">{status.connected ? "Cuenta conectada" : "Cuenta no conectada"}</p>
                {status.connected ? <>
                  <p className="mt-1 break-all text-sm text-muted-foreground">{status.account_email}</p>
                  {status.connected_at ? <p className="mt-1 text-xs text-muted-foreground">Conectada el {new Date(status.connected_at).toLocaleString("es-CL")}</p> : null}
                </> : <p className="mt-1 text-sm text-muted-foreground">Conecta la cuenta que debe aparecer como organizadora de las invitaciones.</p>}
              </div>
            </div>

            {!status.configured ? <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
              <div className="flex gap-3"><TriangleAlert className="mt-0.5 h-5 w-5 shrink-0" /><div>
                <p className="font-semibold">Falta preparar la conexión de Google</p>
                <p className="mt-1">La API necesita estas variables antes de habilitar el botón:</p>
                <ul className="mt-2 list-inside list-disc space-y-1 font-mono text-xs">{status.missing_configuration.map((name) => <li key={name}>{name}</li>)}</ul>
                <p className="mt-2 text-xs">Dirección de retorno para registrar en Google Cloud:</p>
                <code className="mt-1 block break-all rounded bg-white/70 p-2 text-xs">{apiBase}/api/v1/integrations/google-calendar/callback</code>
              </div></div>
            </div> : null}

            <p className="text-xs leading-5 text-muted-foreground">La autorización permite administrar invitaciones de eventos. Al desconectar se revoca el acceso de EcoEvent; las invitaciones ya enviadas no se borran de los calendarios de sus destinatarios.</p>
            <Button variant="ghost" size="sm" disabled={busy} onClick={() => void loadStatus()}><RefreshCw className="h-4 w-4" />Actualizar estado</Button>
          </> : null}
        </CardContent>
      </Card>
    </div>
  );
}

export default function SettingsPage() {
  return <RoleGuard roles={["SUPER_ADMIN"]}><SettingsContent /></RoleGuard>;
}
