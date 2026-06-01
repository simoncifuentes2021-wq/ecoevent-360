from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import routers
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "API REST para gestionar clientes, eventos, servicios ambientales, tareas, "
        "incidencias, evidencias, residuos, huella de carbono, encuestas y reportes."
    ),
    openapi_tags=[
        {"name": "auth", "description": "JWT, usuarios y sesion."},
        {"name": "clients", "description": "Gestion de clientes empresa."},
        {"name": "events", "description": "Eventos masivos y su estado operacional."},
        {"name": "services", "description": "Catalogo de servicios ambientales y sanitarios."},
        {"name": "event services", "description": "Servicios contratados por evento."},
        {"name": "event zones", "description": "Zonas fisicas o funcionales dentro del evento."},
        {"name": "tasks", "description": "Tareas operativas del equipo en terreno."},
        {"name": "incidents", "description": "Incidencias operativas y sanitarias."},
        {"name": "evidences", "description": "Evidencias fotograficas por evento o incidencia."},
        {"name": "waste", "description": "Registros de residuos y destino."},
        {"name": "carbon factors", "description": "Factores para calculo de CO2e."},
        {"name": "carbon records", "description": "Registros de huella de carbono."},
        {"name": "surveys", "description": "Importacion CSV desde Google Forms/Sheets."},
        {"name": "dashboard", "description": "Indicadores resumidos por evento."},
        {"name": "reports", "description": "Generacion de reportes PDF para clientes."},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.backend_cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in routers:
    app.include_router(router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
