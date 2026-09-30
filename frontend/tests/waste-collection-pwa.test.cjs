const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const root = path.resolve(__dirname, "..");
const read = file => fs.readFileSync(path.join(root, file), "utf8");

test("formulario público de acopio tiene cola IndexedDB e idempotencia", () => {
  const form = read("components/waste/PublicWasteEntry.tsx");
  const offline = read("lib/waste-offline.ts");
  assert.match(form, /savePendingRecord\(queued\)/);
  assert.match(form, /submitPublicWasteBatch/);
  assert.match(form, /client_generated_id: createUuid\(\)/);
  assert.match(form, /collection_point_id: pointId/);
  assert.match(form, /collectionPoints\.map\(point/);
  assert.match(form, /selectedPoint\?\.allowed_waste_types/);
  assert.match(form, /Array\.isArray\(rawMetadata\.collection_points\)/);
  assert.match(form, /Array\.isArray\(cached\.collection_points\)/);
  assert.match(form, /Formulario listo para trabajar sin conexión/);
  assert.match(offline, /indexedDB\.open/);
  assert.match(offline, /createIndex\("token"/);
  assert.match(read("lib/api/waste.ts"), /\/public\/waste-forms\/\$\{encodeURIComponent\(token\)\}\/records/);
  assert.match(read("lib/api/waste.ts"), /\/events\/\$\{eventId\}\/waste-public-form/);
  assert.match(read("components/waste/WasteTab.tsx"), /Registros ambientales/);
  assert.match(read("components/waste/WasteTab.tsx"), /Acopios/);
  assert.match(read("components/waste/CollectionPointsManager.tsx"), /Registros de acopio/);
  assert.match(read("components/waste/CollectionPointsManager.tsx"), /Formulario público Greenway/);
  assert.match(read("components/waste/CollectionPointsManager.tsx"), /Materiales permitidos/);
});

test("el formulario público y el resumen de acopios usan recursos separados", () => {
  const service = read("../backend/app/services/collection_point_service.py");
  const model = read("../backend/app/models/core.py");
  assert.match(service, /WasteCollectionRecord\(/);
  assert.doesNotMatch(service, /WasteRecord\(/);
  assert.match(model, /class WasteCollectionRecord\(Base\)/);
  assert.match(model, /class EventWastePublicForm\(Base\)/);
  assert.match(model, /waste_collection_point_types/);
  assert.match(service, /WASTE_TYPE_NOT_ALLOWED/);
  assert.match(service, /FORM_CLOSED_AFTER_RECORD/);
  assert.match(read("components/waste/WasteTab.tsx"), /WasteSummaryCards/);
});

test("service worker queda limitado a rutas de acopios", () => {
  const worker = read("public/acopios/sw.js");
  assert.match(worker, /const FORM_PREFIX = "\/acopios\/"/);
  assert.match(worker, /url\.pathname\.startsWith\(FORM_PREFIX\)/);
  assert.match(read("app/(public)/acopios/[token]/page.tsx"), /PublicWasteEntry/);
  assert.match(read("app/(public)/acopios/[token]/manifest.webmanifest/route.ts"), /scope: "\/acopios\/"/);
});
