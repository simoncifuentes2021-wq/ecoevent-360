"use client";

import { useState } from "react";
import { Search } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { checkInBikeZone, checkOutBikeZone, type BikeZoneRecord, verifyBikeZoneCode } from "@/lib/api/bikeZone";

export function BikeZoneVerifier() {
  const [code, setCode] = useState("");
  const [record, setRecord] = useState<BikeZoneRecord | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function verify() {
    const normalized = code.trim().toUpperCase();
    if (!normalized) return;
    setLoading(true);
    setError(null);
    try {
      setRecord(await verifyBikeZoneCode(normalized));
      setCode(normalized);
    } catch (err) {
      setRecord(null);
      setError(err instanceof Error ? err.message : "No se pudo verificar el código.");
    } finally {
      setLoading(false);
    }
  }

  async function checkIn() {
    if (!record) return;
    setLoading(true);
    setError(null);
    try {
      setRecord(await checkInBikeZone(record.code));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo marcar check-in.");
    } finally {
      setLoading(false);
    }
  }

  async function checkOut() {
    if (!record) return;
    setLoading(true);
    setError(null);
    try {
      setRecord(await checkOutBikeZone(record.code));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo marcar check-out.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="rounded-lg border bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold text-slate-950">Validación Bike Zone</h3>
          <p className="text-sm text-slate-600">Busca el código Bike Zone BZ o el código de respuesta FR y marca su entrada o salida.</p>
        </div>
      </div>
      <div className="mt-4 flex flex-col gap-2 md:flex-row">
        <Input placeholder="BZ-XXXXXX o FR-XXXXXX" value={code} onChange={(event) => setCode(event.target.value.toUpperCase())} onKeyDown={(event) => { if (event.key === "Enter") void verify(); }} />
        <Button disabled={loading || !code.trim()} type="button" onClick={verify}>
          <Search className="h-4 w-4" />
          Buscar código
        </Button>
      </div>
      {error ? <div className="mt-3"><ErrorState message={error} title="No se pudo validar" /></div> : null}
      {record ? (
        <div className="mt-4 rounded-lg bg-slate-50 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase text-slate-500">Código</p>
              <p className="text-2xl font-black text-slate-950">{record.code}</p>
            </div>
            <span className="rounded-md bg-white px-3 py-1 text-sm font-bold text-emerald-800 shadow-sm">{record.status}</span>
          </div>
          <div className="mt-3 grid gap-2 text-sm md:grid-cols-2">
            <p>Check-in: <strong>{formatBikeZoneDate(record.check_in_at)}</strong></p>
            <p>Check-out: <strong>{formatBikeZoneDate(record.check_out_at)}</strong></p>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button disabled={loading || Boolean(record.check_in_at)} type="button" onClick={checkIn}>Marcar check-in</Button>
            <Button disabled={loading || Boolean(record.check_out_at)} type="button" variant="secondary" onClick={checkOut}>Marcar check-out</Button>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function formatBikeZoneDate(value?: string | null) {
  if (!value) return "Pendiente";
  const isoValue = /(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : `${value}Z`;
  return new Intl.DateTimeFormat("es-CL", {
    dateStyle: "short",
    timeStyle: "medium",
    hour12: false,
    timeZone: "America/Santiago",
  }).format(new Date(isoValue));
}
