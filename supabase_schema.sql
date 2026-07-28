-- DAILYLOOK.SM shared access-code mode
-- Run once in Supabase SQL Editor after supabase_schema.sql.

alter table public.events alter column created_by drop not null;
alter table public.events alter column updated_by drop not null;
alter table public.people alter column created_by drop not null;
alter table public.audit_logs alter column actor_id drop not null;

grant usage on schema public to anon;
grant select, insert, update, delete on table
  public.events,
  public.event_people,
  public.people,
  public.audit_logs
to anon;

alter table public.events enable row level security;
alter table public.event_people enable row level security;
alter table public.people enable row level security;
alter table public.audit_logs enable row level security;

drop policy if exists "team_code_events" on public.events;
create policy "team_code_events"
on public.events for all to anon
using (true) with check (true);

drop policy if exists "team_code_event_people" on public.event_people;
create policy "team_code_event_people"
on public.event_people for all to anon
using (true) with check (true);

drop policy if exists "team_code_people" on public.people;
create policy "team_code_people"
on public.people for all to anon
using (true) with check (true);

drop policy if exists "team_code_audit_logs" on public.audit_logs;
create policy "team_code_audit_logs"
on public.audit_logs for all to anon
using (true) with check (true);
