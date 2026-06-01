"use client";

import { Building2, Mail, UserRound } from "lucide-react";

import { RoleBadge } from "@/components/common/RoleBadge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { AuthUser } from "@/types/auth";
import type { Client } from "@/types/client";

export function ClientAccountPage({ user, client }: { user: AuthUser; client?: Client | null }) {
  return (
    <div className="grid gap-4 xl:grid-cols-[.8fr_1.2fr]">
      <Card>
        <CardHeader><h2 className="font-semibold">Usuario</h2></CardHeader>
        <CardContent className="space-y-4">
          <Info icon={<UserRound className="h-5 w-5" />} label="Nombre" value={user.full_name} />
          <Info icon={<Mail className="h-5 w-5" />} label="Email" value={user.email} />
          <div><p className="text-xs font-semibold uppercase text-slate-500">Rol</p><RoleBadge role={user.role} /></div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><h2 className="font-semibold">Empresa asociada</h2></CardHeader>
        <CardContent className="space-y-4">
          <Info icon={<Building2 className="h-5 w-5" />} label="Razon social" value={client?.business_name || "No informada"} />
          <Info label="RUT" value={client?.rut || "No informado"} />
          <Info label="Contacto" value={client?.contact_name || "No informado"} />
          <Info label="Email contacto" value={client?.contact_email || "No informado"} />
          <Info label="Telefono" value={client?.contact_phone || "No informado"} />
          <Info label="Direccion" value={client?.address || "No informada"} />
          <div className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-900">Para modificar datos comerciales, contacta al administrador del sistema.</div>
        </CardContent>
      </Card>
    </div>
  );
}

function Info({ icon, label, value }: { icon?: React.ReactNode; label: string; value: string }) {
  return <div className="flex gap-3 rounded-xl bg-slate-50 p-3">{icon ? <span className="text-emerald-700">{icon}</span> : null}<div><p className="text-xs font-semibold uppercase text-slate-500">{label}</p><p className="font-semibold text-slate-950">{value}</p></div></div>;
}
