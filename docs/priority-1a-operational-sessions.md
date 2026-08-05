# Prioridad 1A: núcleo operacional de shows

## Semántica

Un evento puede seguir funcionando sin shows. `EventSession` representa un show, jornada o sesión opcional dentro del rango del evento. Los módulos operacionales conservarán `session_id = NULL` como “General del evento”; esta etapa no asigna datos históricos a sesiones.

Los estados permitidos son `PLANNED`, `READY`, `IN_PROGRESS`, `COMPLETED` y `CANCELLED`. Las transiciones se validan en el servicio. El archivado se representa con `archived_at` y no elimina información.

## Integridad y seguridad

- El responsable debe pertenecer a `event_staff` del mismo evento.
- La fecha debe estar entre `events.start_date` y `events.end_date`; el término debe ser posterior al inicio.
- Un solapamiento de horario en el mismo escenario (o, si no hay escenario, en el mismo recinto) genera `overlap_warning`; no bloquea la programación.
- El borrado físico sólo se permite si no existen formularios, respuestas, registros Bike Zone ni QR asociados. En otro caso se responde `409` y debe archivarse.
- CLIENT puede consultar sesiones de sus eventos, pero `internal_notes` se elimina de su respuesta.
- RLS separa lectura de mutaciones. Sólo administradores y supervisores con acceso al evento pueden insertar, actualizar o eliminar.

## API

- `GET /events/{event_id}/sessions?include_archived=false`
- `POST /events/{event_id}/sessions`
- `GET/PATCH/DELETE /event-sessions/{session_id}`
- `POST /event-sessions/{session_id}/transition`
- `POST /event-sessions/{session_id}/archive`
- `POST /event-sessions/{session_id}/restore`
- `POST /event-sessions/{session_id}/duplicate`
- `PUT /events/{event_id}/sessions/reorder`

## Próximas etapas

1B agregará `event_session_staff` y `session_id` nullable a tareas, incidencias y evidencias generales. Las evidencias con padre derivarán la sesión de ese padre. Las etapas posteriores agregarán las asociaciones ambientales, logísticas y de bitácoras sin backfill de históricos.

## Despliegue y rollback

Ejecutar primero la migración `20260804_0039` y luego desplegar backend y frontend. Verificar que Alembic tenga una sola cabeza y probar cada rol con RLS activo. El downgrade restaura la política anterior y elimina únicamente las columnas/índices/checks creados por 1A; debe ejecutarse sólo después de retirar el código que usa esos campos.
