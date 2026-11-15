-- ==============================================================================
-- Migration 003: Complete Web Platform, Premium Subscriptions & Config Audit
-- NOVEXA Enterprise Architecture
-- ==============================================================================

-- 1. Configurable Premium Subscription Plans
CREATE TABLE IF NOT EXISTS premium_plans (
    plan_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    price_inr INTEGER NOT NULL,
    tier_level INTEGER NOT NULL,
    max_backups INTEGER DEFAULT 5,
    max_ai_daily INTEGER DEFAULT 50,
    custom_embeds INTEGER DEFAULT 1,
    audit_retention_days INTEGER DEFAULT 30,
    perks_json TEXT DEFAULT '[]',
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Seed Default Plans (Silver ₹299, Gold ₹599, Platinum ₹999)
INSERT OR IGNORE INTO premium_plans (plan_id, name, price_inr, tier_level, max_backups, max_ai_daily, custom_embeds, audit_retention_days, perks_json)
VALUES 
('silver', 'Silver VIP', 299, 1, 10, 150, 1, 30, '["Priority Anti-Nuke Response", "Up to 10 Server Backups", "150 Daily AI Requests", "Silver Discord Role & Badge"]'),
('gold', 'Gold Elite', 599, 2, 25, 500, 1, 90, '["Instant Anti-Nuke Interception", "25 Server Backups", "500 Daily AI Requests", "24/7 Dedicated Voice Mode", "Gold Discord Role & Badge"]'),
('platinum', 'Platinum Ultimate', 999, 3, 100, 2000, 1, 365, '["Ultimate Protection Suite", "Unlimited Server Backups", "Unlimited AI Coding Assistance", "Custom Welcome Canvas Branding", "Personal VIP Support Concierge", "Platinum Discord Role & Badge"]');

-- 2. Server Premium Subscriptions
CREATE TABLE IF NOT EXISTS premium_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    plan_id TEXT NOT NULL,
    status TEXT DEFAULT 'ACTIVE',
    starts_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    payment_ref TEXT,
    auto_renew INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (plan_id) REFERENCES premium_plans(plan_id)
);

CREATE INDEX IF NOT EXISTS idx_premium_sub_guild ON premium_subscriptions(guild_id);
CREATE INDEX IF NOT EXISTS idx_premium_sub_status ON premium_subscriptions(status);

-- 3. Two-Way Configuration Audit Logs (Track all changes from Discord & Website)
CREATE TABLE IF NOT EXISTS config_audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    actor_id INTEGER,
    actor_tag TEXT,
    source TEXT NOT NULL DEFAULT 'WEBSITE', -- 'DISCORD', 'WEBSITE', 'API', 'SYSTEM'
    module TEXT NOT NULL,
    setting_key TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_config_audit_guild ON config_audit_logs(guild_id);
CREATE INDEX IF NOT EXISTS idx_config_audit_time ON config_audit_logs(timestamp);

-- 4. Global System Settings (Owner controllable)
CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Seed System Defaults
INSERT OR IGNORE INTO system_settings (key, value) VALUES
('maintenance_mode', 'false'),
('registration_open', 'true'),
('global_announcement', ''),
('motd', 'NOVEXA Enterprise v2.0 is online and protecting servers.');

