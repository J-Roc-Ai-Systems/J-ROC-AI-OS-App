-- J-ROC AI platform agent persistence.
-- Apply with a trusted backend migration role. Clients must never receive the service_role key.
-- All application access to these tables is through the authenticated platform backend.

create table if not exists public.platform_agent_definitions (
  agent_id text not null,
  agent_version text not null,
  lifecycle_state text not null check (lifecycle_state in ('specified','registered','available','degraded','disabled','retired')),
  manifest jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (agent_id, agent_version)
);

create table if not exists public.platform_agent_audit_events (
  event_id uuid primary key default gen_random_uuid(),
  event_type text not null,
  request_id text,
  agent_id text,
  agent_version text,
  tenant_id text,
  principal_id text,
  capability text,
  approval_id uuid,
  result_status text,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists platform_agent_audit_tenant_created_idx
  on public.platform_agent_audit_events (tenant_id, created_at desc);
create index if not exists platform_agent_audit_request_idx
  on public.platform_agent_audit_events (request_id);

create or replace function public.reject_platform_agent_audit_mutation()
returns trigger
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
  raise exception 'Platform agent audit records are append-only';
end;
$$;
drop trigger if exists platform_agent_audit_immutable on public.platform_agent_audit_events;
create trigger platform_agent_audit_immutable
  before update or delete on public.platform_agent_audit_events
  for each row execute function public.reject_platform_agent_audit_mutation();

create table if not exists public.platform_agent_approvals (
  approval_id uuid primary key default gen_random_uuid(),
  tenant_id text not null,
  request_id text not null,
  agent_id text not null,
  capability text not null,
  principal_id text not null,
  approved_by text,
  status text not null default 'pending' check (status in ('pending','approved','rejected','consumed','expired')),
  reason text,
  expires_at timestamptz not null,
  consumed_at timestamptz,
  created_at timestamptz not null default now()
);
create index if not exists platform_agent_approvals_pending_idx
  on public.platform_agent_approvals (tenant_id, status, expires_at);

create or replace function public.consume_platform_agent_approval(
  p_approval_id uuid,
  p_request_id text,
  p_agent_id text,
  p_capability text,
  p_tenant_id text,
  p_principal_id text
)
returns boolean
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  was_consumed boolean := false;
begin
  with consumed as (
    update public.platform_agent_approvals
       set status = 'consumed', consumed_at = clock_timestamp()
     where approval_id = p_approval_id
       and request_id = p_request_id
       and agent_id = p_agent_id
       and capability = p_capability
       and tenant_id = p_tenant_id
       and principal_id = p_principal_id
       and status = 'approved'
       and expires_at > clock_timestamp()
    returning 1
  )
  select exists(select 1 from consumed) into was_consumed;
  return was_consumed;
end;
$$;

create table if not exists public.platform_agent_idempotency (
  tenant_id text not null,
  idempotency_key text not null,
  request_fingerprint text not null,
  state text not null check (state in ('running','completed','failed')),
  response jsonb,
  error_code text,
  lease_expires_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (tenant_id, idempotency_key)
);
create index if not exists platform_agent_idempotency_expiry_idx
  on public.platform_agent_idempotency (state, lease_expires_at);

create or replace function public.claim_platform_agent_idempotency(
  p_tenant_id text,
  p_idempotency_key text,
  p_fingerprint text,
  p_lease_seconds integer default 120
)
returns table(claim_state text, cached_response jsonb)
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  current_record public.platform_agent_idempotency%rowtype;
begin
  insert into public.platform_agent_idempotency (
    tenant_id, idempotency_key, request_fingerprint, state, lease_expires_at
  ) values (
    p_tenant_id, p_idempotency_key, p_fingerprint, 'running',
    clock_timestamp() + make_interval(secs => greatest(15, least(p_lease_seconds, 3600)))
  )
  on conflict (tenant_id, idempotency_key) do nothing;

  if found then
    return query select 'acquired'::text, null::jsonb;
    return;
  end if;

  select * into current_record
    from public.platform_agent_idempotency
   where tenant_id = p_tenant_id and idempotency_key = p_idempotency_key
   for update;

  if not found then
    raise exception 'Unable to inspect idempotency reservation';
  end if;
  if current_record.request_fingerprint <> p_fingerprint then
    return query select 'conflict'::text, null::jsonb;
    return;
  end if;
  if current_record.state = 'completed' then
    return query select 'completed'::text, current_record.response;
    return;
  end if;
  if current_record.state = 'failed'
     or (current_record.state = 'running' and current_record.lease_expires_at <= clock_timestamp()) then
    update public.platform_agent_idempotency
       set state = 'running',
           response = null,
           error_code = null,
           lease_expires_at = clock_timestamp() + make_interval(secs => greatest(15, least(p_lease_seconds, 3600))),
           updated_at = clock_timestamp()
     where tenant_id = p_tenant_id and idempotency_key = p_idempotency_key;
    return query select 'acquired'::text, null::jsonb;
    return;
  end if;

  return query select 'in_progress'::text, null::jsonb;
end;
$$;

create or replace function public.complete_platform_agent_idempotency(
  p_tenant_id text,
  p_idempotency_key text,
  p_fingerprint text,
  p_response jsonb
)
returns boolean
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  was_completed boolean := false;
begin
  update public.platform_agent_idempotency
     set state = 'completed', response = p_response, error_code = null,
         lease_expires_at = null, updated_at = clock_timestamp()
   where tenant_id = p_tenant_id
     and idempotency_key = p_idempotency_key
     and request_fingerprint = p_fingerprint
     and state = 'running';
  was_completed := found;
  return was_completed;
end;
$$;

create or replace function public.fail_platform_agent_idempotency(
  p_tenant_id text,
  p_idempotency_key text,
  p_fingerprint text,
  p_error_code text
)
returns boolean
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  was_failed boolean := false;
begin
  update public.platform_agent_idempotency
     set state = 'failed', response = null, error_code = left(p_error_code, 80),
         lease_expires_at = null, updated_at = clock_timestamp()
   where tenant_id = p_tenant_id
     and idempotency_key = p_idempotency_key
     and request_fingerprint = p_fingerprint
     and state = 'running';
  was_failed := found;
  return was_failed;
end;
$$;

create table if not exists public.platform_agent_jobs (
  job_id uuid primary key default gen_random_uuid(),
  tenant_id text not null,
  request_id text not null,
  agent_id text not null,
  agent_version text not null,
  capability text not null,
  payload jsonb not null,
  state text not null default 'queued' check (state in ('queued','running','completed','failed','cancelled')),
  attempts integer not null default 0,
  max_attempts integer not null default 3,
  worker_id text,
  lease_expires_at timestamptz,
  result jsonb,
  error_code text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists platform_agent_jobs_claim_idx
  on public.platform_agent_jobs (state, created_at)
  where state in ('queued','running');

create or replace function public.claim_platform_agent_job(
  p_worker_id text,
  p_lease_seconds integer default 120
)
returns setof public.platform_agent_jobs
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
  -- A worker may crash after receiving its final attempt. Close that lease
  -- instead of leaving a permanently running job that can never be claimed.
  update public.platform_agent_jobs
     set state = 'failed',
         error_code = coalesce(error_code, 'MAX_ATTEMPTS_EXCEEDED'),
         lease_expires_at = null,
         updated_at = clock_timestamp()
   where state = 'running'
     and attempts >= max_attempts
     and lease_expires_at <= clock_timestamp();

  return query
  with candidate as (
    select job_id
      from public.platform_agent_jobs
     where attempts < max_attempts
       and (state = 'queued' or (state = 'running' and lease_expires_at <= clock_timestamp()))
     order by created_at
     for update skip locked
     limit 1
  )
  update public.platform_agent_jobs as job
     set state = 'running',
         worker_id = p_worker_id,
         attempts = job.attempts + 1,
         lease_expires_at = clock_timestamp() + make_interval(secs => greatest(15, least(p_lease_seconds, 3600))),
         updated_at = clock_timestamp()
    from candidate
   where job.job_id = candidate.job_id
  returning job.*;
end;
$$;

create or replace function public.complete_platform_agent_job(
  p_job_id uuid,
  p_worker_id text,
  p_result jsonb
)
returns boolean
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  was_completed boolean := false;
begin
  update public.platform_agent_jobs
     set state = 'completed', result = p_result, error_code = null,
         lease_expires_at = null, updated_at = clock_timestamp()
   where job_id = p_job_id and worker_id = p_worker_id and state = 'running';
  was_completed := found;
  return was_completed;
end;
$$;

create or replace function public.fail_platform_agent_job(
  p_job_id uuid,
  p_worker_id text,
  p_error_code text
)
returns boolean
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  was_failed boolean := false;
begin
  update public.platform_agent_jobs
     set state = case when attempts >= max_attempts then 'failed' else 'queued' end,
         error_code = left(p_error_code, 80),
         lease_expires_at = null,
         updated_at = clock_timestamp()
   where job_id = p_job_id and worker_id = p_worker_id and state = 'running';
  was_failed := found;
  return was_failed;
end;
$$;

-- These tables are server-side only. RLS is enabled and no client role receives table privileges.
alter table public.platform_agent_definitions enable row level security;
alter table public.platform_agent_audit_events enable row level security;
alter table public.platform_agent_approvals enable row level security;
alter table public.platform_agent_idempotency enable row level security;
alter table public.platform_agent_jobs enable row level security;

revoke all on public.platform_agent_definitions from public, anon, authenticated;
revoke all on public.platform_agent_audit_events from public, anon, authenticated;
revoke all on public.platform_agent_approvals from public, anon, authenticated;
revoke all on public.platform_agent_idempotency from public, anon, authenticated;
revoke all on public.platform_agent_jobs from public, anon, authenticated;

grant select, insert, update, delete on public.platform_agent_definitions to service_role;
grant select, insert on public.platform_agent_audit_events to service_role;
grant select, insert, update on public.platform_agent_approvals to service_role;
grant select, insert, update, delete on public.platform_agent_idempotency to service_role;
grant select, insert, update, delete on public.platform_agent_jobs to service_role;

revoke all on function public.consume_platform_agent_approval(uuid,text,text,text,text,text) from public, anon, authenticated;
revoke all on function public.claim_platform_agent_idempotency(text,text,text,integer) from public, anon, authenticated;
revoke all on function public.complete_platform_agent_idempotency(text,text,text,jsonb) from public, anon, authenticated;
revoke all on function public.fail_platform_agent_idempotency(text,text,text,text) from public, anon, authenticated;
revoke all on function public.claim_platform_agent_job(text,integer) from public, anon, authenticated;
revoke all on function public.complete_platform_agent_job(uuid,text,jsonb) from public, anon, authenticated;
revoke all on function public.fail_platform_agent_job(uuid,text,text) from public, anon, authenticated;

grant execute on function public.consume_platform_agent_approval(uuid,text,text,text,text,text) to service_role;
grant execute on function public.claim_platform_agent_idempotency(text,text,text,integer) to service_role;
grant execute on function public.complete_platform_agent_idempotency(text,text,text,jsonb) to service_role;
grant execute on function public.fail_platform_agent_idempotency(text,text,text,text) to service_role;
grant execute on function public.claim_platform_agent_job(text,integer) to service_role;
grant execute on function public.complete_platform_agent_job(uuid,text,jsonb) to service_role;
grant execute on function public.fail_platform_agent_job(uuid,text,text) to service_role;
