# Informe UX: diálogos de Bitácoras

Fecha: 2026-07-23
Alcance exclusivo: frontend de Bitácoras. No hubo cambios de backend,
migraciones ni otros módulos.

## Inventario de ventanas nativas

Se localizaron 15 llamadas nativas:

| Archivo | Acción anterior | Reemplazo |
|---|---|---|
| `LogbookTemplatePage.tsx` | Confirmar archivado | Diálogo que explica disponibilidad futura e historial |
| `LogbookTemplatePage.tsx` | Preguntar si publicar al crear | La plantilla queda como borrador y la publicación usa el flujo explícito del editor |
| `TemplateDetailEditor.tsx` | Confirmar publicación | Diálogo “Publicar versión de la plantilla” |
| `EventLogbooksTab.tsx` | Pedir motivo de cancelación | Formulario modal con motivo obligatorio |
| `WorkerLogbookDetail.tsx` | Confirmar eliminación de foto | Diálogo con nombre y advertencia del mínimo |
| `WorkerLogbookDetail.tsx` | Confirmar envío | Resumen de envío inicial/reenvío, intento y pendientes |
| `SupervisorLogbookDetail.tsx` | Pedir ID de participante | Selector modal con nombres |
| `SupervisorLogbookDetail.tsx` | Confirmar retiro | Diálogo contextual según existencia de respuestas |
| `SupervisorLogbookDetail.tsx` | Pedir comentario de corrección | Formulario modal obligatorio |
| `SupervisorLogbookDetail.tsx` | Preguntar evidencia por evidencia | Lista de selección dentro del formulario correctivo |
| `SupervisorLogbookDetail.tsx` | Pedir título de incidencia | Campo del formulario modal |
| `SupervisorLogbookDetail.tsx` | Pedir prioridad de incidencia | Selector del formulario modal |
| `SupervisorLogbookDetail.tsx` | Pedir responsable de tarea | Selector de personal del evento |
| `SupervisorLogbookDetail.tsx` | Pedir vencimiento de tarea | Campo de fecha/hora |
| `SupervisorLogbookDetail.tsx` | Pedir prioridad de tarea | Selector del formulario modal |

También se sustituyeron eliminaciones silenciosas de secciones e ítems, tanto
al crear como al editar una plantilla.

La búsqueda final en componentes, páginas y funciones de Bitácoras devuelve
`NATIVE_DIALOGS=0`.

## Componentes

Se reutilizaron `Button`, `ToastProvider`, estados de carga/error y el
`ModalShell` existente para el formulario principal de creación.

Se creó `LogbookDialog`, limitado a Bitácoras. Usa `<dialog>.showModal()` para
foco modal y navegación por teclado; asocia título/descripción/error, soporta
variantes normal/advertencia/peligrosa, diseño móvil, contenido desplazable,
Escape seguro y bloqueo de cierre mientras procesa.

Se creó `logbookError()` para traducir conflictos, permisos, evidencia
obligatoria, participantes inválidos, duplicados y validaciones. Filtra
mensajes que puedan contener tokens, trazas o claves de almacenamiento.

## Confirmaciones y formularios

- Publicar y archivar plantilla.
- Eliminar sección o ítem configurado.
- Abrir y cancelar ejecución; cancelar exige motivo.
- Enviar o reenviar; muestra intento, respuestas y pendientes.
- Eliminar fotografía; advierte si rompe el mínimo.
- Conflicto SHARED con acción “Recargar respuesta”.
- Agregar y retirar participantes.
- Aprobar y solicitar correcciones; comentario obligatorio.
- Crear incidencia y tarea correctiva con evidencia, prioridad, responsable y
  vencimiento cuando corresponde.

Las acciones mantienen el diálogo y los campos ante error, deshabilitan el
botón principal, verifican el estado `busy/processing` antes de invocar la API,
cierran sólo después del éxito y muestran una notificación. Cancelar sólo
limpia el estado visual y no llama a la API.

## Responsive y accesibilidad

- Ancho `calc(100% - 1.5rem)` y máximo legible.
- Alto máximo basado en `dvh` y desplazamiento vertical.
- Botones apilados en móvil, con acción segura al final del orden visual.
- Áreas principales de al menos 44 px.
- `aria-labelledby`, `aria-describedby`, `role="alert"` y `aria-invalid`
  cuando corresponde.
- Foco inicial en campos principales.
- Foco atrapado y restaurado por el elemento `<dialog>`.
- Escape cierra únicamente cuando no hay procesamiento.
- Icono y texto acompañan el color.

## Verificación

- Búsqueda nativa: **0 coincidencias**.
- TypeScript `npm run typecheck`: **código 0**.
- ESLint `npm run lint`: **código 0**; permanecen advertencias no bloqueantes
  preexistentes sobre dependencias de hooks e imágenes.
- Pruebas focalizadas:
  `pytest tests/test_logbook_rules.py tests/test_logbook_integration.py -q`:
  **12 passed**, 0 failed, 5 warnings, 36.89 s.
- Build `npm run build`: **código 0**, compilación correcta y 77 páginas
  generadas.
- `git diff --check`: **código 0**, con avisos informativos LF/CRLF.

No se ejecutó la matriz E2E completa, prueba con dos navegadores, teléfono
físico, despliegue, downgrade ni nueva certificación integral, conforme al
alcance solicitado.
