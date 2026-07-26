const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const ui = fs.readFileSync(path.join(root, "components/logbooks/EventLogbooksTab.tsx"), "utf8");
const api = fs.readFileSync(path.join(root, "lib/api/logbooks.ts"), "utf8");

test("muestra estados y fechas del ciclo en America/Santiago", () => {
  for (const state of ["SCHEDULED", "OPEN", "OVERDUE"]) assert.match(ui, new RegExp(state));
  assert.match(ui, /America\/Santiago/);
  assert.match(ui, /Apertura:/);
  assert.match(ui, /Vence:/);
  assert.match(ui, /text-red-700/);
});

test("control manual se limita a roles administrativos y evita doble clic", () => {
  assert.match(ui, /role === "ADMIN" \|\| role === "SUPER_ADMIN"/);
  assert.match(ui, /disabled=\{processing\}/);
  assert.match(ui, /if \(processing\) return/);
  assert.match(api, /\/admin\/logbooks\/lifecycle\/process/);
});

test("confirmación solo presenta cantidades agregadas", () => {
  assert.match(ui, /opened_count/);
  assert.match(ui, /overdue_count/);
  for (const forbidden of ["storage_key", "review_comment"]) {
    assert.doesNotMatch(ui, new RegExp(forbidden));
  }
});
