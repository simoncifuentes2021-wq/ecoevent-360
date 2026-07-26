# Ciclo automático de Bitácoras

Las ejecuciones pendientes siguen una máquina de estados acotada:

- `SCHEDULED → OPEN` cuando `opens_at <= now`.
- `OPEN → OVERDUE` cuando `due_at <= now`.

Una ejecución atrasada con ambas fechas cumplidas registra las dos transiciones, en orden. No se
modifican `IN_PROGRESS`, `UNDER_REVIEW`, `CHANGES_REQUESTED`, `COMPLETED`, `CANCELLED` ni las
respuestas, participantes, evidencias o correctivos. Los instantes se almacenan y comparan en UTC.
Como el dominio aún no configura una zona por evento u organización, la presentación usa el
fallback explícito `America/Santiago`, que contempla automáticamente el horario de verano.

## Ejecución

El servicio usa lotes de 1 a 500 filas, transacciones PostgreSQL y `FOR UPDATE SKIP LOCKED`. La
auditoría pertenece a la misma transacción y un índice único parcial evita repetir una transición.
Se puede ejecutar manualmente con un usuario `ADMIN` o `SUPER_ADMIN` mediante
`POST /api/v1/admin/logbooks/lifecycle/process`.

El comando independiente es:

```sh
cd backend
python -m app.commands.process_logbook_lifecycle
```

Después de aprobar y mezclar el PR, debe crearse en Render un Cron Job separado, con las mismas
variables privadas del backend, el comando anterior y una periodicidad recomendada de cinco
minutos. Esa activación no forma parte de este cambio: requiere una solicitud separada, validar la
migración `20260725_0036`, ejecutar primero una invocación manual controlada y comprobar logs y
auditoría. No debe usarse un bucle dentro del proceso web ni un cron de GitHub Actions.
