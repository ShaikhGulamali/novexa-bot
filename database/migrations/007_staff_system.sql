-- ==============================================================================
-- Migration 007: Staff Role, Nickname Styling & Channel Permissions Engine
-- NOVEXA Enterprise Architecture
-- ==============================================================================

CREATE TABLE IF NOT EXISTS staff_config (
    guild_id INTEGER PRIMARY KEY,
    role_id INTEGER DEFAULT NULL,
    name_style TEXT DEFAULT 'small_caps',
    channels_json TEXT DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS server_staff (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    original_nick TEXT DEFAULT NULL,
    added_by INTEGER NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_server_staff_guild ON server_staff(guild_id);

