-- ==============================================================================
-- Migration 004: OwO Gaming Suite & Dedicated Interactive Channels
-- NOVEXA Enterprise Architecture
-- ==============================================================================

CREATE TABLE IF NOT EXISTS owo_channels (
    guild_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    panel_message_id INTEGER DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, channel_id)
);

CREATE INDEX IF NOT EXISTS idx_owo_channels_guild ON owo_channels(guild_id);

