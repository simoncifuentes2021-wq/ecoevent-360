# Plataforma transversal de IA

EcoEvent centraliza las capacidades de IA en `backend/app/services/ai`. Los módulos consumidores no conocen proveedores ni credenciales: construyen un contexto mínimo y autorizado, seleccionan un prompt versionado y llaman a `AIService`.

## Flujo ambiental

`POST /api/v1/events/{event_id}/environmental-actions/{action_id}/ai-interpretation` autentica al usuario, valida su acceso al evento mediante los permisos existentes, recupera la acción y sus métricas persistidas, y construye el contexto en el backend. El navegador no envía indicadores ambientales.

La IA solo interpreta resultados ya calculados por EcoEvent. Energía, CO2e, diésel, PM2.5, PM10 y NOx continúan siendo responsabilidad exclusiva del motor ambiental. Las equivalencias incluidas proceden de factores controlados y versionados por EcoEvent.

Cada intento queda en `ai_generations` con usuario, acción, evento, fecha, proveedor, modelo solicitado y efectivo, versión de prompt, hash y snapshot de entrada, estado, latencia y error sanitizado. Un éxito con el mismo hash, prompt, proveedor y modelo se reutiliza. Al cambiar la acción, métricas, metodología o equivalencias cambia el hash y se invalida el cache automáticamente.

## Asistente de reportes

`POST /api/v1/reports/{report_id}/sections/{section_id}/ai-draft` genera, mejora o regenera un candidato editorial. El backend recupera el reporte y la sección usando los permisos existentes; el navegador solo envía operación, estilo, extensión y el texto actual del editor. El alcance `EVENT` o `SHOW` nunca se amplía.

Los valores efectivos de la sección, incluidas correcciones manuales, tienen prioridad sobre el snapshot automático. Para resumen ejecutivo y conclusión solo se incorporan secciones habilitadas. Antes de invocar al proveedor se eliminan claves sensibles y la salida se rechaza si introduce cifras no presentes (se permite redondeo). La respuesta estructurada contiene `title_suggestion`, `generated_text`, `key_points`, `warnings` y `used_data_keys`.

Una generación es siempre un candidato: no modifica la sección. El usuario debe aceptar o descartar; al aceptar se usa el guardado normal del editor, con control de concurrencia y revisiones. `REGENERATE` fuerza un intento nuevo; las otras operaciones reutilizan caché cuando contexto, prompt, proveedor y modelo no cambiaron.

### Dirección editorial integral

`POST /api/v1/reports/{report_id}/ai-editorial-plan` analiza todas las secciones habilitadas y devuelve una propuesta tipada de título, orden, layout, agrupación por páginas y mejoras opcionales de texto. La IA solo elige componentes soportados por el renderizador; no genera HTML, CSS ni coordenadas arbitrarias.

La propuesta no modifica el reporte. `POST /api/v1/reports/{report_id}/ai-editorial-plan/apply` valida nuevamente el alcance y la versión, crea primero una revisión completa con la nota `Antes de aplicar optimizacion editorial con IA` y recién después aplica el plan. El botón de deshacer restaura esa revisión; el mismo punto de retorno permanece en el historial aunque se recargue el navegador.

## Configuración

```env
AI_ENABLED=true
AI_REPORTS_ENABLED=true
AI_PROVIDER=openrouter
AI_MODEL=openrouter/free
AI_API_KEY=replace-me
AI_TIMEOUT_SECONDS=30
AI_MAX_OUTPUT_TOKENS=800
AI_TEMPERATURE=0.2
RATE_LIMIT_AI_INTERPRETATION=5/300
RATE_LIMIT_AI_REPORTS=10/300
```

`AI_BASE_URL` es opcional. OpenRouter usa por defecto `https://openrouter.ai/api/v1`. La clave vive exclusivamente en el backend. Con `AI_ENABLED=false`, el resto de EcoEvent funciona normalmente.

## Carril profesional de reportes

Los reportes no heredan el proveedor general. Usan `AI_REPORT_PROVIDER`, `AI_REPORT_MODEL`,
`AI_REPORT_API_KEY`, `AI_REPORT_BASE_URL`, `AI_REPORT_TIMEOUT_SECONDS`,
`AI_REPORT_MAX_OUTPUT_TOKENS`, `AI_REPORT_TEMPERATURE` y
`AI_REPORT_MONTHLY_BUDGET_USD`. La clave sigue esta prioridad: `AI_REPORT_API_KEY` y,
solo por compatibilidad, `OPENAI_API_KEY`. Nunca cae implícitamente en `AI_API_KEY`.

OpenAI usa Responses API con Structured Outputs y `store=false`. La IA entrega propuestas
para `ReportSection`, presets y variantes certificadas; no genera HTML, CSS, páginas libres,
coordenadas, publicaciones ni modifica `layout_overrides`. Toda aplicación requiere aceptación
humana y crea primero una revisión reversible.

El registro central incluye para `openai:gpt-5.6-luna` los precios oficiales consultados el
2026-08-25: entrada US$0.20, entrada cacheada US$0.02 y salida US$1.20 por millón de tokens.
`AI_REPORT_PRICING_JSON` permite sobreescribirlos localmente sin dispersar precios por el código.
Si el modelo efectivo no tiene precio, el presupuesto falla cerrado antes de llamar al proveedor.
El editor muestra consumo, presupuesto y saldo del mes; el coste real usa los tokens reportados
por Responses API y resta la entrada cacheada de la entrada regular.

### Privacidad y retención

El contexto elimina claves sensibles y enmascara PII habitual en texto libre. No se envían URLs
privadas ni respuestas individuales de formularios. `AIGeneration.input_snapshot` conserva solo
el contexto sanitizado necesario, source keys y agregados para auditoría. Se recomienda una
retención configurable de 90 días para snapshots y una retención mayor para metadatos de uso;
esta fase no ejecuta borrado automático.

## Proveedores

`AIProvider` define el contrato async normalizado. `OpenRouterProvider` y el adaptador OpenAI-compatible están registrados en `ai_router.py`. Para usar OpenAI se cambian `AI_PROVIDER=openai`, modelo y clave; Impacto Ambiental no cambia.

Para agregar otro proveedor:

1. Implementar `AIProvider.generate` en `providers/`.
2. Traducir su respuesta a `ProviderResult`.
3. Registrarlo en `ai_router.build_provider`.
4. Agregar pruebas con el proveedor mockeado, sin llamadas reales a internet.

Gemini queda como extensión futura y no está implementado en esta etapa.

## Nuevos módulos

1. Crear un constructor seguro en `contexts/` que reciba IDs y usuario, valide permisos y consulte únicamente datos necesarios.
2. Crear un prompt centralizado y una versión en `prompts/`.
3. Definir/usar un output Pydantic normalizado.
4. Registrar la capability en `AIService`.
5. Exponer un endpoint específico autenticado y con rate limit.
6. Conectar el frontend al endpoint sin claves ni payloads arbitrarios.

La búsqueda web abierta no forma parte de esta versión. Una futura búsqueda deberá ser una herramienta explícita con lista de fuentes oficiales permitidas y nunca participar en cálculos certificados.
