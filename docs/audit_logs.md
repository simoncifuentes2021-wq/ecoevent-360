# Auditoria de EcoEvent 360

Este modulo registra trazabilidad operativa y administrativa sin bloquear el flujo principal: si falla la escritura de auditoria, el endpoint original continua respondiendo.

## Base de datos

La migracion `20260601_0002_add_audit_logs.py` solo agrega:

- Tabla `audit_logs`.
- Indices por usuario, evento, cliente, modulo, accion, entidad y fecha.

No modifica tablas, columnas, enums ni migraciones antiguas.

La migracion `20260601_0003_add_context_fields_to_audit_logs.py` agrega contexto opcional:

- `task_id`
- `incident_id`
- `zone_id`
- `description`

Estos campos son nullable para conservar compatibilidad con registros anteriores.

Campos clave:

- `user_id`, `event_id`, `client_id`: UUID nullable con `ON DELETE SET NULL`.
- `old_data`, `new_data`, `metadata`: JSONB.
- `action`, `module`, `entity_type`, `entity_id`, `status`: contexto de la accion.
- `task_id`, `incident_id`, `zone_id`: contexto operativo directo cuando aplica.
- `description`: descripcion humana del movimiento.
- `ip_address`, `user_agent`, `request_method`, `request_path`: contexto HTTP.

## Seguridad

Antes de guardar JSON se aplica `sanitize_audit_data`, que elimina o redacta claves sensibles como:

- password
- password_hash
- token
- access_token
- refresh_token
- secret
- authorization

No se deben guardar contrasenas, tokens ni cabeceras de autorizacion en auditoria.

## Endpoints

Solo `SUPER_ADMIN` y `ADMIN` pueden consultar auditoria global:

```http
GET /api/v1/audit-logs
GET /api/v1/audit-logs/export
```

Filtros soportados:

- `user_id`
- `event_id`
- `client_id`
- `module`
- `action`
- `status`
- `task_id`
- `incident_id`
- `zone_id`
- `entity_type`
- `entity_id`
- `from_date`
- `to_date`
- `q`
- `page`
- `limit`

Auditoria por evento:

```http
GET /api/v1/events/{event_id}/audit-logs
```

Permisos:

- `SUPER_ADMIN` y `ADMIN`: pueden ver cualquier evento.
- `SUPERVISOR`: solo eventos asignados.
- `CLIENT` y `WORKER`: sin acceso.

## Frontend

Pantallas implementadas:

- `/admin/auditoria`: filtros, KPIs, tabla, paginacion, detalle y export CSV.
- Tab `Auditoria` en detalle de evento admin.

La UI incluye estados de carga, error y vacio.

## Integracion en servicios

Usar `create_audit_log` desde los servicios o routers donde ocurra una accion relevante:

```python
create_audit_log(
    db,
    user=current_user,
    action="UPDATE",
    module="tasks",
    entity_type="task",
    entity_id=task.id,
    event_id=task.event_id,
    task_id=task.id,
    zone_id=task.zone_id,
    old_data=old_data,
    new_data=new_data,
    request=request,
)
```

La funcion es reutilizable y tolerante a fallos.

Si no se envia `description`, el servicio intenta construirla con `build_audit_description`.
Tambien intenta completar automaticamente `event_id`, `client_id`, `task_id`, `incident_id`
y `zone_id` cuando puede deducirlos desde la entidad auditada.
