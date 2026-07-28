-- DAILYLOOK.SM v10 — ชื่อ + PIN ส่วนตัว และประวัติแยกรายบุคคล
-- รันไฟล์นี้ใน Supabase SQL Editor หนึ่งครั้ง

create extension if not exists pgcrypto;

create table if not exists public.team_members (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  pin_hash text not null,
  role text not null default 'member' check (role in ('admin', 'member')),
  active boolean not null default true,
  created_at timestamptz not null default now()
);

alter table public.team_members enable row level security;
revoke all on table public.team_members from anon;

create or replace function public.list_team_members()
returns table(id uuid, name text, role text)
language sql
security definer
set search_path = public
as $$
  select tm.id, tm.name, tm.role
  from public.team_members tm
  where tm.active = true
  order by tm.name;
$$;

create or replace function public.verify_team_member_pin(member_id uuid, member_pin text)
returns table(id uuid, name text, role text)
language sql
security definer
set search_path = public
as $$
  select tm.id, tm.name, tm.role
  from public.team_members tm
  where tm.id = member_id
    and tm.active = true
    and tm.pin_hash = crypt(member_pin, tm.pin_hash);
$$;

create or replace function public.create_team_member(
  member_name text,
  member_pin text,
  member_role text default 'member'
)
returns table(id uuid, name text, role text)
language plpgsql
security definer
set search_path = public
as $$
begin
  if length(trim(member_name)) = 0 then
    raise exception 'กรุณาใส่ชื่อ';
  end if;
  if member_pin !~ '^[0-9]{4,8}$' then
    raise exception 'PIN ต้องเป็นตัวเลข 4–8 หลัก';
  end if;
  if member_role not in ('admin', 'member') then
    raise exception 'สิทธิ์ไม่ถูกต้อง';
  end if;
  return query
  insert into public.team_members(name, pin_hash, role)
  values (trim(member_name), crypt(member_pin, gen_salt('bf')), member_role)
  returning team_members.id, team_members.name, team_members.role;
end;
$$;

create or replace function public.change_team_member_pin(
  member_id uuid,
  new_pin text
)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
begin
  if new_pin !~ '^[0-9]{4,8}$' then
    raise exception 'PIN ต้องเป็นตัวเลข 4–8 หลัก';
  end if;
  update public.team_members
  set pin_hash = crypt(new_pin, gen_salt('bf'))
  where id = member_id and active = true;
  return found;
end;
$$;

grant execute on function public.list_team_members() to anon;
grant execute on function public.verify_team_member_pin(uuid, text) to anon;
grant execute on function public.create_team_member(text, text, text) to anon;
grant execute on function public.change_team_member_pin(uuid, text) to anon;

-- ให้ events/audit_logs อ้างอิงผู้ใช้งาน v10 ได้ โดยไม่บังคับ FK จากระบบ Auth เดิม
alter table public.events drop constraint if exists events_created_by_fkey;
alter table public.events drop constraint if exists events_updated_by_fkey;
alter table public.people drop constraint if exists people_created_by_fkey;
alter table public.audit_logs drop constraint if exists audit_logs_actor_id_fkey;

select 'DAILYLOOK.SM v10 member PIN setup complete' as result;
