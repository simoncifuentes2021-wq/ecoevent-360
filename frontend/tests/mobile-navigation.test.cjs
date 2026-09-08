const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const frontend = path.join(__dirname, "..");
const read = (...parts) => fs.readFileSync(path.join(frontend, ...parts), "utf8");

test("el menú móvil usa el viewport real y permite desplazar todas las opciones", () => {
  const mobile = read("components", "layout", "MobileSidebar.tsx");
  const sidebar = read("components", "layout", "Sidebar.tsx");

  assert.match(mobile, /h-\[100dvh\]/);
  assert.match(mobile, /safe-area-inset-bottom/);
  assert.match(mobile, /document\.body\.style\.overflow = "hidden"/);
  assert.match(mobile, /event\.key === "Escape"/);
  assert.match(mobile, /aria-modal="true"/);
  assert.match(sidebar, /min-h-0 flex-1 touch-pan-y/);
  assert.match(sidebar, /overflow-y-auto overscroll-contain/);
  assert.match(sidebar, /-webkit-overflow-scrolling:touch/);
  assert.match(sidebar, /shrink-0/);
});
