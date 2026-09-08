"""Structured editorial boundaries shared by all report AI capabilities."""

SECTION_GUIDANCE_VERSION = "report_section_guidance_v1"


def _policy(objective, include, exclude, success):
    return {"objective": objective, "include_only_if_available": include,
            "must_not_include": exclude, "success_criteria": success}


SECTION_GUIDANCE = {
    "COVER": _policy("Identificar el informe sin convertir la portada en análisis.", ["evento", "cliente", "fecha", "ubicación", "imagen disponible"], ["resultados", "recomendaciones", "cifras ausentes"], ["título breve", "identidad inequívoca"]),
    "EXECUTIVE_SUMMARY": _policy("Sintetizar los resultados más materiales del informe.", ["tres a cinco resultados respaldados", "contexto indispensable", "hallazgo principal"], ["secciones ocultas", "recomendaciones nuevas", "detalle operativo"], ["cada afirmación es rastreable", "no introduce cifras"]),
    "EVENT_INFO": _policy("Describir antecedentes verificables del evento.", ["nombre", "tipo", "inicio", "término", "ubicación", "asistencia estimada", "asistencia real"], ["residuos", "movilidad", "carbono", "impactos ajenos"], ["distingue asistencia estimada y real", "omite campos sin dato"]),
    "SHOW_INFO": _policy("Describir la función o jornada cubierta.", ["nombre", "horario", "ubicación", "asistencia", "estado"], ["datos de otras funciones", "atribuir resultados globales a una función"], ["mantiene alcance SHOW", "etiqueta datos agregados"]),
    "SERVICES": _policy("Resumir servicios planificados o prestados.", ["servicio", "cantidad", "estado", "observación"], ["personal", "tareas", "incidentes", "beneficios no medidos"], ["distingue planificado y ejecutado", "no transforma cantidades en impactos"]),
    "OPERATIONS": _policy("Explicar la ejecución operacional relevante.", ["recursos", "acciones", "horarios", "estado", "observaciones"], ["incidentes no registrados", "impactos inferidos", "datos personales"], ["separa hechos y observaciones", "respeta alcance temporal"]),
    "STAFF": _policy("Presentar la dotación sin exponer información personal.", ["cantidad", "roles", "turnos", "áreas"], ["nombres", "correo", "teléfono", "identificadores", "evaluaciones individuales"], ["usa agregados", "preserva privacidad"]),
    "TASKS": _policy("Informar el avance verificable de tareas.", ["tarea", "estado", "fecha", "totales ya calculados"], ["incidentes", "causas inferidas", "responsables", "porcentajes nuevos"], ["distingue completado y pendiente", "no presenta planes como ejecución"]),
    "INCIDENTS": _policy("Reportar incidencias registradas.", ["tipo", "cantidad", "severidad", "estado", "acción registrada"], ["causalidad inferida", "culpables", "datos personales", "incidentes inexistentes"], ["diferencia abierto y resuelto", "trata el cero objetivamente"]),
    "FORMS": _policy("Sintetizar resultados agregados de formularios.", ["número de respuestas", "distribuciones", "indicadores calculados"], ["respuestas personales", "nombres", "contactos", "inferencias individuales"], ["indica base disponible", "mantiene agregación", "omite PII"]),
    "BIKE_ZONE": _policy("Comunicar uso y desempeño del bicicletero.", ["usuarios", "ingresos", "retiros", "ocupación", "capacidad", "impactos precomputados"], ["residuos", "materiales", "valorización", "emisiones calculadas por el modelo"], ["no mezcla movilidad y residuos", "distingue capacidad y uso"]),
    "WASTE": _policy("Explicar gestión y circularidad de residuos.", ["total gestionado o recuperado", "distribución por material", "destino", "tasa de valorización ya calculada", "hallazgo clave"], ["Bike Zone", "bicicleteros", "movilidad", "usuarios de bicicletas", "carbono no suministrado"], ["conserva unidades", "distingue generado, recuperado y valorizado", "no mezcla movilidad"]),
    "CARBON": _policy("Presentar la huella calculada y sus límites.", ["total kgCO2e", "fuentes", "alcance", "metodología", "período"], ["compensación no registrada", "neutralidad", "net zero", "conversiones nuevas"], ["distingue emisiones e impacto evitado", "mantiene kgCO2e"]),
    "ENVIRONMENTAL_IMPACT": _policy("Sintetizar impactos ambientales verificados y evitados.", ["indicador", "unidad", "origen", "resultado evitado calculado"], ["confundir evitado con emitido", "sumar unidades incompatibles", "inventarios ajenos"], ["conserva unidad y fuente", "distingue resultado y equivalencia"]),
    "EVIDENCES": _policy("Organizar y contextualizar evidencias disponibles.", ["identificador", "leyenda", "fecha", "sección"], ["describir contenido visual no informado", "identificar personas", "inventar lugar o fecha"], ["usa evidence_ids permitidos", "no afirma haber visto la imagen"]),
    "RECOMMENDATIONS": _policy("Proponer acciones derivadas de hallazgos.", ["acción", "fundamento", "prioridad", "resultado cualitativo", "source_keys"], ["garantías", "objetivos numéricos inventados", "acciones sin fuente"], ["cada recomendación es accionable", "cada una cita evidencia"]),
    "CONCLUSION": _policy("Cerrar con una síntesis fiel y breve.", ["balance principal", "aprendizaje", "proyección sustentada"], ["cifras nuevas", "hallazgos ausentes", "recomendaciones nuevas"], ["no duplica el resumen", "toda afirmación proviene del informe"]),
    "CUSTOM": _policy("Desarrollar solo el tema y fuentes de la sección personalizada.", ["contenido y métricas propios"], ["datos ajenos", "cálculos nuevos", "afirmaciones fuera del título"], ["alcance acotado", "trazabilidad", "sin cruces temáticos"]),
}

ECO_EQUIVALENCES_GUIDANCE = _policy(
    "Comunicar ecoequivalencias precomputadas como apoyo comprensible.",
    ["equivalencia", "valor", "unidad", "base disponible"],
    ["calcular equivalencias", "compensación", "neutralidad", "beneficios no certificados"],
    ["usa solo valores precomputados", "declara carácter comunicacional", "no duplica la huella"],
)


def guidance_for(section_type: str, section_key: str | None = None) -> dict:
    if section_key == "preset_eco_equivalences":
        return {"policy_id": "ECO_EQUIVALENCES", **ECO_EQUIVALENCES_GUIDANCE}
    kind = str(section_type or "CUSTOM").upper()
    policy_id = kind if kind in SECTION_GUIDANCE else "CUSTOM"
    return {"policy_id": policy_id, **SECTION_GUIDANCE[policy_id]}


def guidance_map(sections) -> dict[str, dict]:
    return {s.section_key: guidance_for(s.section_type.value, s.section_key)
            for s in sections if s.is_enabled}
