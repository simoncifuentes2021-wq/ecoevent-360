-- =========================================================
-- EcoEvent 360 - Base de Datos Completa PostgreSQL
-- Plataforma de gestión ambiental, sanitaria y experiencia
-- para eventos masivos.
-- =========================================================

-- Recomendado para UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =========================================================
-- 1. ENUMS
-- =========================================================

DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('SUPER_ADMIN', 'ADMIN', 'CLIENT', 'SUPERVISOR', 'WORKER');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE event_status AS ENUM ('QUOTE', 'PLANNING', 'IN_PROGRESS', 'FINISHED', 'REPORT_DELIVERED', 'CANCELLED');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE task_status AS ENUM ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'OBSERVED', 'CANCELLED');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE incident_status AS ENUM ('REPORTED', 'ASSIGNED', 'IN_PROGRESS', 'RESOLVED', 'CLOSED', 'CANCELLED');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE priority_level AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE waste_destination AS ENUM ('RECYCLING', 'COMPOSTING', 'LANDFILL', 'RECOVERY', 'SPECIAL_DISPOSAL', 'OTHER');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE carbon_scope AS ENUM ('SCOPE_1', 'SCOPE_2', 'SCOPE_3');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE survey_status AS ENUM ('DRAFT', 'ACTIVE', 'CLOSED', 'ARCHIVED');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE report_status AS ENUM ('DRAFT', 'GENERATED', 'DELIVERED', 'ARCHIVED');
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- =========================================================
-- 2. CLIENTES Y USUARIOS
-- =========================================================

CREATE TABLE IF NOT EXISTS clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_name VARCHAR(180) NOT NULL,
    rut VARCHAR(30),
    contact_name VARCHAR(160),
    contact_email VARCHAR(180),
    contact_phone VARCHAR(50),
    address TEXT,
    industry VARCHAR(120),
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    full_name VARCHAR(160) NOT NULL,
    email VARCHAR(180) NOT NULL UNIQUE,
    phone VARCHAR(50),
    password_hash TEXT NOT NULL,
    role user_role NOT NULL DEFAULT 'WORKER',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_client_id ON users(client_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- =========================================================
-- 3. EVENTOS
-- =========================================================

CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    name VARCHAR(180) NOT NULL,
    event_type VARCHAR(100),
    description TEXT,
    location_name VARCHAR(180),
    address TEXT,
    city VARCHAR(100),
    region VARCHAR(100),
    country VARCHAR(100) DEFAULT 'Chile',
    latitude NUMERIC(10, 7),
    longitude NUMERIC(10, 7),
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    estimated_attendees INTEGER DEFAULT 0,
    real_attendees INTEGER,
    status event_status NOT NULL DEFAULT 'QUOTE',
    hidden_from_operations BOOLEAN NOT NULL DEFAULT FALSE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_client_id ON events(client_id);
CREATE INDEX IF NOT EXISTS idx_events_status ON events(status);
CREATE INDEX IF NOT EXISTS idx_events_dates ON events(start_date, end_date);

CREATE TABLE IF NOT EXISTS event_zones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    name VARCHAR(160) NOT NULL,
    description TEXT,
    qr_code_url TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_event_zones_event_id ON event_zones(event_id);

-- =========================================================
-- 4. SERVICIOS CONTRATADOS
-- =========================================================

CREATE TABLE IF NOT EXISTS services (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(160) NOT NULL,
    category VARCHAR(120),
    description TEXT,
    unit VARCHAR(50),
    base_price NUMERIC(12, 2),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS event_services (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    service_id UUID NOT NULL REFERENCES services(id) ON DELETE RESTRICT,
    quantity NUMERIC(12, 2) DEFAULT 1,
    unit_price NUMERIC(12, 2),
    total_price NUMERIC(12, 2),
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_event_services_event_id ON event_services(event_id);
CREATE INDEX IF NOT EXISTS idx_event_services_service_id ON event_services(service_id);

-- =========================================================
-- 5. PERSONAL ASIGNADO AL EVENTO
-- =========================================================

CREATE TABLE IF NOT EXISTS event_staff (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_in_event VARCHAR(100),
    shift_start TIMESTAMP,
    shift_end TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(event_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_event_staff_event_id ON event_staff(event_id);
CREATE INDEX IF NOT EXISTS idx_event_staff_user_id ON event_staff(user_id);

-- =========================================================
-- 6. TAREAS OPERATIVAS
-- =========================================================

CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    zone_id UUID REFERENCES event_zones(id) ON DELETE SET NULL,
    assigned_to UUID REFERENCES users(id) ON DELETE SET NULL,
    title VARCHAR(180) NOT NULL,
    description TEXT,
    status task_status NOT NULL DEFAULT 'PENDING',
    priority priority_level NOT NULL DEFAULT 'MEDIUM',
    scheduled_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tasks_event_id ON tasks(event_id);
CREATE INDEX IF NOT EXISTS idx_tasks_zone_id ON tasks(zone_id);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned_to ON tasks(assigned_to);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);

-- =========================================================
-- 7. INCIDENCIAS
-- =========================================================

CREATE TABLE IF NOT EXISTS incidents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    zone_id UUID REFERENCES event_zones(id) ON DELETE SET NULL,
    reported_by UUID REFERENCES users(id) ON DELETE SET NULL,
    assigned_to UUID REFERENCES users(id) ON DELETE SET NULL,
    title VARCHAR(180) NOT NULL,
    description TEXT,
    incident_type VARCHAR(100),
    status incident_status NOT NULL DEFAULT 'REPORTED',
    priority priority_level NOT NULL DEFAULT 'MEDIUM',
    source VARCHAR(80) DEFAULT 'INTERNAL', -- INTERNAL, CLIENT, SURVEY, QR
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMP,
    closed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_incidents_event_id ON incidents(event_id);
CREATE INDEX IF NOT EXISTS idx_incidents_zone_id ON incidents(zone_id);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_priority ON incidents(priority);

-- =========================================================
-- 8. EVIDENCIAS FOTOGRAFICAS Y DOCUMENTALES
-- =========================================================

CREATE TABLE IF NOT EXISTS evidences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    incident_id UUID REFERENCES incidents(id) ON DELETE SET NULL,
    uploaded_by UUID REFERENCES users(id) ON DELETE SET NULL,
    file_url TEXT NOT NULL,
    file_type VARCHAR(80),
    description TEXT,
    taken_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evidences_event_id ON evidences(event_id);
CREATE INDEX IF NOT EXISTS idx_evidences_task_id ON evidences(task_id);
CREATE INDEX IF NOT EXISTS idx_evidences_incident_id ON evidences(incident_id);

-- =========================================================
-- 9. GESTION DE RESIDUOS
-- =========================================================

CREATE TABLE IF NOT EXISTS waste_types (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(120) NOT NULL UNIQUE,
    description TEXT,
    is_recyclable BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS waste_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    zone_id UUID REFERENCES event_zones(id) ON DELETE SET NULL,
    waste_type_id UUID REFERENCES waste_types(id) ON DELETE RESTRICT,
    weight_kg NUMERIC(12, 3) NOT NULL CHECK (weight_kg >= 0),
    destination waste_destination NOT NULL,
    destination_detail TEXT,
    recorded_by UUID REFERENCES users(id) ON DELETE SET NULL,
    evidence_id UUID REFERENCES evidences(id) ON DELETE SET NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_waste_records_event_id ON waste_records(event_id);
CREATE INDEX IF NOT EXISTS idx_waste_records_type_id ON waste_records(waste_type_id);
CREATE INDEX IF NOT EXISTS idx_waste_records_destination ON waste_records(destination);

-- =========================================================
-- 10. HUELLA DE CARBONO
-- =========================================================

CREATE TABLE IF NOT EXISTS carbon_factors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category VARCHAR(120) NOT NULL, -- transporte, energia, residuos, agua, insumos
    name VARCHAR(180) NOT NULL,
    unit VARCHAR(50) NOT NULL, -- litro, km, kWh, kg, unidad
    factor_kgco2e NUMERIC(14, 6) NOT NULL CHECK (factor_kgco2e >= 0),
    scope carbon_scope,
    source TEXT,
    year INTEGER,
    country VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS carbon_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    factor_id UUID NOT NULL REFERENCES carbon_factors(id) ON DELETE RESTRICT,
    category VARCHAR(120) NOT NULL,
    description TEXT,
    activity_value NUMERIC(14, 4) NOT NULL CHECK (activity_value >= 0),
    activity_unit VARCHAR(50) NOT NULL,
    emissions_kgco2e NUMERIC(14, 4) NOT NULL CHECK (emissions_kgco2e >= 0),
    recorded_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_carbon_records_event_id ON carbon_records(event_id);
CREATE INDEX IF NOT EXISTS idx_carbon_records_factor_id ON carbon_records(factor_id);
CREATE INDEX IF NOT EXISTS idx_carbon_records_category ON carbon_records(category);

-- =========================================================
-- 11. CONSUMOS OPERATIVOS
-- =========================================================

CREATE TABLE IF NOT EXISTS fuel_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    vehicle_name VARCHAR(160),
    vehicle_plate VARCHAR(40),
    fuel_type VARCHAR(80), -- diesel, gasolina, electrico, etc.
    liters NUMERIC(12, 3) CHECK (liters >= 0),
    kilometers NUMERIC(12, 3) CHECK (kilometers >= 0),
    trips INTEGER DEFAULT 1,
    recorded_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS energy_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    source VARCHAR(100), -- red electrica, generador, solar, etc.
    kwh NUMERIC(12, 3) CHECK (kwh >= 0),
    hours_used NUMERIC(12, 2),
    notes TEXT,
    recorded_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS water_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    source VARCHAR(100),
    liters NUMERIC(14, 3) NOT NULL CHECK (liters >= 0),
    usage_type VARCHAR(120), -- banos, limpieza, hidratacion, etc.
    notes TEXT,
    recorded_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =========================================================
-- 12. ENCUESTAS GOOGLE FORMS / GOOGLE SHEETS
-- =========================================================

CREATE TABLE IF NOT EXISTS surveys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    title VARCHAR(180) NOT NULL,
    description TEXT,
    google_form_url TEXT,
    google_sheet_url TEXT,
    status survey_status NOT NULL DEFAULT 'DRAFT',
    opens_at TIMESTAMP,
    closes_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS survey_imports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    survey_id UUID NOT NULL REFERENCES surveys(id) ON DELETE CASCADE,
    file_url TEXT,
    imported_rows INTEGER DEFAULT 0,
    imported_by UUID REFERENCES users(id) ON DELETE SET NULL,
    imported_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS survey_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    survey_id UUID NOT NULL REFERENCES surveys(id) ON DELETE CASCADE,
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    zone_id UUID REFERENCES event_zones(id) ON DELETE SET NULL,
    response_external_id VARCHAR(180),
    response_date TIMESTAMP,
    age_range VARCHAR(80),
    origin_commune VARCHAR(120),
    transport_mode VARCHAR(120),
    cleanliness_rating NUMERIC(4, 2),
    bathroom_rating NUMERIC(4, 2),
    recycling_visibility VARCHAR(80),
    separated_waste BOOLEAN,
    general_rating NUMERIC(4, 2),
    would_recommend BOOLEAN,
    main_problem VARCHAR(160),
    comments TEXT,
    raw_data JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_survey_responses_survey_id ON survey_responses(survey_id);
CREATE INDEX IF NOT EXISTS idx_survey_responses_event_id ON survey_responses(event_id);
CREATE INDEX IF NOT EXISTS idx_survey_responses_zone_id ON survey_responses(zone_id);

-- =========================================================
-- 13. ALERTAS GENERADAS DESDE ENCUESTAS O SISTEMA
-- =========================================================

CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    zone_id UUID REFERENCES event_zones(id) ON DELETE SET NULL,
    title VARCHAR(180) NOT NULL,
    description TEXT,
    alert_type VARCHAR(100),
    priority priority_level NOT NULL DEFAULT 'MEDIUM',
    status VARCHAR(80) NOT NULL DEFAULT 'OPEN',
    generated_from VARCHAR(80), -- SURVEY, INCIDENT, TASK, MANUAL
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alerts_event_id ON alerts(event_id);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);

-- =========================================================
-- 14. REPORTES PDF
-- =========================================================

CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    title VARCHAR(180) NOT NULL,
    summary TEXT,
    pdf_url TEXT,
    status report_status NOT NULL DEFAULT 'DRAFT',
    generated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    generated_at TIMESTAMP,
    delivered_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reports_event_id ON reports(event_id);
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);

-- =========================================================
-- 15. VISTAS PARA DASHBOARD
-- =========================================================

CREATE OR REPLACE VIEW event_task_summary
WITH (security_invoker = true) AS
SELECT
    e.id AS event_id,
    COUNT(t.id) AS total_tasks,
    COUNT(*) FILTER (WHERE t.status = 'PENDING') AS pending_tasks,
    COUNT(*) FILTER (WHERE t.status = 'IN_PROGRESS') AS in_progress_tasks,
    COUNT(*) FILTER (WHERE t.status = 'COMPLETED') AS completed_tasks,
    COUNT(*) FILTER (WHERE t.status = 'OBSERVED') AS observed_tasks,
    COUNT(*) FILTER (WHERE t.status = 'CANCELLED') AS cancelled_tasks
FROM events e
LEFT JOIN tasks t ON t.event_id = e.id
GROUP BY e.id;

CREATE OR REPLACE VIEW event_incident_summary
WITH (security_invoker = true) AS
SELECT
    e.id AS event_id,
    COUNT(i.id) AS total_incidents,
    COUNT(*) FILTER (WHERE i.status IN ('REPORTED','ASSIGNED','IN_PROGRESS')) AS open_incidents,
    COUNT(*) FILTER (WHERE i.status IN ('RESOLVED','CLOSED')) AS resolved_incidents,
    COUNT(*) FILTER (WHERE i.priority = 'CRITICAL') AS critical_incidents
FROM events e
LEFT JOIN incidents i ON i.event_id = e.id
GROUP BY e.id;

CREATE OR REPLACE VIEW event_waste_summary
WITH (security_invoker = true) AS
SELECT
    e.id AS event_id,
    COALESCE(SUM(w.weight_kg), 0) AS total_waste_kg,
    COALESCE(SUM(w.weight_kg) FILTER (WHERE w.destination IN ('RECYCLING','COMPOSTING','RECOVERY')), 0) AS recovered_waste_kg,
    COALESCE(SUM(w.weight_kg) FILTER (WHERE w.destination = 'LANDFILL'), 0) AS landfill_waste_kg,
    CASE
        WHEN COALESCE(SUM(w.weight_kg), 0) = 0 THEN 0
        ELSE ROUND((SUM(w.weight_kg) FILTER (WHERE w.destination IN ('RECYCLING','COMPOSTING','RECOVERY')) / SUM(w.weight_kg)) * 100, 2)
    END AS recovery_percentage
FROM events e
LEFT JOIN waste_records w ON w.event_id = e.id
GROUP BY e.id;

CREATE OR REPLACE VIEW event_carbon_summary
WITH (security_invoker = true) AS
SELECT
    e.id AS event_id,
    COALESCE(SUM(c.emissions_kgco2e), 0) AS total_kgco2e,
    ROUND(COALESCE(SUM(c.emissions_kgco2e), 0) / 1000, 4) AS total_tco2e,
    CASE
        WHEN COALESCE(e.real_attendees, e.estimated_attendees, 0) = 0 THEN 0
        ELSE ROUND(COALESCE(SUM(c.emissions_kgco2e), 0) / COALESCE(e.real_attendees, e.estimated_attendees), 4)
    END AS kgco2e_per_attendee
FROM events e
LEFT JOIN carbon_records c ON c.event_id = e.id
GROUP BY e.id, e.real_attendees, e.estimated_attendees;

CREATE OR REPLACE VIEW event_survey_summary
WITH (security_invoker = true) AS
SELECT
    e.id AS event_id,
    COUNT(sr.id) AS total_responses,
    ROUND(AVG(sr.cleanliness_rating), 2) AS avg_cleanliness_rating,
    ROUND(AVG(sr.bathroom_rating), 2) AS avg_bathroom_rating,
    ROUND(AVG(sr.general_rating), 2) AS avg_general_rating,
    COUNT(*) FILTER (WHERE sr.would_recommend = TRUE) AS would_recommend_count,
    CASE
        WHEN COUNT(sr.id) = 0 THEN 0
        ELSE ROUND((COUNT(*) FILTER (WHERE sr.would_recommend = TRUE)::NUMERIC / COUNT(sr.id)) * 100, 2)
    END AS recommendation_percentage
FROM events e
LEFT JOIN survey_responses sr ON sr.event_id = e.id
GROUP BY e.id;

-- =========================================================
-- 16. DATOS INICIALES RECOMENDADOS
-- =========================================================

INSERT INTO services (name, category, description, unit, is_active)
VALUES
('Baños químicos', 'Sanitario', 'Instalación y mantención de baños químicos para eventos.', 'unidad', TRUE),
('Limpieza general', 'Sanitario', 'Servicio de limpieza antes, durante y después del evento.', 'jornada', TRUE),
('Gestión de residuos', 'Ambiental', 'Separación, retiro y disposición de residuos del evento.', 'servicio', TRUE),
('Puntos limpios', 'Ambiental', 'Instalación de puntos limpios para reciclaje.', 'unidad', TRUE),
('Retiro de residuos', 'Ambiental', 'Retiro programado de residuos desde el recinto.', 'viaje', TRUE),
('Informe ambiental', 'Reporte', 'Informe final con indicadores ambientales y sanitarios.', 'informe', TRUE),
('Huella de carbono', 'Sustentabilidad', 'Cálculo estimado de emisiones del evento.', 'informe', TRUE),
('Encuesta asistentes', 'Experiencia', 'Formulario QR para recopilar opinión de asistentes.', 'servicio', TRUE)
ON CONFLICT DO NOTHING;

INSERT INTO waste_types (name, description, is_recyclable)
VALUES
('Plástico', 'Botellas, vasos y envases plásticos.', TRUE),
('Cartón y papel', 'Cartón, papel y material similar.', TRUE),
('Vidrio', 'Botellas y envases de vidrio.', TRUE),
('Aluminio', 'Latas y materiales de aluminio.', TRUE),
('Orgánico', 'Restos de alimentos y residuos compostables.', TRUE),
('General no reciclable', 'Residuos no valorizables enviados a disposición final.', FALSE),
('Peligroso', 'Residuos que requieren disposición especial.', FALSE)
ON CONFLICT (name) DO NOTHING;

-- Factores de emisión de ejemplo. Deben reemplazarse por factores oficiales según país, año y metodología.
INSERT INTO carbon_factors (category, name, unit, factor_kgco2e, scope, source, year, country, is_active)
VALUES
('Transporte', 'Diésel - combustión móvil', 'litro', 2.680000, 'SCOPE_1', 'Factor referencial. Reemplazar por fuente oficial.', 2026, 'Chile', TRUE),
('Transporte', 'Gasolina - combustión móvil', 'litro', 2.310000, 'SCOPE_1', 'Factor referencial. Reemplazar por fuente oficial.', 2026, 'Chile', TRUE),
('Energía', 'Electricidad red', 'kWh', 0.300000, 'SCOPE_2', 'Factor referencial. Reemplazar por fuente oficial.', 2026, 'Chile', TRUE),
('Residuos', 'Residuos a relleno sanitario', 'kg', 0.450000, 'SCOPE_3', 'Factor referencial. Reemplazar por fuente oficial.', 2026, 'Chile', TRUE),
('Residuos', 'Reciclaje cartón/papel', 'kg', 0.050000, 'SCOPE_3', 'Factor referencial. Reemplazar por fuente oficial.', 2026, 'Chile', TRUE),
('Residuos', 'Compostaje orgánicos', 'kg', 0.080000, 'SCOPE_3', 'Factor referencial. Reemplazar por fuente oficial.', 2026, 'Chile', TRUE)
ON CONFLICT DO NOTHING;

-- =========================================================
-- 17. ROW LEVEL SECURITY
-- =========================================================

CREATE OR REPLACE FUNCTION app_current_user_id()
RETURNS UUID
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT NULLIF(current_setting('app.current_user_id', TRUE), '')::UUID
$$;

CREATE OR REPLACE FUNCTION app_current_client_id()
RETURNS UUID
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT NULLIF(current_setting('app.current_client_id', TRUE), '')::UUID
$$;

CREATE OR REPLACE FUNCTION app_current_role()
RETURNS TEXT
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT NULLIF(current_setting('app.current_role', TRUE), '')
$$;

CREATE OR REPLACE FUNCTION app_is_admin()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT app_current_role() IN ('SUPER_ADMIN', 'ADMIN')
$$;

CREATE OR REPLACE FUNCTION app_is_authenticated()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT app_current_user_id() IS NOT NULL
$$;

CREATE OR REPLACE FUNCTION app_can_access_client(client_uuid UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT
        app_is_admin()
        OR (
            app_current_role() = 'CLIENT'
            AND app_current_client_id() = client_uuid
        )
$$;

CREATE OR REPLACE FUNCTION app_can_view_event(event_uuid UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM events e
        WHERE e.id = event_uuid
          AND (
            app_is_admin()
            OR (
                app_current_role() = 'CLIENT'
                AND app_current_client_id() = e.client_id
            )
            OR (
                app_current_role() IN ('SUPERVISOR', 'WORKER')
                AND e.status <> 'QUOTE'
                AND e.hidden_from_operations = FALSE
                AND (
                    EXISTS (
                        SELECT 1
                        FROM event_staff es
                        WHERE es.event_id = e.id
                          AND es.user_id = app_current_user_id()
                    )
                    OR EXISTS (
                        SELECT 1
                        FROM tasks t
                        WHERE t.event_id = e.id
                          AND t.assigned_to = app_current_user_id()
                    )
                )
            )
          )
    )
$$;

CREATE OR REPLACE FUNCTION app_can_manage_reference_data()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT app_is_admin()
$$;

ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE event_zones ENABLE ROW LEVEL SECURITY;
ALTER TABLE event_services ENABLE ROW LEVEL SECURITY;
ALTER TABLE event_staff ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE incidents ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidences ENABLE ROW LEVEL SECURITY;
ALTER TABLE waste_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE carbon_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE fuel_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE energy_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE water_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE surveys ENABLE ROW LEVEL SECURITY;
ALTER TABLE survey_imports ENABLE ROW LEVEL SECURITY;
ALTER TABLE survey_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE services ENABLE ROW LEVEL SECURITY;
ALTER TABLE waste_types ENABLE ROW LEVEL SECURITY;
ALTER TABLE carbon_factors ENABLE ROW LEVEL SECURITY;

CREATE POLICY clients_rls ON clients
    FOR ALL
    USING (app_is_admin() OR (app_current_role() = 'CLIENT' AND id = app_current_client_id()))
    WITH CHECK (app_is_admin() OR (app_current_role() = 'CLIENT' AND id = app_current_client_id()));

CREATE POLICY users_read_rls ON users
    FOR SELECT
    USING (
        app_current_user_id() IS NULL
        OR app_is_admin()
        OR id = app_current_user_id()
        OR (
            app_current_role() = 'SUPERVISOR'
            AND role IN ('SUPERVISOR', 'WORKER', 'LOGISTICS_OPERATOR')
            AND is_active = TRUE
        )
    );

CREATE POLICY users_write_rls ON users
    FOR ALL
    USING (app_is_admin())
    WITH CHECK (app_is_admin());

CREATE POLICY users_self_update_rls ON users
    FOR UPDATE
    USING (id = app_current_user_id())
    WITH CHECK (id = app_current_user_id());

CREATE POLICY events_rls ON events
    FOR ALL
    USING (
        app_is_admin()
        OR (
            app_current_role() = 'CLIENT'
            AND app_current_client_id() = client_id
        )
        OR (
            app_current_role() IN ('SUPERVISOR', 'WORKER', 'LOGISTICS_OPERATOR')
            AND status <> 'QUOTE'
            AND hidden_from_operations = FALSE
            AND (
                EXISTS (
                    SELECT 1
                    FROM event_staff es
                    WHERE es.event_id = events.id
                      AND es.user_id = app_current_user_id()
                )
                OR EXISTS (
                    SELECT 1
                    FROM tasks t
                    WHERE t.event_id = events.id
                      AND t.assigned_to = app_current_user_id()
                )
            )
        )
    )
    WITH CHECK (app_is_admin() OR app_can_access_client(client_id));

CREATE POLICY event_zones_rls ON event_zones
    FOR ALL
    USING (app_can_view_event(event_id))
    WITH CHECK (app_can_view_event(event_id));

CREATE POLICY event_services_rls ON event_services
    FOR ALL
    USING (app_can_view_event(event_id))
    WITH CHECK (app_can_view_event(event_id));

CREATE POLICY event_staff_rls ON event_staff
    FOR ALL
    USING (app_can_view_event(event_id) OR user_id = app_current_user_id())
    WITH CHECK (app_can_view_event(event_id));

CREATE POLICY tasks_rls ON tasks
    FOR ALL
    USING (app_can_view_event(event_id) OR assigned_to = app_current_user_id())
    WITH CHECK (app_can_view_event(event_id));

CREATE POLICY incidents_rls ON incidents
    FOR ALL
    USING (
        app_can_view_event(event_id)
        OR reported_by = app_current_user_id()
        OR assigned_to = app_current_user_id()
    )
    WITH CHECK (app_can_view_event(event_id));

CREATE POLICY evidences_rls ON evidences
    FOR ALL
    USING (app_can_view_event(event_id) OR uploaded_by = app_current_user_id())
    WITH CHECK (app_can_view_event(event_id) OR uploaded_by = app_current_user_id());

CREATE POLICY waste_records_rls ON waste_records
    FOR ALL
    USING (app_can_view_event(event_id) OR recorded_by = app_current_user_id())
    WITH CHECK (app_can_view_event(event_id) OR recorded_by = app_current_user_id());

CREATE POLICY carbon_records_rls ON carbon_records
    FOR ALL
    USING (app_can_view_event(event_id) OR recorded_by = app_current_user_id())
    WITH CHECK (app_can_view_event(event_id) OR recorded_by = app_current_user_id());

CREATE POLICY fuel_records_rls ON fuel_records
    FOR ALL
    USING (app_can_view_event(event_id) OR recorded_by = app_current_user_id())
    WITH CHECK (app_can_view_event(event_id) OR recorded_by = app_current_user_id());

CREATE POLICY energy_records_rls ON energy_records
    FOR ALL
    USING (app_can_view_event(event_id) OR recorded_by = app_current_user_id())
    WITH CHECK (app_can_view_event(event_id) OR recorded_by = app_current_user_id());

CREATE POLICY water_records_rls ON water_records
    FOR ALL
    USING (app_can_view_event(event_id) OR recorded_by = app_current_user_id())
    WITH CHECK (app_can_view_event(event_id) OR recorded_by = app_current_user_id());

CREATE POLICY surveys_rls ON surveys
    FOR ALL
    USING (app_can_view_event(event_id))
    WITH CHECK (app_can_view_event(event_id));

CREATE POLICY survey_imports_rls ON survey_imports
    FOR ALL
    USING (
        EXISTS (
            SELECT 1
            FROM surveys s
            WHERE s.id = survey_id
              AND app_can_view_event(s.event_id)
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1
            FROM surveys s
            WHERE s.id = survey_id
              AND app_can_view_event(s.event_id)
        )
    );

CREATE POLICY survey_responses_rls ON survey_responses
    FOR ALL
    USING (app_can_view_event(event_id))
    WITH CHECK (app_can_view_event(event_id));

CREATE POLICY alerts_rls ON alerts
    FOR ALL
    USING (app_can_view_event(event_id))
    WITH CHECK (app_can_view_event(event_id));

CREATE POLICY reports_rls ON reports
    FOR ALL
    USING (app_can_view_event(event_id))
    WITH CHECK (app_can_view_event(event_id));

CREATE POLICY audit_logs_rls ON audit_logs
    FOR ALL
    USING (
        app_is_admin()
        OR user_id = app_current_user_id()
        OR (client_id IS NOT NULL AND app_can_access_client(client_id))
        OR (event_id IS NOT NULL AND app_can_view_event(event_id))
    )
    WITH CHECK (
        app_is_authenticated()
        OR module = 'auth'
    );

CREATE POLICY services_read_rls ON services
    FOR SELECT
    USING (app_is_authenticated());

CREATE POLICY services_write_rls ON services
    FOR ALL
    USING (app_can_manage_reference_data())
    WITH CHECK (app_can_manage_reference_data());

CREATE POLICY waste_types_read_rls ON waste_types
    FOR SELECT
    USING (app_is_authenticated());

CREATE POLICY waste_types_write_rls ON waste_types
    FOR ALL
    USING (app_can_manage_reference_data())
    WITH CHECK (app_can_manage_reference_data());

CREATE POLICY carbon_factors_read_rls ON carbon_factors
    FOR SELECT
    USING (app_is_authenticated());

CREATE POLICY carbon_factors_write_rls ON carbon_factors
    FOR ALL
    USING (app_can_manage_reference_data())
    WITH CHECK (app_can_manage_reference_data());

-- =========================================================
-- FIN DEL SCRIPT
-- =========================================================
