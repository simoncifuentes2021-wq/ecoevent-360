const assert = require("node:assert/strict");
const fs = require("node:fs");
const Module = require("node:module");
const path = require("node:path");
const test = require("node:test");
const ts = require("typescript");

const sourcePath = path.join(__dirname, "..", "lib", "logbook-validation.ts");
const source = fs.readFileSync(sourcePath, "utf8");
const output = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText;
const compiled = new Module(sourcePath);
compiled.paths = module.paths;
compiled._compile(output, sourcePath);
const { isAnswered, validateLogbook } = compiled.exports;

const evidence = { id: "e", deleted_at: undefined };
const response = (patch = {}) => ({
  id: "r", assignment_id: "a", logbook_item_id: "i", is_not_applicable: false,
  result_status: "COMPLETED", version: 1, evidences: [], ...patch,
});
const item = (patch = {}) => ({
  id: "i", title: "Control", item_type: "YES_NO", is_required: true,
  allow_not_applicable: true, evidence_policy: "NONE", min_evidences: 0,
  max_evidences: 5, require_comment_on_failure: false, requires_supervisor_review: false,
  client_visible_by_default: false, creates_incident_suggestion: false, options: [], ...patch,
});

test("métricas cuentan false, cero y N/A, pero no vacíos", () => {
  assert.equal(isAnswered(response({ boolean_value: false })), true);
  assert.equal(isAnswered(response({ numeric_value: 0 })), true);
  assert.equal(isAnswered(response({ is_not_applicable: true, result_status: "NOT_APPLICABLE" })), true);
  assert.equal(isAnswered(response({ text_value: "  ", result_status: "PENDING" })), false);
  assert.equal(isAnswered(undefined), false);
});

test("distingue respuestas, comentarios y evidencias pendientes", () => {
  const items = [
    item({ id: "required", title: "Pendiente" }),
    item({ id: "failure", title: "Fallo", require_comment_on_failure: true, evidence_policy: "REQUIRED_ON_FAILURE", min_evidences: 1 }),
    item({ id: "photo", title: "Foto", evidence_policy: "REQUIRED", min_evidences: 1 }),
    item({ id: "optional", title: "Opcional", is_required: false }),
  ];
  const responses = new Map([
    ["failure", response({ logbook_item_id: "failure", boolean_value: false, result_status: "FAILED" })],
    ["photo", response({ logbook_item_id: "photo", boolean_value: true })],
  ]);
  const result = validateLogbook([{ title: "General", items }], responses);
  assert.equal(result.answeredItems, 2);
  assert.equal(result.optionalUnansweredItems, 1);
  assert.deepEqual(result.pendingRequiredResponses.map((entry) => entry.itemId), ["required"]);
  assert.deepEqual(result.pendingComments.map((entry) => entry.itemId), ["failure"]);
  assert.deepEqual(result.pendingFailureEvidences.map((entry) => entry.itemId), ["failure"]);
  assert.deepEqual(result.pendingEvidences.map((entry) => entry.itemId), ["photo"]);
  assert.equal(result.complete, false);
});

test("REQUIRED_ON_FAILURE no exige fotografía cuando la respuesta cumple", () => {
  const control = item({ evidence_policy: "REQUIRED_ON_FAILURE", min_evidences: 1 });
  const result = validateLogbook(
    [{ title: "General", items: [control] }],
    new Map([["i", response({ boolean_value: true, evidences: [] })]]),
  );
  assert.equal(result.pendingFailureEvidences.length, 0);
  assert.equal(result.complete, true);
  assert.equal(result.evidenceCount, 0);
});

test("evidencia activa satisface el requisito", () => {
  const control = item({ evidence_policy: "REQUIRED", min_evidences: 1 });
  const result = validateLogbook(
    [{ title: "General", items: [control] }],
    new Map([["i", response({ boolean_value: true, evidences: [evidence] })]]),
  );
  assert.equal(result.pendingEvidences.length, 0);
  assert.equal(result.complete, true);
});
