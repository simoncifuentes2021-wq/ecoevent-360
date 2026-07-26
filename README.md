# EcoEvent 360

Plataforma web para empresas que gestionan servicios ambientales y sanitarios en eventos masivos.

## Estructura

- `backend/`: API REST con FastAPI, SQLAlchemy, Alembic, PostgreSQL y JWT.
- `frontend/`: aplicacion Next.js con TypeScript, Tailwind CSS, Shadcn-style UI, Recharts, Framer Motion y Lucide React.
- `docs/`: notas de arquitectura y decisiones tecnicas.

## Arranque local

Backend:

```bash
cd backend
cp .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app
```

Alembic:

La base local actual se crea desde `base_datos/ecoevent_360_schema.sql`.
La revision `20260528_0001` es un baseline vacio para registrar ese esquema
existente sin recrear tablas.

```bash
cd backend
alembic history
alembic current
# Solo cuando la base ya exista desde el SQL y quieras marcarla:
alembic stamp head
```

Base de datos Docker:

```bash
docker compose up -d postgres
```

Conexion local: `postgresql://ecoevent:ecoevent_password@localhost:5434/ecoevent360`

Healthchecks:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/health
```

Frontend:

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

## Deploy

La guia completa para Render, Vercel, Supabase/Neon y Cloudflare R2 esta en
`README_DEPLOY.md`.

## Guia de pruebas

Para validar manualmente todo lo implementado en el frontend por rol y por modulo:

- [Guia de pruebas frontend](docs/GUIA_PRUEBAS_FRONTEND.md)

### Verificacion automatizada y CI

Runtimes de referencia: Python 3.11, Node.js 20.19 y PostgreSQL 16. El backend se
instala desde `backend/pyproject.toml` y el frontend de forma reproducible con
`npm ci` y `frontend/package-lock.json`.

```bash
cd backend && python -m venv .venv && . .venv/bin/activate
python -m pip install -e ".[dev]"
cd ../frontend && npm ci
```

Desde cualquier directorio se pueden ejecutar los scripts mediante su ruta
absoluta o desde la raiz del repositorio:

```bash
scripts/ci/backend.sh quick       # Ruff, FastAPI, OpenAPI y mappers
scripts/ci/backend.sh unit        # reglas unitarias de Bitacoras
scripts/ci/backend.sh integration # integracion de Bitacoras con PostgreSQL
scripts/ci/frontend.sh quick      # TypeScript, ESLint y pruebas de Bitacoras
scripts/ci/frontend.sh logbooks   # solo pruebas frontend de Bitacoras
scripts/verify-logbooks.sh        # certificacion completa de Bitacoras
scripts/verify-all.sh             # verificacion completa aplicable a CI
```

Los scripts Bash requieren Linux, macOS, WSL o Git Bash. `PYTHON_BIN` permite
indicar otro ejecutable de Python. Para integracion, `DATABASE_URL` debe apuntar
exclusivamente a PostgreSQL local o al servicio `postgres` de CI. Una base vacia
se prepara así:

```bash
export DATABASE_URL=postgresql+psycopg://ecoevent_ci:ci_password@127.0.0.1:5432/ecoevent_ci
export CI_DATABASE_CONFIRM=ecoevent-test-only
scripts/ci/bootstrap-test-database.sh
scripts/ci/backend.sh integration
```

El bootstrap recupera el esquema inmutable correspondiente a la revision
baseline desde `0bcc03b:base_datos/ecoevent_360_schema.sql`, verifica su SHA-256,
marca `20260528_0001` y deja que Alembic aplique todo cambio posterior en orden
en transacciones separadas antes de comprobar `head`. Las transacciones por
revision son necesarias porque `0011` agrega un valor enum que revisiones
posteriores utilizan y PostgreSQL exige un commit intermedio. El checkout de CI
usa historial completo para poder leer el baseline. Nunca debe apuntarse este
comando a desarrollo o produccion.
El almacenamiento R2, correo, Supabase, Vercel y Render no se usan en CI; los
archivos de prueba utilizan almacenamiento local temporal.

GitHub Actions ejecuta cuatro checks independientes en pull requests y mediante
ejecucion manual: backend estatico/unitario, PostgreSQL real, calidad frontend y
build. Un fallo detiene su job. Errores de conexion aparecen en el health check;
errores de esquema en la carga baseline o Alembic; y errores frontend en el paso
especifico de TypeScript, ESLint, pruebas o build.

## Auditoria

La trazabilidad administrativa y operativa se documenta en:

- [Auditoria de EcoEvent 360](docs/audit_logs.md)
