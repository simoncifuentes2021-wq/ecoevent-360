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
