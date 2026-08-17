const { chromium } = require("playwright-core");
const assert = require("node:assert/strict");

const baseURL = process.env.E2E_BASE_URL || "http://127.0.0.1:3010";
const chrome = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const reportId = "11111111-1111-4111-8111-111111111111";
const sectionId = "22222222-2222-4222-8222-222222222222";
const user = { id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", email: "admin@example.test", full_name: "Admin", role: "ADMIN", is_active: true };
let version = 1;
let publications = [];
let section = { id: sectionId, report_id: reportId, section_key: "bike_zone", section_type: "BIKE_ZONE", title: "Bike Zone", layout_variant: "BIG_NUMBERS", is_enabled: true, sort_order: 0, content: { text: "Operación sustentable", fields: [{ key: "users", label: "Usuarios", auto_value: 5, value: 8, unit: null, description: null, is_overridden: true, source: "BIKE_ZONE" }], items: [] }, source_snapshot: { text: null, fields: [{ key: "users", label: "Usuarios", auto_value: 5, value: 5, unit: null, description: null, is_overridden: false, source: "BIKE_ZONE" }], items: [] }, source_metadata: { availability: "AVAILABLE", source_scope: "SHOW_SCOPED" }, is_custom: false, edit_version: 1, created_at: new Date().toISOString(), updated_at: new Date().toISOString() };
const editor = () => ({ id: reportId, event_id: "33333333-3333-4333-8333-333333333333", title: "Reporte editorial E2E", summary: null, pdf_url: null, status: "DRAFT", scope: "EVENT", session_id: null, generated_by: null, generated_at: null, delivered_at: null, created_by: user.id, edit_version: version, created_at: new Date().toISOString(), updated_at: new Date().toISOString(), sections: [section], evidences: [] });

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: chrome });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = []; page.on("pageerror", error => errors.push(error.message));
  await page.route("**/*", async route => {
    const request = route.request(); if (!["fetch", "xhr"].includes(request.resourceType())) return route.continue();
    const path = new URL(request.url()).pathname; const json = (body, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
    if (path.endsWith("/auth/me")) return json(user);
    if (path.endsWith(`/reports/${reportId}/editor`)) return json(editor());
    if (path.endsWith(`/reports/${reportId}/available-evidences`)) return json([]);
    if (path.endsWith(`/reports/${reportId}/revisions`)) return json([]);
    if (path.endsWith(`/reports/${reportId}/publications`) && request.method() === "GET") return json(publications);
    if (path.endsWith(`/reports/${reportId}/html-preview`)) return route.fulfill({ status: 200, contentType: "text/html", body: `<html><body><section data-layout="${section.layout_variant}"><h1>${section.title}</h1></section></body></html>` });
    if (path.endsWith(`/reports/${reportId}/publications`) && request.method() === "POST") { publications = [{ id: "44444444-4444-4444-8444-444444444444", report_id: reportId, revision_id: null, publication_number: 1, status: "GENERATED", sha256: "a".repeat(64), file_size: 154299, page_count: 10, generated_by: user.id, generated_at: new Date().toISOString(), delivered_by: null, delivered_at: null, created_at: new Date().toISOString() }]; return json(publications[0], 201); }
    if (path.endsWith("/pdf-preview")) return route.fulfill({ status: 200, contentType: "application/pdf", body: Buffer.from("%PDF-1.7\nE2E premium preview\n%%EOF") });
    if (path.endsWith("/publications/44444444-4444-4444-8444-444444444444/deliver")) { publications[0] = { ...publications[0], status: "DELIVERED", delivered_at: new Date().toISOString() }; return json(publications[0]); }
    if (path.endsWith("/publications/44444444-4444-4444-8444-444444444444/download")) return route.fulfill({ status: 200, contentType: "application/pdf", body: Buffer.from("%PDF-1.7\nE2E immutable publication\n%%EOF") });
    if (path.endsWith(`/reports/${reportId}/sections/${sectionId}`) && request.method() === "PATCH") { const body = request.postDataJSON(); section = { ...section, ...body, edit_version: section.edit_version + 1 }; version += 1; return json(section); }
    return json({ items: [], total: 0, page: 1, limit: 50 });
  });
  await page.addInitScript(({ user }) => {
    try {
      localStorage.setItem("ecoevent360.access_token", "e2e-token");
      localStorage.setItem("ecoevent360.user", JSON.stringify(user));
    } catch {
      // The exact PDF preview iframe is intentionally sandboxed without storage access.
    }
  }, { user });
  await page.goto(`${baseURL}/reports/${reportId}/edit`, { waitUntil: "networkidle" });
  try {
    await page.getByText("Reporte editorial E2E").waitFor();
  } catch (error) {
    console.error("E2E page state", { url: page.url(), body: (await page.locator("body").innerText()).slice(0, 1200), errors });
    throw error;
  }
  await page.getByRole("button", { name: /Galer.a fotogr.fica/i }).click();
  await page.getByRole("button", { name: "Guardar ahora" }).click();
  await page.getByRole("button", { name: /Galer.a fotogr.fica/i }).waitFor();
  assert.equal(await page.getByRole("button", { name: /Galer.a fotogr.fica/i }).getAttribute("aria-pressed"), "true");
  await page.getByRole("button", { name: "Preview" }).click();
  await page.getByTitle("Vista previa exacta del reporte").waitFor();
  const previewFrame = page.getByTitle("Vista previa exacta del reporte").contentFrame();
  await previewFrame.getByText(section.title).waitFor();
  let internalControls = null;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      internalControls = await page.getByTitle("Vista previa exacta del reporte")
        .contentFrame().getByText("Editado manualmente").count();
      break;
    } catch (error) {
      if (attempt === 2) throw error;
      await page.waitForTimeout(250);
    }
  }
  assert.equal(internalControls, 0, "preview no debe mostrar controles internos");
  await page.getByRole("button", { name: "Generar PDF" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Generar versión" }).click();
  await page.getByText("v1").waitFor();
  await page.getByRole("button", { name: "Entregar" }).evaluate((button) => button.click());
  await page.waitForTimeout(500);
  assert.equal(publications[0].status, "DELIVERED", "la entrega debe invocar el endpoint de publicación");
  await page.getByText("DELIVERED").waitFor();
  assert.deepEqual(errors, []);
  await browser.close(); console.log("E2E report builder browser: editor and typed preview passed");
})().catch(error => { console.error(error); process.exit(1); });
