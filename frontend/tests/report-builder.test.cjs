const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const root = path.join(__dirname, "..");
const read = (...parts) => fs.readFileSync(path.join(root, ...parts), "utf8");

test("wizard supports event and show drafts", () => {
  const source = read("components", "reports", "ReportDraftDialog.tsx");
  assert.match(source, /Evento completo/); assert.match(source, /Show específico/);
  assert.match(source, /getEventSessions/); assert.match(source, /sessionId/);
});

test("editor exposes override, reset, refresh, reorder and preview", () => {
  const source = read("components", "reports", "ReportBuilder.tsx");
  for (const pattern of [/auto_value/, /Editado manualmente/, /Restablecer/, /refreshReport/, /reorderReportSections/, /Preview/]) assert.match(source, pattern);
  assert.doesNotMatch(source, /dangerouslySetInnerHTML|window\.(?:alert|confirm|prompt)/);
});

test("editor includes custom sections, evidences and immutable revisions", () => {
  const source = read("components", "reports", "ReportBuilder.tsx");
  for (const pattern of [/addCustomReportSection/, /deleteCustomReportSection/, /Eliminar sección/, /getAvailableReportEvidences/, /addReportEvidence/, /createReportRevision/, /restoreReportRevision/]) assert.match(source, pattern);
});

test("preview supports typed reusable editorial layouts", () => {
  const source = read("components", "reports", "ReportBuilder.tsx");
  for (const layout of ["HERO_IMAGE_TEXT", "KPI_GRID", "TWO_COLUMN", "METRIC_LIST", "FEATURE_CHART", "PHOTO_GRID", "EDITORIAL", "TEXT_IMAGE", "BIG_NUMBERS"]) assert.match(source, new RegExp(layout));
  assert.match(source, /data-layout/);
  assert.match(source, /PreviewEvidenceGallery/);
  assert.match(source, /getStoredToken/);
  assert.doesNotMatch(source, /dangerouslySetInnerHTML/);
  assert.match(source, /ENVIRONMENTAL_STORY/);
  assert.match(source, /Gestión ambiental premium/);
});

test("2B.1 editor uses three panels and the backend page plan", () => {
  const builder = read("components", "reports", "ReportBuilder.tsx");
  const api = read("lib", "api", "reports.ts");
  const types = read("types", "report.ts");
  assert.match(builder, /report-builder-three-panels/);
  assert.match(builder, /live-a4-preview/);
  assert.match(builder, /getReportPagePlan/);
  assert.match(api, /\/page-plan/);
  assert.match(types, /ReportPagePlan/);
  assert.match(builder, /Zoom de vista previa/);
  assert.match(builder, /Ajustar/);
  assert.match(builder, /794 \* zoom/);
  assert.match(builder, /Guardado automático activo/);
  assert.match(builder, /Fotografía principal/);
  assert.match(builder, /layout-thumbnail-selector/);
  assert.match(builder, /Incluir/);
  assert.match(builder, /Mostrar fila/);
  assert.match(builder, /material de reciclaje/);
  assert.match(builder, /ítem de huella de carbono/);
  assert.match(builder, /maxItems/);
  assert.match(builder, /La cantidad y unidad son opcionales/);
  assert.match(builder, /Texto explicativo para el PDF/);
  assert.match(builder, /Texto explicativo que aparecerá bajo el indicador/);
  assert.match(types, /is_visible/);
});

test("API surface retains legacy and adds professional builder operations", () => {
  const source = read("lib", "api", "reports.ts");
  for (const pattern of [/generateFinalReport/, /createReportDraft/, /getReportEditor/, /resetReportField/, /getReportRevisions/]) assert.match(source, pattern);
});

test("premium PDF workflow uses exact preview and immutable publications", () => {
  const editor = read("components", "reports", "ReportBuilder.tsx");
  const api = read("lib", "api", "reports.ts");
  for (const pattern of [/Vista previa PDF/, /Generar versión PDF/, /Versiones PDF/, /deliverReportPublication/, /idempotency_key/]) {
    assert.match(`${editor}\n${api}`, pattern);
  }
  assert.match(editor, /role="dialog"/);
  assert.doesNotMatch(editor, /window\.confirm/);
});

test("client portal lists only delivered authenticated publications", () => {
  const source = read("components", "client", "ClientReportsTab.tsx");
  assert.match(source, /status === "DELIVERED"/);
  assert.match(source, /downloadReportPublication/);
  assert.doesNotMatch(source, /downloadReport\(/);
});

test("legacy report list delegates download and delivery to premium publications", () => {
  const router = read("../backend/app/api/routers/reports.py");
  const publications = read("../backend/app/services/report_publication_service.py");
  const table = read("components/reports/ReportTable.tsx");
  const dialog = read("components/reports/MarkReportDeliveredDialog.tsx");

  for (const pattern of [
    /latest_publication\(db, report_id, current_user\)/,
    /deliver_latest/,
    /read_stored_file\(publication\.storage_key\)/,
    /"premium": True/,
  ]) assert.match(router, pattern);
  assert.match(publications, /def deliver_latest/);
  assert.match(publications, /item = generate/);
  assert.match(publications, /return deliver\(db, item\.id, user\)/);
  assert.match(table, /Entregar PDF premium al cliente/);
  assert.match(dialog, /Generar y entregar PDF/);
});
