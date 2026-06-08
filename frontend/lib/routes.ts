import {
  AlertTriangle,
  BarChart3,
  BriefcaseBusiness,
  Camera,
  ClipboardList,
  FileText,
  Home,
  Leaf,
  Recycle,
  Settings,
  ShieldCheck,
  Sparkles,
  Upload,
  Users,
  UserRound
} from "lucide-react";

import type { UserRole } from "@/types/roles";

export type NavItem = {
  href: string;
  label: string;
  icon: typeof Home;
};

export const roleNavigation: Record<UserRole, NavItem[]> = {
  SUPER_ADMIN: [
    { href: "/admin/dashboard", label: "Dashboard", icon: Home },
    { href: "/admin/clientes", label: "Clientes", icon: BriefcaseBusiness },
    { href: "/admin/usuarios", label: "Usuarios", icon: Users },
    { href: "/admin/eventos", label: "Eventos", icon: Sparkles },
    { href: "/admin/servicios", label: "Servicios", icon: Settings },
    { href: "/admin/residuos/tipos", label: "Residuos", icon: Recycle },
    { href: "/admin/huella/factores", label: "Factores", icon: Leaf },
    { href: "/admin/auditoria", label: "Auditoria", icon: ShieldCheck },
    { href: "/reports", label: "Reportes", icon: FileText },
    { href: "/settings", label: "Configuracion", icon: ShieldCheck }
  ],
  ADMIN: [
    { href: "/admin/dashboard", label: "Dashboard", icon: Home },
    { href: "/admin/clientes", label: "Clientes", icon: BriefcaseBusiness },
    { href: "/admin/usuarios", label: "Usuarios", icon: Users },
    { href: "/admin/eventos", label: "Eventos", icon: Sparkles },
    { href: "/admin/servicios", label: "Servicios", icon: Settings },
    { href: "/admin/residuos/tipos", label: "Residuos", icon: Recycle },
    { href: "/admin/huella/factores", label: "Factores", icon: Leaf },
    { href: "/admin/auditoria", label: "Auditoria", icon: ShieldCheck },
    { href: "/reports", label: "Reportes", icon: FileText },
    { href: "/settings", label: "Configuracion", icon: ShieldCheck }
  ],
  CLIENT: [
    { href: "/client/dashboard", label: "Dashboard", icon: Home },
    { href: "/client/mis-eventos", label: "Mis eventos", icon: Sparkles },
    { href: "/client/indicadores", label: "Indicadores", icon: BarChart3 },
    { href: "/client/reportes", label: "Reportes", icon: FileText },
    { href: "/client/mi-cuenta", label: "Mi cuenta", icon: UserRound }
  ],
  SUPERVISOR: [
    { href: "/supervisor/dashboard", label: "Dashboard", icon: Home },
    { href: "/supervisor/eventos", label: "Eventos asignados", icon: Sparkles },
    { href: "/worker/dashboard", label: "Panel terreno", icon: Home },
    { href: "/worker/mis-tareas", label: "Mis tareas", icon: ClipboardList },
    { href: "/worker/incidencias", label: "Incidencias", icon: AlertTriangle },
    { href: "/worker/reportar-incidencia", label: "Reportar incidencia", icon: AlertTriangle },
    { href: "/worker/subir-evidencia", label: "Evidencias", icon: Camera },
    { href: "/worker/registrar-residuo", label: "Residuos", icon: Recycle },
    { href: "/worker/registrar-consumo", label: "Consumos", icon: Leaf },
    { href: "/supervisor/alertas", label: "Alertas", icon: ShieldCheck }
  ],
  WORKER: [
    { href: "/worker/dashboard", label: "Inicio", icon: Home },
    { href: "/worker/mis-tareas", label: "Mis tareas", icon: ClipboardList },
    { href: "/worker/incidencias", label: "Incidencias", icon: AlertTriangle },
    { href: "/worker/reportar-incidencia", label: "Reportar incidencia", icon: AlertTriangle },
    { href: "/worker/subir-evidencia", label: "Subir evidencia", icon: Upload },
    { href: "/worker/registrar-residuo", label: "Registrar residuo", icon: Recycle },
    { href: "/worker/registrar-consumo", label: "Registrar consumo", icon: Leaf },
    { href: "/worker/cuenta", label: "Mi cuenta", icon: UserRound }
  ]
};
