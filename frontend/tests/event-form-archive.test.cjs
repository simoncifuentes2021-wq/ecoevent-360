const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const root = path.resolve(__dirname, "..");
const api = fs.readFileSync(path.join(root, "lib/api/eventForms.ts"), "utf8");
const tab = fs.readFileSync(path.join(root, "components/event-forms/EventFormsTab.tsx"), "utf8");

test("los formularios se pueden archivar sin eliminarlos físicamente", () => {
  assert.match(api, /archiveEventForm/);
  assert.match(api, /restoreEventForm/);
  assert.match(api, /\/forms\/\$\{formId\}\/restore/);
  assert.match(api, /api\.delete<void>\(`\/forms\/\$\{formId\}`\)/);
  assert.match(tab, /archiveEventForm\(archiveTarget\.id\)/);
  assert.match(tab, /Formulario archivado/);
  assert.match(tab, /ConfirmDialog/);
  assert.match(tab, /Sus respuestas, configuración y enlace se conservarán/);
  assert.match(tab, /include_archived: showArchived/);
  assert.match(tab, /Ver archivados/);
  assert.match(tab, /Ocultar archivados/);
  assert.match(tab, /restoreArchivedForm\(item\)/);
  assert.match(tab, /Desarchivar/);
});
