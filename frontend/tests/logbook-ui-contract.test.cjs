const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const read = (name) => fs.readFileSync(path.join(__dirname, "..", "components", "logbooks", name), "utf8");

test("asignación revisa antes de crear y tiene guardia lógica inmediata", () => {
  const source = read("EventLogbooksTab.tsx");
  assert.match(source, /Revisar asignación/);
  assert.match(source, /Confirmar asignación/);
  assert.match(source, /requestInFlight\.current/);
  assert.match(source, /if \(saving \|\| requestInFlight\.current \|\| !canReview\) return/);
  assert.equal((source.match(/await createEventLogbook/g) || []).length, 1);
});

test("selector Sí/No mantiene estado neutro y limpia sin convertirlo en No", () => {
  const source = read("WorkerLogbookDetail.tsx");
  assert.match(source, /if \(value === ""\)/);
  assert.match(source, /if \(response\) void clear\(item\)/);
  assert.doesNotMatch(source, /boolean_value: event\.target\.value === "YES"/);
});

test("Bitácoras no usa ventanas nativas ni muestra e.message", () => {
  const directory = path.join(__dirname, "..", "components", "logbooks");
  const source = fs.readdirSync(directory).filter((name) => name.endsWith(".tsx"))
    .map((name) => read(name)).join("\n");
  assert.doesNotMatch(source, /\b(?:alert|confirm|prompt)\s*\(/);
  assert.doesNotMatch(source, /window\.(?:alert|confirm|prompt)/);
  assert.doesNotMatch(source, /\be\.message\b/);
});
