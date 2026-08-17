const assert = require("node:assert/strict");
const fs = require("node:fs");
const Module = require("node:module");
const path = require("node:path");
const test = require("node:test");
const ts = require("typescript");

function loadTypescript(relativePath) {
  const sourcePath = path.join(__dirname, "..", relativePath);
  const output = ts.transpileModule(fs.readFileSync(sourcePath, "utf8"), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
  const compiled = new Module(sourcePath); compiled.paths = module.paths; compiled._compile(output, sourcePath); return compiled.exports;
}

const { chileToday, chileLocalToIso, formatChileDateTime } = loadTypescript("lib/chile-time.ts");

test("hoy se calcula por el calendario de Chile y no por UTC", () => {
  assert.equal(chileToday(new Date("2026-08-16T02:30:00Z")), "2026-08-15");
});

test("datetime-local respeta horario de verano e invierno chileno", () => {
  assert.equal(chileLocalToIso("2026-01-15T12:00"), "2026-01-15T15:00:00.000Z");
  assert.equal(chileLocalToIso("2026-07-15T12:00"), "2026-07-15T16:00:00.000Z");
});

test("la visualización es estable aunque el computador use otra zona", () => {
  assert.match(formatChileDateTime("2026-07-15T16:00:00Z"), /12:00/);
});

test("las respuestas API sin zona se reconocen como timestamps UTC", () => {
  const apiSource = fs.readFileSync(path.join(__dirname, "..", "lib", "api", "index.ts"), "utf8");
  assert.match(apiSource, /normalizeApiDateTimes/);
  assert.match(apiSource, /return `\$\{value\}Z`/);
  assert.match(apiSource, /normalizeApiDateTimes\(await response\.json\(\)\)/);
});
