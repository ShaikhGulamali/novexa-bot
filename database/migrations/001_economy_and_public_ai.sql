-- GULAMALI ULTIMATE BOT
-- Database Migration 001: Economy, RPG, Games, Collectibles, Social & Public AI System

-- 1. Core Economy User Profiles
CREATE TABLE IF NOT EXISTS economy_users (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    wallet INTEGER DEFAULT 500,
    bank INTEGER DEFAULT 1000,
    gems INTEGER DEFAULT 10,
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    reputation INTEGER DEFAULT 0,
    daily_streak INTEGER DEFAULT 0,
    last_daily REAL DEFAULT 0.0,
    last_weekly REAL DEFAULT 0.0,
    last_monthly REAL DEFAULT 0.0,
    last_work REAL DEFAULT 0.0,
    last_crime REAL DEFAULT 0.0,
    last_slut REAL DEFAULT 0.0,
    last_rep REAL DEFAULT 0.0,
    last_hunt REAL DEFAULT 0.0,
    last_battle REAL DEFAULT 0.0,
    total_earned INTEGER DEFAULT 0,
    total_spent INTEGER DEFAULT 0,
    commands_used INTEGER DEFAULT 0,
    hunts_count INTEGER DEFAULT 0,
    battles_won INTEGER DEFAULT 0,
    battles_lost INTEGER DEFAULT 0,
    gambles_won INTEGER DEFAULT 0,
    gambles_lost INTEGER DEFAULT 0,
    is_banned INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, user_id)
);

-- 2. Audit Trail & Economy Transactions
CREATE TABLE IF NOT EXISTS economy_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    from_user_id INTEGER,
    to_user_id INTEGER,
    amount INTEGER NOT NULL,
    currency_type TEXT DEFAULT 'coins',
    tx_type TEXT NOT NULL,
    description TEXT DEFAULT '',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Items Catalog
CREATE TABLE IF NOT EXISTS economy_items (
    item_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    rarity TEXT NOT NULL,
    buy_price INTEGER DEFAULT 0,
    sell_price INTEGER DEFAULT 0,
    gem_price INTEGER DEFAULT 0,
    attack_bonus INTEGER DEFAULT 0,
    defense_bonus INTEGER DEFAULT 0,
    hunt_luck INTEGER DEFAULT 0,
    consumable INTEGER DEFAULT 0,
    max_stack INTEGER DEFAULT 999,
    icon TEXT DEFAULT '📦',
    slot TEXT DEFAULT NULL,
    special_ability TEXT DEFAULT ''
);

-- 4. User Inventories
CREATE TABLE IF NOT EXISTS economy_inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    item_id TEXT NOT NULL,
    quantity INTEGER DEFAULT 1,
    is_equipped INTEGER DEFAULT 0,
    slot TEXT DEFAULT NULL,
    acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(guild_id, user_id, item_id),
    FOREIGN KEY (item_id) REFERENCES economy_items(item_id) ON DELETE CASCADE
);

-- 5. Animals Catalog
CREATE TABLE IF NOT EXISTS economy_animals (
    animal_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    emoji TEXT NOT NULL,
    rarity TEXT NOT NULL,
    base_value INTEGER NOT NULL,
    base_xp INTEGER NOT NULL,
    catch_weight INTEGER NOT NULL,
    ability TEXT DEFAULT '',
    description TEXT DEFAULT ''
);

-- 6. User Animals (Zoo / Collection)
CREATE TABLE IF NOT EXISTS economy_user_animals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    animal_id TEXT NOT NULL,
    count INTEGER DEFAULT 1,
    is_favorite INTEGER DEFAULT 0,
    first_caught TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_caught TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(guild_id, user_id, animal_id),
    FOREIGN KEY (animal_id) REFERENCES economy_animals(animal_id) ON DELETE CASCADE
);

-- 7. Pets Catalog
CREATE TABLE IF NOT EXISTS economy_pets (
    pet_type TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    emoji TEXT NOT NULL,
    rarity TEXT NOT NULL,
    bonus_type TEXT NOT NULL,
    bonus_value REAL NOT NULL,
    description TEXT NOT NULL
);

-- 8. User Pets
CREATE TABLE IF NOT EXISTS economy_user_pets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    pet_type TEXT NOT NULL,
    nickname TEXT NOT NULL,
    level INTEGER DEFAULT 1,
    xp INTEGER DEFAULT 0,
    happiness INTEGER DEFAULT 100,
    is_equipped INTEGER DEFAULT 0,
    last_fed REAL DEFAULT 0.0,
    adopted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pet_type) REFERENCES economy_pets(pet_type) ON DELETE CASCADE
);

-- 9. PvP Battle Logs
CREATE TABLE IF NOT EXISTS economy_battles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    challenger_id INTEGER NOT NULL,
    opponent_id INTEGER NOT NULL,
    winner_id INTEGER NOT NULL,
    loser_id INTEGER NOT NULL,
    bet_amount INTEGER DEFAULT 0,
    xp_awarded INTEGER DEFAULT 0,
    battle_log TEXT DEFAULT '',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. Atomic Trading System
CREATE TABLE IF NOT EXISTS economy_trades (
    trade_id TEXT PRIMARY KEY,
    guild_id INTEGER NOT NULL,
    sender_id INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    sender_coins INTEGER DEFAULT 0,
    sender_items TEXT DEFAULT '[]',
    receiver_coins INTEGER DEFAULT 0,
    receiver_items TEXT DEFAULT '[]',
    sender_confirmed INTEGER DEFAULT 0,
    receiver_confirmed INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP DEFAULT NULL
);

-- 11. Marriage & Relationships
CREATE TABLE IF NOT EXISTS economy_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    user1_id INTEGER NOT NULL,
    user2_id INTEGER NOT NULL,
    ring_item_id TEXT DEFAULT 'diamond_ring',
    love_affinity INTEGER DEFAULT 100,
    married_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(guild_id, user1_id),
    UNIQUE(guild_id, user2_id)
);

-- 12. Friends
CREATE TABLE IF NOT EXISTS economy_friends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    friend_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(guild_id, user_id, friend_id)
);

-- 13. Achievements Catalog
CREATE TABLE IF NOT EXISTS economy_achievements (
    key TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    icon TEXT DEFAULT '🏆',
    gem_reward INTEGER DEFAULT 5,
    coin_reward INTEGER DEFAULT 500
);

-- 14. User Achievements Unlocks
CREATE TABLE IF NOT EXISTS economy_user_achievements (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    achievement_key TEXT NOT NULL,
    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, user_id, achievement_key),
    FOREIGN KEY (achievement_key) REFERENCES economy_achievements(key) ON DELETE CASCADE
);

-- 15. Economy Guild Settings
CREATE TABLE IF NOT EXISTS economy_guild_settings (
    guild_id INTEGER PRIMARY KEY,
    is_enabled INTEGER DEFAULT 1,
    currency_name TEXT DEFAULT 'GULAMALI COINS',
    currency_symbol TEXT DEFAULT '🪙',
    work_cooldown INTEGER DEFAULT 300,
    crime_cooldown INTEGER DEFAULT 600,
    slut_cooldown INTEGER DEFAULT 900,
    hunt_cooldown INTEGER DEFAULT 15,
    battle_cooldown INTEGER DEFAULT 60,
    channel_enforcement INTEGER DEFAULT 0,
    daily_reward_min INTEGER DEFAULT 500,
    daily_reward_max INTEGER DEFAULT 1000,
    weekly_reward INTEGER DEFAULT 5000,
    monthly_reward INTEGER DEFAULT 25000,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 16. Economy Channel Assignments
CREATE TABLE IF NOT EXISTS economy_channel_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    category_type TEXT NOT NULL,
    UNIQUE(guild_id, channel_id, category_type)
);

-- 17. Public AI Settings (Independent of AI Coding Agent)
CREATE TABLE IF NOT EXISTS public_ai_settings (
    guild_id INTEGER PRIMARY KEY,
    is_enabled INTEGER DEFAULT 1,
    provider TEXT DEFAULT 'gemini',
    model TEXT DEFAULT 'gemini-1.5-flash',
    cooldown_seconds INTEGER DEFAULT 3,
    hourly_limit INTEGER DEFAULT 50,
    system_prompt TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 18. Public AI Designated Channels
CREATE TABLE IF NOT EXISTS public_ai_channels (
    channel_id INTEGER PRIMARY KEY,
    guild_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 19. Public AI Multi-User Conversations
CREATE TABLE IF NOT EXISTS public_ai_conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    has_image INTEGER DEFAULT 0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 20. Public AI Usage Metrics
CREATE TABLE IF NOT EXISTS public_ai_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_eco_users_guild_wallet ON economy_users(guild_id, wallet DESC);
CREATE INDEX IF NOT EXISTS idx_eco_users_guild_level ON economy_users(guild_id, level DESC, xp DESC);
CREATE INDEX IF NOT EXISTS idx_eco_users_guild_rep ON economy_users(guild_id, reputation DESC);
CREATE INDEX IF NOT EXISTS idx_eco_inv_user ON economy_inventory(guild_id, user_id);
CREATE INDEX IF NOT EXISTS idx_eco_animals_user ON economy_user_animals(guild_id, user_id);
CREATE INDEX IF NOT EXISTS idx_eco_pets_user ON economy_user_pets(guild_id, user_id);
CREATE INDEX IF NOT EXISTS idx_eco_tx_guild ON economy_transactions(guild_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_eco_chan_guild ON economy_channel_settings(guild_id, category_type);
CREATE INDEX IF NOT EXISTS idx_pub_ai_chan_guild ON public_ai_channels(guild_id);
CREATE INDEX IF NOT EXISTS idx_pub_ai_conv ON public_ai_conversations(guild_id, channel_id, user_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_pub_ai_usage ON public_ai_usage(guild_id, timestamp);

