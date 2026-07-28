-- Read-only RLS/runtime-role diagnostic. Run with psql using the runtime URL.
select current_user, session_user, r.rolsuper, r.rolbypassrls, r.rolinherit
from pg_roles r where r.rolname = current_user;
select roleid::regrole as inherited_role from pg_auth_members where member = current_user::regrole;
select n.nspname, c.relname, pg_get_userbyid(c.relowner) owner, c.relrowsecurity, c.relforcerowsecurity
from pg_class c join pg_namespace n on n.oid=c.relnamespace
where n.nspname='public' and c.relkind='r' order by c.relname;
select schemaname, tablename, policyname, roles, cmd, qual, with_check
from pg_policies where schemaname='public' order by tablename, policyname;
select table_name, privilege_type from information_schema.role_table_grants
where grantee=current_user and privilege_type in ('TRIGGER','REFERENCES','TRUNCATE') order by table_name;
select c.relname as sensitive_table_without_rls from pg_class c join pg_namespace n on n.oid=c.relnamespace
where n.nspname='public' and c.relkind='r' and not c.relrowsecurity
and c.relname in ('users','clients','events','evidences','logistics_evidences','form_responses','reports','logbook_evidences');
