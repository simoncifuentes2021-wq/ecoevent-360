const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const frontend = path.join(__dirname, "..");
const read = (...parts) => fs.readFileSync(path.join(frontend, ...parts), "utf8");

test("las bandejas logisticas usan tarjetas responsivas con progreso y contexto", () => {
  const overview = read("components", "logistics", "LogisticsOrdersOverview.tsx");
  const pages = [
    read("app", "(dashboard)", "admin", "logistica", "pedidos", "page.tsx"),
    read("app", "(dashboard)", "supervisor", "logistica", "pedidos", "page.tsx"),
    read("app", "(dashboard)", "logistica", "mis-pedidos", "page.tsx")
  ];

  assert.match(overview, /LogisticsOrderProgress/);
  assert.match(overview, /Abrir pedido/);
  assert.match(overview, /grid gap-4 lg:grid-cols-2/);
  assert.match(overview, /Bodega/);
  assert.match(overview, /Productos/);

  for (const page of pages) {
    assert.match(page, /LogisticsOrdersOverview/);
    assert.doesNotMatch(page, /<DataTable/);
  }
});

test("el detalle comunica la etapa sin eliminar acciones operativas", () => {
  const detail = read("components", "logistics", "LogisticsOrderDetailView.tsx");
  const api = read("lib", "api", "logistics-orders.ts");

  assert.match(detail, /LogisticsOrderStatusBadge status=\{order\.status\}/);
  assert.match(detail, /Paso a paso del pedido/);
  assert.match(detail, /nextActionFor/);
  assert.match(detail, /visibleStep === 0/);
  assert.match(detail, /visibleStep === 5/);
  assert.match(detail, /Ir al paso actual/);
  assert.match(detail, /Las etapas futuras se habilitan al avanzar/);
  assert.match(detail, /Productos solicitados/);
  assert.match(detail, /reserveLogisticsOrderStock/);
  assert.match(detail, /dispatchLogisticsOrder/);
  assert.match(detail, /confirmLogisticsOrderDelivery/);
  assert.match(detail, /confirmLogisticsOrderOutcome/);
  assert.match(detail, /closeLogisticsOrder/);
  assert.match(detail, /<OutcomeItemModal[\s\S]*error=\{stockError\}/);
  assert.match(detail, /role="alert"/);
  assert.match(detail, /Productos que debes revisar/);
  assert.match(detail, /¿Los consumibles se utilizaron completamente\?/);
  assert.match(detail, /OutcomeProductCard/);
  assert.match(detail, /Elige el caso habitual/);
  assert.match(detail, /Todo consumido/);
  assert.match(detail, /Todo devuelto usable/);
  assert.match(detail, /Guardar y volver/);
  assert.doesNotMatch(detail, /min-w-\[1120px\]/);
  assert.match(detail, /markAllLogisticsOrderConsumablesConsumed/);
  assert.match(detail, /Los retornables y consumibles parciales no se modificarán/);
  assert.match(detail, /Reservar disponible/);
  assert.match(detail, /reservar ahora lo disponible y crear una compra solo por el faltante/);
  assert.match(detail, /delivery_mode: "TO_WAREHOUSE"/);
  assert.match(detail, /warehouse_id: order\.warehouse_id/);
  assert.match(detail, /Ingreso a bodega/);
  assert.match(detail, /Stock en otras bodegas/);
  assert.match(detail, /Transferir a \{stockAvailability\.warehouse_name\}/);
  assert.match(detail, /StockTransferModal/);
  assert.match(api, /stock-availability/);
  assert.match(api, /stock-transfers/);
  assert.match(detail, /Solicitar despacho disponible/);
  assert.match(detail, /Aprobar y dividir pedido/);
  assert.match(detail, /PartialDispatchModal/);
  assert.match(api, /partial-dispatch-request/);
  assert.match(api, /logistics-partial-dispatch-requests/);
  assert.match(api, /outcomes\/mark-consumables-consumed/);
});

test("la creación carga el catálogo completo y explica el stock por bodega", () => {
  const catalog = read("components", "logistics", "WarehouseProductCatalog.tsx");
  const inventoryApi = read("lib", "api", "inventory.ts");
  const stockApi = read("lib", "api", "stock.ts");
  const creationSurfaces = [
    read("app", "(dashboard)", "admin", "logistica", "pedidos", "page.tsx"),
    read("app", "(dashboard)", "supervisor", "logistica", "pedidos", "page.tsx"),
    read("components", "logistics", "LogisticsOrdersTab.tsx")
  ];

  assert.match(inventoryApi, /getAllInventoryItems/);
  assert.match(inventoryApi, /Math\.ceil\(first\.total \/ limit\)/);
  assert.match(stockApi, /getAllStockBalances/);
  assert.match(catalog, /Disponible en origen/);
  assert.match(catalog, /Otras bodegas/);
  assert.match(catalog, /Se podrá transferir desde otra bodega/);
  assert.match(catalog, /El faltante podrá enviarse a compra/);
  assert.match(catalog, /products\.length/);
  assert.match(catalog, /registrados/);
  assert.doesNotMatch(catalog, /slice\(0, 8\)/);
  assert.doesNotMatch(catalog, /warehouse\?\.address|warehouse\?\.city/);

  for (const surface of creationSurfaces) {
    assert.match(surface, /WarehouseProductCatalog/);
    assert.match(surface, /getAllInventoryItems/);
    assert.match(surface, /getAllStockBalances/);
  }
});

test("movimientos de stock conserva visibles las etiquetas al desplazarse", () => {
  const dataTable = read("components", "common", "DataTable.tsx");
  const adminMovements = read("app", "(dashboard)", "admin", "stock", "movimientos", "page.tsx");
  const operatorMovements = read("app", "(dashboard)", "logistica", "stock", "movimientos", "page.tsx");

  assert.match(dataTable, /stickyHeader\?: boolean/);
  assert.match(dataTable, /sticky top-0 z-20 bg-white/);
  assert.match(dataTable, /max-h-\[70vh\] overflow-auto/);
  assert.match(adminMovements, /stickyHeader/);
  assert.match(operatorMovements, /stickyHeader/);
});
