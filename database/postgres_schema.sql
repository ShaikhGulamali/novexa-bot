-- ========================================================
-- NOVEXA Discord Bot - Production PostgreSQL Schema (Neon)
-- Generated with 100% Exact Fidelity from SQLite Schema
-- ========================================================

CREATE TABLE IF NOT EXISTS "economy_items" (
    "item_id" TEXT,
    "name" TEXT NOT NULL,
    "description" TEXT NOT NULL,
    "category" TEXT NOT NULL,
    "rarity" TEXT NOT NULL,
    "buy_price" INTEGER DEFAULT 0,
    "sell_price" INTEGER DEFAULT 0,
    "gem_price" INTEGER DEFAULT 0,
    "attack_bonus" INTEGER DEFAULT 0,
    "defense_bonus" INTEGER DEFAULT 0,
    "hunt_luck" INTEGER DEFAULT 0,
    "consumable" INTEGER DEFAULT 0,
    "max_stack" INTEGER DEFAULT 999,
    "icon" TEXT DEFAULT '📦',
    "slot" TEXT DEFAULT NULL,
    "special_ability" TEXT DEFAULT '',
    PRIMARY KEY ("item_id")
);

CREATE TABLE IF NOT EXISTS "economy_achievements" (
    "key" TEXT,
    "name" TEXT NOT NULL,
    "description" TEXT NOT NULL,
    "icon" TEXT DEFAULT '🏆',
    "gem_reward" INTEGER DEFAULT 5,
    "coin_reward" INTEGER DEFAULT 500,
    PRIMARY KEY ("key")
);

CREATE TABLE IF NOT EXISTS "economy_animals" (
    "animal_id" TEXT,
    "name" TEXT NOT NULL,
    "emoji" TEXT NOT NULL,
    "rarity" TEXT NOT NULL,
    "base_value" INTEGER NOT NULL,
    "base_xp" BIGINT NOT NULL,
    "catch_weight" INTEGER NOT NULL,
    "ability" TEXT DEFAULT '',
    "description" TEXT DEFAULT '',
    PRIMARY KEY ("animal_id")
);

CREATE TABLE IF NOT EXISTS "economy_pets" (
    "pet_type" TEXT,
    "name" TEXT NOT NULL,
    "emoji" TEXT NOT NULL,
    "rarity" TEXT NOT NULL,
    "bonus_type" TEXT NOT NULL,
    "bonus_value" DOUBLE PRECISION NOT NULL,
    "description" TEXT NOT NULL,
    PRIMARY KEY ("pet_type")
);

CREATE TABLE IF NOT EXISTS "premium_plans" (
    "plan_id" TEXT,
    "name" TEXT NOT NULL,
    "price_inr" INTEGER NOT NULL,
    "tier_level" INTEGER NOT NULL,
    "max_backups" INTEGER DEFAULT 5,
    "max_ai_daily" INTEGER DEFAULT 50,
    "custom_embeds" INTEGER DEFAULT 1,
    "audit_retention_days" INTEGER DEFAULT 30,
    "perks_json" TEXT DEFAULT '[]',
    "is_active" INTEGER DEFAULT 1,
    "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("plan_id")
);

CREATE TABLE IF NOT EXISTS "admin_config" (
    "guild_id" BIGINT,
    "role_id" BIGINT DEFAULT NULL,
    "name_style" TEXT DEFAULT 'crown',
    "auto_sync_channels" INTEGER DEFAULT 1,
    "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("guild_id")
);

CREATE TABLE IF NOT EXISTS "ai_channels" (
    "channel_id" BIGINT,
    "guild_id" BIGINT NOT NULL,
    "mode" TEXT DEFAULT 'coding_assistant',
    "auto_thread" INTEGER DEFAULT 0,
    "added_by" BIGINT,
    "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("channel_id")
);

CREATE TABLE IF NOT EXISTS "ai_config" (
    "guild_id" BIGINT,
    "provider" TEXT DEFAULT 'gemini',
    "model" TEXT DEFAULT 'gemini-1.5-flash',
    "language" TEXT DEFAULT 'English',
    "response_style" TEXT DEFAULT 'detailed',
    "user_limit_hourly" INTEGER DEFAULT 30,
    "cooldown_seconds" INTEGER DEFAULT 3,
    "system_prompt" TEXT DEFAULT '',
    "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("guild_id")
);

CREATE TABLE IF NOT EXISTS "ai_logs" (
    "id" BIGSERIAL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "channel_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "provider" TEXT NOT NULL,
    "error_message" TEXT NOT NULL,
    "timestamp" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "ai_memory" (
    "id" BIGSERIAL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "channel_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "role" TEXT NOT NULL,
    "content" TEXT NOT NULL,
    "has_image" INTEGER DEFAULT 0,
    "timestamp" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "ai_usage" (
    "id" BIGSERIAL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "channel_id" BIGINT NOT NULL,
    "provider" TEXT NOT NULL,
    "model" TEXT NOT NULL,
    "prompt_tokens" INTEGER DEFAULT 0,
    "completion_tokens" INTEGER DEFAULT 0,
    "has_image" INTEGER DEFAULT 0,
    "timestamp" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "antinuke_config" (
    "guild_id" BIGINT,
    "enabled" INTEGER DEFAULT 1,
    "punishment_type" TEXT DEFAULT 'ban',
    "max_channel_deletions" INTEGER DEFAULT 3,
    "max_channel_creations" INTEGER DEFAULT 4,
    "max_role_deletions" INTEGER DEFAULT 3,
    "max_role_creations" INTEGER DEFAULT 4,
    "max_bans" INTEGER DEFAULT 3,
    "max_kicks" INTEGER DEFAULT 3,
    "max_webhook_creations" INTEGER DEFAULT 2,
    "max_webhook_deletions" INTEGER DEFAULT 2,
    "time_window" INTEGER DEFAULT 30,
    "log_channel_id" BIGINT DEFAULT NULL,
    "mode" TEXT DEFAULT 'medium',
    "max_channel_updates" INTEGER DEFAULT 4,
    "max_role_updates" INTEGER DEFAULT 4,
    "max_webhook_changes" INTEGER DEFAULT 5,
    "max_permission_changes" INTEGER DEFAULT 5,
    "bot_protection_enabled" INTEGER DEFAULT 1,
    PRIMARY KEY ("guild_id")
);

CREATE TABLE IF NOT EXISTS "antinuke_whitelist" (
    "id" BIGSERIAL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "target_id" BIGINT NOT NULL,
    "target_type" TEXT DEFAULT 'user',
    "added_by" BIGINT,
    "added_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE ("guild_id", "target_id")
);

CREATE TABLE IF NOT EXISTS "antispam_config" (
    "guild_id" BIGINT,
    "enabled" INTEGER DEFAULT 1,
    "max_mentions" INTEGER DEFAULT 5,
    "max_emojis" INTEGER DEFAULT 10,
    "max_messages_per_window" INTEGER DEFAULT 5,
    "time_window" INTEGER DEFAULT 5,
    "duplicate_filter" INTEGER DEFAULT 1,
    "invite_filter" INTEGER DEFAULT 1,
    "link_filter" INTEGER DEFAULT 0,
    "scam_filter" INTEGER DEFAULT 1,
    "punishment" TEXT DEFAULT 'timeout',
    "action_duration" INTEGER DEFAULT 300,
    "log_channel_id" BIGINT DEFAULT NULL,
    "caps_filter_enabled" INTEGER DEFAULT 0,
    "blocked_words" TEXT DEFAULT '',
    "attachment_spam_limit" INTEGER DEFAULT 5,
    "automod_action" TEXT DEFAULT 'warn',
    PRIMARY KEY ("guild_id")
);

CREATE TABLE IF NOT EXISTS "antispam_exemptions" (
    "id" BIGSERIAL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "target_id" BIGINT NOT NULL,
    "target_type" TEXT NOT NULL,
    "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE ("guild_id", "target_id", "target_type")
);

CREATE TABLE IF NOT EXISTS "auto_responders" (
    "id" BIGSERIAL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "trigger" TEXT NOT NULL,
    "response" TEXT NOT NULL,
    "match_type" TEXT DEFAULT 'exact'
);

CREATE TABLE IF NOT EXISTS "auto_roles" (
    "guild_id" BIGINT NOT NULL,
    "role_id" BIGINT NOT NULL,
    PRIMARY KEY ("guild_id", "role_id")
);

CREATE TABLE IF NOT EXISTS "birthdays" (
    "guild_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "day" INTEGER NOT NULL,
    "month" INTEGER NOT NULL,
    PRIMARY KEY ("guild_id", "user_id")
);

CREATE TABLE IF NOT EXISTS "cloned_templates" (
    "template_id" TEXT,
    "source_guild_id" BIGINT NOT NULL,
    "source_guild_name" TEXT NOT NULL,
    "template_name" TEXT NOT NULL,
    "creator_id" BIGINT NOT NULL,
    "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "structure_json" TEXT NOT NULL,
    PRIMARY KEY ("template_id")
);

CREATE TABLE IF NOT EXISTS "config_audit_logs" (
    "id" BIGSERIAL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "actor_id" BIGINT,
    "actor_tag" TEXT,
    "source" TEXT DEFAULT 'WEBSITE' NOT NULL,
    "module" TEXT NOT NULL,
    "setting_key" TEXT NOT NULL,
    "old_value" TEXT,
    "new_value" TEXT,
    "timestamp" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "economy" (
    "guild_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "wallet" BIGINT DEFAULT 100,
    "bank" BIGINT DEFAULT 500,
    "last_daily" DOUBLE PRECISION DEFAULT 0,
    PRIMARY KEY ("guild_id", "user_id")
);

CREATE TABLE IF NOT EXISTS "economy_battles" (
    "id" BIGSERIAL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "challenger_id" BIGINT NOT NULL,
    "opponent_id" BIGINT NOT NULL,
    "winner_id" BIGINT NOT NULL,
    "loser_id" BIGINT NOT NULL,
    "bet_amount" INTEGER DEFAULT 0,
    "xp_awarded" BIGINT DEFAULT 0,
    "battle_log" TEXT DEFAULT '',
    "timestamp" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "economy_channel_settings" (
    "id" BIGSERIAL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "channel_id" BIGINT NOT NULL,
    "category_type" TEXT NOT NULL,
    UNIQUE ("guild_id", "channel_id", "category_type")
);

CREATE TABLE IF NOT EXISTS "economy_friends" (
    "id" BIGSERIAL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "friend_id" BIGINT NOT NULL,
    "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE ("guild_id", "user_id", "friend_id")
);

CREATE TABLE IF NOT EXISTS "economy_guild_settings" (
    "guild_id" BIGINT,
    "is_enabled" INTEGER DEFAULT 1,
    "currency_name" TEXT DEFAULT 'GULAMALI COINS',
    "currency_symbol" TEXT DEFAULT '🪙',
    "work_cooldown" INTEGER DEFAULT 300,
    "crime_cooldown" INTEGER DEFAULT 600,
    "slut_cooldown" INTEGER DEFAULT 900,
    "hunt_cooldown" INTEGER DEFAULT 15,
    "battle_cooldown" INTEGER DEFAULT 60,
    "channel_enforcement" INTEGER DEFAULT 0,
    "daily_reward_min" INTEGER DEFAULT 500,
    "daily_reward_max" INTEGER DEFAULT 1000,
    "weekly_reward" INTEGER DEFAULT 5000,
    "monthly_reward" INTEGER DEFAULT 25000,
    "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("guild_id")
);

CREATE TABLE IF NOT EXISTS "economy_inventory" (
    "id" BIGSERIAL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "item_id" TEXT NOT NULL,
    "quantity" INTEGER DEFAULT 1,
    "is_equipped" INTEGER DEFAULT 0,
    "slot" TEXT DEFAULT NULL,
    "acquired_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE ("guild_id", "user_id", "item_id"),
    FOREIGN KEY ("item_id") REFERENCES "economy_items" ("item_id") ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS "economy_relationships" (
    "id" BIGSERIAL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "user1_id" BIGINT NOT NULL,
    "user2_id" BIGINT NOT NULL,
    "ring_item_id" TEXT DEFAULT 'diamond_ring',
    "love_affinity" INTEGER DEFAULT 100,
    "married_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE ("guild_id", "user1_id"),
    UNIQUE ("guild_id", "user2_id")
);

CREATE TABLE IF NOT EXISTS "economy_trades" (
    "trade_id" TEXT,
    "guild_id" BIGINT NOT NULL,
    "sender_id" BIGINT NOT NULL,
    "receiver_id" BIGINT NOT NULL,
    "sender_coins" BIGINT DEFAULT 0,
    "sender_items" TEXT DEFAULT '[]',
    "receiver_coins" BIGINT DEFAULT 0,
    "receiver_items" TEXT DEFAULT '[]',
    "sender_confirmed" INTEGER DEFAULT 0,
    "receiver_confirmed" INTEGER DEFAULT 0,
    "status" TEXT DEFAULT 'pending',
    "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "completed_at" TIMESTAMP DEFAULT NULL,
    PRIMARY KEY ("trade_id")
);

CREATE TABLE IF NOT EXISTS "economy_transactions" (
    "id" BIGSERIAL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "from_user_id" BIGINT,
    "to_user_id" BIGINT,
    "amount" INTEGER NOT NULL,
    "currency_type" TEXT DEFAULT 'coins',
    "tx_type" TEXT NOT NULL,
    "description" TEXT DEFAULT '',
    "timestamp" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "economy_user_achievements" (
    "guild_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "achievement_key" TEXT NOT NULL,
    "unlocked_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("guild_id", "user_id", "achievement_key"),
    FOREIGN KEY ("achievement_key") REFERENCES "economy_achievements" ("key") ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS "economy_user_animals" (
    "id" BIGSERIAL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "animal_id" TEXT NOT NULL,
    "count" BIGINT DEFAULT 1,
    "is_favorite" INTEGER DEFAULT 0,
    "first_caught" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "last_caught" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE ("guild_id", "user_id", "animal_id"),
    FOREIGN KEY ("animal_id") REFERENCES "economy_animals" ("animal_id") ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS "economy_user_pets" (
    "id" BIGSERIAL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "pet_type" TEXT NOT NULL,
    "nickname" TEXT NOT NULL,
    "level" INTEGER DEFAULT 1,
    "xp" BIGINT DEFAULT 0,
    "happiness" INTEGER DEFAULT 100,
    "is_equipped" INTEGER DEFAULT 0,
    "last_fed" DOUBLE PRECISION DEFAULT 0.0,
    "adopted_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY ("pet_type") REFERENCES "economy_pets" ("pet_type") ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS "economy_users" (
    "guild_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "wallet" BIGINT DEFAULT 500,
    "bank" BIGINT DEFAULT 1000,
    "gems" INTEGER DEFAULT 10,
    "xp" BIGINT DEFAULT 0,
    "level" INTEGER DEFAULT 1,
    "reputation" INTEGER DEFAULT 0,
    "daily_streak" INTEGER DEFAULT 0,
    "last_daily" DOUBLE PRECISION DEFAULT 0.0,
    "last_weekly" DOUBLE PRECISION DEFAULT 0.0,
    "last_monthly" DOUBLE PRECISION DEFAULT 0.0,
    "last_work" DOUBLE PRECISION DEFAULT 0.0,
    "last_crime" DOUBLE PRECISION DEFAULT 0.0,
    "last_slut" DOUBLE PRECISION DEFAULT 0.0,
    "last_rep" DOUBLE PRECISION DEFAULT 0.0,
    "last_hunt" DOUBLE PRECISION DEFAULT 0.0,
    "last_battle" DOUBLE PRECISION DEFAULT 0.0,
    "total_earned" BIGINT DEFAULT 0,
    "total_spent" BIGINT DEFAULT 0,
    "commands_used" INTEGER DEFAULT 0,
    "hunts_count" BIGINT DEFAULT 0,
    "battles_won" INTEGER DEFAULT 0,
    "battles_lost" INTEGER DEFAULT 0,
    "gambles_won" INTEGER DEFAULT 0,
    "gambles_lost" INTEGER DEFAULT 0,
    "is_banned" INTEGER DEFAULT 0,
    "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("guild_id", "user_id")
);

CREATE TABLE IF NOT EXISTS "giveaways" (
    "message_id" BIGINT,
    "guild_id" BIGINT NOT NULL,
    "channel_id" BIGINT NOT NULL,
    "prize" TEXT NOT NULL,
    "winners_count" BIGINT DEFAULT 1,
    "end_time" DOUBLE PRECISION NOT NULL,
    "ended" INTEGER DEFAULT 0,
    "host_id" BIGINT NOT NULL,
    PRIMARY KEY ("message_id")
);

CREATE TABLE IF NOT EXISTS "guild_settings" (
    "guild_id" BIGINT,
    "prefix" TEXT DEFAULT '/',
    "welcome_enabled" INTEGER DEFAULT 1,
    "tickets_enabled" INTEGER DEFAULT 1,
    "antinuke_enabled" INTEGER DEFAULT 1,
    "music_enabled" INTEGER DEFAULT 1,
    "leveling_enabled" INTEGER DEFAULT 1,
    "economy_enabled" INTEGER DEFAULT 1,
    "payments_enabled" INTEGER DEFAULT 1,
    "logging_enabled" INTEGER DEFAULT 1,
    "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "mod_log_channel_id" BIGINT DEFAULT NULL,
    "dm_on_punish" INTEGER DEFAULT 1,
    "max_warnings_kick" INTEGER DEFAULT 3,
    "max_warnings_ban" INTEGER DEFAULT 5,
    "level_up_channel_id" BIGINT DEFAULT NULL,
    "xp_per_message" BIGINT DEFAULT 15,
    "xp_cooldown" BIGINT DEFAULT 60,
    PRIMARY KEY ("guild_id")
);

CREATE TABLE IF NOT EXISTS "leveling" (
    "guild_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "xp" BIGINT DEFAULT 0,
    "level" INTEGER DEFAULT 0,
    "last_xp_time" DOUBLE PRECISION DEFAULT 0,
    PRIMARY KEY ("guild_id", "user_id")
);

CREATE TABLE IF NOT EXISTS "logging_config" (
    "guild_id" BIGINT,
    "joins_channel_id" BIGINT DEFAULT NULL,
    "leaves_channel_id" BIGINT DEFAULT NULL,
    "message_edits_channel_id" BIGINT DEFAULT NULL,
    "message_deletes_channel_id" BIGINT DEFAULT NULL,
    "role_changes_channel_id" BIGINT DEFAULT NULL,
    "channel_changes_channel_id" BIGINT DEFAULT NULL,
    "bans_channel_id" BIGINT DEFAULT NULL,
    "kicks_channel_id" BIGINT DEFAULT NULL,
    "timeouts_channel_id" BIGINT DEFAULT NULL,
    "ticket_activity_channel_id" BIGINT DEFAULT NULL,
    "payment_activity_channel_id" BIGINT DEFAULT NULL,
    "antinuke_channel_id" BIGINT DEFAULT NULL,
    "errors_channel_id" BIGINT DEFAULT NULL,
    "voice_logs_channel_id" BIGINT DEFAULT NULL,
    "member_logs_channel_id" BIGINT DEFAULT NULL,
    "server_logs_channel_id" BIGINT DEFAULT NULL,
    "category_id" BIGINT DEFAULT NULL,
    PRIMARY KEY ("guild_id")
);

CREATE TABLE IF NOT EXISTS "mention_replies" (
    "guild_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "reply_message" TEXT NOT NULL,
    "embed_enabled" INTEGER DEFAULT 0,
    "is_enabled" INTEGER DEFAULT 1,
    "cooldown_seconds" INTEGER DEFAULT 5,
    "created_by" INTEGER NOT NULL,
    "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("guild_id", "user_id")
);

CREATE TABLE IF NOT EXISTS "moderation_logs" (
    "id" BIGSERIAL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "moderator_id" BIGINT NOT NULL,
    "action" TEXT NOT NULL,
    "reason" TEXT DEFAULT 'No reason provided.',
    "duration" INTEGER DEFAULT 0,
    "timestamp" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "music_config" (
    "guild_id" BIGINT,
    "is_247" INTEGER DEFAULT 0,
    "voice_channel_id" BIGINT DEFAULT NULL,
    "text_channel_id" BIGINT DEFAULT NULL,
    PRIMARY KEY ("guild_id")
);

CREATE TABLE IF NOT EXISTS "music_history" (
    "id" BIGSERIAL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "title" TEXT NOT NULL,
    "webpage_url" TEXT NOT NULL,
    "duration" INTEGER DEFAULT 0,
    "requested_by" INTEGER NOT NULL,
    "played_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "owo_channels" (
    "guild_id" BIGINT NOT NULL,
    "channel_id" BIGINT NOT NULL,
    "panel_message_id" BIGINT DEFAULT NULL,
    "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("guild_id", "channel_id")
);

CREATE TABLE IF NOT EXISTS "payment_records" (
    "id" BIGSERIAL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "amount" TEXT NOT NULL,
    "reference_id" TEXT NOT NULL,
    "screenshot_url" TEXT NOT NULL,
    "status" TEXT DEFAULT 'pending',
    "notes" TEXT DEFAULT '',
    "reviewed_by" INTEGER DEFAULT NULL,
    "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "reviewed_at" TIMESTAMP DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS "payments_config" (
    "guild_id" BIGINT,
    "upi_id" TEXT DEFAULT '',
    "qr_image_url" TEXT DEFAULT '',
    "instructions" TEXT DEFAULT 'Scan QR or send UPI to the address above. Submit your reference ID & screenshot for verification.',
    "staff_role_id" BIGINT DEFAULT NULL,
    "log_channel_id" BIGINT DEFAULT NULL,
    PRIMARY KEY ("guild_id")
);

CREATE TABLE IF NOT EXISTS "premium_subscriptions" (
    "id" BIGSERIAL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "plan_id" TEXT NOT NULL,
    "status" TEXT DEFAULT 'ACTIVE',
    "starts_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "expires_at" TIMESTAMP NOT NULL,
    "payment_ref" TEXT,
    "auto_renew" INTEGER DEFAULT 0,
    "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY ("plan_id") REFERENCES "premium_plans" ("plan_id") ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS "premium_orders" (
    "order_id" TEXT PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "plan_id" TEXT NOT NULL,
    "amount" DOUBLE PRECISION NOT NULL,
    "currency" TEXT DEFAULT 'INR',
    "status" TEXT DEFAULT 'CREATED',
    "payment_id" TEXT DEFAULT '',
    "customer_email" TEXT DEFAULT '',
    "customer_phone" TEXT DEFAULT '',
    "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "paid_at" TIMESTAMP,
    "granted" INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS "public_ai_channels" (
    "channel_id" BIGINT,
    "guild_id" BIGINT NOT NULL,
    "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("channel_id")
);

CREATE TABLE IF NOT EXISTS "public_ai_conversations" (
    "id" BIGSERIAL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "channel_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "role" TEXT NOT NULL,
    "content" TEXT NOT NULL,
    "has_image" INTEGER DEFAULT 0,
    "timestamp" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "public_ai_settings" (
    "guild_id" BIGINT,
    "is_enabled" INTEGER DEFAULT 1,
    "provider" TEXT DEFAULT 'gemini',
    "model" TEXT DEFAULT 'gemini-1.5-flash',
    "cooldown_seconds" INTEGER DEFAULT 3,
    "hourly_limit" INTEGER DEFAULT 50,
    "system_prompt" TEXT DEFAULT '',
    "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("guild_id")
);

CREATE TABLE IF NOT EXISTS "public_ai_usage" (
    "id" BIGSERIAL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "channel_id" BIGINT NOT NULL,
    "provider" TEXT NOT NULL,
    "model" TEXT NOT NULL,
    "timestamp" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "react_users" (
    "guild_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "emoji" TEXT NOT NULL,
    "is_enabled" INTEGER DEFAULT 1,
    "created_by" INTEGER NOT NULL,
    "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("guild_id", "user_id")
);

CREATE TABLE IF NOT EXISTS "reaction_roles" (
    "id" BIGSERIAL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "message_id" BIGINT NOT NULL,
    "channel_id" BIGINT NOT NULL,
    "emoji" TEXT NOT NULL,
    "role_id" BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS "security_approved_bots" (
    "id" BIGSERIAL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "bot_id" BIGINT NOT NULL,
    "bot_name" TEXT DEFAULT 'Unknown Bot',
    "approved_by" INTEGER NOT NULL,
    "approved_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE ("guild_id", "bot_id")
);

CREATE TABLE IF NOT EXISTS "security_audit_logs" (
    "id" BIGSERIAL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "executor_id" BIGINT,
    "executor_tag" TEXT,
    "target_id" BIGINT,
    "target_name" TEXT,
    "action_type" TEXT NOT NULL,
    "details" TEXT NOT NULL,
    "severity" TEXT DEFAULT 'MEDIUM',
    "punishment_applied" TEXT DEFAULT 'NONE',
    "restored" INTEGER DEFAULT 0,
    "timestamp" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "latency_ms" INTEGER DEFAULT 0,
    "correlation_status" TEXT DEFAULT 'EXACT_MATCH'
);

CREATE TABLE IF NOT EXISTS "server_admins" (
    "guild_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "original_nick" TEXT DEFAULT NULL,
    "added_by" BIGINT NOT NULL,
    "added_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("guild_id", "user_id")
);

CREATE TABLE IF NOT EXISTS "server_backups" (
    "backup_id" TEXT,
    "guild_id" BIGINT NOT NULL,
    "created_by" INTEGER NOT NULL,
    "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "backup_name" TEXT NOT NULL,
    "data_json" TEXT NOT NULL,
    PRIMARY KEY ("backup_id")
);

CREATE TABLE IF NOT EXISTS "server_clone_history" (
    "id" BIGSERIAL PRIMARY KEY,
    "source_guild_id" BIGINT NOT NULL,
    "source_guild_name" TEXT NOT NULL,
    "dest_guild_id" BIGINT NOT NULL,
    "dest_guild_name" TEXT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "mode" TEXT NOT NULL,
    "cloned_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "created_roles" TEXT DEFAULT '[]',
    "created_categories" TEXT DEFAULT '[]',
    "created_channels" TEXT DEFAULT '[]',
    "report_json" TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS "server_setups" (
    "guild_id" BIGINT,
    "template_id" TEXT NOT NULL,
    "template_name" TEXT NOT NULL,
    "server_name" TEXT,
    "created_categories" TEXT DEFAULT '[]',
    "created_channels" TEXT DEFAULT '[]',
    "created_roles" TEXT DEFAULT '[]',
    "welcome_channel_id" BIGINT DEFAULT NULL,
    "exit_channel_id" BIGINT DEFAULT NULL,
    "rules_channel_id" BIGINT DEFAULT NULL,
    "ticket_category_id" BIGINT DEFAULT NULL,
    "logging_channels" TEXT DEFAULT '{}',
    "setup_status" TEXT DEFAULT 'completed',
    "setup_timestamp" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "ai_channel_id" BIGINT DEFAULT NULL,
    PRIMARY KEY ("guild_id")
);

CREATE TABLE IF NOT EXISTS "server_staff" (
    "guild_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "original_nick" TEXT DEFAULT NULL,
    "added_by" BIGINT NOT NULL,
    "added_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("guild_id", "user_id")
);

CREATE TABLE IF NOT EXISTS "staff_config" (
    "guild_id" BIGINT,
    "role_id" BIGINT DEFAULT NULL,
    "name_style" TEXT DEFAULT 'small_caps',
    "channels_json" TEXT DEFAULT '[]',
    "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("guild_id")
);

CREATE TABLE IF NOT EXISTS "starboard_config" (
    "guild_id" BIGINT,
    "channel_id" BIGINT,
    "star_count" BIGINT DEFAULT 3,
    "enabled" INTEGER DEFAULT 1,
    PRIMARY KEY ("guild_id")
);

CREATE TABLE IF NOT EXISTS "starboard_messages" (
    "original_message_id" BIGINT,
    "starboard_message_id" BIGINT,
    "guild_id" BIGINT NOT NULL,
    "channel_id" BIGINT NOT NULL,
    PRIMARY KEY ("original_message_id")
);

CREATE TABLE IF NOT EXISTS "sticky_messages" (
    "channel_id" BIGINT,
    "guild_id" BIGINT NOT NULL,
    "content" TEXT NOT NULL,
    "last_message_id" BIGINT DEFAULT NULL,
    PRIMARY KEY ("channel_id")
);

CREATE TABLE IF NOT EXISTS "system_settings" (
    "key" TEXT,
    "value" TEXT,
    "updated_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("key")
);

CREATE TABLE IF NOT EXISTS "ticket_panels" (
    "panel_id" TEXT,
    "guild_id" BIGINT NOT NULL,
    "channel_id" BIGINT NOT NULL,
    "message_id" BIGINT,
    "title" TEXT DEFAULT 'Support Ticket',
    "description" TEXT DEFAULT 'Click the button below to open a ticket.',
    "category_id" BIGINT,
    "support_role_id" BIGINT,
    "naming_scheme" TEXT DEFAULT 'ticket-{number}',
    "transcript_channel_id" BIGINT,
    PRIMARY KEY ("panel_id")
);

CREATE TABLE IF NOT EXISTS "tickets" (
    "id" BIGSERIAL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "channel_id" BIGINT NOT NULL,
    "ticket_number" INTEGER NOT NULL,
    "author_id" BIGINT NOT NULL,
    "claimed_by" BIGINT DEFAULT NULL,
    "status" TEXT DEFAULT 'open',
    "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "closed_at" TIMESTAMP DEFAULT NULL,
    "reason" TEXT DEFAULT 'General Support'
);

CREATE TABLE IF NOT EXISTS "user_profiles" (
    "guild_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "bio" TEXT DEFAULT 'Hello! I am using Gulamali Ultimate Bot.',
    "custom_color" TEXT DEFAULT '#5865F2',
    "custom_avatar_url" TEXT DEFAULT '',
    "custom_banner_url" TEXT DEFAULT '',
    "background_url" TEXT DEFAULT '',
    PRIMARY KEY ("guild_id", "user_id")
);

CREATE TABLE IF NOT EXISTS "warnings" (
    "id" BIGSERIAL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "moderator_id" BIGINT NOT NULL,
    "reason" TEXT NOT NULL,
    "timestamp" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "welcome_config" (
    "guild_id" BIGINT,
    "channel_id" BIGINT,
    "message_template" TEXT DEFAULT 'Welcome {user} to **{server}**! You are member #{member_count}.',
    "embed_enabled" INTEGER DEFAULT 1,
    "banner_enabled" INTEGER DEFAULT 1,
    "background_url" TEXT DEFAULT '',
    "leave_channel_id" BIGINT,
    "leave_template" TEXT DEFAULT '{username} has left **{server}**.',
    "is_enabled" INTEGER DEFAULT 1,
    "template_id" TEXT DEFAULT 'novexa_exclusive',
    "title" TEXT DEFAULT 'Welcome to {server}!',
    "custom_color" TEXT DEFAULT '#5865F2',
    "footer_text" TEXT DEFAULT 'Member #{member_count} • NOVEXA',
    "message_enabled" INTEGER DEFAULT 1,
    "dm_enabled" INTEGER DEFAULT 0,
    "dm_template" TEXT DEFAULT 'Welcome to **{server}**, {user}! We are thrilled to have you here.',
    "autorole_enabled" INTEGER DEFAULT 0,
    "autorole_id" BIGINT DEFAULT NULL,
    "goodbye_enabled" INTEGER DEFAULT 1,
    "goodbye_template_id" TEXT DEFAULT 'minimal_dark',
    "goodbye_embed_enabled" INTEGER DEFAULT 1,
    "leave_embed_enabled" INTEGER DEFAULT 1,
    "leave_message_template" TEXT DEFAULT NULL,
    PRIMARY KEY ("guild_id")
);

CREATE TABLE IF NOT EXISTS "whitelist_audit" (
    "id" BIGSERIAL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "target_id" BIGINT NOT NULL,
    "target_type" TEXT NOT NULL,
    "action" TEXT NOT NULL,
    "performed_by" INTEGER NOT NULL,
    "expires_at" TIMESTAMP DEFAULT NULL,
    "timestamp" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================================
-- INDEXES FOR HIGH-THROUGHPUT QUERIES
-- ========================================================

CREATE INDEX idx_ai_channels_guild ON ai_channels(guild_id);
CREATE INDEX idx_ai_memory_user ON ai_memory(guild_id, channel_id, user_id, timestamp);
CREATE INDEX idx_ai_usage_guild ON ai_usage(guild_id, timestamp);
CREATE INDEX idx_antispam_exemptions ON antispam_exemptions(guild_id, target_id);
CREATE INDEX idx_approved_bots_guild ON security_approved_bots(guild_id, bot_id);
CREATE INDEX idx_config_audit_guild ON config_audit_logs(guild_id);
CREATE INDEX idx_config_audit_time ON config_audit_logs(timestamp);
CREATE INDEX idx_eco_animals_user ON economy_user_animals(guild_id, user_id);
CREATE INDEX idx_eco_chan_guild ON economy_channel_settings(guild_id, category_type);
CREATE INDEX idx_eco_inv_user ON economy_inventory(guild_id, user_id);
CREATE INDEX idx_eco_pets_user ON economy_user_pets(guild_id, user_id);
CREATE INDEX idx_eco_tx_guild ON economy_transactions(guild_id, timestamp DESC);
CREATE INDEX idx_eco_users_guild_level ON economy_users(guild_id, level DESC, xp DESC);
CREATE INDEX idx_eco_users_guild_rep ON economy_users(guild_id, reputation DESC);
CREATE INDEX idx_eco_users_guild_wallet ON economy_users(guild_id, wallet DESC);
CREATE INDEX idx_leveling_guild_xp ON leveling(guild_id, xp DESC);
CREATE INDEX idx_logging_config_cat ON logging_config(category_id);
CREATE INDEX idx_mention_replies_guild ON mention_replies(guild_id);
CREATE INDEX idx_moderation_guild_user ON moderation_logs(guild_id, user_id);
CREATE INDEX idx_music_history_guild ON music_history(guild_id, played_at DESC);
CREATE INDEX idx_owo_channels_guild ON owo_channels(guild_id);
CREATE INDEX idx_payment_records_guild ON payment_records(guild_id, status);
CREATE INDEX idx_premium_sub_guild ON premium_subscriptions(guild_id);
CREATE INDEX idx_premium_sub_status ON premium_subscriptions(status);
CREATE INDEX idx_pub_ai_chan_guild ON public_ai_channels(guild_id);
CREATE INDEX idx_pub_ai_conv ON public_ai_conversations(guild_id, channel_id, user_id, timestamp);
CREATE INDEX idx_pub_ai_usage ON public_ai_usage(guild_id, timestamp);
CREATE INDEX idx_react_users_guild ON react_users(guild_id);
CREATE INDEX idx_security_logs_guild ON security_audit_logs(guild_id, timestamp DESC);
CREATE INDEX idx_server_admins_guild ON server_admins(guild_id);
CREATE INDEX idx_server_backups_guild ON server_backups(guild_id, created_at DESC);
CREATE INDEX idx_server_staff_guild ON server_staff(guild_id);
CREATE INDEX idx_tickets_guild ON tickets(guild_id, status);
CREATE INDEX idx_warnings_guild_user ON warnings(guild_id, user_id);
CREATE INDEX idx_whitelist_audit_guild ON whitelist_audit(guild_id, timestamp DESC);
-- ==============================================================================
-- Join to Create Voice System (parity with SQLite migration 010)
-- ==============================================================================

CREATE TABLE IF NOT EXISTS "voice_config" (
    "guild_id" BIGINT PRIMARY KEY,
    "generator_channel_id" BIGINT,
    "category_id" BIGINT,
    "channel_name_format" TEXT DEFAULT '🔊・{username}',
    "default_user_limit" INTEGER DEFAULT 0,
    "default_bitrate" INTEGER DEFAULT 64000,
    "delete_when_empty" INTEGER DEFAULT 1,
    "is_enabled" INTEGER DEFAULT 1,
    "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "active_temp_channels" (
    "channel_id" BIGINT PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "owner_id" BIGINT NOT NULL,
    "control_panel_message_id" BIGINT,
    "is_locked" INTEGER DEFAULT 0,
    "is_hidden" INTEGER DEFAULT 0,
    "custom_status" TEXT,
    "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_temp_channels_guild ON active_temp_channels(guild_id);
CREATE INDEX IF NOT EXISTS idx_temp_channels_owner ON active_temp_channels(owner_id);

-- ==============================================================================
-- AI Wallpaper Studio
-- ==============================================================================

CREATE TABLE IF NOT EXISTS "wallpaper_channels" (
    "guild_id" BIGINT NOT NULL,
    "channel_id" BIGINT NOT NULL,
    "created_by" BIGINT,
    "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("guild_id", "channel_id")
);
