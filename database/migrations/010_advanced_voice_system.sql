-- ==============================================================================
-- Migration 010: Advanced Join to Create Voice Channel System
-- NOVEXA Voice Architecture
-- ==============================================================================

CREATE TABLE IF NOT EXISTS voice_config (
    guild_id INTEGER PRIMARY KEY,
    generator_channel_id INTEGER,
    category_id INTEGER,
    channel_name_format TEXT DEFAULT '🔊・{username}',
    default_user_limit INTEGER DEFAULT 0,
    default_bitrate INTEGER DEFAULT 64000,
    is_enabled INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS active_temp_channels (
    channel_id INTEGER PRIMARY KEY,
    guild_id INTEGER NOT NULL,
    owner_id INTEGER NOT NULL,
    control_panel_message_id INTEGER,
    is_locked INTEGER DEFAULT 0,
    is_hidden INTEGER DEFAULT 0,
    custom_status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_temp_channels_guild ON active_temp_channels(guild_id);
CREATE INDEX IF NOT EXISTS idx_temp_channels_owner ON active_temp_channels(owner_id);

