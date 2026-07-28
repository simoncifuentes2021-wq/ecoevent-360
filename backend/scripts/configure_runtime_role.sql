-- Run as the database owner after replacing the two psql variables.
-- psql -v runtime_role=ecoevent_app -v runtime_password='generated-secret' -f ...
\if :{?runtime_role}
\else
\quit
\endif
create role :runtime_role login password :'runtime_password' nosuperuser nocreatedb nocreaterole noinherit nobypassrls;
select format('grant connect on database %I to %I', current_database(), :'runtime_role') \gexec
grant usage on schema public to :runtime_role;
grant select, insert, update, delete on all tables in schema public to :runtime_role;
grant usage, select on all sequences in schema public to :runtime_role;
alter default privileges in schema public grant select, insert, update, delete on tables to :runtime_role;
alter default privileges in schema public grant usage, select on sequences to :runtime_role;
-- Never grant CREATE on schema public or membership in the owner/migrator role.
