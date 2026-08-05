const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const root = path.join(__dirname, "..", "components");
const read = (...parts) => fs.readFileSync(path.join(root, ...parts), "utf8");

test("tareas e incidencias permiten General del evento o show activo", () => {
  for (const source of [read("tasks", "TaskFormModal.tsx"), read("incidents", "IncidentFormModal.tsx")]) {
    assert.match(source, /General del evento/);
    assert.match(source, /session_id/);
    assert.match(source, /!item\.archived_at/);
  }
});

test("evidencia independiente usa show directo y evidencia vinculada lo deriva", () => {
  const source = read("evidences", "EvidenceUploader.tsx");
  assert.match(source, /!taskId && !incidentId && sessionId/);
  assert.match(source, /se deriva automáticamente/);
  assert.match(source, /disabled=\{Boolean\(taskId \|\| incidentId\)\}/);
});

test("detalle del show integra resumen y operación humana sin diálogos nativos", () => {
  const sources = [
    read("event-sessions", "EventSessionsTab.tsx"),
    read("event-sessions", "ShowOperationsPanel.tsx"),
    read("tasks", "TaskFormModal.tsx"),
    read("incidents", "IncidentFormModal.tsx"),
    read("evidences", "EvidenceUploader.tsx"),
  ].join("\n");
  assert.match(sources, /Personal y turnos/);
  assert.match(sources, /ShowOperationalSummary/);
  assert.match(sources, /ConfirmDialog/);
  assert.doesNotMatch(sources, /window\.(?:alert|confirm|prompt)|\b(?:alert|confirm|prompt)\s*\(/);
});
