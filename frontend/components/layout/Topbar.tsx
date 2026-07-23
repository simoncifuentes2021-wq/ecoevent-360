"use client";

import { usePathname } from "next/navigation";

import { MobileSidebar } from "@/components/layout/MobileSidebar";
import { UserMenu } from "@/components/layout/UserMenu";
import type { AuthUser } from "@/types/auth";

const idSegmentPattern = /^[0-9a-f]{8,}(?:-[0-9a-f]{4,}){2,}$/i;

const routeTitles: Record<string, string> = {
  "/admin/clientes/nuevo": "Nuevo cliente",
  "/admin/eventos/nuevo": "Nuevo evento",
  "/admin/servicios/nuevo": "Nuevo servicio",
  "/admin/usuarios/nuevo": "Nuevo usuario",
  "/admin/logistica/pedidos": "Pedidos logisticos",
  "/admin/stock/bodegas": "Bodegas",
  "/admin/stock/compras": "Compras",
  "/admin/stock/movimientos": "Movimientos",
  "/admin/stock/productos": "Productos",
  "/client/mi-cuenta": "Mi cuenta",
  "/client/mis-eventos": "Mis eventos",
  "/logistica/mis-pedidos": "Mis pedidos",
  "/logistica/stock/movimientos": "Movimientos",
  "/supervisor/logistica/pedidos": "Pedidos logisticos",
  "/worker/mis-tareas": "Mis tareas",
  "/worker/registrar-consumo": "Registrar consumo",
  "/worker/registrar-residuo": "Registrar residuo",
  "/worker/reportar-incidencia": "Reportar incidencia",
  "/worker/subir-evidencia": "Subir evidencia"
};

const detailTitles: Record<string, string> = {
  bitacoras: "Detalle de bitácora",
  ejecuciones: "Ejecución de bitácora",
  clientes: "Detalle cliente",
  eventos: "Detalle evento",
  incidencias: "Detalle incidencia",
  "mis-pedidos": "Detalle pedido",
  "mis-tareas": "Detalle tarea",
  pedidos: "Detalle pedido",
  servicios: "Detalle servicio",
  tareas: "Detalle tarea",
  usuarios: "Detalle usuario"
};

function formatSegment(segment: string) {
  return segment.replaceAll("-", " ");
}

function titleFromPath(pathname: string) {
  const parts = pathname.split("/").filter(Boolean);
  if (parts.length === 0) return "Inicio";
  const path = `/${parts.join("/")}`;
  if (routeTitles[path]) return routeTitles[path];

  const last = parts[parts.length - 1];
  const previous = parts[parts.length - 2];
  const beforePrevious = parts[parts.length - 3];

  if (last === "editar" && beforePrevious) {
    return `Editar ${formatSegment(beforePrevious).replace(/s$/, "")}`;
  }

  if (idSegmentPattern.test(last) && previous) {
    return detailTitles[previous] || `Detalle ${formatSegment(previous).replace(/s$/, "")}`;
  }

  return formatSegment(last);
}

export function Topbar({ user }: { user: AuthUser }) {
  const pathname = usePathname();
  const title = titleFromPath(pathname);

  return (
    <header className="sticky top-0 z-30 border-b bg-background/88 px-4 py-3 backdrop-blur md:px-8">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <MobileSidebar user={user} />
          <div>
            <p className="text-xs font-medium uppercase text-muted-foreground">EcoEvent 360</p>
            <h1 className="capitalize text-lg font-bold md:text-xl">{title}</h1>
          </div>
        </div>
        <UserMenu />
      </div>
    </header>
  );
}
