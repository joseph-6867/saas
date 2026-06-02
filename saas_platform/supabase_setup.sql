-- ============================================================
-- supabase_setup.sql  —  Full Database Schema
-- ============================================================
-- HOW TO RUN:
--   1. Go to https://supabase.com → your project
--   2. Click "SQL Editor" → "New query"
--   3. Paste this entire file → click "Run"
-- ============================================================

-- ── 1. PROFILES ───────────────────────────────────────────────
-- Stores extra info about each authenticated user.
-- Linked to Supabase Auth via the same UUID.

CREATE TABLE IF NOT EXISTS public.profiles (
    id          UUID PRIMARY KEY,          -- same UUID as auth.users
    email       TEXT NOT NULL,
    full_name   TEXT DEFAULT '',
    avatar_url  TEXT DEFAULT '',
    provider    TEXT DEFAULT 'email',      -- 'email' | 'google'
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$;

DROP TRIGGER IF EXISTS profiles_updated_at ON public.profiles;
CREATE TRIGGER profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ── 2. LOGIN HISTORY ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.login_history (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    email       TEXT,
    provider    TEXT,
    user_agent  TEXT DEFAULT '',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_login_user ON public.login_history(user_id);


-- ── 3. DATASETS ───────────────────────────────────────────────
-- Stores metadata about uploaded CSV/Excel files.
-- (Actual file bytes are NOT stored to keep DB light)

CREATE TABLE IF NOT EXISTS public.datasets (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    rows         INTEGER DEFAULT 0,
    cols         INTEGER DEFAULT 0,
    columns_json TEXT DEFAULT '[]',        -- JSON array of column names
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_datasets_user ON public.datasets(user_id);


-- ── 4. REPORTS ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.reports (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title        TEXT NOT NULL,
    report_type  TEXT DEFAULT 'analytics',
    summary      TEXT DEFAULT '',
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_reports_user ON public.reports(user_id);


-- ── 5. PREDICTIONS ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.predictions (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    prediction_type  TEXT NOT NULL,   -- 'churn' | 'revenue' | 'ltv' | 'segmentation'
    model_name       TEXT DEFAULT '',
    accuracy         FLOAT DEFAULT 0,
    summary          TEXT DEFAULT '',
    created_at       TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_predictions_user ON public.predictions(user_id);


-- ── 6. NOTIFICATIONS ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.notifications (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title      TEXT NOT NULL,
    message    TEXT DEFAULT '',
    type       TEXT DEFAULT 'info',    -- 'info' | 'success' | 'warning' | 'error'
    read       BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_notif_user ON public.notifications(user_id);


-- ── ROW LEVEL SECURITY ────────────────────────────────────────
-- RLS ensures each user can only access THEIR OWN rows.

ALTER TABLE public.profiles       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.login_history  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.datasets       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reports        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.predictions    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications  ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to manage only their own data
CREATE POLICY "own_profiles"      ON public.profiles       FOR ALL USING (true);
CREATE POLICY "own_login_history" ON public.login_history  FOR ALL USING (true);
CREATE POLICY "own_datasets"      ON public.datasets       FOR ALL USING (true);
CREATE POLICY "own_reports"       ON public.reports        FOR ALL USING (true);
CREATE POLICY "own_predictions"   ON public.predictions    FOR ALL USING (true);
CREATE POLICY "own_notifications" ON public.notifications  FOR ALL USING (true);


-- ── VERIFY ────────────────────────────────────────────────────
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
