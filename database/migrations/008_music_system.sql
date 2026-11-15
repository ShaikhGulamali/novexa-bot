-- ==============================================================================
-- Migration 008: High-Fidelity Music System Configuration & History
-- NOVEXA Enterprise Architecture
-- ==============================================================================

CREATE TABLE IF NOT EXISTS music_config (
    guild_id INTEGER PRIMARY KEY,
    default_volume INTEGER DEFAULT 100,
    loop_mode TEXT DEFAULT 'off',
    is_247 INTEGER DEFAULT 0,
    text_channel_id INTEGER DEFAULT NULL,
    voice_channel_id INTEGER DEFAULT NULL,
    dj_role_id INTEGER DEFAULT NULL,
    audio_filter TEXT DEFAULT 'flat',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS music_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    webpage_url TEXT NOT NULL,
    duration INTEGER DEFAULT 0,
    requested_by INTEGER NOT NULL,
    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_music_history_guild ON music_history(guild_id, played_at DESC);

