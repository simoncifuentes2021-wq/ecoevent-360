const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const root = path.join(__dirname, "..");
const read = (...parts) => fs.readFileSync(path.join(root, ...parts), "utf8");

test("edición masiva exige vista previa antes de aplicar", () => {
  const source = read("components", "logbooks", "LogbookImportBatchEditor.tsx");
  assert.match(source, /previewImportBatchParticipants/);
  assert.match(source, /updateImportBatchParticipants/);
  assert.match(source, /!preview\?<Button/);
  assert.match(source, /Confirmar cambio masivo/);
  assert.match(source, /historical_assignments_preserved/);
});

test("edición masiva ofrece operaciones y alcances explícitos", () => {
  const source = read("components", "logbooks", "LogbookImportBatchEditor.tsx");
  for (const value of ["ADD", "REMOVE", "REPLACE", "ALL", "FUTURE", "DATES"]) {
    assert.match(source, new RegExp(`value=\\"${value}\\"`));
  }
  assert.match(source, /Fechas seleccionadas/);
  assert.match(source, /Editar participantes del lote/);
});

test("cliente API usa endpoints dedicados del lote", () => {
  const source = read("lib", "api", "logbooks.ts");
  assert.match(source, /participants\/preview/);
  assert.match(source, /updateImportBatchParticipants/);
  assert.match(source, /api\.patch<LogbookBulkParticipantsPreview>/);
  assert.match(source, /supervisor\/preview/);
  assert.match(source, /updateImportBatchSupervisor/);
});

test("el supervisor del lote usa vista previa, alcance y respeta bloqueos", () => {
  const source = read("components", "logbooks", "LogbookImportBatchEditor.tsx");
  assert.match(source, /Editar supervisor del lote/);
  assert.match(source, /previewImportBatchSupervisor/);
  assert.match(source, /instances_locked/);
  assert.match(source, /scope==="DATES"/);
});

test("generador limita el rango al evento y descarga el xlsx autenticado", () => {
  const component = read("components", "logbooks", "LogbookXlsxTemplateGenerator.tsx");
  const api = read("lib", "api", "logbooks.ts");
  assert.match(component, /getEvent\(eventId\)/);
  assert.match(component, /min=\{minimum\}/);
  assert.match(component, /max=\{maximum\}/);
  assert.match(component, /days<=366/);
  assert.match(component, /Descargar plantilla Excel/);
  assert.match(component, /URL\.createObjectURL/);
  assert.match(api, /import-xlsx\/template/);
  assert.match(api, /Authorization:`Bearer/);
  assert.match(api, /response\.blob\(\)/);
});

test("generador oficial aparece antes de cargar la planificación completada", () => {
  const source = read("components", "logbooks", "LogbookExcelImport.tsx");
  const generator = source.indexOf("<LogbookXlsxTemplateGenerator");
  const upload = source.indexOf("Cargar planificación completada");
  assert.ok(generator >= 0 && upload > generator);
});
