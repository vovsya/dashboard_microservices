CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS monitors (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  url TEXT NOT NULL UNIQUE,
  interval_minutes INT NOT NULL CHECK (interval_minutes > 0),

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  next_check_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  last_checked_at TIMESTAMPTZ,
  last_text_hash TEXT,
  last_text TEXT
);

CREATE INDEX IF NOT EXISTS idx_monitors_next_check ON monitors(next_check_at);

CREATE TABLE IF NOT EXISTS changes (
  id BIGSERIAL PRIMARY KEY,
  monitor_id UUID NOT NULL REFERENCES monitors(id) ON DELETE CASCADE,
  checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  diff TEXT NOT NULL,
  summary TEXT
);

CREATE INDEX IF NOT EXISTS idx_changes_monitor_time ON changes(monitor_id, checked_at DESC);
