const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const root = path.resolve(__dirname, "..");
const metadata = fs.readFileSync(path.join(root, "lib/publicFormMetadata.ts"), "utf8");
const legacyRoute = fs.readFileSync(path.join(root, "app/(public)/f/[slug]/page.tsx"), "utf8");
const showRoute = fs.readFileSync(path.join(root, "app/(public)/f/[slug]/[formSlug]/page.tsx"), "utf8");

test("los enlaces de formularios generan tarjetas sociales específicas", () => {
  assert.match(metadata, /form\?\.session_name.*form\?\.event_name.*showSlug/s);
  assert.match(metadata, /openGraph:/);
  assert.match(metadata, /summary_large_image/);
  assert.match(metadata, /form\?\.banner_url \|\| DEFAULT_SHARE_IMAGE/);
  assert.match(metadata, /humanizeSlug\(formSlug\)/);
});

test("las rutas antigua y con show generan metadata dinámica", () => {
  assert.match(legacyRoute, /generateMetadata/);
  assert.match(legacyRoute, /publicFormMetadata\(params\.slug/);
  assert.match(showRoute, /generateMetadata/);
  assert.match(showRoute, /publicFormMetadata\(params\.formSlug.*params\.slug/s);
  assert.doesNotMatch(legacyRoute, /"use client"/);
  assert.doesNotMatch(showRoute, /"use client"/);
});
