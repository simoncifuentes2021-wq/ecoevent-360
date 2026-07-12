# EcoEvent 360: guia de deploy

Esta guia prepara el despliegue completo con frontend en Vercel, backend en Render,
PostgreSQL en Supabase o Neon y archivos en Cloudflare R2.

## 1. Base de datos PostgreSQL

1. Crea un proyecto en Supabase o Neon.
2. Copia la URL de conexion PostgreSQL.
3. Usa el driver `psycopg` en la URL si es necesario:

```bash
postgresql+psycopg://USER:PASSWORD@HOST:PORT/DATABASE
```

## 2. Backend en Render

Configura un nuevo Web Service:

- Root directory: `backend`
- Runtime: Docker
- Healthcheck path: `/api/v1/health`
- Entrypoint de la app: `app.main:app`
- Comando de produccion: definido en `backend/Dockerfile` con `gunicorn` y worker `uvicorn`

Variables de entorno requeridas:

```bash
DATABASE_URL=
SECRET_KEY=
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
BACKEND_CORS_ORIGINS=https://app.ecoevent360.cl,https://ecoevent-360.vercel.app
CLOUDFLARE_R2_BUCKET=
CLOUDFLARE_R2_ACCOUNT_ID=
CLOUDFLARE_R2_ACCESS_KEY_ID=
CLOUDFLARE_R2_SECRET_ACCESS_KEY=
CLOUDFLARE_R2_PUBLIC_BASE_URL=
MAX_UPLOAD_SIZE_MB=10
SEED_ADMIN_EMAIL=
SEED_ADMIN_PASSWORD=
SEED_ADMIN_NAME=
ENVIRONMENT=production
```

Despues de crear el servicio, ejecuta las migraciones desde Render Shell:

```bash
alembic upgrade head
```

La migracion `20260610_0005` activa Row Level Security en las tablas de negocio.
Para que PostgreSQL aplique RLS en produccion, la `DATABASE_URL` del backend debe
usar un rol de aplicacion que no sea propietario de las tablas ni tenga
`BYPASSRLS`. El rol propietario/admin se debe reservar para migraciones.

Crea el usuario inicial SUPER_ADMIN:

```bash
python -m app.seed_admin
```

El seed no duplica usuarios: si `SEED_ADMIN_EMAIL` ya existe, no crea otro registro.

## 3. Frontend en Vercel

Configura un nuevo proyecto:

- Root directory: `frontend`
- Framework: Next.js
- Build command: `npm run build`
- Variable:

```bash
NEXT_PUBLIC_API_URL=https://URL_BACKEND/api/v1
```

Cuando Vercel entregue la URL final, actualiza `BACKEND_CORS_ORIGINS` en Render con
el dominio de Vercel y cualquier dominio propio.

## 4. Cloudflare R2

1. Crea un bucket en Cloudflare R2.
2. Crea credenciales S3 compatibles para el backend.
3. Configura un dominio publico o URL publica para servir archivos.
4. Define en Render:

```bash
CLOUDFLARE_R2_BUCKET=
CLOUDFLARE_R2_ACCOUNT_ID=
CLOUDFLARE_R2_ACCESS_KEY_ID=
CLOUDFLARE_R2_SECRET_ACCESS_KEY=
CLOUDFLARE_R2_PUBLIC_BASE_URL=
```

El backend usa almacenamiento local en desarrollo y lo sirve desde `/uploads`.
En produccion usa R2 cuando todas las variables R2 estan configuradas. Las claves
privadas no se exponen al frontend.

Rutas de almacenamiento usadas:

- `evidences/`: fotos y PDF subidos como evidencias operativas.
- `qrcodes/`: PNG generados para formularios publicos.
- `surveys/`: CSV importados desde Google Forms/Sheets.

Tipos permitidos:

- `image/jpeg`
- `image/png`
- `application/pdf`
- `text/csv`

## 5. Dominio propio con Cloudflare DNS

1. Agrega el dominio a Cloudflare.
2. Apunta el frontend a Vercel siguiendo los registros que indique Vercel.
3. Apunta el backend a Render si usaras subdominio propio para la API.
4. Actualiza:

```bash
NEXT_PUBLIC_API_URL=https://api.tudominio.cl/api/v1
BACKEND_CORS_ORIGINS=https://app.tudominio.cl,https://ecoevent-360.vercel.app
```

## 6. Checklist final

- `GET /api/v1/health` responde `{"status":"ok"}`.
- `alembic upgrade head` termina sin errores.
- `python -m app.seed_admin` crea o detecta el SUPER_ADMIN.
- El frontend compila con `npm run build`.
- El login funciona con el usuario seed.
- CORS contiene solo dominios reales, sin `*` en produccion.
- `SECRET_KEY` es largo, aleatorio y distinto al ejemplo.
- `DATABASE_URL` apunta a Supabase o Neon.
- Las evidencias y CSV de encuestas suben a R2 en produccion.
- No hay archivos `.env` versionados.
