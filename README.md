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

## Guia de pruebas

Para validar manualmente todo lo implementado en el frontend por rol y por modulo:

- [Guia de pruebas frontend](docs/GUIA_PRUEBAS_FRONTEND.md)
