import { EmptyState } from "@/components/common/EmptyState";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { Event } from "@/types/event";

export function RecentEventsTable({ events }: { events: Event[] }) {
  return (
    <Card>
      <CardHeader>
        <h2 className="font-semibold">Últimos eventos</h2>
      </CardHeader>
      <CardContent>
        {events.length === 0 ? (
          <EmptyState
            description="Cuando existan eventos, aparecerán aquí con su estado operativo."
            title="No hay eventos recientes"
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead className="text-xs uppercase text-muted-foreground">
                <tr className="border-b">
                  <th className="py-3 pr-4">Evento</th>
                  <th className="py-3 pr-4">Tipo</th>
                  <th className="py-3 pr-4">Inicio</th>
                  <th className="py-3 pr-4">Asistentes</th>
                  <th className="py-3">Estado</th>
                </tr>
              </thead>
              <tbody>
                {events.map((event) => (
                  <tr className="border-b last:border-0" key={event.id}>
                    <td className="py-3 pr-4 font-semibold">{event.name}</td>
                    <td className="py-3 pr-4 text-muted-foreground">{event.event_type ?? "Sin tipo"}</td>
                    <td className="py-3 pr-4 text-muted-foreground">
                      {new Date(event.start_date).toLocaleDateString("es-CL")}
                    </td>
                    <td className="py-3 pr-4 text-muted-foreground">
                      {event.real_attendees ?? event.estimated_attendees ?? 0}
                    </td>
                    <td className="py-3">
                      <StatusBadge status={event.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
