"use client";

import type { UseFormRegisterReturn } from "react-hook-form";

import { canCreateSuperAdmin } from "@/lib/permissions";
import type { UserRole } from "@/types/roles";

const roles: UserRole[] = [
  "SUPER_ADMIN",
  "ADMIN",
  "CLIENT",
  "SUPERVISOR",
  "LOGISTICS_OPERATOR",
  "WORKER"
];

export function RoleSelect({
  registration,
  currentRole
}: {
  registration: UseFormRegisterReturn;
  currentRole: UserRole;
}) {
  return (
    <select className="h-10 rounded-md border bg-white px-3 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" {...registration}>
      {roles
        .filter((role) => role !== "SUPER_ADMIN" || canCreateSuperAdmin(currentRole))
        .map((role) => (
          <option key={role} value={role}>
            {role}
          </option>
        ))}
    </select>
  );
}
