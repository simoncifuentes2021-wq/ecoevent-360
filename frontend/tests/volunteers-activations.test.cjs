const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const read = (file) => fs.readFileSync(path.join(__dirname, "..", file), "utf8");

test("módulo conectado a los roles autorizados sin modificar rutas públicas existentes", () => {
  const routes = read("lib/routes.ts");
  for (const rolePath of ["/admin/voluntarios-activaciones", "/supervisor/voluntarios-activaciones", "/worker/voluntarios-activaciones", "/logistica/voluntarios-activaciones"]) {
    assert.ok(routes.includes(rolePath), `falta navegación para ${rolePath}`);
  }
  assert.ok(read("app/(dashboard)/admin/voluntarios-activaciones/page.tsx").includes("SUPER_ADMIN"));
  assert.ok(read("app/(dashboard)/logistica/voluntarios-activaciones/page.tsx").includes("LOGISTICS_OPERATOR"));
  assert.ok(read("app/(public)/public/inscripcion-voluntarios/[slug]/page.tsx").includes("PublicVolunteerRegistrationPage"));
  assert.ok(read("app/(public)/public/mi-aporte/[token]/page.tsx").includes("PublicVolunteerImpactPage"));
  assert.ok(read("app/(public)/f/[slug]/page.tsx").includes("PublicFormPage"));
});

test("inscripción pública exige consentimiento operativo y mantiene separado el marketing opcional", () => {
  const page = read("components/volunteers/PublicVolunteerPages.tsx");
  assert.match(page, /checked=\{consent\}/);
  assert.match(page, /required type="checkbox"/);
  assert.match(page, /checked=\{marketing\}/);
  assert.match(page, /promocionales\. Es opcional/);
  assert.match(page, /registerPublicVolunteer\(slug/);
  assert.match(read("lib/api/volunteers.ts"), /auth: false/);
});

test("registro operativo admite varios materiales, evidencia móvil, idempotencia y anulación auditada", () => {
  const module = read("components/volunteers/VolunteersActivationsModule.tsx");
  const modal = read("components/volunteers/VolunteerModals.tsx");
  const api = read("lib/api/volunteers.ts");
  assert.match(modal, /Agregar material/);
  assert.match(modal, /capture="environment"/);
  assert.match(modal, /crypto\.randomUUID\(\)/);
  assert.match(module, /voidContribution/);
  assert.match(module, /uploadContributionEvidence/);
  assert.match(api, /volunteer-contributions\.csv/);
  assert.match(api, /getPublicVolunteerImpact/);
});

test("el historial público solo muestra aportes agregados y usa enlace-capacidad aleatorio", () => {
  const page = read("components/volunteers/PublicVolunteerPages.tsx");
  const service = fs.readFileSync(path.join(__dirname, "..", "..", "backend", "app", "services", "volunteer_service.py"), "utf8");
  assert.match(page, /getPublicVolunteerImpact\(token\)/);
  assert.match(page, /Este enlace es privado/);
  assert.match(service, /secrets\.token_urlsafe\(36\)/);
  assert.match(service, /hashlib\.sha256\(access_token\.encode\(\)\)/);
  assert.match(service, /token_hash/);
});
