-- PHONGPAT M. Team Calendar
-- Run this file once in Supabase > SQL Editor.

create extension if not exists pgcrypto;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null default '',
  role text not null default 'member' check (role in ('admin', 'member')),
  approved boolean not null default false,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

alter table public.profiles
  add column if not exists approved boolean not null default false;

create table if not exists public.people (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  linked_user_id uuid references auth.users(id) on delete set null,
  active boolean not null default true,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now()
);

create table if not exists public.events (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  details text not null default '',
  start_date date not null,
  end_date date not null,
  start_time time,
  item_type text not null default 'task'
    check (item_type in ('task', 'info', 'holiday')),
  pin_color text not null default 'blue'
    check (pin_color in ('blue', 'green', 'orange', 'pink', 'purple', 'brown')),
  priority text not null default 'normal'
    check (priority in ('normal', 'urgent')),
  status text not null default 'not_started'
    check (status in ('not_started', 'in_progress', 'waiting', 'done')),
  created_by uuid references auth.users(id) on delete set null,
  updated_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (end_date >= start_date),
  check (item_type = 'task' or status <> 'done'),
  unique (title, start_date, end_date, item_type)
);

create table if not exists public.event_people (
  event_id uuid not null references public.events(id) on delete cascade,
  person_id uuid not null references public.people(id) on delete cascade,
  primary key (event_id, person_id)
);

create table if not exists public.audit_logs (
  id bigint generated always as identity primary key,
  event_id uuid references public.events(id) on delete set null,
  action text not null check (action in ('create', 'update', 'delete', 'status')),
  actor_id uuid references auth.users(id) on delete set null,
  actor_name text not null default '',
  changes jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists events_date_idx
  on public.events(start_date, end_date);
create index if not exists events_status_idx
  on public.events(status);
create index if not exists audit_logs_created_at_idx
  on public.audit_logs(created_at desc);

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, display_name, role, approved)
  values (
    new.id,
    coalesce(new.raw_user_meta_data ->> 'display_name', split_part(new.email, '@', 1)),
    case
      when not exists (select 1 from public.profiles) then 'admin'
      else 'member'
    end,
    not exists (select 1 from public.profiles)
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

create or replace function public.is_team_member()
returns boolean
language sql
stable
security definer set search_path = public
as $$
  select exists (
    select 1 from public.profiles
    where id = auth.uid() and approved = true and active = true
  );
$$;

create or replace function public.is_admin()
returns boolean
language sql
stable
security definer set search_path = public
as $$
  select exists (
    select 1 from public.profiles
    where id = auth.uid() and role = 'admin' and active = true
  );
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists events_set_updated_at on public.events;
create trigger events_set_updated_at
  before update on public.events
  for each row execute procedure public.set_updated_at();

alter table public.profiles enable row level security;
alter table public.people enable row level security;
alter table public.events enable row level security;
alter table public.event_people enable row level security;
alter table public.audit_logs enable row level security;

drop policy if exists "profiles_read" on public.profiles;
create policy "profiles_read" on public.profiles
  for select to authenticated using (id = auth.uid() or public.is_admin());

drop policy if exists "admin_update_profiles" on public.profiles;
create policy "admin_update_profiles" on public.profiles
  for update to authenticated using (public.is_admin())
  with check (public.is_admin());

drop policy if exists "team_read_people" on public.people;
create policy "team_read_people" on public.people
  for select to authenticated using (public.is_team_member());

drop policy if exists "team_insert_people" on public.people;
create policy "team_insert_people" on public.people
  for insert to authenticated
  with check (public.is_team_member() and created_by = auth.uid());

drop policy if exists "team_update_people" on public.people;
create policy "team_update_people" on public.people
  for update to authenticated using (public.is_team_member())
  with check (public.is_team_member());

drop policy if exists "team_read_events" on public.events;
create policy "team_read_events" on public.events
  for select to authenticated using (public.is_team_member());

drop policy if exists "team_insert_events" on public.events;
create policy "team_insert_events" on public.events
  for insert to authenticated
  with check (public.is_team_member() and created_by = auth.uid());

drop policy if exists "team_update_events" on public.events;
create policy "team_update_events" on public.events
  for update to authenticated using (public.is_team_member())
  with check (public.is_team_member() and updated_by = auth.uid());

drop policy if exists "admin_delete_events" on public.events;
create policy "admin_delete_events" on public.events
  for delete to authenticated using (public.is_admin());

drop policy if exists "team_read_event_people" on public.event_people;
create policy "team_read_event_people" on public.event_people
  for select to authenticated using (public.is_team_member());

drop policy if exists "team_manage_event_people" on public.event_people;
create policy "team_manage_event_people" on public.event_people
  for all to authenticated using (public.is_team_member())
  with check (public.is_team_member());

drop policy if exists "team_read_audit" on public.audit_logs;
create policy "team_read_audit" on public.audit_logs
  for select to authenticated using (public.is_team_member());

drop policy if exists "team_insert_audit" on public.audit_logs;
create policy "team_insert_audit" on public.audit_logs
  for insert to authenticated
  with check (public.is_team_member() and actor_id = auth.uid());

-- Make the first account an administrator after it signs up:
-- update public.profiles set role = 'admin'
-- where id = (select id from auth.users order by created_at limit 1);
