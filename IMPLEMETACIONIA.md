Prioridad alta
1. Aplicar completamente la propuesta premium
Actualmente el Asistente premium propone:
- Variantes visuales.
- Énfasis.
- Indicadores seleccionados.
- Hallazgos.
- Recomendaciones.
- Conclusión.
- Fotografías.
- Cantidad estimada de páginas.
Pero al aceptar, el sistema solo aplica:
- Visibilidad.
- Orden.
- Narrativa.
- Preset general.
- Algunas asignaciones de fotografías.
Debería aplicar también:
- premium_variant a la composición correspondiente.
- emphasis al diseño visual.
- selected_metric_keys para priorizar indicadores.
- Hallazgos en Resumen ejecutivo.
- Recomendaciones en su sección.
- Conclusión generada.
- Distribución de páginas propuesta.
- Selección completa de evidencias.
Este es actualmente el vacío funcional más importante.

2. Que la IA revise el resultado visual después de aplicarlo
Ahora la IA propone sin comprobar cómo quedó realmente el informe.
El flujo ideal sería:
1. La IA genera una propuesta.
2. El sistema produce temporalmente el HTML/PDF.
3. Un validador comprueba:
   - Texto cortado.
   - Elementos fuera de la página.
   - Fotografías que desplazan información.
   - Secciones demasiado densas.
   - Páginas casi vacías.
   - Gráficos sin datos.
   - Mezcla de secciones ocultas.
   - Mala distribución de imágenes.
4. Si encuentra problemas, realiza una segunda corrección automática.
5. Presenta al usuario la propuesta final.
Esto habría detectado automáticamente varios de los problemas que revisamos en Residuos, Bike Zone y Ecoequivalencias.

3. Separar el modelo según la tarea
No todas las funciones necesitan el mismo nivel de razonamiento.
Recomendación:
Función	Tipo de modelo recomendado
Mejorar una sección	Modelo rápido y económico
Generar un resumen	Modelo rápido con buen lenguaje
Director editorial completo	Modelo de razonamiento más potente
Auditoría final del informe	Modelo potente más validadores deterministas
Selección de fotografías	Modelo con visión


gpt-5.6-luna está bien para redacción rápida, pero el Director editorial completo se beneficiaría de un modelo más fuerte, especialmente para coordinar 10–15 secciones, páginas, métricas e imágenes.
Mejoras de calidad

4. Prompts especializados por sección
Actualmente hay prompts generales. Conviene disponer de reglas diferentes para:
- Portada.
- Resumen ejecutivo.
- Datos del evento.
- Residuos.
- Bike Zone.
- Huella de carbono.
- Impacto ambiental.
- Ecoequivalencias.
- Evidencias.
- Recomendaciones.
- Conclusión.
Por ejemplo, Residuos debería pedir explícitamente:
- Total recuperado.
- Distribución por material.
- Destino.
- Tasa de recuperación.
- Hallazgo principal.
- No mezclar datos de movilidad.
Esto produciría textos más precisos y menos genéricos.

5. Darle contexto de capacidad visual
La IA conoce las composiciones disponibles, pero no conoce suficientemente sus límites reales.
Debe recibir reglas como:
- Máximo de indicadores por composición.
- Máximo de fotografías.
- Cantidad de texto recomendable.
- Compatibilidad entre gráficos y datos.
- Capacidad aproximada de una página A4.
- Cuándo dividir una sección.
- Qué composiciones funcionan con cero, uno o varios datos.
Así no elegiría una galería sin fotografías ni un gráfico protagonista sin suficientes categorías.
6. Incorporar análisis visual de fotografías
Actualmente la IA recibe principalmente:
- ID.
- Descripción.
- Fecha.
- Sección asignada.
No analiza realmente el contenido de la imagen.
Una IA con visión podría determinar:
- Si la foto es de residuos, Bike Zone, público o escenario.
- Calidad y resolución.
- Orientación.
- Si funciona como portada.
- Si contiene personas identificables.
- Si está repetida.
- Cuál fotografía es más representativa.
- Qué recorte sería adecuado.
7. Proteger explícitamente las modificaciones manuales
La IA debería distinguir entre:
- Datos automáticos.
- Cambios manuales.
- Contenido generado anteriormente.
- Elementos bloqueados por el usuario.
Se podría añadir “Bloquear para IA” en cada sección, campo, composición e imagen. Así una optimización global no tocaría decisiones manuales importantes.
Validación y aprendizaje
8. Trazabilidad para todos los textos
Las cifras ya están protegidas, pero cada afirmación relevante debería conservar sus fuentes.
Por ejemplo:
“Los residuos orgánicos fueron la categoría predominante.”

Debería guardar internamente:
Fuente: waste.items.organic
No solamente validar números, sino también afirmaciones comparativas como:
- Mayor.
- Menor.
- Principal.
- Aumentó.
- Disminuyó.
- Más eficiente.
9. Registrar el feedback del usuario
Cuando el usuario:
- Acepta una propuesta.
- La descarta.
- Cambia el texto generado.
- Cambia la composición recomendada.
- Deshace la optimización.
El sistema debería registrar esa diferencia como señal de calidad. Actualmente existe historial técnico, pero no un ciclo completo de evaluación editorial.
10. Crear una certificación automática permanente
Conviene preparar varios informes de referencia con todos los módulos y verificar automáticamente:
- Contenido preservado.
- Visibilidad.
- Composiciones.
- Fotografías.
- Página completa.
- Ausencia de mezclas.
- Ausencia de contenido cortado.
- PDF válido.
- Cifras fundamentadas.
- Propuesta reversible.
Orden recomendado de implementación
1. Aplicar completamente las propuestas premium.
2. Agregar revisión visual automática posterior al render.
3. Separar modelo rápido y modelo editorial potente.
4. Incorporar reglas específicas por sección.
5. Proteger elementos manuales con bloqueo.
6. Añadir análisis real de imágenes.
7. Crear evaluación continua basada en aceptación, edición y deshacer.