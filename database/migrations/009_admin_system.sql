-- ==============================================================================
-- Migration 009: Admin Role, Universal Channel Access & Sentinel Anti-Nuke Trap
-- NOVEXA Enterprise Architecture
-- ==============================================================================

CREATE TABLE IF NOT EXISTS admin_config (
    guild_id INTEGER PRIMARY KEY,
    role_id INTEGER DEFAULT NULL,
    name_style TEXT DEFAULT 'crown',
    auto_sync_channels INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS server_admins (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    original_nick TEXT DEFAULT NULL,
    added_by INTEGER NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_server_admins_guild ON server_admins(guild_id);

