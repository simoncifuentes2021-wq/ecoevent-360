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
```
