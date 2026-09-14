create extension if not exists pgcrypto;

create table if not exists pipeline_runs (
  id uuid primary key default gen_random_uuid(),
  source text not null,
  trigger text not null default 'manual',
  status text not null check (status in ('running', 'succeeded', 'failed')),
  config jsonb not null default '{}'::jsonb,
  fetched_count integer not null default 0,
  accepted_count integer not null default 0,
  published_count integer not null default 0,
  input_tokens bigint not null default 0,
  output_tokens bigint not null default 0,
  estimated_cost_usd numeric(12, 6) not null default 0,
  error text,
  started_at timestamptz not null default now(),
  finished_at timestamptz
);

create table if not exists raw_items (
  id bigint generated always as identity primary key,
  source text not null,
  source_item_id text not null,
  source_version integer not null default 1,
  pipeline_run_id uuid references pipeline_runs(id) on delete set null,
  payload_sha256 text not null,
  raw_payload jsonb not null,
  processing_status text not null default 'fetched',
  processing_error text,
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  unique (source, source_item_id, source_version)
);

create table if not exists papers (
  id uuid primary key default gen_random_uuid(),
  arxiv_id text not null unique,
  latest_version integer not null default 1,
  doi text unique,
  title text not null,
  abstract text not null,
  authors jsonb not null default '[]'::jsonb,
  affiliations jsonb not null default '[]'::jsonb,
  categories text[] not null default '{}',
  primary_category text,
  topics text[] not null default '{}',
  published_at timestamptz not null,
  source_updated_at timestamptz not null,
  abstract_url text not null,
  pdf_url text not null,
  source_comment text,
  geography_status text not null default 'unknown'
    check (geography_status in ('unknown', 'eligible', 'ineligible')),
  country_codes text[] not null default '{}',
  rule_relevance numeric(5, 4),
  ai_relevance numeric(5, 4),
  global_importance numeric(5, 4),
  confidence numeric(5, 4),
  processing_status text not null default 'fetched',
  processing_error text,
  source_metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists papers_published_at_idx on papers (published_at desc);
create index if not exists papers_processing_status_idx on papers (processing_status);
create index if not exists papers_topics_idx on papers using gin (topics);

create table if not exists stories (
  id uuid primary key default gen_random_uuid(),
  paper_id uuid not null unique references papers(id) on delete cascade,
  slug text not null unique,
  status text not null default 'draft' check (status in ('draft', 'published', 'failed')),
  global_importance numeric(5, 4) not null default 0,
  personal_relevance numeric(5, 4) not null default 0,
  freshness numeric(5, 4) not null default 0,
  confidence numeric(5, 4) not null default 0,
  final_score numeric(5, 4) not null default 0,
  is_exploration boolean not null default false,
  why_recommended text,
  processing_scope text,
  published_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists stories_feed_idx on stories (status, final_score desc, published_at desc);

create table if not exists story_sources (
  id uuid primary key default gen_random_uuid(),
  story_id uuid not null references stories(id) on delete cascade,
  source_type text not null,
  label text not null,
  url text not null,
  external_id text,
  is_original boolean not null default false,
  created_at timestamptz not null default now(),
  unique (story_id, url)
);

create table if not exists explanations (
  id uuid primary key default gen_random_uuid(),
  story_id uuid not null references stories(id) on delete cascade,
  language text not null default 'zh-CN',
  model text not null,
  prompt_version text not null,
  content jsonb not null,
  limitations jsonb not null default '[]'::jsonb,
  terminology jsonb not null default '[]'::jsonb,
  input_tokens integer not null default 0,
  output_tokens integer not null default 0,
  estimated_cost_usd numeric(12, 6) not null default 0,
  created_at timestamptz not null default now(),
  unique (story_id, model, prompt_version)
);

create table if not exists feedback_events (
  id uuid primary key default gen_random_uuid(),
  story_id uuid references stories(id) on delete cascade,
  event_type text not null,
  entity_type text,
  entity_id text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists preference_profile (
  id text primary key default 'owner',
  topic_affinity jsonb not null default '{}'::jsonb,
  author_affinity jsonb not null default '{}'::jsonb,
  institution_affinity jsonb not null default '{}'::jsonb,
  source_affinity jsonb not null default '{}'::jsonb,
  technical_depth numeric(5, 4) not null default 0.5,
  example_preference numeric(5, 4) not null default 0.5,
  term_familiarity jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

insert into preference_profile (id, topic_affinity)
values (
  'owner',
  '{"neuroscience":0.9,"neuroimaging":0.8,"brain-computer interfaces":0.75,"protein design":0.65,"drug discovery":0.65,"genomics":0.55,"single-cell biology":0.5,"biomedical ai":0.7}'::jsonb
)
on conflict (id) do nothing;

alter table pipeline_runs enable row level security;
alter table raw_items enable row level security;
alter table papers enable row level security;
alter table stories enable row level security;
alter table story_sources enable row level security;
alter table explanations enable row level security;
alter table feedback_events enable row level security;
alter table preference_profile enable row level security;

