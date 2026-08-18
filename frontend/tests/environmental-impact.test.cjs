const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const tab = fs.readFileSync(path.join(root, "components/environmental-impact/EnvironmentalImpactTab.tsx"), "utf8");
const form = fs.readFileSync(path.join(root, "components/environmental-impact/EnvironmentalActionForm.tsx"), "utf8");
const api = fs.readFileSync(path.join(root, "lib/api/environmental.ts"), "utf8");
const eventTabs = fs.readFileSync(path.join(root, "components/events/EventTabs.tsx"), "utf8");

assert.match(eventTabs, /Impacto Ambiental/);
assert.match(tab, /No calculado/);
assert.match(tab, /Factor o metodología pendiente/);
assert.match(tab, /LoadingState/);
assert.match(tab, /ErrorState/);
assert.match(tab, /ConfirmDialog/);
assert.match(tab, /updateEnvironmentalAction/);
assert.match(tab, /setFormAction\(item\)/);
assert.doesNotMatch(tab + form, /window\.(alert|confirm)/);
assert.match(form, /ELECTRIC_LIGHTING_TOWER/);
assert.match(form, /ELECTRIC_MOTORCYCLE/);
assert.match(form, /scope === "SHOW"/);
assert.match(form, /Potencia promedio por equipo/);
assert.match(api, /environmental-impact\/summary/);
assert.match(api, /environmental-actions/);
console.log("environmental impact UI contract passed");
