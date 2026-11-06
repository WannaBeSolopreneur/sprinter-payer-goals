-- Snowflake row access policy for payer tenants.
-- dbt does not run this file on DuckDB. The demo applies the same predicate
-- in every published mart, and the export checks it again.
--
-- Internal analysts are in SPRINTER_INTERNAL_ANALYTICS and can read every payer.
-- A payer role is listed once in governance.role_payer_access.
-- The key is payer_id because that is the tenant on every published table.

create schema if not exists governance;

create or replace table governance.role_payer_access (
    role_name varchar,
    payer_id varchar
);

-- Example grants. Load these from the app. Do not hard-code a real payer.
-- insert into governance.role_payer_access values
--     ('HARBORLINE_ANALYST', 'payer_harborline'),
--     ('NORTHWIND_ANALYST', 'payer_northwind');

create or replace row access policy governance.payer_tenant_isolation
as (payer_id varchar) returns boolean ->
    is_role_in_session('SPRINTER_INTERNAL_ANALYTICS')
    or exists (
        select 1
        from governance.role_payer_access as access
        where access.role_name = current_role()
          and access.payer_id = payer_id
    );

-- Apply the policy to every customer-facing table that carries payer_id.
-- alter table marts.fct_visits
--   add row access policy governance.payer_tenant_isolation on (payer_id);
-- alter table marts.fct_members
--   add row access policy governance.payer_tenant_isolation on (payer_id);
-- alter table marts.fct_completed_visits
--   add row access policy governance.payer_tenant_isolation on (payer_id);
-- alter table marts.fct_terminal_visits
--   add row access policy governance.payer_tenant_isolation on (payer_id);
-- alter table marts.fct_care_gaps
--   add row access policy governance.payer_tenant_isolation on (payer_id);
-- alter table marts.fct_er_after_miss
--   add row access policy governance.payer_tenant_isolation on (payer_id);
-- alter table marts.mart_goal_status
--   add row access policy governance.payer_tenant_isolation on (payer_id);
-- alter table marts.mart_visit_pace
--   add row access policy governance.payer_tenant_isolation on (payer_id);
-- alter table marts.mart_weekly_trend
--   add row access policy governance.payer_tenant_isolation on (payer_id);
-- alter table marts.mart_actions_this_week
--   add row access policy governance.payer_tenant_isolation on (payer_id);

-- The page states the predicate in SQL so a reader can see why a row is in or out.
-- The policy is the backstop. Do not give a payer role a bypass.
