const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const ts = require("typescript");

const root = path.resolve(__dirname, "..");
const read = file => fs.readFileSync(path.join(root, file), "utf8");
const normalizerPath = path.join(root, "lib/normalizers/waste.ts");
const normalizerJs = ts.transpileModule(fs.readFileSync(normalizerPath, "utf8"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 }
}).outputText;
const normalizerModule = { exports: {} };
new Function("module", "exports", normalizerJs)(normalizerModule, normalizerModule.exports);
const { normalizeWasteSummary, formatPercentage } = normalizerModule.exports;

const combinedSummary = {
  total_kg: 735,
  total_event_kg: 735,
  total_records: 96,
  waste_types_count: 7,
  collection_points: { weight_kg: 600, percentage: 81.63, records_count: 82 },
  direct_records: { weight_kg: 135, percentage: 18.37, records_count: 14 },
  top_waste_type: {
    id: "cardboard-id", waste_type_id: "cardboard-id", name: "Cartón y papel", total_kg: 370,
    collection_points_kg: 350, direct_kg: 20, percentage: 50.34
  },
  top_collection_point: { collection_point_id: "ac-02", code: "AC-02", name: "Food Trucks", weight_kg: 245 },
  by_type: [{
    id: "cardboard-id", waste_type_id: "cardboard-id", name: "Cartón y papel", total_kg: 370,
    collection_points_kg: 350, direct_kg: 20, percentage: 50.34
  }],
  by_source: [
    { source: "COLLECTION_POINT", weight_kg: 600, percentage: 81.63, records_count: 82 },
    { source: "DIRECT", weight_kg: 135, percentage: 18.37, records_count: 14 }
  ],
  by_collection_point: [{ collection_point_id: "ac-02", code: "AC-02", name: "Food Trucks", weight_kg: 245 }]
};

test("normaliza sin duplicar fuentes y presenta KPI y material combinado", () => {
  const summary = normalizeWasteSummary(combinedSummary);
  assert.equal(summary.total_event_kg, 735);
  assert.equal(summary.collection_points.weight_kg, 600);
  assert.equal(summary.direct_records.weight_kg, 135);
  assert.equal(summary.total_records, 96);
  assert.equal(summary.waste_types_count, 7);
  assert.equal(summary.top_waste_type.kg, 370);
  assert.equal(summary.top_waste_type.collection_points_kg, 350);
  assert.equal(summary.top_waste_type.direct_kg, 20);
  assert.equal(summary.top_collection_point.code, "AC-02");
});

test("maneja cero, solo acopios y solo registro directo sin NaN", () => {
  const empty = normalizeWasteSummary(null);
  assert.equal(empty.total_event_kg, 0);
  assert.equal(empty.collection_points.percentage, 0);
  assert.equal(empty.direct_records.percentage, 0);
  assert.equal(empty.top_waste_type, null);
  assert.equal(empty.top_collection_point, null);
  assert.equal(formatPercentage(empty.collection_points.percentage).includes("NaN"), false);

  const collectionOnly = normalizeWasteSummary({
    total_event_kg: 600,
    total_records: 82,
    collection_points: { weight_kg: 600, percentage: 100, records_count: 82 },
    direct_records: { weight_kg: 0, percentage: 0, records_count: 0 },
    by_type: [{ name: "Cartón", total_kg: 600, collection_points_kg: 600, direct_kg: 0, percentage: 100 }]
  });
  assert.equal(collectionOnly.total_event_kg, 600);
  assert.equal(collectionOnly.top_waste_type.kg, 600);

  const directOnly = normalizeWasteSummary({
    total_event_kg: 135,
    total_records: 14,
    collection_points: { weight_kg: 0, percentage: 0, records_count: 0 },
    direct_records: { weight_kg: 135, percentage: 100, records_count: 14 },
    by_type: [{ name: "Aceite", total_kg: 135, collection_points_kg: 0, direct_kg: 135, percentage: 100 }]
  });
  assert.equal(directOnly.total_event_kg, 135);
  assert.equal(directOnly.direct_records.percentage, 100);
});

test("el resumen usa nombres operacionales, estado vacío, carga y distribución móvil", () => {
  const cards = read("components/waste/WasteSummaryCards.tsx");
  const insights = read("components/waste/WasteSummaryInsights.tsx");
  const charts = read("components/waste/WasteCharts.tsx");
  const tab = read("components/waste/WasteTab.tsx");
  for (const label of ["Total residuos registrados", "Recibido en acopios", "Registros realizados", "Material principal"]) assert.ok(cards.includes(label));
  for (const title of ["Acopio con mayor recepción", "Tipos de residuos registrados", "Registro directo"]) assert.ok(insights.includes(title));
  for (const title of ["Distribución por material", "Origen del registro", "Recepción por acopio"]) assert.ok(charts.includes(title));
  assert.ok(charts.includes("collection_points_kg"));
  assert.ok(charts.includes("direct_kg"));
  assert.ok(charts.includes("grid min-w-0 gap-4 lg:grid-cols-2"));
  assert.ok(tab.includes("Aún no hay residuos registrados"));
  assert.ok(tab.includes("summaryLoading"));
  assert.ok(tab.includes("summaryError"));
});
