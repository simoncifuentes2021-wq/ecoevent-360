# Etapa 1B: operación humana por show

## Objetivo y diseño

La Etapa 1B conecta `event_sessions` con personal, turnos, tareas, incidencias y
evidencias sin convertir el show en obligatorio. En tareas, incidencias y
evidencias independientes, `session_id IS NULL` significa **General del evento**.
No se realiza backfill de datos históricos.

Relaciones principales:

```text
events ── event_sessions
  ├── event_staff ── event_session_staff ── event_sessions
  ├── tasks(session_id?, source_incident_id?)
  ├── incidents(session_id?, source_task_id?)
  └── evidences(session_id?, task_id?, incident_id?)
```

`event_session_staff` referencia la asignación `event_staff`, no un usuario
arbitrario. Sus FKs compuestas garantizan que show y personal pertenezcan al
mismo evento. Una persona puede participar en varios shows, pero no duplicarse
dentro del mismo show. El turno general de `event_staff` permanece intacto.

## Tareas e incidencias

Los payloads antiguos continúan siendo válidos. Los listados admiten
`session_id` y `scope=general|session|general_and_session`. Una asociación puede
cambiar sólo mientras la entidad carezca de actividad relevante y exige
`reassignment_reason`; evidencias, estados iniciados, correctivos y vínculos de
Bitácora bloquean la reasignación.

Una incidencia creada con `source_task_id` hereda el show de la tarea y rechaza
un `session_id` contradictorio. `POST /incidents/{id}/corrective-task` crea una
tarea trazable que hereda el show de la incidencia.

## Evidencias

La procedencia se resuelve en SQL con prioridad coherente desde tarea,
incidencia o `session_id` directo. El campo directo sólo se persiste para una
evidencia independiente. No se copian binarios ni objetos R2. Las respuestas
siguen sustituyendo la storage key por `/evidences/{id}/download`, que exige
autenticación y entrega contenido privado sin caché.

## Permisos y RLS

- ADMIN/SUPER_ADMIN: gestión completa autorizada.
- SUPERVISOR asignado: gestión dentro del evento operativo.
- WORKER: lectura de su asignación por show y operación de sus tareas según el
  ciclo existente.
- LOGISTICS_OPERATOR: sólo lectura de su propia asignación; no obtiene gestión
  de tareas o incidencias.
- CLIENT: no accede a personal, turnos, tareas, incidencias ni notas internas;
  las evidencias conservan el alcance expresamente autorizado del portal y no
  permiten mutación.

La migración separa SELECT/INSERT/UPDATE/DELETE para
`event_session_staff`, `tasks`, `incidents` y `evidences`. Debe verificarse con
un rol runtime sin `BYPASSRLS`.

## API

- `GET/POST /event-sessions/{session_id}/staff`
- `PATCH/DELETE /event-session-staff/{assignment_id}`
- `GET /event-staff/{event_staff_id}/sessions`
- `GET /event-sessions/{session_id}/operations/summary`
- `GET /events/{event_id}/tasks?session_id=&scope=`
- `GET /events/{event_id}/incidents?session_id=&scope=`
- `GET /events/{event_id}/evidences?session_id=&scope=`
- `POST /incidents/{incident_id}/corrective-task`

Las rutas de creación/edición existentes aceptan `session_id` opcional.

## Migración, despliegue y rollback

`20260806_0040` depende de `20260804_0039`. Antes del despliegue: respaldo
verificable, `alembic current`, revisión del rol migrador y ventana controlada.
Después:

```bash
cd backend
python -m alembic upgrade head
python -m alembic current
```

Desplegar backend y frontend del mismo SHA y ejecutar smoke tests. Para rollback,
retirar primero el código 1B. Sólo si ninguna operación 1B debe conservarse:

```bash
python -m alembic downgrade 20260804_0039
```

El downgrade elimina asignaciones por show y las asociaciones `session_id` de
1B; por ello se prefiere restaurar el respaldo en una base nueva si existen
datos productivos relevantes.

## Pruebas manuales

1. Evento sin shows y registros generales siguen visibles.
2. Asignar personal del evento, editar turno/función y retirar asignación.
3. Confirmar advertencia de solapamiento entre shows.
4. Crear tarea/incidencia general y específica; filtrar ambos contextos.
5. Confirmar herencia tarea → incidencia → tarea correctiva.
6. Bloquear reasignación después de actividad o evidencia.
7. Subir evidencia independiente y evidencia derivada sin exponer storage key.
8. Revisar resumen agregado y paginación del detalle del show.
9. Repetir permisos con todos los roles y UUID de otro evento.
10. Revisar auditoría, móvil y ausencia de diálogos nativos.

## Riesgos y límites

Los solapamientos son advertencias deliberadas. El resumen es operacional
básico, no el dashboard profesional de una etapa posterior. No se integran por
show residuos, carbono, logística, formularios, Bike Zone ni Bitácoras.
