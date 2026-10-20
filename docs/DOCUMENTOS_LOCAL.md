# Módulo Documentos (solo local)

El módulo vive en `Documentos` para administradores y supervisores. Personas no crea usuarios EcoEvent. Una ficha puede tener asignaciones laborales globales (`event_id` nulo) o de evento; ambos contextos muestran el mismo documento, sin duplicarlo.

## Seguridad y alcance de esta V1

- Las tablas nuevas tienen políticas RLS por cliente y evento; una URL pública solo habilita una solicitud concreta cuyo token aleatorio se almacena como SHA-256. El token se envía al API en el cuerpo HTTP; el navegador lo extrae del fragmento de URL y lo retira de la barra.
- El trabajador valida su RUT antes de ver el contenido. El endpoint no incluye token, RUT, salario ni datos privados en logs/auditoría. La firma de trabajador requiere confirmar el nombre y revisar el PDF.
- La firma `LOCAL_SIMULATED` es una simulación técnica, no una firma electrónica ni tiene validez legal. El PDF contractual es una maqueta de flujo con aviso visible; requiere incorporar y revisar el texto aprobado por asesoría laboral antes de un uso real.
- Los PDFs se generan en preview bajo demanda y se guardan inmutables solo al enviar/finalizar. En local pueden guardarse bajo `LOCAL_PRIVATE_STORAGE_ROOT/documents/<uuid>/`; con `DOCUMENTS_USE_R2_STORAGE=true` usan el bucket privado R2. En producción, todos los archivos y evidencias pasan por R2 y el backend exige que esté configurado.
- El limitador del portal público vive en memoria de este proceso y no usa el Redis configurado en el `.env`. Es apropiado para la demostración local; no sirve como limitador distribuido multi-instancia.
- Supervisores administran exclusivamente documentos de eventos a los que tienen acceso. Admin/Super Admin gestionan la colección global y pueden filtrar por cliente/evento.

## Variables locales

Para una prueba local aislada, en `backend/.env` usa `APP_ENV=local` y `FORCE_LOCAL_STORAGE=true`. Los archivos generales quedan en disco local; `DOCUMENTS_USE_R2_STORAGE` controla por separado los PDFs del módulo Documentos. No uses credenciales de producción si no quieres que las pruebas escriban en el bucket real.

```dotenv
DOCUMENTS_PUBLIC_BASE_URL=http://localhost:3001
LOCAL_PRIVATE_STORAGE_ROOT=uploads/private
```

`backend/.env.example` incluye la URL pública local. La firma manuscrita y sus datos de auditoría forman parte del registro del documento; el PDF final se conserva en el almacenamiento configurado.

## Base local y migración

La migración `20261006_0077` es aditiva y crea seis tablas nuevas. En este checkout, `MIGRATION_DATABASE_URL` del `.env` apunta a un host remoto mientras `DATABASE_URL` es local; no ejecutes Alembic sin sobreescribir explícitamente la URL de migración por una URL PostgreSQL local verificada. La aplicación no necesita Docker ni servicios nuevos, pero sí una instancia PostgreSQL local con la base ya inicializada.

En PowerShell, desde `backend`, configura las variables de proceso con las credenciales de TU instancia local (no las de Supabase) y valida host/base antes de ejecutar:

```powershell
$env:APP_ENV = "local"
$env:MIGRATION_DATABASE_URL = "postgresql+psycopg://USUARIO_LOCAL:CLAVE_LOCAL@127.0.0.1:5434/ecoevent360"
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Si tu instancia local usa otro puerto/base, reemplázalos después de comprobarlos. No ejecutes `alembic downgrade` salvo que quieras borrar los datos creados en estas seis tablas locales: el downgrade elimina las tablas nuevas de Documentos.

## Levantar la app

En una terminal, desde `backend`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8001
```

En otra terminal, desde `frontend`:

```powershell
npm run dev -- --port 3001
```

La pantalla es `http://localhost:3001/admin/documentos` (supervisor: `/supervisor/documentos`). El portal externo local es `http://localhost:3001/public/documents` y normalmente se abre usando el enlace generado con QR.

## Flujos manuales

1. Inicia sesión como Admin; elige cliente y usa **Nueva persona**, o descarga la plantilla `.xlsx`, complétala, pulsa **Analizar archivo** y confirma solo si no hay errores. Los duplicados existentes por RUT se actualizan y se crea una nueva asignación; el Excel nunca se conserva.
2. En Documentos, crea **Contrato por obra o faena** o **EPP / Seguridad**. El evento es opcional. El borrador se edita en PostgreSQL; **Ver** compone un PDF temporal.
3. Pulsa **Enviar**, confirma que los datos se congelarán y copia el enlace/QR. No se envía correo. Abre el enlace en una ventana privada, ingresa el RUT, revisa el PDF y confirma el flujo simulado.
4. Vuelve al panel autenticado y usa **Completar firma** como supervisor autorizado/admin. Descarga el original y el PDF final; sus rutas usan UUID, nunca RUT/nombre.
5. En EPP, registra fecha, RIOHS/EIRL y recepción/devolución por elemento. Las fechas y conformidad quedan estructuradas; al enviar, la misma versión se congela.
6. Para cambiar un documento ya enviado o completado, crea una **Nueva versión**. El original firmado permanece intacto; el enlace anterior se revoca.

## Pruebas

En `frontend`: `npm run typecheck` y `npm run test:documents`. En `backend`: `ruff check ...` y `pytest tests/test_documents_domain.py`. El `conftest.py` exige `CI_DATABASE_CONFIRM=ecoevent-test-only` y URLs de una base desechable localhost cuyo nombre incluya `test`, `ci`, `disposable` o `certification`; no apuntes esas pruebas al `.env` real ni a una base con datos.

La integración contra PostgreSQL (RLS, migración y workflows API) solo debe correrse cuando exista una base local desechable, luego de verificar `DATABASE_URL` y `MIGRATION_DATABASE_URL` independientemente. No pruebes esta migración con Supabase.
