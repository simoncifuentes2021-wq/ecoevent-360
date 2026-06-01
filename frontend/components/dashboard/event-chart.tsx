"use client";

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { eventTrend } from "@/lib/mock-data";

export function EventChart() {
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={eventTrend} margin={{ left: -16, right: 12, top: 12 }}>
          <defs>
            <linearGradient id="residuos" x1="0" x2="0" y1="0" y2="1">
              <stop offset="5%" stopColor="#0f766e" stopOpacity={0.26} />
              <stop offset="95%" stopColor="#0f766e" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#d7dee8" />
          <XAxis dataKey="name" tickLine={false} axisLine={false} />
          <YAxis tickLine={false} axisLine={false} />
          <Tooltip />
          <Area
            type="monotone"
            dataKey="residuos"
            stroke="#0f766e"
            fill="url(#residuos)"
            strokeWidth={2}
          />
          <Area type="monotone" dataKey="co2e" stroke="#f59e0b" fill="transparent" strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

