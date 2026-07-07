import {
  AlertTriangle,
  BarChart3,
  BriefcaseBusiness,
  Camera,
  ClipboardList,
  FileText,
  Home,
  Leaf,
  Boxes,
  Recycle,
  Settings,
  ShieldCheck,
  Sparkles,
  ShoppingCart,
  Upload,
  PackageSearch,
  Users,
  UserRound
} from "lucide-react";

import type { UserRole } from "@/types/roles";

export type NavItem = {
  href: string;
  label: string;
  icon: typeof Home;
  disabled?: boolean;
  indent?: boolean;
};

export const roleNavigation: Record<UserRole, NavItem[]> = {
  SUPER_ADMIN: [
    { href: "/admin/dashboard", label: "Dashboard", icon: Home },
    { href: "/admin/clientes", label: "Clientes", icon: BriefcaseBusiness },
    { href: "/admin/usuarios", label: "Usuarios", icon: Users },
    { href: "/admin/eventos", label: "Eventos", icon: Sparkles },
    { href: "/admin/logistica/pedidos", label: "Pedidos logisticos", icon: PackageSearch },
    { href: "/admin/stock", label: "Stock", icon: Boxes },
    { href: "/admin/stock/bodegas", label: "Bodegas", icon: Boxes, indent: true },
    { href: "/admin/stock/productos", label: "Productos", icon: PackageSearch, indent: true },
    { href: "/admin/stock/movimientos", label: "Movimientos", icon: ClipboardList, indent: true },
    { href: "/admin/stock/compras", label: "Compras", icon: ShoppingCart, indent: true },
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
    { href: "/admin/logistica/pedidos", label: "Pedidos logisticos", icon: PackageSearch },
    { href: "/admin/stock", label: "Stock", icon: Boxes },
    { href: "/admin/stock/bodegas", label: "Bodegas", icon: Boxes, indent: true },
    { href: "/admin/stock/productos", label: "Productos", icon: PackageSearch, indent: true },
    { href: "/admin/stock/movimientos", label: "Movimientos", icon: ClipboardList, indent: true },
    { href: "/admin/stock/compras", label: "Compras", icon: ShoppingCart, indent: true },
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
    { href: "/supervisor/logistica/pedidos", label: "Pedidos logisticos", icon: PackageSearch },
    { href: "/worker/dashboard", label: "Panel terreno", icon: Home },
    { href: "/worker/mis-tareas", label: "Mis tareas", icon: ClipboardList },
    { href: "/worker/incidencias", label: "Incidencias", icon: AlertTriangle },
    { href: "/worker/reportar-incidencia", label: "Reportar incidencia", icon: AlertTriangle },
    { href: "/worker/subir-evidencia", label: "Evidencias", icon: Camera },
    { href: "/worker/registrar-residuo", label: "Residuos", icon: Recycle },
    { href: "/worker/registrar-consumo", label: "Consumos", icon: Leaf },
    { href: "/supervisor/alertas", label: "Alertas", icon: ShieldCheck }
  ],
  LOGISTICS_OPERATOR: [
    { href: "/logistica/dashboard", label: "Dashboard", icon: Home },
    { href: "/logistica/mis-pedidos", label: "Mis pedidos", icon: PackageSearch },
    { href: "/logistica/stock", label: "Inventario", icon: Boxes },
    { href: "/logistica/stock/movimientos", label: "Movimientos", icon: ClipboardList, indent: true },
    { href: "/logistica/productos", label: "Productos", icon: PackageSearch },
    { href: "/logistica/compras", label: "Compras", icon: ShoppingCart }
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
