# Certificación manual guiada: Bitácora SHARED

## Preparación

- Usar una base PostgreSQL de pruebas con `alembic current` en `20260722_0035`.
- Disponer de un ADMIN o SUPER_ADMIN, un SUPERVISOR asignado al evento, dos
  participantes activos en `EventStaff` y, si se desea probarlo, un
  `LOGISTICS_OPERATOR` expresamente asignado.
- Abrir dos sesiones de navegador independientes (por ejemplo, una normal y una
  privada) para evitar compartir credenciales.

## Recorrido exacto

1. Como ADMIN/SUPER_ADMIN, entrar a **Administración > Plantillas de bitácora**.
2. Crear una plantilla o clonar una versión concreta. Confirmar que la nueva
   versión figura como **Borrador**.
3. Agregar secciones e ítems, guardar y publicar. Confirmar que la versión
   publicada queda de solo lectura.
4. Entrar al evento, abrir **Bitácoras > Administrar**, crear una ejecución,
   seleccionar modalidad **Compartida**, el supervisor y ambos participantes
   de `EventStaff`.
5. Abrir la ejecución. En la primera sesión iniciar como participante A y en la
   segunda como participante B.
6. A completa un ítem y B completa otro. Recargar ambas sesiones: las dos
   respuestas deben aparecer en una única bitácora, con su autor/último editor.
7. Abrir el mismo ítem en ambas sesiones. Guardar primero en A y, sin recargar,
   intentar guardar en B. B debe recibir un conflicto de versión; al recargar
   debe conservarse el valor de A, sin sobrescritura silenciosa.
8. En un ítem que permita evidencia, pulsar **Tomar foto o seleccionar
   archivo** desde un teléfono. Autorizar la cámara, capturar una imagen y
   confirmar miniatura/nombre. Probar también PNG o WebP desde archivos.
9. Enviar la ejecución. Todos los participantes deben verla **Enviada** y ya no
   deben poder editar respuestas.
10. Como SUPERVISOR, abrir **Mis supervisiones**, revisar autores, evidencias e
    historial y solicitar cambios con comentario obligatorio.
11. Volver como participante, corregir y reenviar. Confirmar incremento del
    número de intento.
12. Aprobar como SUPERVISOR. Todos los participantes deben verla **Aprobada** y
    la instancia **Completada**.
13. Revisar historial, colaboradores, porcentaje de avance, resultado y
    aprobación. Como CLIENT propietario, comprobar sólo el resumen agregado y
    evidencias públicas; no deben aparecer nombres, correos, respuestas
    individuales, comentarios internos, supervisor ni claves de almacenamiento.
14. Repetir accesos con un trabajador no asignado, supervisor no asignado,
    operador logístico no asignado y CLIENT de otra organización: deben ser
    rechazados aunque conozcan el UUID.

## Resultado automatizado que respalda el recorrido

`tests/test_logbook_certification.py::test_certification_shared_concurrency_collaboration_and_review`
reproduce en PostgreSQL la colaboración, autoría, última modificación,
conflicto optimista 409, ausencia de sobrescritura, envío común, solicitud de
cambios, reenvío, aprobación, métricas e historial. La captura visual/cámara
queda como comprobación manual porque depende del navegador y dispositivo.
