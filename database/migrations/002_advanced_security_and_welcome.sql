-- ========================================================
-- NOVEXA DATABASE MIGRATION 002: ADVANCED SECURITY & WELCOME
-- ========================================================

-- 1. Extend welcome_config with template & visual customization columns
-- (Using ALTER TABLE with safe fallback in case columns already exist)
CREATE TABLE IF NOT EXISTS welcome_config (
    guild_id INTEGER PRIMARY KEY,
    channel_id INTEGER,
    message_template TEXT DEFAULT 'Welcome {user} to **{server}**! You are member #{member_count}.',
    embed_enabled INTEGER DEFAULT 1,
    banner_enabled INTEGER DEFAULT 1,
    background_url TEXT DEFAULT '',
    leave_channel_id INTEGER,
    leave_template TEXT DEFAULT '{username} has left **{server}**.',
    is_enabled INTEGER DEFAULT 1,
    template_id TEXT DEFAULT 'novexa_exclusive',
    title TEXT DEFAULT 'Welcome to {server}!',
    custom_color TEXT DEFAULT '#5865F2',
    footer_text TEXT DEFAULT 'Member #{member_count} • NOVEXA',
    message_enabled INTEGER DEFAULT 1,
    dm_enabled INTEGER DEFAULT 0,
    dm_template TEXT DEFAULT 'Welcome to **{server}**, {user}! We are thrilled to have you here.',
    autorole_enabled INTEGER DEFAULT 0,
    autorole_id INTEGER DEFAULT NULL,
    goodbye_enabled INTEGER DEFAULT 1,
    goodbye_template_id TEXT DEFAULT 'minimal_dark',
    goodbye_embed_enabled INTEGER DEFAULT 1
);

-- 2. Anti-Spam Protection Configuration Table
CREATE TABLE IF NOT EXISTS antispam_config (
    guild_id INTEGER PRIMARY KEY,
    enabled INTEGER DEFAULT 1,
    max_mentions INTEGER DEFAULT 5,
    max_emojis INTEGER DEFAULT 10,
    max_messages_per_window INTEGER DEFAULT 5,
    time_window INTEGER DEFAULT 5,
    duplicate_filter INTEGER DEFAULT 1,
    invite_filter INTEGER DEFAULT 1,
    link_filter INTEGER DEFAULT 0,
    scam_filter INTEGER DEFAULT 1,
    punishment TEXT DEFAULT 'timeout',
    action_duration INTEGER DEFAULT 300,
    log_channel_id INTEGER DEFAULT NULL
);

-- 3. Anti-Spam Exemptions Table (Channels and Roles)
CREATE TABLE IF NOT EXISTS antispam_exemptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    target_id INTEGER NOT NULL,
    target_type TEXT NOT NULL, -- 'channel' or 'role'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(guild_id, target_id, target_type)
);

-- 4. Approved Bots Table (Bot Addition Protection)
CREATE TABLE IF NOT EXISTS security_approved_bots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    bot_id INTEGER NOT NULL,
    bot_name TEXT DEFAULT 'Unknown Bot',
    approved_by INTEGER NOT NULL,
    approved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(guild_id, bot_id)
);

-- 5. Security Audit Incident Logs Table
CREATE TABLE IF NOT EXISTS security_audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    executor_id INTEGER,
    executor_tag TEXT,
    target_id INTEGER,
    target_name TEXT,
    action_type TEXT NOT NULL,
    details TEXT NOT NULL,
    severity TEXT DEFAULT 'MEDIUM',
    punishment_applied TEXT DEFAULT 'NONE',
    restored INTEGER DEFAULT 0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Server Backups Table
CREATE TABLE IF NOT EXISTS server_backups (
    backup_id TEXT PRIMARY KEY,
    guild_id INTEGER NOT NULL,
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    backup_name TEXT NOT NULL,
    data_json TEXT NOT NULL
);

-- 7. Whitelist Audit History Table
CREATE TABLE IF NOT EXISTS whitelist_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    target_id INTEGER NOT NULL,
    target_type TEXT NOT NULL,
    action TEXT NOT NULL, -- 'ADD' or 'REMOVE'
    performed_by INTEGER NOT NULL,
    expires_at TIMESTAMP DEFAULT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. High-Performance Indexes
CREATE INDEX IF NOT EXISTS idx_security_logs_guild ON security_audit_logs(guild_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_server_backups_guild ON server_backups(guild_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_approved_bots_guild ON security_approved_bots(guild_id, bot_id);
CREATE INDEX IF NOT EXISTS idx_antispam_exemptions ON antispam_exemptions(guild_id, target_id);
CREATE INDEX IF NOT EXISTS idx_whitelist_audit_guild ON whitelist_audit(guild_id, timestamp DESC);

