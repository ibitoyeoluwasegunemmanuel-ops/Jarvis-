-- JARVIS core schema, PostgreSQL 15+
-- Apply through a migration runner using a privileged migration role.
-- Runtime access must use authenticated identities and workspace-scoped RLS.

create extension if not exists pgcrypto;

create table if not exists workspaces (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  owner_id text not null,
  created_at timestamptz not null default now()
);

create table if not exists projects (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  name text not null,
  description text not null default '',
  status text not null default 'active' check (status in ('active','paused','completed','archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists projects_workspace_idx on projects(workspace_id, updated_at desc);

create table if not exists project_tasks (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  project_id uuid not null references projects(id) on delete cascade,
  title text not null,
  description text not null default '',
  status text not null default 'todo' check (status in ('todo','in_progress','blocked','done','cancelled')),
  priority text not null default 'normal' check (priority in ('low','normal','high','critical')),
  due_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists project_tasks_project_idx on project_tasks(project_id, status);

create table if not exists project_decisions (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  project_id uuid not null references projects(id) on delete cascade,
  title text not null,
  decision text not null,
  rationale text not null default '',
  decided_by text not null,
  created_at timestamptz not null default now()
);

create table if not exists memory_items (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  project_id uuid references projects(id) on delete cascade,
  category text not null check (category in ('fact','preference','decision','note','reference')),
  content text not null,
  source text,
  confidence numeric(4,3) check (confidence between 0 and 1),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists memory_items_workspace_idx on memory_items(workspace_id, created_at desc);

create table if not exists agent_runs (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  project_id uuid references projects(id) on delete set null,
  agent_key text not null,
  task text not null,
  status text not null default 'queued' check (status in ('queued','running','succeeded','failed','cancelled')),
  started_at timestamptz,
  finished_at timestamptz,
  result_summary text,
  created_at timestamptz not null default now()
);

create table if not exists approval_requests (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references workspaces(id) on delete cascade,
  actor_id text not null,
  action_name text not null,
  action_digest text not null,
  risk_tier text not null check (risk_tier in ('external_side_effect','high_impact')),
  status text not null default 'pending' check (status in ('pending','approved','rejected','expired','consumed')),
  expires_at timestamptz not null,
  decided_at timestamptz,
  created_at timestamptz not null default now()
);
create index if not exists approval_pending_idx on approval_requests(workspace_id, status, expires_at);

create table if not exists audit_events (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references workspaces(id) on delete set null,
  actor_id text,
  event_type text not null,
  resource_type text,
  resource_id text,
  outcome text not null,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists audit_events_workspace_idx on audit_events(workspace_id, created_at desc);

-- RLS is deliberately not enabled here: the API must first establish a trusted
-- identity-to-workspace membership model. Enabling incomplete policies can
-- create a false sense of security. Do not expose these tables to anon clients.
