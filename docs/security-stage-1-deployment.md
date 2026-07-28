# Etapa 1: despliegue seguro

Alembic es la única fuente de verdad. `base_datos/ecoevent_360_schema.sql` es un snapshot histórico y no debe ejecutarse antes de `alembic upgrade head`, ni combinarse con `stamp head` sin verificar cada objeto.

## Inventario de archivos

- Privados: evidencias operativas, incidencias, residuos, pedidos, logística, compras y bitácoras (`private/...`).
- Importación administrativa: CSV de encuestas (`private/surveys/...`).
- Públicos/regenerables: QR de formularios y Bike Zone; apuntan al flujo web público, nunca a evidencias.
- Legacy: URLs absolutas y rutas `uploads/...`; son legibles por compatibilidad, pero las nuevas cargas guardan claves.
- Pendientes: PDF históricos de reportes; solo se entregan a través del endpoint autenticado de reportes.

## Orden de despliegue

1. Crear respaldo verificable y registrar `select version_num from alembic_version;` y `alembic heads` (debe haber un head).
2. Ejecutar `scripts/diagnose_rls.sql` con el rol actual y guardar el resultado sin URL de conexión.
3. En R2 desactivar Public Development URL y cualquier dominio público del bucket. Comprobar con `curl -I https://<url-anterior>/<objeto>`: se espera 401/403/404.
4. Crear una API token limitada al bucket (Object Read/Write), configurar endpoint, bucket, access key y secret en Render.
5. Aprovisionar Redis/Upstash con TLS y definir `REDIS_URL`; producción no inicia sin backend distribuido.
6. Crear el rol runtime con `scripts/configure_runtime_role.sql`. Confirmar `rolsuper=false`, `rolbypassrls=false` y que no es dueño de tablas.
7. En Render usar `DATABASE_URL` para runtime limitado y `MIGRATION_DATABASE_URL` para el propietario/migrador. Ambos son secretos.
8. Antes de migrar: `python -m app.commands.audit_legacy_files` (dry-run), `alembic current`, `alembic upgrade head` usando exclusivamente la URL migradora.
9. Desplegar backend, verificar `/health`, login normal, 429 controlado, descarga autorizada y rechazo entre clientes.
10. Desplegar frontend y ejecutar smoke test de formularios, Bike Zone, logística y bitácoras.

## Base histórica y divergencias

No aplicar migraciones si falta `alembic_version`. Comparar primero tablas/columnas con `information_schema`, políticas con `pg_policies` y el snapshot. Solo después de identificar la revisión exacta se permite `alembic stamp <revision-específica>`; nunca `head`. Para una base vacía: crear DB aislada, ejecutar `alembic upgrade head`, `alembic current`, `alembic heads` y `scripts/ci/verify_alembic_head.py`.

## Archivos legacy

`python -m app.commands.audit_legacy_files` solo cuenta y entrega hashes de referencias ambiguas. Tras respaldo y revisión, `--apply` convierte únicamente referencias inequívocas; no mueve ni borra objetos. Después de validar descargas privadas, retirar el acceso público anterior en Cloudflare. Mantener el rollback de aplicación mientras existan referencias legacy.

## Proxy y secretos

`TRUSTED_PROXY_COUNT` debe ser el número exacto de proxies controlados entre Render y la app; `0` ignora `X-Forwarded-For`. No registrar JWT, contraseñas, claves, URLs firmadas ni datos de respuestas. La URL firmada expira en 300 segundos por defecto.

## Rollback operacional

Detener tráfico/escalar a cero, restaurar la versión previa de la aplicación y conservar objetos R2. No hacer downgrade de `20260727_0037` si ya hay idempotency keys que deban auditarse. Si la migración falla, restaurar el respaldo en una base nueva y cambiar las URLs de Render; no sobrescribir la base fallida. Repetir diagnóstico RLS y smoke tests antes de reabrir tráfico.

Acciones externas pendientes de comprobación: privacidad real del bucket, roles de Supabase, variables de Render y pruebas contra producción. Este repositorio no modifica ninguno de esos servicios.
