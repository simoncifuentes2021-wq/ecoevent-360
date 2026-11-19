# Voluntarios y Activaciones

## Alcance

El módulo administra activaciones de reciclaje dentro de un evento, una ficha única por correo normalizado, participaciones por activación y entregas con varias líneas de material. Las métricas se calculan desde entregas activas; las anuladas quedan en historial y auditoría, fuera de los totales.

## Datos y rutas

- `volunteers`: identidad, consentimiento y código operativo único.
- `recycling_activations`: punto, horario, capacidad, evento y enlace público.
- `volunteer_activations`: relación de la misma persona con varias activaciones.
- `waste_types`: catálogo único compartido con Residuos; los aportes de voluntariado usan sus mismos identificadores y conservan una copia histórica del nombre y la unidad.
- `material_contributions` y `material_contribution_items`: entregas y pesos decimales con nombre/unidad históricos.
- `volunteer_access_tokens`: solo almacena hash de tokens privados y su vencimiento.
- `evidences.volunteer_contribution_id`: conecta fotos con el almacenamiento de evidencias existente.

La API se registra bajo `/api/v1`. La interfaz está disponible para administración, supervisión, trabajador y operador logístico, respetando la autorización de eventos existente. Las páginas públicas nuevas son `/public/inscripcion-voluntarios/{slug}` y `/public/mi-aporte/{token}`. No se cambian enlaces ni slugs de Formularios, Bike Zone, Huella u otros módulos.

## Flujos

1. Administración crea una activación en un evento, la publica al cambiar a Activa y comparte su QR/enlace.
2. La inscripción pública exige consentimiento operacional. El permiso promocional es separado y opcional. El correo normalizado evita crear una segunda ficha cuando la persona vuelve a inscribirse.
3. El encargado busca por email, teléfono o código, selecciona uno o más tipos desde el mismo catálogo de Residuos, ingresa kg, adjunta opcionalmente una foto y guarda. La API valida pesos, deduplica el envío con idempotencia y calcula los totales con `Decimal`.
4. Tras confirmar la entrega, se intenta enviar el correo con Resend ya configurado por el proyecto. Un fallo de correo no revierte el aporte y se conserva el estado de entrega de correo.
5. El historial público usa un token aleatorio enviado al correo; en la base solo queda su hash. El token vence al año. El enlace permite consultar el impacto acumulado y las entregas sin exponer email, teléfono ni identificadores internos.
6. Una corrección o anulación requiere permisos, deja registro de auditoría y los aportes anulados no entran a los gráficos ni totales.

## Permisos y datos ambientales

Las operaciones se limitan a eventos a los que la persona usuaria tiene acceso. El catálogo lo administra ADMIN/SUPER_ADMIN. Las páginas públicas solo leen activaciones activas por slug o el impacto asociado a un token válido. RLS recibe capacidades acotadas para esos flujos.

Los kg de voluntariado se reportan en su dashboard propio y no se insertan automáticamente como registros de residuos ni como reducción de huella. El catálogo sí es compartido; los movimientos y métricas siguen separados para evitar duplicar impactos.

## Evidencias, correo y trazabilidad

Las fotos usan `save_evidence_file` / `read_stored_file` y el proveedor configurado por el servicio de evidencias (R2 cuando está configurado). La base guarda metadatos y vínculo con la entrega, no los bytes. Las operaciones administrativas registran auditoría.

El envío de correo de la entrega se ejecuta mediante `BackgroundTasks` de FastAPI: el aporte se confirma antes del correo y se registra `PENDING`, `SENT`, `FAILED` o `SKIPPED`. No es una cola durable: si el proceso termina justo después de guardar y antes de intentar enviar, el estado puede quedar pendiente. Para campañas de alto volumen o garantía de reintentos se debe migrar a la cola durable compartida por el proyecto si existe, o agregar Outbox/worker como etapa separada.

## Migración y validación

Las migraciones `20261110_0088` y `20261110_0089` son reversibles. En desarrollo/local, Alembic siempre usa `DATABASE_URL`; solo en producción puede usar `MIGRATION_DATABASE_URL`. Validar sobre una base desechable local y nunca contra Supabase durante revisión. El módulo no escribe en registros de stock, residuos ni huella existentes.
