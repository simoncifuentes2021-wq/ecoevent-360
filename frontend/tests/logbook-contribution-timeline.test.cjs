const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const ui = fs.readFileSync(path.join(root, "components", "logbooks", "DailyContributionList.tsx"), "utf8");
const api = fs.readFileSync(path.join(root, "lib", "api", "logbooks.ts"), "utf8");

test("cada actividad permite agregar múltiples registros independientes", () => {
  assert.match(ui, /Agregar una nueva actualización/);
  assert.match(ui, /Agregar registro/);
  assert.match(ui, /createMyLogbookContribution/);
  assert.doesNotMatch(ui, /mine\?\.description/);
});

test("cada registro propio se edita, elimina y recibe evidencia por separado", () => {
  assert.match(ui, /updateMyLogbookContribution\(entry\.id/);
  assert.match(ui, /deleteMyLogbookContribution\(entry\.id/);
  assert.match(ui, /uploadContributionEvidence\(entry\.id/);
  assert.match(ui, /entry\.evidences\.length<5/);
  assert.match(ui, /setPreview\(`\$\{API_ORIGIN\}/);
});

test("API separa creación y edición con control de versión", () => {
  assert.match(api, /post<LogbookContribution>\(`\/logbook-instance-items\/\$\{itemId\}\/my-contributions`/);
  assert.match(api, /patch<LogbookContribution>\(`\/logbook-contributions\/\$\{contributionId\}`/);
  assert.match(api, /\{description,version\}/);
});
