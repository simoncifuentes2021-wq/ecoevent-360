const assert = require("node:assert/strict");
const fs = require("node:fs");
const Module = require("node:module");
const path = require("node:path");
const test = require("node:test");
const ts = require("typescript");

function loadTypescript(relativePath) {
  const sourcePath = path.join(__dirname, "..", relativePath);
  const output = ts.transpileModule(fs.readFileSync(sourcePath, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText;
  const compiled = new Module(sourcePath);
  compiled.paths = module.paths;
  compiled._compile(output, sourcePath);
  return compiled.exports;
}

const { activeEvidenceCount, participantAssignment, SingleFlight } = loadTypescript("lib/logbook-clear.ts");

test("cuenta únicamente evidencias activas para la confirmación", () => {
  const response = { evidences: [
    { id: "active", deleted_at: undefined },
    { id: "deleted", deleted_at: "2026-07-25T00:00:00Z" },
  ] };
  assert.equal(activeEvidenceCount(response), 1);
  assert.equal(activeEvidenceCount(undefined), 0);
});

test("solo una persona formalmente asignada recibe capacidad de edición", () => {
  const assignments = [{ id: "a", user_id: "worker", status: "IN_PROGRESS" }];
  assert.equal(participantAssignment(assignments, "admin"), undefined);
  assert.equal(participantAssignment(assignments, "supervisor"), undefined);
  assert.equal(participantAssignment(assignments, "worker").id, "a");
});

test("dos confirmaciones simultáneas generan una sola solicitud", async () => {
  const flight = new SingleFlight();
  let calls = 0;
  let release;
  const pending = new Promise((resolve) => { release = resolve; });
  const operation = async () => { calls += 1; await pending; return "ok"; };
  const first = flight.run(operation);
  const second = await flight.run(operation);
  assert.equal(second.started, false);
  assert.equal(calls, 1);
  release();
  assert.deepEqual(await first, { started: true, value: "ok" });
});

test("después de un error permite reintentar", async () => {
  const flight = new SingleFlight();
  let calls = 0;
  await assert.rejects(() => flight.run(async () => { calls += 1; throw new Error("fallo"); }));
  const retry = await flight.run(async () => { calls += 1; return "guardado"; });
  assert.equal(calls, 2);
  assert.deepEqual(retry, { started: true, value: "guardado" });
});
