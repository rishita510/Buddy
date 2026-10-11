-- Final database schema for the YouTube RAG Chat app.
-- Run once in the Supabase SQL editor for a NEW project.
-- (An existing project that already ran the individual migrations is up to date.)
--
-- Security note: the app talks to Supabase with the SERVICE key, which bypasses
-- Row Level Security, so per-user isolation is enforced in application code
-- (every query is filtered by user_id). Enable RLS and add policies before
-- letting any client call Supabase directly with the anon key.

create extension if not exists vector;

-- Videos: one row per ingested YouTube video, shared by all users.
-- status tracks ingestion: processing -> ready, or failed (retryable).
create table if not exists videos (
  id text primary key,                      -- YouTube video id
  title text,
  status text not null default 'processing'
    check (status in ('processing', 'ready', 'failed')),
  status_updated_at timestamptz not null default now(),
  ingested_at timestamptz default now()
);

-- Chunks: transcript pieces, shared by all users of a video.
create table if not exists chunks (
  id bigserial primary key,
  video_id text not null,
  content text not null,                    -- original transcript text
  content_en text,                          -- English translation (used for retrieval + answering)
  start_time float not null,                -- seconds into the video where the chunk starts
  embedding vector(1536)                    -- text-embedding-3-small, computed from content_en
);
create index if not exists chunks_video_id_idx on chunks (video_id);

-- Threads: one conversation, owned by one user, about one video.
create table if not exists threads (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id),
  video_id text not null,
  title text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create index if not exists threads_video_id_idx on threads (video_id);
create index if not exists threads_user_id_idx on threads (user_id);

-- Messages: the turns of a thread. Deleting a thread deletes its messages.
create table if not exists messages (
  id bigserial primary key,
  thread_id uuid references threads(id) on delete cascade,
  role text not null,                       -- 'user' or 'assistant'
  content text not null,
  created_at timestamptz default now()
);
create index if not exists messages_thread_id_idx on messages (thread_id);

-- Similarity search over one video's chunks (cosine distance via pgvector).
create or replace function match_chunks (
  query_embedding vector(1536),
  match_video_id text,
  match_count int default 5
)
returns table (
  id bigint,
  content text,
  content_en text,
  start_time float,
  similarity float
)
language sql stable
as $$
  select
    id,
    content,
    content_en,
    start_time,
    1 - (embedding <=> query_embedding) as similarity
  from chunks
  where video_id = match_video_id
  order by embedding <=> query_embedding
  limit match_count;
$$;