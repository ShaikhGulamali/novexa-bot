-- ==============================================================================
-- Migration 005: Mention Reply & React User Auto-Response Systems
-- NOVEXA Enterprise Architecture
-- ==============================================================================

CREATE TABLE IF NOT EXISTS mention_replies (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    reply_message TEXT NOT NULL,
    embed_enabled INTEGER DEFAULT 0,
    is_enabled INTEGER DEFAULT 1,
    cooldown_seconds INTEGER DEFAULT 5,
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS react_users (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    emoji TEXT NOT NULL,
    is_enabled INTEGER DEFAULT 1,
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_mention_replies_guild ON mention_replies(guild_id);
CREATE INDEX IF NOT EXISTS idx_react_users_guild ON react_users(guild_id);

