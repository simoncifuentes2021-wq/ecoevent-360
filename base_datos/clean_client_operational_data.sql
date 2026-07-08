-- Limpieza operativa para entregar la base al cliente sin romper datos maestros.
--
-- Borra datos transaccionales:
--   - eventos y todo lo asociado a eventos
--   - pedidos operativos y logisticos
--   - compras logisticas
--   - stock registrado y movimientos
--   - productos de inventario
--   - evidencias, auditoria y reportes transaccionales
--
-- Conserva datos maestros/configuracion:
--   - clients
--   - users
--   - warehouses
--   - warehouse_users
--   - catalog_items
--   - services
--   - waste_types
--   - carbon_factors
--   - alembic_version
--
-- Ejecutar con rol admin/owner de la base. Hacer backup antes.

BEGIN;

TRUNCATE TABLE
    audit_logs,
    logistics_evidences,
    purchase_request_items,
    purchase_requests,
    logistics_order_items,
    logistics_orders,
    stock_movements,
    stock_balances,
    inventory_items,
    order_evidences,
    event_order_items,
    event_orders,
    reports,
    alerts,
    survey_responses,
    survey_imports,
    surveys,
    water_records,
    energy_records,
    fuel_records,
    carbon_records,
    waste_records,
    evidences,
    incidents,
    tasks,
    event_staff,
    event_services,
    event_zones,
    events
RESTART IDENTITY CASCADE;

COMMIT;
