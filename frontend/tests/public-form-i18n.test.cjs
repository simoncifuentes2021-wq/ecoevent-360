const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const root = path.resolve(__dirname, "..");
const renderer = fs.readFileSync(path.join(root, "components/public-forms/PublicFormRenderer.tsx"), "utf8");
const page = fs.readFileSync(path.join(root, "components/public-forms/PublicFormPage.tsx"), "utf8");
const i18n = fs.readFileSync(path.join(root, "lib/publicFormI18n.ts"), "utf8");

test("los formularios públicos usan el catálogo i18n para textos de interfaz", () => {
  assert.match(renderer, /publicFormCopy/);
  assert.match(renderer, /publicFormFieldLabel/);
  assert.match(renderer, /publicFormOptionLabel/);
  assert.match(renderer, /translatePublicFormError/);
  assert.match(page, /publicFormCopy/);
  assert.doesNotMatch(renderer, />Selecciona</);
  assert.doesNotMatch(renderer, />Sí</);
  assert.doesNotMatch(renderer, />Respuesta recibida</);
  assert.doesNotMatch(renderer, />Código Bike Zone</);
});

test("Huella público, Huella equipo y Bike Zone tienen traducciones de campos críticos", () => {
  for (const key of [
    "event_name",
    "venue_name",
    "full_name",
    "email",
    "company",
    "country_origin",
    "country_residence",
    "residence_region",
    "residence_commune",
    "transport_mode",
    "bike_brand",
    "bike_model",
    "bike_color",
    "event_ticket_number",
    "comments",
  ]) {
    assert.match(i18n, new RegExp(`${key}: \\{`), `falta traducción para ${key}`);
  }
  assert.match(i18n, /email: \{ es: "Correo electrónico", en: "Email", pt: "E-mail", ko: "이메일" \}/);
});

test("los valores canónicos usados por la lógica de formularios no se traducen", () => {
  assert.match(renderer, /value !== "Chile"/);
  assert.match(renderer, /answers\.residence_region === "Metropolitana de Santiago"/);
  assert.match(renderer, /<option key=\{option\.value\} value=\{option\.value\}>/);
});
