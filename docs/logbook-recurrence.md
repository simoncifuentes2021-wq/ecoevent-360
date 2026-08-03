# Bitácoras recurrentes

## Modelo y reglas

Una serie recurrente congela una versión publicada de plantilla y la configuración futura: evento, modalidad, supervisor, participantes, zona y visibilidad. Cada fecha crea un `logbook_instance` independiente; respuestas, fotografías privadas, revisiones y auditoría siguen vinculadas exclusivamente a esa ejecución.

Frecuencias admitidas: diaria, semanal (uno o varios días) y mensual, con intervalo mayor que cero. La serie termina por fecha final inclusiva o por cantidad, con un máximo de 500 ocurrencias. En reglas mensuales, los meses que no contienen el día seleccionado se omiten; no se desplaza la fecha al último día del mes.

Las horas se interpretan en una zona IANA, por defecto `America/Santiago`, y se almacenan como instantes UTC. Una hora local inexistente por cambio de horario se rechaza. En una hora ambigua se utiliza la primera ocurrencia (`fold=0`) de forma determinista.

Estados de serie: `ACTIVE`, `PAUSED`, `FINISHED` y `CANCELLED`. Pausar impide nueva generación; reanudar completa la ventana; finalizar conserva todo el historial.

## Generación y excepciones

Una serie acotada de hasta 100 fechas se genera al crearla. Las series extensas mantienen una ventana de 12 semanas. El mismo procesador general que abre y vence bitácoras completa esa ventana; no existe un segundo cron.

La restricción PostgreSQL `UNIQUE (recurrence_series_id, occurrence_date)` es la defensa final contra duplicados. La generación bloquea la fila de la serie y es segura ante reintentos. Las bitácoras no recurrentes conservan `NULL` en ambos campos y permanecen compatibles.

Los participantes se validan contra `EventStaff` al configurar la serie y nuevamente al generar. Quienes ya no estén activos no reciben una asignación nueva. Si no queda ningún participante válido se registra una excepción `NO_VALID_PARTICIPANTS`, evitando regeneraciones inseguras.

Omitir una fecha persiste una excepción. Reprogramar conserva la fecha original y marca la ocurrencia como modificada. Las ejecuciones con respuestas, evidencias, inicio, envío o revisión no se reescriben. Los cambios de supervisor o participantes se aplican solamente a ocurrencias futuras sin actividad.

## Seguridad y permisos

El backend es la fuente de verdad. `SCHEDULED`, `UNDER_REVIEW`, `COMPLETED`, `CANCELLED` y `OVERDUE` son sólo lectura. `OPEN` e `IN_PROGRESS` permiten edición al participante asignado. `CHANGES_REQUESTED` permite corregir exclusivamente a la asignación correspondiente. Esta política cubre guardar/limpiar respuestas, cargar/eliminar fotografías y enviar.

ADMIN y SUPER_ADMIN gestionan series. SUPERVISOR sólo puede hacerlo si pertenece al evento conforme a la política existente. WORKER sólo accede a sus ejecuciones; CLIENT no recibe configuración interna de series ni evidencias no autorizadas. RLS replica el aislamiento administrativo y de supervisor por `event_staff`.

Las auditorías registran actor, evento, serie, acción y fechas mínimas. Nunca incluyen tokens, URLs firmadas ni `storage_key`.

## API

- `POST /logbook-recurrences/preview`: calcula fechas sin persistir.
- `POST/GET /events/{event_id}/logbook-recurrences`: crea o lista series.
- `GET/PATCH /logbook-recurrences/{series_id}`: detalle o cambios futuros.
- `POST /logbook-recurrences/{series_id}/pause|resume|finish`: ciclo de serie.
- `GET /logbook-recurrences/{series_id}/occurrences`: historial y próximas ejecuciones.
- `POST /logbook-recurrences/{series_id}/skip`: omite y persiste la excepción.
- `POST /logbook-recurrences/{series_id}/reschedule`: reprograma sin perder trazabilidad.
- `POST /logbook-recurrences/{series_id}/generate`: completa idempotentemente la ventana, protegido por permisos de gestión.

Ejemplo abreviado de creación:

```json
{
  "template_version_id": "00000000-0000-0000-0000-000000000000",
  "assignment_mode": "SHARED",
  "participant_ids": ["00000000-0000-0000-0000-000000000001"],
  "frequency": "WEEKLY",
  "interval": 1,
  "weekdays": [1],
  "start_date": "2026-08-04",
  "end_mode": "END_DATE",
  "end_date": "2026-11-04",
  "opens_at_local": "09:00:00",
  "due_at_local": "18:00:00",
  "timezone": "America/Santiago",
  "client_visibility": false
}
```

## Operación sin cron y despliegue posterior

La generación anticipada permite usar series acotadas sin cron. La actualización lazy del detalle aplica `SCHEDULED → OPEN → OVERDUE` al primer acceso reutilizando el servicio central. Para transiciones estrictamente puntuales y notificaciones futuras se recomienda un único Job general.

Checklist posterior, fuera de esta tarea:

1. Respaldar y probar la base de destino.
2. Aplicar `alembic upgrade head` con la revisión `20260802_0038`.
3. Desplegar backend y frontend compatibles.
4. Ejecutar una vista previa y una serie acotada de prueba.
5. Cuando corresponda, conectar el Job general existente; no crear un cron exclusivo.

Esta implementación no ejecuta migraciones ni despliegues de producción.
