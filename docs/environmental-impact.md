# Impacto Ambiental

Este módulo es independiente de **Huella de Carbono**. Huella mide lo emitido por el evento; Impacto Ambiental compara una línea base convencional con el escenario real sostenible y registra la diferencia evitada.

## Modelo de cálculo

Una acción pertenece siempre a un evento y opcionalmente a un show. La FK compuesta `(event_id, session_id)` impide asociar un show de otro evento. Los tipos de solución son identificadores estables; los nombres visibles nunca determinan fórmulas.

Las metodologías declaran tecnologías baseline/real y referencias a factores ambientales documentados. Sin metodología o factor activo, la métrica queda no disponible: nunca se sustituye por cero. Cada resultado conserva inputs, metodología, factores, fuente, año y fecha en `calculation_snapshot`, por lo que cambiar un factor no altera resultados históricos hasta un recálculo explícito.

Los resultados distinguen `calculated_value` de `reported_value`. Un override solo puede ser aplicado por ADMIN/SUPER_ADMIN, exige motivo y genera auditoría; no destruye el cálculo original.

## Extensión futura

`environmental_actions` admite cantidad manual sin depender de inventario. Una etapa posterior puede añadir una FK nullable al ítem real de inventario y sugerir cantidades desde Logística. Reportes podrá consumir el endpoint de summary y las métricas persistidas sin recalcular el evento ni modificar el significado de Carbon.
