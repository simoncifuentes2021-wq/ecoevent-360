# Acta final de certificación: Bitácoras de tareas

Fecha: 2026-07-23
Alcance: base PostgreSQL existente en revisión `20260722_0035`; sin despliegue,
downgrade ni modificación de migraciones históricas, `0034` o `0035`.

## Resultado

El módulo queda aprobado funcionalmente para la base existente. No queda
certificado el aprovisionamiento de una instalación limpia: la cadena Alembic
legacy carece de un bootstrap ejecutable.

## Defectos demostrados y corregidos

1. El envío contaba evidencias desde una relación ORM posiblemente obsoleta y
   podía responder “Evidence required” después de una carga válida. Ahora
   consulta el conteo vigente en PostgreSQL.
2. En modalidad SHARED la revisión del supervisor sólo actualizaba una
   asignación. Ahora aprobación o solicitud de cambios sincroniza estado,
   actor, comentario y fechas en todas las asignaciones de la instancia.

No se añadieron funciones visuales durante esta fase.

## Matriz certificada

| Área | Resultado |
|---|---|
| ADMIN / SUPER_ADMIN | APROBADO |
| Supervisor asignado / no asignado | APROBADO |
| EventStaff asignado / trabajador ajeno | APROBADO |
| Operador logístico expresamente asignado / usuario ajeno | APROBADO |
| CLIENT propietario / CLIENT de otra organización | APROBADO |
| Usuario inactivo como participante | Rechazado, APROBADO |
| Acceso por UUID y evento ajeno | Rechazado, APROBADO |
| Plantillas, borrador, publicación, clon, orden, posiciones y archivo histórico | APROBADO |
| Ejecución INDIVIDUAL, tipos, N/A, fallo, revisión e intentos | APROBADO |
| Ejecución SHARED, colaboración, autoría y conflicto optimista | APROBADO |
| JPEG/PNG/WebP, MIME falso, corrupto, tamaño, máximo y borrado lógico | APROBADO |
| Tokens temporales, vencido, cruzado y acceso de otro trabajador | APROBADO |
| Incidencia/tarea correctiva, evidencia seleccionada y duplicados | APROBADO |
| Resumen CLIENT, métricas y ausencia de datos internos | APROBADO |
| Auditoría, actor, transición y metadata sin secretos | APROBADO |

La captura de cámara real y la interacción simultánea de dos navegadores se
dejan en la guía manual; su lógica de backend está cubierta en PostgreSQL.

## Comandos y resultados

- Matriz PostgreSQL nueva:
  `pytest tests/test_logbook_certification.py -q` → **4 passed**, 0 failed,
  40 warnings, 208.10 s.
- Caso INDIVIDUAL reforzado después de separar MIME/tamaño:
  **1 passed**, 0 failed, 19 warnings, 101.21 s.
- Unitarias Bitácoras: **11 passed**, 0 failed, 1 warning, 1.98 s.
- QR: **10 passed, 1 skipped**, 0 failed; la omisión corresponde a `cv2` no
  instalado.
- Suite backend completa: **43 passed, 1 skipped**, 0 failed, 88 warnings,
  656.22 s.
- FastAPI/OpenAPI/mappers/rutas: importación OK, **182 paths**, **272
  operaciones**, **0 duplicadas**, `configure_mappers()` OK.
- Ruff del módulo y pruebas de certificación: **All checks passed**.
- `alembic heads`: `20260722_0035 (head)`.
- `alembic current`: `20260722_0035 (head)` sobre PostgreSQL.
- `git diff --check`: código 0; sólo avisos informativos LF/CRLF.
- Frontend `npm run typecheck`: código 0.
- Frontend `npm run lint`: código 0, con advertencias no bloqueantes existentes
  sobre hooks e imágenes.
- Frontend `npm run build`: código 0, compilación y generación de **77 páginas**.
- Rutas compiladas: admin plantilla/ejecución, supervisor detalle y trabajador
  lista/detalle presentes.
- API frontend: endpoints relativos bajo el `baseURL`; no existe el prefijo
  duplicado `/api/v1/api/v1`; cámara móvil usa `capture="environment"`.

El primer build encontró un `next dev` del mismo repositorio reteniendo
`.next/trace`; se cerraron únicamente esos procesos, se eliminó el artefacto
regenerable y el build volvió a fallar dentro del sandbox al crear workers.
Ejecutado con permiso fuera del sandbox, compiló correctamente. No fue necesario
modificar código para resolverlo.

## Archivos de esta fase

- `backend/app/services/logbook_service.py`
- `backend/tests/test_logbook_certification.py`
- `docs/logbook-shared-manual-certification.md`
- `docs/alembic-bootstrap-diagnosis.md`
- `docs/logbook-final-certification.md`

El resto de archivos del módulo que aparece en el árbol de trabajo corresponde
a la implementación conservada y certificada, incluida la carga de evidencias,
las rutas y pantallas por rol.

## Pendientes y bloqueos

- **BLOQUEADO:** instalación limpia hasta implementar y probar el bootstrap
  oficial propuesto.
- **PENDIENTE manual:** recorrido visual en dos navegadores y captura con cámara
  sobre un teléfono físico.
- **PENDIENTE no bloqueante:** migrar usos de `datetime.utcnow()` y atender las
  advertencias ESLint existentes en una tarea separada.
