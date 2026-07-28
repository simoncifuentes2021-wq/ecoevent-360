-- SOLO LECTURA. Ejecutar manualmente en Supabase si se desea verificar el incidente local.
-- Ventana aproximada: 2026-07-27, durante la ejecución de pytest de certificación.
select id, email, full_name, created_at from users
where email like 'comparison-%@example.com'
   or email like 'comparison-admin-%@example.com'
   or email like 'comparison-supervisor-%@example.com'
   or email like 'comparison-client-%@example.com'
order by created_at desc;

select id, business_name, contact_email, created_at from clients
where business_name like 'Comparison Client %'
   or contact_email like 'comparison-%@example.com'
order by created_at desc;

select e.id, e.name, e.client_id, e.created_at from events e
where e.name like 'Comparison Event %'
order by e.created_at desc;

select f.id, f.name, f.event_id, f.created_at from event_forms f
where f.public_slug like 'comparison-%'
order by f.created_at desc;

select r.id, r.form_id, r.event_id, r.submitted_at
from form_responses r join event_forms f on f.id=r.form_id
where f.public_slug like 'comparison-%'
order by r.submitted_at desc;

-- También pudieron ejecutarse los dos fixtures de portal anteriores al fallo observado.
select id, email, full_name, created_at from users
where email like 'portal-%@example.com' order by created_at desc;
select id, business_name, contact_email, created_at from clients
where business_name like 'Portal Client %' or contact_email like 'portal-%@example.com'
order by created_at desc;
-- No hay DELETE en este archivo. Revisar relaciones antes de proponer una limpieza transaccional.
