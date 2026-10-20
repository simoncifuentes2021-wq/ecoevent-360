const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const adminTabs = fs.readFileSync(path.join(root, "components/events/EventTabs.tsx"), "utf8");
const clientTabs = fs.readFileSync(path.join(root, "components/client/ClientEventTabs.tsx"), "utf8");

for (const source of [adminTabs, clientTabs]) {
  assert.match(source, /useSearchParams\(\)/, "active tab is read from the current URL");
  assert.match(source, /searchParams\.get\("tab"\)/, "tab is restored from its URL parameter");
  assert.match(source, /params\.set\("tab", key\)/, "choosing a tab persists it to the URL");
  assert.match(source, /router\.replace\(query \? `\$\{pathname\}\?\$\{query\}` : pathname, \{ scroll: false \}\)/,
    "tab changes do not add history entries or jump the viewport");
}

console.log("event tab navigation persistence passed");
