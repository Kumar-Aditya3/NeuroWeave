-- NeuroWeave Supabase bootstrap schema
-- Run this in Supabase SQL editor.

create extension if not exists pgcrypto;
create extension if not exists pg_cron;

create table if not exists public.events_raw (
  id bigint generated always as identity primary key,
  dedupe_key text unique,
  user_id text not null,
  device_id text,
  client_name text,
  source text not null,
  event_type text not null,
  url text,
  title text,
  category text,
  duration_seconds integer,
  selected_text text,
  content_text text,
  process_name text,
  topic_scores_json jsonb,
  embedding_json jsonb,
  classifier_mode text,
  sentiment text,
  vibe text,
  created_at timestamptz not null default now(),
  received_at timestamptz not null default now()
);

create index if not exists idx_events_raw_user_created on public.events_raw(user_id, created_at desc);
create index if not exists idx_events_raw_user_device on public.events_raw(user_id, device_id);

create table if not exists public.devices_state (
  id bigint generated always as identity primary key,
  user_id text not null,
  device_id text not null,
  client_name text not null,
  last_seen_at timestamptz not null default now(),
  unique (user_id, device_id)
);

create table if not exists public.feedback_events (
  id bigint generated always as identity primary key,
  user_id text not null,
  recommendation_topic text not null,
  action text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.wallpaper_memory (
  id bigint generated always as identity primary key,
  user_id text not null,
  topic text not null,
  vibe text not null,
  style text not null,
  provider text not null,
  wallpaper_query text not null,
  wallpaper_preview_url text,
  created_at timestamptz not null default now()
);

create index if not exists idx_wallpaper_memory_user_created
on public.wallpaper_memory(user_id, created_at desc);

create table if not exists public.arc_centroids (
  id bigint generated always as identity primary key,
  user_id text not null,
  arc_name text not null,
  centroid_json jsonb not null,
  sample_count double precision not null,
  dominant_topic text,
  vibe text,
  strength double precision,
  updated_at timestamptz not null default now(),
  unique (user_id, arc_name)
);

alter table public.events_raw enable row level security;
alter table public.devices_state enable row level security;
alter table public.feedback_events enable row level security;
alter table public.wallpaper_memory enable row level security;
alter table public.arc_centroids enable row level security;

-- Application service role can bypass RLS; these policies allow future authenticated clients.
drop policy if exists events_raw_user_policy on public.events_raw;
create policy events_raw_user_policy on public.events_raw
for all
using (auth.uid()::text = user_id)
with check (auth.uid()::text = user_id);

drop policy if exists devices_state_user_policy on public.devices_state;
create policy devices_state_user_policy on public.devices_state
for all
using (auth.uid()::text = user_id)
with check (auth.uid()::text = user_id);

drop policy if exists feedback_events_user_policy on public.feedback_events;
create policy feedback_events_user_policy on public.feedback_events
for all
using (auth.uid()::text = user_id)
with check (auth.uid()::text = user_id);

drop policy if exists wallpaper_memory_user_policy on public.wallpaper_memory;
create policy wallpaper_memory_user_policy on public.wallpaper_memory
for all
using (auth.uid()::text = user_id)
with check (auth.uid()::text = user_id);

drop policy if exists arc_centroids_user_policy on public.arc_centroids;
create policy arc_centroids_user_policy on public.arc_centroids
for all
using (auth.uid()::text = user_id)
with check (auth.uid()::text = user_id);

create or replace function public.neuroweave_purge_old_data() returns void
language plpgsql
as $$
begin
  delete from public.events_raw where created_at < now() - interval '14 days';
  delete from public.wallpaper_memory where created_at < now() - interval '30 days';
  delete from public.feedback_events where created_at < now() - interval '30 days';
end;
$$;

do $$
begin
  perform cron.schedule(
    'neuroweave-purge-old-data-daily',
    '0 3 * * *',
    $job$select public.neuroweave_purge_old_data();$job$
  );
exception
  when unique_violation then
    null;
end;
$$;
