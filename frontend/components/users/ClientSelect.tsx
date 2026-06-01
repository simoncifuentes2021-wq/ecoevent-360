"use client";

import type { UseFormRegisterReturn } from "react-hook-form";

import type { Client } from "@/types/client";

export function ClientSelect({
  registration,
  clients
}: {
  registration: UseFormRegisterReturn;
  clients: Client[];
}) {
  return (
    <select className="h-10 rounded-md border bg-white px-3 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" {...registration}>
      <option value="">Sin cliente</option>
      {clients.map((client) => (
        <option key={client.id} value={client.id}>
          {client.business_name}
        </option>
      ))}
    </select>
  );
}
