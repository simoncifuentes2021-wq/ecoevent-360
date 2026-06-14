# EcoEvent 360 API

Backend FastAPI con SQLAlchemy, Alembic, PostgreSQL y JWT.

## Local

```bash
cp .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Healthcheck:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

## Produccion

Render debe ejecutar el Dockerfile desde `backend`.

El contenedor inicia con:

```bash
gunicorn app.main:app --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

Migraciones:

```bash
alembic upgrade head
```

En produccion, no ejecutes migraciones automaticamente con el rol de la app si
ese rol no es propietario de las tablas. Render solo corre migraciones al
arranque si defines:

```bash
RUN_MIGRATIONS_ON_STARTUP=true
```

El flujo recomendado es dejar esa variable ausente o en `false` en Render y
ejecutar `alembic upgrade head` desde local usando la `DATABASE_URL` admin.

La migracion de Row Level Security usa variables de sesion PostgreSQL seteadas
por el backend en cada request autenticada. En produccion, usa un rol de base de
datos no propietario de las tablas para la `DATABASE_URL` de la app; deja el rol
propietario/admin solo para ejecutar migraciones.

Seed SUPER_ADMIN:

```bash
python -m app.seed_admin
```

Variables requeridas:

```bash
DATABASE_URL=
SECRET_KEY=
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
BACKEND_CORS_ORIGINS=
ENVIRONMENT=production
```

Variables R2:

```bash
CLOUDFLARE_R2_BUCKET=
CLOUDFLARE_R2_ACCOUNT_ID=
CLOUDFLARE_R2_ACCESS_KEY_ID=
CLOUDFLARE_R2_SECRET_ACCESS_KEY=
CLOUDFLARE_R2_PUBLIC_BASE_URL=
MAX_UPLOAD_SIZE_MB=10
```

R2 almacena `evidences/` y `surveys/` cuando todas las variables R2 estan
configuradas. Si falta alguna, se usa `uploads/`, servido por FastAPI desde
`/uploads`.
