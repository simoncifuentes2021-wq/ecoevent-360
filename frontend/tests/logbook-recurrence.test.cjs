const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const panel = fs.readFileSync(path.join(root, "components/logbooks/LogbookRecurrencePanel.tsx"), "utf8");
const worker = fs.readFileSync(path.join(root, "components/logbooks/WorkerLogbookDetail.tsx"), "utf8");

test("formulario recurrente incluye frecuencias, varios días y vista previa", () => {
  for (const token of ["DAILY", "WEEKLY", "MONTHLY", "weekdays", "Vista previa", "America/Santiago"]) {
    assert.match(panel, new RegExp(token));
  }
  assert.match(panel, /flight\.current/);
});

test("gestión usa diálogos internos y acciones accesibles", () => {
  assert.match(panel, /LogbookDialog/);
  assert.doesNotMatch(panel, /window\.(alert|confirm|prompt)/);
  for (const action of ["Pausar", "Reanudar", "Finalizar"]) assert.match(panel, new RegExp(action));
  assert.match(panel, /Editar responsables futuros/);
  assert.match(panel, /supervisor_id:supervisor\|\|null/);
  assert.match(panel, /updateLogbookRecurrence/);
  assert.match(panel, /revision:item\.revision/);
});

test("SCHEDULED queda visualmente bloqueada además de la política backend", () => {
  assert.match(worker, /instanceEditable/);
  assert.match(worker, /está programada/);
  assert.match(worker, /solo lectura/);
});
