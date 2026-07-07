-- Reset de datos para partir produccion desde una base limpia.
-- Mantiene estructura, extensiones, tipos, funciones, politicas RLS y alembic_version.
-- Ejecutar con un rol admin/owner de la base, no con el rol limitado de la app.
--
-- Despues de ejecutar este script, crear el primer SUPER_ADMIN con:
--   cd backend
--   python -m app.seed_admin

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
    warehouse_users,
    warehouses,
    inventory_items,
    order_evidences,
    event_order_items,
    event_orders,
    catalog_items,
    reports,
    alerts,
    survey_responses,
    survey_imports,
    surveys,
    water_records,
    energy_records,
    fuel_records,
    carbon_records,
    carbon_factors,
    waste_records,
    waste_types,
    evidences,
    incidents,
    tasks,
    event_staff,
    event_services,
    services,
    event_zones,
    events,
    users,
    clients
RESTART IDENTITY CASCADE;

COMMIT;
