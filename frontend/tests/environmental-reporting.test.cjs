const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const tabs = fs.readFileSync(path.join(root, "components/client/ClientEventTabs.tsx"), "utf8");
const impact = fs.readFileSync(path.join(root, "components/client/ClientEnvironmentalImpactTab.tsx"), "utf8");
const types = fs.readFileSync(path.join(root, "types/clientPortal.ts"), "utf8");

assert.match(tabs, /sectionKey: "environmental_impact"/);
assert.match(tabs, /ClientEnvironmentalImpactTab/);
assert.match(impact, /Resultados oficialmente aprobados/);
assert.match(impact, /Resultados por alcance/);
assert.match(impact, /Metodologías y fuentes/);
assert.match(impact, /Equivalencias comunicacionales/);
assert.match(types, /"environmental_actions_approved"/);

console.log("environmental reporting and client portal UI contract passed");
