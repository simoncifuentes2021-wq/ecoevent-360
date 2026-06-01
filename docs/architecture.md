# Arquitectura Inicial

EcoEvent 360 usa un monorepo con dos aplicaciones desacopladas:

- Backend FastAPI con modulos por dominio, servicios de negocio y modelos SQLAlchemy.
- Frontend Next.js con App Router, componentes reutilizables y paginas por rol.

## Dominios iniciales

1. Auth y permisos por rol.
2. Clientes.
3. Eventos.
4. Catalogo de servicios.
5. Servicios contratados.
6. Zonas.
7. Tareas.
8. Incidencias.
9. Evidencias fotograficas.
10. Residuos.
11. Factores de emision.
12. Huella de carbono.
13. Encuestas externas y CSV.
14. Dashboard.
15. Reportes PDF.

## Flujo de datos

El frontend consume la API usando `NEXT_PUBLIC_API_URL`. La API valida JWT, aplica permisos por rol y persiste datos en PostgreSQL. Las evidencias quedan modeladas para URL externa, preparando integracion futura con Cloudflare R2.

