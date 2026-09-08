const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const frontend = path.join(__dirname, "..");
const read = (...parts) => fs.readFileSync(path.join(frontend, ...parts), "utf8");

test("el filtro de usuarios permite buscar operadores logísticos", () => {
  const filters = read("components", "users", "UserFilters.tsx");
  const api = read("lib", "api", "users.ts");

  assert.match(filters, /label: "Operador logístico", value: "LOGISTICS_OPERATOR"/);
  assert.match(api, /toQuery\(params\)/);
});

test("crear y editar usuarios mantienen disponible el rol logístico", () => {
  const roleSelect = read("components", "users", "RoleSelect.tsx");
  const userForm = read("components", "users", "UserForm.tsx");

  assert.match(roleSelect, /"LOGISTICS_OPERATOR"/);
  assert.match(userForm, /"LOGISTICS_OPERATOR"/);
});
