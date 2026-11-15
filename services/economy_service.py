"""NOVEXA - Production Economy, RPG & Collectibles Engine.

This service manages all database interactions, atomic balance transactions,
hunting odds, battle computations, inventory, pet progression, and achievements.
"""

import logging
import random
import time
import json
from typing import Optional, List, Dict, Any, Tuple
from database.database import db

logger = logging.getLogger("novexa.economy_service")

# ==================== CONSTANTS & BRANDING ====================
CURRENCY_NAME = "NOVEXA COINS"
CURRENCY_SYMBOL = "<a:933416goldenspincoin:1568628266774831195>"
GEM_NAME = "GEMS"
GEM_SYMBOL = "<a:422891purplediamond:1568627946485317632>"

# Color constants for Discord Embeds
COLOR_ECONOMY = 0x6C3483     # Royal Purple
COLOR_GOLD = 0xF1C40F        # Radiant Gold
COLOR_SUCCESS = 0x2ECC71     # Emerald Green
COLOR_DANGER = 0xE74C3C      # Crimson Red
COLOR_INFO = 0x3498DB        # Sky Blue
COLOR_DARK = 0x1E1B2E        # Novexa Midnight Dark Canvas

# ==================== DEFAULT CATALOGS ====================

DEFAULT_ITEMS: List[Dict[str, Any]] = [
    # --- SWORDS ---
    {
        "item_id": "wooden_sword",
        "name": "Wooden Training Sword",
        "description": "A basic wooden blade for aspiring warriors.",
        "category": "swords",
        "rarity": "Common",
        "buy_price": 150,
        "sell_price": 75,
        "gem_price": 0,
        "attack_bonus": 6,
        "defense_bonus": 0,
        "hunt_luck": 0,
        "consumable": 0,
        "icon": "🗡️",
        "slot": "weapon",
        "special_ability": "Basic Strike (+6 ATK)",
    },
    {
        "item_id": "iron_sword",
        "name": "Forged Iron Katana",
        "description": "A razor-sharp iron katana forged in the heart of Novexa armory.",
        "category": "swords",
        "rarity": "Uncommon",
        "buy_price": 600,
        "sell_price": 300,
        "gem_price": 0,
        "attack_bonus": 18,
        "defense_bonus": 2,
        "hunt_luck": 2,
        "consumable": 0,
        "icon": "⚔️",
        "slot": "weapon",
        "special_ability": "Swift Slash (+18 ATK)",
    },
    {
        "item_id": "shadow_blade",
        "name": "Shadow Assassin Blade",
        "description": "Enveloped in dark aura, striking fear into rivals.",
        "category": "swords",
        "rarity": "Rare",
        "buy_price": 2800,
        "sell_price": 1400,
        "gem_price": 0,
        "attack_bonus": 42,
        "defense_bonus": 5,
        "hunt_luck": 5,
        "consumable": 0,
        "icon": "🗡️",
        "slot": "weapon",
        "special_ability": "Shadow Flurry (+42 ATK, 10% Crit)",
    },
    {
        "item_id": "crimson_slayer",
        "name": "Crimson Dragon Slayer",
        "description": "Tempered in dragon fire with devastating crushing power.",
        "category": "swords",
        "rarity": "Epic",
        "buy_price": 12000,
        "sell_price": 6000,
        "gem_price": 25,
        "attack_bonus": 85,
        "defense_bonus": 15,
        "hunt_luck": 8,
        "consumable": 0,
        "icon": "🔥",
        "slot": "weapon",
        "special_ability": "Infernal Blaze (+85 ATK, Lifesteal)",
    },
    {
        "item_id": "celestial_blade",
        "name": "Celestial Blade of Novexa",
        "description": "The ultimate mythical weapon whispered of in galactic legends.",
        "category": "swords",
        "rarity": "Mythical",
        "buy_price": 60000,
        "sell_price": 30000,
        "gem_price": 100,
        "attack_bonus": 200,
        "defense_bonus": 40,
        "hunt_luck": 20,
        "consumable": 0,
        "icon": "✨",
        "slot": "weapon",
        "special_ability": "Divine Judgement (+200 ATK, 25% True Damage)",
    },

    # --- GUNS (FICTIONAL GAME GEAR) ---
    {
        "item_id": "plasma_pistol",
        "name": "Pulse Plasma Pistol",
        "description": "Compact sci-fi sidearm firing superheated electromagnetic bursts.",
        "category": "guns",
        "rarity": "Uncommon",
        "buy_price": 850,
        "sell_price": 420,
        "gem_price": 0,
        "attack_bonus": 22,
        "defense_bonus": 0,
        "hunt_luck": 3,
        "consumable": 0,
        "icon": "🔫",
        "slot": "weapon",
        "special_ability": "Overcharge Pulse (+22 ATK)",
    },
    {
        "item_id": "cyber_shotgun",
        "name": "Cybernetic Scatter Blaster",
        "description": "High-impact close-quarters energy weapon.",
        "category": "guns",
        "rarity": "Rare",
        "buy_price": 3500,
        "sell_price": 1750,
        "gem_price": 0,
        "attack_bonus": 50,
        "defense_bonus": 5,
        "hunt_luck": 6,
        "consumable": 0,
        "icon": "💥",
        "slot": "weapon",
        "special_ability": "Spread Fire (+50 ATK)",
    },
    {
        "item_id": "vortex_rifle",
        "name": "Void Vortex Sniper",
        "description": "Long-range anti-material kinetic blaster with pinpoint thermal targeting.",
        "category": "guns",
        "rarity": "Epic",
        "buy_price": 14000,
        "sell_price": 7000,
        "gem_price": 30,
        "attack_bonus": 95,
        "defense_bonus": 10,
        "hunt_luck": 12,
        "consumable": 0,
        "icon": "⚡",
        "slot": "weapon",
        "special_ability": "Vortex Piercer (+95 ATK, 15% Armor Piercing)",
    },
    {
        "item_id": "antimatter_cannon",
        "name": "Antimatter Obliterator",
        "description": "Experimental heavy artillery harnessing concentrated dark energy.",
        "category": "guns",
        "rarity": "Legendary",
        "buy_price": 40000,
        "sell_price": 20000,
        "gem_price": 75,
        "attack_bonus": 160,
        "defense_bonus": 25,
        "hunt_luck": 18,
        "consumable": 0,
        "icon": "☄️",
        "slot": "weapon",
        "special_ability": "Singularity Blast (+160 ATK)",
    },

    # --- BOWS ---
    {
        "item_id": "hunting_bow",
        "name": "Oak Ranger Bow",
        "description": "A supple wooden bow preferred by woodland scouts.",
        "category": "bows",
        "rarity": "Common",
        "buy_price": 220,
        "sell_price": 110,
        "gem_price": 0,
        "attack_bonus": 10,
        "defense_bonus": 0,
        "hunt_luck": 6,
        "consumable": 0,
        "icon": "🏹",
        "slot": "weapon",
        "special_ability": "Scout Shot (+10 ATK, +6% Hunt Luck)",
    },
    {
        "item_id": "windrunner_bow",
        "name": "Windrunner Composite Bow",
        "description": "Crafted from enchanted yew and silkstring for swift hunting.",
        "category": "bows",
        "rarity": "Rare",
        "buy_price": 3200,
        "sell_price": 1600,
        "gem_price": 0,
        "attack_bonus": 38,
        "defense_bonus": 5,
        "hunt_luck": 15,
        "consumable": 0,
        "icon": "🌪️",
        "slot": "weapon",
        "special_ability": "Gale Force (+38 ATK, +15% Hunt Luck)",
    },
    {
        "item_id": "astral_bow",
        "name": "Astral Starfall Bow",
        "description": "Fires arrows forged from falling starlight.",
        "category": "bows",
        "rarity": "Epic",
        "buy_price": 13500,
        "sell_price": 6750,
        "gem_price": 28,
        "attack_bonus": 80,
        "defense_bonus": 15,
        "hunt_luck": 25,
        "consumable": 0,
        "icon": "🌠",
        "slot": "weapon",
        "special_ability": "Starfall Volley (+80 ATK, +25% Hunt Luck)",
    },

    # --- SHIELDS ---
    {
        "item_id": "wooden_buckler",
        "name": "Sturdy Wooden Buckler",
        "description": "Lightweight buckler capable of deflecting small hits.",
        "category": "shields",
        "rarity": "Common",
        "buy_price": 180,
        "sell_price": 90,
        "gem_price": 0,
        "attack_bonus": 0,
        "defense_bonus": 8,
        "hunt_luck": 0,
        "consumable": 0,
        "icon": "🛡️",
        "slot": "shield",
        "special_ability": "Block (+8 DEF)",
    },
    {
        "item_id": "iron_shield",
        "name": "Iron Tower Shield",
        "description": "Heavy fortified iron shield offering dependable protection.",
        "category": "shields",
        "rarity": "Uncommon",
        "buy_price": 750,
        "sell_price": 375,
        "gem_price": 0,
        "attack_bonus": 0,
        "defense_bonus": 22,
        "hunt_luck": 0,
        "consumable": 0,
        "icon": "🛡️",
        "slot": "shield",
        "special_ability": "Iron Wall (+22 DEF)",
    },
    {
        "item_id": "guardian_aegis",
        "name": "Guardian Aegis of Valour",
        "description": "Gleaming golden shield etched with defensive runes.",
        "category": "shields",
        "rarity": "Epic",
        "buy_price": 9500,
        "sell_price": 4750,
        "gem_price": 20,
        "attack_bonus": 5,
        "defense_bonus": 65,
        "hunt_luck": 5,
        "consumable": 0,
        "icon": "🔰",
        "slot": "shield",
        "special_ability": "Divine Barrier (+65 DEF, 10% Damage Reflection)",
    },
    {
        "item_id": "celestial_shield",
        "name": "Novexa Divine Bastion",
        "description": "An impenetrable barrier blessed by the celestial guardians.",
        "category": "shields",
        "rarity": "Legendary",
        "buy_price": 35000,
        "sell_price": 17500,
        "gem_price": 60,
        "attack_bonus": 15,
        "defense_bonus": 130,
        "hunt_luck": 10,
        "consumable": 0,
        "icon": "💎",
        "slot": "shield",
        "special_ability": "Invulnerable Fortress (+130 DEF, 20% Reflection)",
    },

    # --- ARMOR ---
    {
        "item_id": "leather_tunic",
        "name": "Trapper's Leather Armor",
        "description": "Supple treated leather suited for stealth and maneuverability.",
        "category": "armor",
        "rarity": "Common",
        "buy_price": 250,
        "sell_price": 125,
        "gem_price": 0,
        "attack_bonus": 2,
        "defense_bonus": 10,
        "hunt_luck": 5,
        "consumable": 0,
        "icon": "🦺",
        "slot": "armor",
        "special_ability": "Agile Step (+10 DEF, +5% Hunt Luck)",
    },
    {
        "item_id": "dragon_scale_armor",
        "name": "Dragonscale Carapace",
        "description": "Armor woven from red dragon scales, naturally resistant to elements.",
        "category": "armor",
        "rarity": "Rare",
        "buy_price": 4500,
        "sell_price": 2250,
        "gem_price": 0,
        "attack_bonus": 10,
        "defense_bonus": 45,
        "hunt_luck": 8,
        "consumable": 0,
        "icon": "🥋",
        "slot": "armor",
        "special_ability": "Draconic Ward (+45 DEF, +10 ATK)",
    },
    {
        "item_id": "cyber_exo_suit",
        "name": "Nanotech Combat Exosuit",
        "description": "State-of-the-art powered exoskeleton amplifying physical endurance.",
        "category": "armor",
        "rarity": "Legendary",
        "buy_price": 32000,
        "sell_price": 16000,
        "gem_price": 55,
        "attack_bonus": 35,
        "defense_bonus": 115,
        "hunt_luck": 15,
        "consumable": 0,
        "icon": "🤖",
        "slot": "armor",
        "special_ability": "Kinetic Overload (+115 DEF, +35 ATK)",
    },

    # --- HUNTING EQUIPMENT ---
    {
        "item_id": "basic_net",
        "name": "Trapper's Basic Net",
        "description": "A durable woven net for snaring wild fauna.",
        "category": "hunting",
        "rarity": "Common",
        "buy_price": 120,
        "sell_price": 60,
        "gem_price": 0,
        "attack_bonus": 0,
        "defense_bonus": 0,
        "hunt_luck": 10,
        "consumable": 0,
        "icon": "🕸️",
        "slot": "hunting_tool",
        "special_ability": "+10% Animal Catch Rate",
    },
    {
        "item_id": "safari_rifle",
        "name": "Safari Dart Tranquilizer",
        "description": "High-accuracy dart rifle ensuring safe animal captures.",
        "category": "hunting",
        "rarity": "Rare",
        "buy_price": 3800,
        "sell_price": 1900,
        "gem_price": 0,
        "attack_bonus": 5,
        "defense_bonus": 0,
        "hunt_luck": 25,
        "consumable": 0,
        "icon": "🎯",
        "slot": "hunting_tool",
        "special_ability": "+25% Catch Rate & +10% Rare Encounter",
    },
    {
        "item_id": "master_net",
        "name": "Master Hunter Energy Net",
        "description": "Electrified containment net capable of capturing powerful beasts.",
        "category": "hunting",
        "rarity": "Epic",
        "buy_price": 11000,
        "sell_price": 5500,
        "gem_price": 20,
        "attack_bonus": 10,
        "defense_bonus": 5,
        "hunt_luck": 40,
        "consumable": 0,
        "icon": "⚡",
        "slot": "hunting_tool",
        "special_ability": "+40% Catch Rate & +20% Rare/Epic Encounter",
    },
    {
        "item_id": "golden_lasso",
        "name": "Golden Celestial Lasso",
        "description": "The fabled lasso capable of subduing mythical creatures.",
        "category": "hunting",
        "rarity": "Mythical",
        "buy_price": 50000,
        "sell_price": 25000,
        "gem_price": 90,
        "attack_bonus": 25,
        "defense_bonus": 20,
        "hunt_luck": 65,
        "consumable": 0,
        "icon": "🪢",
        "slot": "hunting_tool",
        "special_ability": "+65% Catch Rate & Massive Mythic Encounter Boost",
    },

    # --- SPECIAL ITEMS & BOOSTERS ---
    {
        "item_id": "lucky_charm",
        "name": "Lucky 4-Leaf Clover",
        "description": "A radiant clover that increases coins earned from activities.",
        "category": "boosters",
        "rarity": "Rare",
        "buy_price": 1800,
        "sell_price": 900,
        "gem_price": 0,
        "attack_bonus": 0,
        "defense_bonus": 0,
        "hunt_luck": 10,
        "consumable": 1,
        "icon": "🍀",
        "slot": None,
        "special_ability": "+20% Work & Crime Payouts",
    },
    {
        "item_id": "exp_booster",
        "name": "Ancient Wisdom Scroll",
        "description": "Contains forbidden knowledge granting bonus XP.",
        "category": "boosters",
        "rarity": "Rare",
        "buy_price": 2500,
        "sell_price": 1250,
        "gem_price": 0,
        "attack_bonus": 0,
        "defense_bonus": 0,
        "hunt_luck": 0,
        "consumable": 1,
        "icon": "📜",
        "slot": None,
        "special_ability": "Grants +1,000 XP instantly on use",
    },
    {
        "item_id": "golden_horseshoe",
        "name": "Golden Horseshoe",
        "description": "Favored by casino champions for higher gambling luck.",
        "category": "special",
        "rarity": "Epic",
        "buy_price": 6000,
        "sell_price": 3000,
        "gem_price": 15,
        "attack_bonus": 0,
        "defense_bonus": 0,
        "hunt_luck": 5,
        "consumable": 0,
        "icon": "🧲",
        "slot": None,
        "special_ability": "+15% Extra Winnings on Gambling",
    },
    {
        "item_id": "diamond_ring",
        "name": "Diamond Engagement Ring",
        "description": "An exquisite diamond ring required to propose with `/marry`.",
        "category": "special",
        "rarity": "Rare",
        "buy_price": 10000,
        "sell_price": 5000,
        "gem_price": 20,
        "attack_bonus": 0,
        "defense_bonus": 0,
        "hunt_luck": 0,
        "consumable": 1,
        "icon": "💍",
        "slot": None,
        "special_ability": "Propose Marriage to your soulmate",
    },
    {
        "item_id": "pet_food",
        "name": "Gourmet Pet Feast",
        "description": "Nutritious gourmet chow that pets love.",
        "category": "special",
        "rarity": "Common",
        "buy_price": 75,
        "sell_price": 30,
        "gem_price": 0,
        "attack_bonus": 0,
        "defense_bonus": 0,
        "hunt_luck": 0,
        "consumable": 1,
        "icon": "🍖",
        "slot": None,
        "special_ability": "Restores +40 Pet Happiness & +25 Pet XP",
    },

    # --- CRATES ---
    {
        "item_id": "common_crate",
        "name": "Oak Mystery Crate",
        "description": "Contains coins, gems, and common/uncommon items.",
        "category": "crates",
        "rarity": "Common",
        "buy_price": 500,
        "sell_price": 250,
        "gem_price": 0,
        "attack_bonus": 0,
        "defense_bonus": 0,
        "hunt_luck": 0,
        "consumable": 1,
        "icon": "📦",
        "slot": None,
        "special_ability": "Open for 250-800 Coins + 1-3 Gems + Items",
    },
    {
        "item_id": "rare_crate",
        "name": "Silver Treasure Crate",
        "description": "Contains abundant coins, gems, and rare equipment.",
        "category": "crates",
        "rarity": "Rare",
        "buy_price": 2200,
        "sell_price": 1100,
        "gem_price": 5,
        "attack_bonus": 0,
        "defense_bonus": 0,
        "hunt_luck": 0,
        "consumable": 1,
        "icon": "🧰",
        "slot": None,
        "special_ability": "Open for 1,500-4,000 Coins + 4-10 Gems + Rare Drops",
    },
    {
        "item_id": "epic_crate",
        "name": "Royal Amethyst Crate",
        "description": "Loot crate shimmering with purple royal gems and epic gear.",
        "category": "crates",
        "rarity": "Epic",
        "buy_price": 8000,
        "sell_price": 4000,
        "gem_price": 18,
        "attack_bonus": 0,
        "defense_bonus": 0,
        "hunt_luck": 0,
        "consumable": 1,
        "icon": "🔮",
        "slot": None,
        "special_ability": "Open for 6,000-15,000 Coins + 12-30 Gems + Epic Gear",
    },
    {
        "item_id": "legendary_crate",
        "name": "Celestial Novexa Vault",
        "description": "The pinnacle vault offering massive wealth and mythical artifacts.",
        "category": "crates",
        "rarity": "Legendary",
        "buy_price": 30000,
        "sell_price": 15000,
        "gem_price": 60,
        "attack_bonus": 0,
        "defense_bonus": 0,
        "hunt_luck": 0,
        "consumable": 1,
        "icon": "👑",
        "slot": None,
        "special_ability": "Open for 25,000-75,000 Coins + 40-100 Gems + Mythic Drops",
    },

    # --- COLLECTIBLES ---
    {
        "item_id": "bronze_trophy",
        "name": "Bronze Hunter Trophy",
        "description": "Commemorating 10 successful animal hunts.",
        "category": "collectibles",
        "rarity": "Common",
        "buy_price": 1000,
        "sell_price": 500,
        "gem_price": 0,
        "attack_bonus": 0,
        "defense_bonus": 0,
        "hunt_luck": 2,
        "consumable": 0,
        "icon": "🥉",
        "slot": None,
        "special_ability": "Hunter Status Symbol",
    },
    {
        "item_id": "silver_trophy",
        "name": "Silver Gladiator Trophy",
        "description": "Commemorating arena dominance.",
        "category": "collectibles",
        "rarity": "Rare",
        "buy_price": 5000,
        "sell_price": 2500,
        "gem_price": 10,
        "attack_bonus": 5,
        "defense_bonus": 5,
        "hunt_luck": 5,
        "consumable": 0,
        "icon": "🥈",
        "slot": None,
        "special_ability": "Gladiator Status Symbol",
    },
    {
        "item_id": "gold_trophy",
        "name": "Gold Champion Trophy",
        "description": "Awarded to the true elite champions of the server.",
        "category": "collectibles",
        "rarity": "Epic",
        "buy_price": 25000,
        "sell_price": 12500,
        "gem_price": 40,
        "attack_bonus": 15,
        "defense_bonus": 15,
        "hunt_luck": 10,
        "consumable": 0,
        "icon": "🥇",
        "slot": None,
        "special_ability": "Champion Prestige Status",
    },
    {
        "item_id": "gulamali_crown",
        "name": "Royal Crown of Novexa",
        "description": "The ultimate symbol of power, royalty, and unimaginable wealth.",
        "category": "collectibles",
        "rarity": "Mythical",
        "buy_price": 120000,
        "sell_price": 60000,
        "gem_price": 200,
        "attack_bonus": 50,
        "defense_bonus": 50,
        "hunt_luck": 25,
        "consumable": 0,
        "icon": "👑",
        "slot": None,
        "special_ability": "Gives +20% Bonus on all Earnings & Mythic Aura",
    },
]

# ==================== ANIMALS CATALOG (50+ Animals across 6 Rarities) ====================

DEFAULT_ANIMALS: List[Dict[str, Any]] = [
    # --- COMMON (Weight: 50) ---
    {"animal_id": "rat", "name": "Brown Rat", "emoji": "🐀", "rarity": "Common", "base_value": 20, "base_xp": 8, "catch_weight": 50, "ability": "Nibble", "description": "A quick city scurryer."},
    {"animal_id": "hamster", "name": "Fluffy Hamster", "emoji": "🐹", "rarity": "Common", "base_value": 25, "base_xp": 10, "catch_weight": 50, "ability": "Cheek Stash", "description": "Hides seeds in its fluffy cheeks."},
    {"animal_id": "rabbit", "name": "Cottontail Rabbit", "emoji": "🐰", "rarity": "Common", "base_value": 30, "base_xp": 12, "catch_weight": 48, "ability": "Hop", "description": "Quick-footed meadow hopper."},
    {"animal_id": "frog", "name": "Green Tree Frog", "emoji": "🐸", "rarity": "Common", "base_value": 25, "base_xp": 10, "catch_weight": 50, "ability": "Croak", "description": "Sticky web-footed amphibian."},
    {"animal_id": "duck", "name": "Mallard Duck", "emoji": "🦆", "rarity": "Common", "base_value": 35, "base_xp": 14, "catch_weight": 45, "ability": "Quack", "description": "Pond swimmer with vibrant plumage."},
    {"animal_id": "chicken", "name": "Farm Chicken", "emoji": "🐔", "rarity": "Common", "base_value": 28, "base_xp": 11, "catch_weight": 48, "ability": "Peck", "description": "Always looking for grains."},
    {"animal_id": "fish", "name": "Golden Carp", "emoji": "🐟", "rarity": "Common", "base_value": 22, "base_xp": 9, "catch_weight": 50, "ability": "Splash", "description": "Glistens under river ripples."},
    {"animal_id": "caterpillar", "name": "Silk Caterpillar", "emoji": "🐛", "rarity": "Common", "base_value": 18, "base_xp": 7, "catch_weight": 50, "ability": "Crawl", "description": "Munching peaceful garden leaves."},
    {"animal_id": "bird", "name": "Blue Songbird", "emoji": "🐦", "rarity": "Common", "base_value": 32, "base_xp": 13, "catch_weight": 47, "ability": "Song", "description": "Chirps a delightful morning tune."},
    {"animal_id": "chipmunk", "name": "Forest Chipmunk", "emoji": "🐿️", "rarity": "Common", "base_value": 30, "base_xp": 12, "catch_weight": 48, "ability": "Scurry", "description": "Hoards acorns for the winter."},

    # --- UNCOMMON (Weight: 25) ---
    {"animal_id": "fox", "name": "Red Fox", "emoji": "🦊", "rarity": "Uncommon", "base_value": 75, "base_xp": 28, "catch_weight": 25, "ability": "Cunning", "description": "Clever hunter of the twilight."},
    {"animal_id": "raccoon", "name": "Masked Raccoon", "emoji": "🦝", "rarity": "Uncommon", "base_value": 80, "base_xp": 30, "catch_weight": 24, "ability": "Scavenge", "description": "Inquisitive nighttime bandit."},
    {"animal_id": "boar", "name": "Wild Boar", "emoji": "🐗", "rarity": "Uncommon", "base_value": 90, "base_xp": 35, "catch_weight": 22, "ability": "Tusk Charge", "description": "Tough hide and aggressive tusks."},
    {"animal_id": "wolf", "name": "Timber Wolf", "emoji": "🐺", "rarity": "Uncommon", "base_value": 110, "base_xp": 42, "catch_weight": 20, "ability": "Pack Howl", "description": "Alpha runner of the boreal forests."},
    {"animal_id": "bat", "name": "Cavern Bat", "emoji": "🦇", "rarity": "Uncommon", "base_value": 70, "base_xp": 26, "catch_weight": 25, "ability": "Echolocation", "description": "Flits through subterranean shadows."},
    {"animal_id": "owl", "name": "Barn Owl", "emoji": "🦉", "rarity": "Uncommon", "base_value": 95, "base_xp": 38, "catch_weight": 22, "ability": "Silent Flight", "description": "Nocturnal hunter with piercing sight."},
    {"animal_id": "hedgehog", "name": "Spiny Hedgehog", "emoji": "🦔", "rarity": "Uncommon", "base_value": 65, "base_xp": 25, "catch_weight": 26, "ability": "Quill Shield", "description": "Rolls into an impenetrable prickly ball."},
    {"animal_id": "skunk", "name": "Striped Skunk", "emoji": "🦨", "rarity": "Uncommon", "base_value": 60, "base_xp": 24, "catch_weight": 26, "ability": "Stench Cloud", "description": "Keep your distance from its tail."},
    {"animal_id": "otter", "name": "River Otter", "emoji": "🦦", "rarity": "Uncommon", "base_value": 85, "base_xp": 32, "catch_weight": 23, "ability": "Water Play", "description": "Playful and skilled swimmer."},
    {"animal_id": "beaver", "name": "Builder Beaver", "emoji": "🦫", "rarity": "Uncommon", "base_value": 78, "base_xp": 29, "catch_weight": 24, "ability": "Dam Builder", "description": "Tireless engineer of the streams."},

    # --- RARE (Weight: 14) ---
    {"animal_id": "bear", "name": "Grizzly Bear", "emoji": "🐻", "rarity": "Rare", "base_value": 260, "base_xp": 90, "catch_weight": 14, "ability": "Mighty Roar", "description": "Colossal apex predator of the mountains."},
    {"animal_id": "deer", "name": "Stag of the Glen", "emoji": "🦌", "rarity": "Rare", "base_value": 240, "base_xp": 80, "catch_weight": 14, "ability": "Antler Clash", "description": "Majestic antlers crowned with moss."},
    {"animal_id": "eagle", "name": "Golden Eagle", "emoji": "🦅", "rarity": "Rare", "base_value": 310, "base_xp": 105, "catch_weight": 13, "ability": "Talon Dive", "description": "Ruler of the thermals and alpine peaks."},
    {"animal_id": "leopard", "name": "Snow Leopard", "emoji": "🐆", "rarity": "Rare", "base_value": 350, "base_xp": 120, "catch_weight": 12, "ability": "Ghost Pounce", "description": "Silent phantom of the frosty crags."},
    {"animal_id": "crocodile", "name": "Nile Crocodile", "emoji": "🐊", "rarity": "Rare", "base_value": 290, "base_xp": 95, "catch_weight": 13, "ability": "Death Roll", "description": "Armored jaws with bone-crushing grip."},
    {"animal_id": "shark", "name": "Great White Shark", "emoji": "🦈", "rarity": "Rare", "base_value": 380, "base_xp": 130, "catch_weight": 11, "ability": "Apex Scent", "description": "Terrifying monarch of the open ocean."},
    {"animal_id": "cobra", "name": "King Cobra", "emoji": "🐍", "rarity": "Rare", "base_value": 270, "base_xp": 92, "catch_weight": 14, "ability": "Venomous Strike", "description": "Hooded serpent with lethal neurotoxin."},
    {"animal_id": "gorilla", "name": "Silverback Gorilla", "emoji": "🦍", "rarity": "Rare", "base_value": 360, "base_xp": 125, "catch_weight": 12, "ability": "Chest Beat", "description": "Unrivaled jungle brute strength."},
    {"animal_id": "seal", "name": "Arctic Leopard Seal", "emoji": "🦭", "rarity": "Rare", "base_value": 250, "base_xp": 85, "catch_weight": 14, "ability": "Glacial Glide", "description": "Torpedos through icy waters."},
    {"animal_id": "flamingo", "name": "Crimson Flamingo", "emoji": "🦩", "rarity": "Rare", "base_value": 230, "base_xp": 78, "catch_weight": 14, "ability": "Balancing Act", "description": "Vibrant pink plumage and graceful poise."},

    # --- EPIC (Weight: 7) ---
    {"animal_id": "lion", "name": "African Sun Lion", "emoji": "🦁", "rarity": "Epic", "base_value": 1100, "base_xp": 320, "catch_weight": 7, "ability": "King's Roar", "description": "Golden mane glowing like the midday sun."},
    {"animal_id": "tiger", "name": "Bengal Royal Tiger", "emoji": "🐯", "rarity": "Epic", "base_value": 1250, "base_xp": 360, "catch_weight": 7, "ability": "Stealth Ambush", "description": "Striped stalker of legendary grace."},
    {"animal_id": "elephant", "name": "Colossal Mammoth-Elephant", "emoji": "🐘", "rarity": "Epic", "base_value": 1400, "base_xp": 400, "catch_weight": 6, "ability": "Earthquake Trample", "description": "Gentle giant capable of shattering rocks."},
    {"animal_id": "rhino", "name": "Armored Iron Rhino", "emoji": "🦏", "rarity": "Epic", "base_value": 1200, "base_xp": 340, "catch_weight": 7, "ability": "Horn Breach", "description": "A walking fortress of solid muscle."},
    {"animal_id": "whale", "name": "Ancient Blue Whale", "emoji": "🐋", "rarity": "Epic", "base_value": 1600, "base_xp": 450, "catch_weight": 5, "ability": "Deep Ocean Song", "description": "Oldest creature singing across hemispheres."},
    {"animal_id": "octopus", "name": "Kraken-Blood Octopus", "emoji": "🐙", "rarity": "Epic", "base_value": 1300, "base_xp": 375, "catch_weight": 6, "ability": "Ink Vortex", "description": "Eight powerful tentacles with suction grip."},
    {"animal_id": "panda", "name": "Celestial Giant Panda", "emoji": "🐼", "rarity": "Epic", "base_value": 1500, "base_xp": 420, "catch_weight": 6, "ability": "Zen Balance", "description": "Wise and revered guardian of the bamboo peaks."},
    {"animal_id": "peacock", "name": "Jeweled Imperial Peacock", "emoji": "🦚", "rarity": "Epic", "base_value": 1150, "base_xp": 330, "catch_weight": 7, "ability": "Prismatic Dazzle", "description": "Fan feathers encrusted with emerald eyes."},

    # --- LEGENDARY (Weight: 3) ---
    {"animal_id": "unicorn", "name": "Starlight Unicorn", "emoji": "🦄", "rarity": "Legendary", "base_value": 4500, "base_xp": 1100, "catch_weight": 3, "ability": "Purifying Horn", "description": "A creature of pure light and celestial virtue."},
    {"animal_id": "wyvern", "name": "Stormcloud Wyvern", "emoji": "🐲", "rarity": "Legendary", "base_value": 5200, "base_xp": 1300, "catch_weight": 3, "ability": "Lightning Breath", "description": "Soars amidst thunderstorm vortexes."},
    {"animal_id": "thunderbird", "name": "Thunderbird of Thunderpeaks", "emoji": "🦅", "rarity": "Legendary", "base_value": 4800, "base_xp": 1200, "catch_weight": 3, "ability": "Tempest Claws", "description": "Wingbeats sound like rolling thunder."},
    {"animal_id": "kraken", "name": "Abyssal Kraken", "emoji": "🦑", "rarity": "Legendary", "base_value": 6000, "base_xp": 1500, "catch_weight": 2, "ability": "Tidal Maelstrom", "description": "Drags entire galleons into the abyss."},
    {"animal_id": "fenrir", "name": "Frost Fenrir Wolf", "emoji": "🐺", "rarity": "Legendary", "base_value": 5500, "base_xp": 1400, "catch_weight": 3, "ability": "Glacial Howl", "description": "Chained in ancient ice until now."},
    {"animal_id": "chimera", "name": "Infernal Chimera", "emoji": "🦁", "rarity": "Legendary", "base_value": 5000, "base_xp": 1250, "catch_weight": 3, "ability": "Triple Menace", "description": "Part lion, goat, and dragon serpent."},

    # --- MYTHICAL (Weight: 1) ---
    {"animal_id": "gulamali_dragon", "name": "Novexa Ancient Void Dragon", "emoji": "🐉", "rarity": "Mythical", "base_value": 25000, "base_xp": 4500, "catch_weight": 1, "ability": "Cosmic Void Nova", "description": "The patron deity of the Novexa universe."},
    {"animal_id": "phoenix", "name": "Eternal Phoenix Sovereign", "emoji": "🔥", "rarity": "Mythical", "base_value": 22000, "base_xp": 4000, "catch_weight": 1, "ability": "Rebirth Flame", "description": "Burns perpetually and rises from stardust."},
    {"animal_id": "kirin", "name": "Celestial Golden Kirin", "emoji": "⚡", "rarity": "Mythical", "base_value": 20000, "base_xp": 3600, "catch_weight": 1, "ability": "Sacred Lightning", "description": "Herald of supreme fortune and cosmic harmony."},
    {"animal_id": "leviathan", "name": "Star Leviathan", "emoji": "🌌", "rarity": "Mythical", "base_value": 24000, "base_xp": 4200, "catch_weight": 1, "ability": "Gravity Collapse", "description": "Swims through deep nebulae between stars."},
    {"animal_id": "golden_lion", "name": "Imperial Solar Lion of Novexa", "emoji": "👑", "rarity": "Mythical", "base_value": 30000, "base_xp": 5000, "catch_weight": 1, "ability": "Solar Flare Roar", "description": "Crowned monarch of all living beasts."},
]

# ==================== PETS CATALOG ====================

DEFAULT_PETS: List[Dict[str, Any]] = [
    {
        "pet_type": "pet_dog",
        "name": "Loyal Shiba Inu",
        "emoji": "🐕",
        "rarity": "Common",
        "bonus_type": "hunt_luck",
        "bonus_value": 5.0,
        "description": "Increases hunting catch rate by +5% per pet level.",
    },
    {
        "pet_type": "pet_cat",
        "name": "Lucky Calico Cat",
        "emoji": "🐱",
        "rarity": "Common",
        "bonus_type": "coin_boost",
        "bonus_value": 5.0,
        "description": "Increases coin rewards from work and games by +5% per pet level.",
    },
    {
        "pet_type": "pet_wolf",
        "name": "Frost Direwolf",
        "emoji": "🐺",
        "rarity": "Uncommon",
        "bonus_type": "battle_attack",
        "bonus_value": 8.0,
        "description": "Boosts battle attack power by +8% per pet level.",
    },
    {
        "pet_type": "pet_owl",
        "name": "Mystic Astral Owl",
        "emoji": "🦉",
        "rarity": "Uncommon",
        "bonus_type": "xp_boost",
        "bonus_value": 10.0,
        "description": "Boosts XP gains by +10% per pet level.",
    },
    {
        "pet_type": "pet_bear",
        "name": "Ironclad Armored Bear",
        "emoji": "🐻",
        "rarity": "Rare",
        "bonus_type": "battle_defense",
        "bonus_value": 12.0,
        "description": "Boosts defense shields in combat by +12% per pet level.",
    },
    {
        "pet_type": "pet_fox",
        "name": "Nine-Tailed Kitsune",
        "emoji": "🦊",
        "rarity": "Rare",
        "bonus_type": "hunt_luck",
        "bonus_value": 14.0,
        "description": "Increases hunting catch chance & rare odds by +14% per pet level.",
    },
    {
        "pet_type": "pet_griffin",
        "name": "Golden High Griffin",
        "emoji": "🦅",
        "rarity": "Epic",
        "bonus_type": "battle_attack",
        "bonus_value": 18.0,
        "description": "Devastating sky combat attack +18% per pet level.",
    },
    {
        "pet_type": "pet_phoenix",
        "name": "Immortal Solar Phoenix",
        "emoji": "🔥",
        "rarity": "Legendary",
        "bonus_type": "battle_attack",
        "bonus_value": 25.0,
        "description": "Burns opponents and grants +25% attack per pet level.",
    },
    {
        "pet_type": "pet_dragon",
        "name": "Novexa Void Wyrm",
        "emoji": "🐉",
        "rarity": "Mythical",
        "bonus_type": "hunt_luck",
        "bonus_value": 30.0,
        "description": "Supreme companion boosting hunting luck, battle, and rewards by +30% per level.",
    },
]

# ==================== ACHIEVEMENTS CATALOG ====================

DEFAULT_ACHIEVEMENTS: List[Dict[str, Any]] = [
    {"key": "first_coin", "name": "First Steps", "description": "Earn your first Novexa Coins.", "icon": "🪙", "gem_reward": 5, "coin_reward": 250},
    {"key": "first_hunt", "name": "Novice Trapper", "description": "Catch your very first animal with /hunt.", "icon": "🐾", "gem_reward": 5, "coin_reward": 300},
    {"key": "hunts_25", "name": "Seasoned Tracker", "description": "Catch 25 wild animals.", "icon": "🎯", "gem_reward": 15, "coin_reward": 1500},
    {"key": "hunts_100", "name": "Master of the Wild", "description": "Catch 100 wild animals.", "icon": "🏹", "gem_reward": 40, "coin_reward": 5000},
    {"key": "mythic_catch", "name": "Legendary Safari", "description": "Successfully catch a Mythical animal.", "icon": "🐉", "gem_reward": 60, "coin_reward": 12000},
    {"key": "first_battle", "name": "Trial by Combat", "description": "Win your first PvP battle.", "icon": "⚔️", "gem_reward": 10, "coin_reward": 600},
    {"key": "battles_10", "name": "Arena Gladiator", "description": "Win 10 PvP battles against other server members.", "icon": "🛡️", "gem_reward": 30, "coin_reward": 4000},
    {"key": "millionaire", "name": "Novexa Tycoon", "description": "Accumulate 1,000,000 Total Net Worth.", "icon": "💰", "gem_reward": 100, "coin_reward": 50000},
    {"key": "daily_streak_7", "name": "Dedicated Citizen", "description": "Reach a 7-day daily reward streak.", "icon": "🔥", "gem_reward": 25, "coin_reward": 3500},
    {"key": "daily_streak_30", "name": "Supreme Dedication", "description": "Reach an astounding 30-day daily reward streak.", "icon": "👑", "gem_reward": 100, "coin_reward": 20000},
    {"key": "happily_married", "name": "Tied the Knot", "description": "Marry another member using a Diamond Ring.", "icon": "💍", "gem_reward": 20, "coin_reward": 5000},
    {"key": "high_roller", "name": "High Roller", "description": "Win at least 10,000 coins in a single gambling game.", "icon": "🎰", "gem_reward": 35, "coin_reward": 5000},
    {"key": "zoo_collector", "name": "Imperial Zoo Keeper", "description": "Collect 20 distinct animal species.", "icon": "🦁", "gem_reward": 50, "coin_reward": 8000},
    {"key": "pet_master", "name": "Beast Tamer", "description": "Level up any pet to Level 5 or higher.", "icon": "🐾", "gem_reward": 30, "coin_reward": 4500},
]


class EconomyService:
    """Core business logic and atomic transactions engine for NOVEXA."""

    def __init__(self):
        self._initialized = False

    async def initialize(self) -> None:
        """Seed catalog items, animals, pets, and achievements if not already present."""
        if self._initialized:
            return

        # 1. Seed Items
        for item in DEFAULT_ITEMS:
            await db.execute(
                """
                INSERT INTO economy_items (
                    item_id, name, description, category, rarity, buy_price, sell_price,
                    gem_price, attack_bonus, defense_bonus, hunt_luck, consumable,
                    max_stack, icon, slot, special_ability
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(item_id) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    category = excluded.category,
                    rarity = excluded.rarity,
                    buy_price = excluded.buy_price,
                    sell_price = excluded.sell_price,
                    gem_price = excluded.gem_price,
                    attack_bonus = excluded.attack_bonus,
                    defense_bonus = excluded.defense_bonus,
                    hunt_luck = excluded.hunt_luck,
                    consumable = excluded.consumable,
                    max_stack = excluded.max_stack,
                    icon = excluded.icon,
                    slot = excluded.slot,
                    special_ability = excluded.special_ability
                """,
                (
                    item["item_id"],
                    item["name"],
                    item["description"],
                    item["category"],
                    item["rarity"],
                    item.get("buy_price", 0),
                    item.get("sell_price", 0),
                    item.get("gem_price", 0),
                    item.get("attack_bonus", 0),
                    item.get("defense_bonus", 0),
                    item.get("hunt_luck", 0),
                    item.get("consumable", 0),
                    item.get("max_stack", 999),
                    item.get("icon", "📦"),
                    item.get("slot"),
                    item.get("special_ability", ""),
                )
            )

        # 2. Seed Animals
        for a in DEFAULT_ANIMALS:
            await db.execute(
                """
                INSERT INTO economy_animals (
                    animal_id, name, emoji, rarity, base_value, base_xp, catch_weight, ability, description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(animal_id) DO UPDATE SET
                    name = excluded.name,
                    emoji = excluded.emoji,
                    rarity = excluded.rarity,
                    base_value = excluded.base_value,
                    base_xp = excluded.base_xp,
                    catch_weight = excluded.catch_weight,
                    ability = excluded.ability,
                    description = excluded.description
                """,
                (
                    a["animal_id"], a["name"], a["emoji"], a["rarity"], a["base_value"],
                    a["base_xp"], a["catch_weight"], a["ability"], a["description"],
                )
            )

        # 3. Seed Pets
        for p in DEFAULT_PETS:
            await db.execute(
                """
                INSERT INTO economy_pets (
                    pet_type, name, emoji, rarity, bonus_type, bonus_value, description
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(pet_type) DO UPDATE SET
                    name = excluded.name,
                    emoji = excluded.emoji,
                    rarity = excluded.rarity,
                    bonus_type = excluded.bonus_type,
                    bonus_value = excluded.bonus_value,
                    description = excluded.description
                """,
                (
                    p["pet_type"], p["name"], p["emoji"], p["rarity"],
                    p["bonus_type"], p["bonus_value"], p["description"],
                )
            )

        # 4. Seed Achievements
        for ach in DEFAULT_ACHIEVEMENTS:
            await db.execute(
                """
                INSERT INTO economy_achievements (
                    key, name, description, icon, gem_reward, coin_reward
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    icon = excluded.icon,
                    gem_reward = excluded.gem_reward,
                    coin_reward = excluded.coin_reward
                """,
                (
                    ach["key"], ach["name"], ach["description"], ach["icon"],
                    ach["gem_reward"], ach["coin_reward"],
                )
            )

        self._initialized = True
        logger.info("Economy service initialized with catalog items, animals, pets, and achievements.")

    # ==================== USER PROFILE MANAGEMENT ====================

    async def get_or_create_user(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        """Fetch user economy profile or create a default one if it doesn't exist."""
        await self.initialize()

        # Check existing economy_users row
        row = await db.fetchone(
            "SELECT * FROM economy_users WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )

        if row:
            return dict(row)

        # Check legacy economy table to preserve prior balances
        legacy_row = await db.fetchone(
            "SELECT wallet, bank FROM economy WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        initial_wallet = legacy_row["wallet"] if legacy_row else 500
        initial_bank = legacy_row["bank"] if legacy_row else 1000

        # Check legacy leveling table
        lvl_row = await db.fetchone(
            "SELECT xp, level FROM leveling WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        initial_xp = lvl_row["xp"] if lvl_row else 0
        initial_lvl = max(1, lvl_row["level"] if lvl_row else 1)

        await db.execute(
            """
            INSERT INTO economy_users (guild_id, user_id, wallet, bank, gems, xp, level)
            VALUES (?, ?, ?, ?, 10, ?, ?)
            ON CONFLICT(guild_id, user_id) DO NOTHING
            """,
            (guild_id, user_id, initial_wallet, initial_bank, initial_xp, initial_lvl),
        )

        # Keep legacy tables synced
        await db.execute(
            """
            INSERT INTO economy (guild_id, user_id, wallet, bank)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO NOTHING
            """,
            (guild_id, user_id, initial_wallet, initial_bank),
        )

        new_row = await db.fetchone(
            "SELECT * FROM economy_users WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        return dict(new_row) if new_row else {}

    # ==================== ATOMIC BALANCE OPERATIONS ====================

    async def modify_wallet(
        self,
        guild_id: int,
        user_id: int,
        amount: int,
        allow_negative: bool = False,
        tx_type: str = "other",
        description: str = "",
    ) -> bool:
        """Atomically modify user wallet coins.

        If amount < 0 and allow_negative is False, requires wallet >= abs(amount).
        Returns True if successful, False if insufficient balance.
        """
        await self.get_or_create_user(guild_id, user_id)

        if amount < 0 and not allow_negative:
            cursor = await db.execute(
                """
                UPDATE economy_users
                SET wallet = wallet + ?,
                    total_spent = total_spent + ABS(?)
                WHERE guild_id = ? AND user_id = ? AND (wallet + ?) >= 0
                """,
                (amount, amount, guild_id, user_id, amount),
            )
            if cursor.rowcount == 0:
                return False
        else:
            earned_inc = amount if amount > 0 else 0
            spent_inc = abs(amount) if amount < 0 else 0
            await db.execute(
                """
                UPDATE economy_users
                SET wallet = wallet + ?,
                    total_earned = total_earned + ?,
                    total_spent = total_spent + ?
                WHERE guild_id = ? AND user_id = ?
                """,
                (amount, earned_inc, spent_inc, guild_id, user_id),
            )

        # Sync legacy economy table
        await db.execute(
            """
            UPDATE economy
            SET wallet = (SELECT wallet FROM economy_users WHERE guild_id = ? AND user_id = ?)
            WHERE guild_id = ? AND user_id = ?
            """,
            (guild_id, user_id, guild_id, user_id),
        )

        # Record audit transaction
        await db.execute(
            """
            INSERT INTO economy_transactions (guild_id, from_user_id, to_user_id, amount, currency_type, tx_type, description)
            VALUES (?, ?, NULL, ?, 'coins', ?, ?)
            """,
            (guild_id, user_id, amount, tx_type, description),
        )
        return True

    async def modify_bank(
        self,
        guild_id: int,
        user_id: int,
        amount: int,
        allow_negative: bool = False,
        tx_type: str = "other",
        description: str = "",
    ) -> bool:
        """Atomically modify user bank coins."""
        await self.get_or_create_user(guild_id, user_id)

        if amount < 0 and not allow_negative:
            cursor = await db.execute(
                """
                UPDATE economy_users
                SET bank = bank + ?
                WHERE guild_id = ? AND user_id = ? AND (bank + ?) >= 0
                """,
                (amount, guild_id, user_id, amount),
            )
            if cursor.rowcount == 0:
                return False
        else:
            await db.execute(
                "UPDATE economy_users SET bank = bank + ? WHERE guild_id = ? AND user_id = ?",
                (amount, guild_id, user_id),
            )

        # Sync legacy economy table
        await db.execute(
            """
            UPDATE economy
            SET bank = (SELECT bank FROM economy_users WHERE guild_id = ? AND user_id = ?)
            WHERE guild_id = ? AND user_id = ?
            """,
            (guild_id, user_id, guild_id, user_id),
        )

        await db.execute(
            """
            INSERT INTO economy_transactions (guild_id, from_user_id, to_user_id, amount, currency_type, tx_type, description)
            VALUES (?, ?, NULL, ?, 'coins', ?, ?)
            """,
            (guild_id, user_id, amount, tx_type, description),
        )
        return True

    async def modify_gems(self, guild_id: int, user_id: int, amount: int) -> bool:
        """Atomically modify user gems balance."""
        await self.get_or_create_user(guild_id, user_id)

        if amount < 0:
            cursor = await db.execute(
                """
                UPDATE economy_users
                SET gems = gems + ?
                WHERE guild_id = ? AND user_id = ? AND (gems + ?) >= 0
                """,
                (amount, guild_id, user_id, amount),
            )
            return cursor.rowcount > 0
        else:
            await db.execute(
                "UPDATE economy_users SET gems = gems + ? WHERE guild_id = ? AND user_id = ?",
                (amount, guild_id, user_id),
            )
            return True

    async def deposit(self, guild_id: int, user_id: int, amount_str: str) -> Tuple[bool, int, str]:
        """Deposit coins from wallet into bank."""
        user = await self.get_or_create_user(guild_id, user_id)
        wallet = user["wallet"]

        if amount_str.lower() in ("all", "max"):
            amount = wallet
        else:
            try:
                amount = int(amount_str)
            except ValueError:
                return False, 0, "Invalid amount provided. Enter a positive number or `all`."

        if amount <= 0:
            return False, 0, "Amount must be greater than 0."
        if wallet < amount:
            return False, 0, f"Insufficient funds in wallet! You only have **{wallet:,} {CURRENCY_NAME}**."

        # Atomic deduction and deposit
        success = await self.modify_wallet(guild_id, user_id, -amount, tx_type="deposit", description="Deposit to Bank")
        if not success:
            return False, 0, "Deposit failed due to insufficient funds."

        await self.modify_bank(guild_id, user_id, amount, tx_type="deposit", description="Deposit from Wallet")
        return True, amount, f"Successfully deposited **{amount:,} {CURRENCY_NAME}** into your bank account!"

    async def withdraw(self, guild_id: int, user_id: int, amount_str: str) -> Tuple[bool, int, str]:
        """Withdraw coins from bank into wallet."""
        user = await self.get_or_create_user(guild_id, user_id)
        bank = user["bank"]

        if amount_str.lower() in ("all", "max"):
            amount = bank
        else:
            try:
                amount = int(amount_str)
            except ValueError:
                return False, 0, "Invalid amount provided. Enter a positive number or `all`."

        if amount <= 0:
            return False, 0, "Amount must be greater than 0."
        if bank < amount:
            return False, 0, f"Insufficient bank balance! You only have **{bank:,} {CURRENCY_NAME}** in the bank."

        success = await self.modify_bank(guild_id, user_id, -amount, tx_type="withdraw", description="Withdraw to Wallet")
        if not success:
            return False, 0, "Withdrawal failed due to insufficient bank balance."

        await self.modify_wallet(guild_id, user_id, amount, tx_type="withdraw", description="Withdraw from Bank")
        return True, amount, f"Successfully withdrew **{amount:,} {CURRENCY_NAME}** from your bank into your wallet!"

    async def pay(self, guild_id: int, from_user_id: int, to_user_id: int, amount: int) -> Tuple[bool, str]:
        """Transfer coins from one member's wallet to another member's wallet atomically."""
        if from_user_id == to_user_id:
            return False, "You cannot transfer coins to yourself!"
        if amount <= 0:
            return False, "Transfer amount must be greater than 0."

        sender = await self.get_or_create_user(guild_id, from_user_id)
        if sender["wallet"] < amount:
            return False, f"Insufficient funds! You only have **{sender['wallet']:,} {CURRENCY_NAME}** in your wallet."

        await self.get_or_create_user(guild_id, to_user_id)

        # Atomic transfer
        deducted = await self.modify_wallet(guild_id, from_user_id, -amount, tx_type="pay", description=f"Transfer to user {to_user_id}")
        if not deducted:
            return False, "Payment failed: Insufficient funds."

        await self.modify_wallet(guild_id, to_user_id, amount, tx_type="pay", description=f"Transfer from user {from_user_id}")

        await db.execute(
            """
            INSERT INTO economy_transactions (guild_id, from_user_id, to_user_id, amount, currency_type, tx_type, description)
            VALUES (?, ?, ?, ?, 'coins', 'pay', 'Direct P2P Payment')
            """,
            (guild_id, from_user_id, to_user_id, amount),
        )
        return True, f"Successfully paid **{amount:,} {CURRENCY_NAME}**!"

    # ==================== PROGRESSION & XP ====================

    def xp_for_level(self, level: int) -> int:
        """Total XP required to reach the given level."""
        return int(100 * (level ** 1.5))

    async def add_xp(self, guild_id: int, user_id: int, amount: int) -> Tuple[bool, int, int, int]:
        """Add XP to user and calculate level up. Returns (leveled_up, new_level, reward_coins, reward_gems)."""
        user = await self.get_or_create_user(guild_id, user_id)
        current_xp = user["xp"] + amount
        current_lvl = user["level"]

        leveled_up = False
        new_lvl = current_lvl
        reward_coins = 0
        reward_gems = 0

        while current_xp >= self.xp_for_level(new_lvl + 1):
            new_lvl += 1
            leveled_up = True
            reward_coins += 500 * new_lvl
            reward_gems += max(1, new_lvl // 2)

        await db.execute(
            """
            UPDATE economy_users
            SET xp = ?, level = ?
            WHERE guild_id = ? AND user_id = ?
            """,
            (current_xp, new_lvl, guild_id, user_id),
        )

        # Sync legacy leveling table
        await db.execute(
            """
            INSERT INTO leveling (guild_id, user_id, xp, level, last_xp_time)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET xp = excluded.xp, level = excluded.level
            """,
            (guild_id, user_id, current_xp, new_lvl, time.time()),
        )

        if leveled_up:
            await self.modify_wallet(guild_id, user_id, reward_coins, tx_type="levelup", description=f"Level Up to {new_lvl}")
            await self.modify_gems(guild_id, user_id, reward_gems)

        return leveled_up, new_lvl, reward_coins, reward_gems

    # ==================== DAILY, WEEKLY & MONTHLY REWARDS ====================

    async def claim_daily(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        """Claim daily reward with consecutive daily streak calculation."""
        user = await self.get_or_create_user(guild_id, user_id)
        now = time.time()
        last_daily = user["last_daily"]
        cooldown = 86400  # 24 Hours
        streak_timeout = 86400 * 2  # 48 Hours to preserve streak

        if now - last_daily < cooldown:
            remaining = int(cooldown - (now - last_daily))
            return {"success": False, "remaining_seconds": remaining}

        # Calculate streak
        current_streak = user["daily_streak"]
        if last_daily > 0 and (now - last_daily) <= streak_timeout:
            new_streak = current_streak + 1
        else:
            new_streak = 1

        # Reward base
        base_reward = random.randint(500, 1000)
        streak_bonus = min(new_streak * 100, 5000)
        total_coins = base_reward + streak_bonus
        gems_reward = 2 if new_streak % 5 == 0 else 1

        # Special milestone bonuses
        crate_awarded = None
        if new_streak % 7 == 0:
            crate_awarded = "rare_crate"
            await self.give_item(guild_id, user_id, "rare_crate", 1)

        await db.execute(
            """
            UPDATE economy_users
            SET daily_streak = ?, last_daily = ?, commands_used = commands_used + 1
            WHERE guild_id = ? AND user_id = ?
            """,
            (new_streak, now, guild_id, user_id),
        )

        await self.modify_wallet(guild_id, user_id, total_coins, tx_type="daily", description=f"Daily Reward (Streak {new_streak})")
        await self.modify_gems(guild_id, user_id, gems_reward)

        # Check achievements
        await self.check_achievements(guild_id, user_id)

        return {
            "success": True,
            "coins": total_coins,
            "base_coins": base_reward,
            "streak_bonus": streak_bonus,
            "gems": gems_reward,
            "streak": new_streak,
            "crate": crate_awarded,
        }

    async def claim_weekly(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        """Claim weekly bonus rewards (7-day cooldown)."""
        user = await self.get_or_create_user(guild_id, user_id)
        now = time.time()
        cooldown = 86400 * 7

        if now - user["last_weekly"] < cooldown:
            remaining = int(cooldown - (now - user["last_weekly"]))
            return {"success": False, "remaining_seconds": remaining}

        coins_reward = random.randint(5000, 8000)
        gems_reward = 15
        crate_reward = "rare_crate"

        await db.execute(
            "UPDATE economy_users SET last_weekly = ? WHERE guild_id = ? AND user_id = ?",
            (now, guild_id, user_id),
        )

        await self.modify_wallet(guild_id, user_id, coins_reward, tx_type="weekly", description="Weekly Reward")
        await self.modify_gems(guild_id, user_id, gems_reward)
        await self.give_item(guild_id, user_id, crate_reward, 1)

        return {
            "success": True,
            "coins": coins_reward,
            "gems": gems_reward,
            "crate": crate_reward,
        }

    async def claim_monthly(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        """Claim monthly grand bonus rewards (30-day cooldown)."""
        user = await self.get_or_create_user(guild_id, user_id)
        now = time.time()
        cooldown = 86400 * 30

        if now - user["last_monthly"] < cooldown:
            remaining = int(cooldown - (now - user["last_monthly"]))
            return {"success": False, "remaining_seconds": remaining}

        coins_reward = random.randint(25000, 40000)
        gems_reward = 50
        crate_reward = "epic_crate"

        await db.execute(
            "UPDATE economy_users SET last_monthly = ? WHERE guild_id = ? AND user_id = ?",
            (now, guild_id, user_id),
        )

        await self.modify_wallet(guild_id, user_id, coins_reward, tx_type="monthly", description="Monthly Reward")
        await self.modify_gems(guild_id, user_id, gems_reward)
        await self.give_item(guild_id, user_id, crate_reward, 1)

        return {
            "success": True,
            "coins": coins_reward,
            "gems": gems_reward,
            "crate": crate_reward,
        }

    # ==================== WORK, CRIME & SLUT ====================

    async def work(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        """Perform honest work for Novexa Coins (5-min cooldown)."""
        user = await self.get_or_create_user(guild_id, user_id)
        now = time.time()
        cooldown = 300  # 5 min

        if now - user["last_work"] < cooldown:
            return {"success": False, "remaining_seconds": int(cooldown - (now - user["last_work"]))}

        jobs = [
            ("Programmer", "You squashed 12 critical compiler bugs in a C++ server engine.", random.randint(200, 450)),
            ("Discord Moderator", "You kept the chat clean and warned 5 spammers.", random.randint(180, 400)),
            ("Zoo Caretaker", "You groomed and fed the wild tigers at the royal zoo.", random.randint(220, 480)),
            ("Cyber Bounty Hunter", "You traced an exploit and patched a database leak.", random.randint(250, 500)),
            ("Novexa Merchant", "You sold exotic spices and enchanted crystals at the bazaar.", random.randint(200, 420)),
            ("Architect", "You designed a breathtaking server layout for a client.", random.randint(240, 470)),
        ]
        title, scenario, base_pay = random.choice(jobs)

        # Check pet coin bonus
        equipped_pet = await self.get_equipped_pet(guild_id, user_id)
        bonus_pct = 0.0
        if equipped_pet and equipped_pet["bonus_type"] == "coin_boost":
            bonus_pct = equipped_pet["bonus_value"] * equipped_pet["level"]

        pay = int(base_pay * (1.0 + bonus_pct / 100.0))
        xp_gain = random.randint(15, 30)

        await db.execute(
            "UPDATE economy_users SET last_work = ?, commands_used = commands_used + 1 WHERE guild_id = ? AND user_id = ?",
            (now, guild_id, user_id),
        )

        await self.modify_wallet(guild_id, user_id, pay, tx_type="work", description=f"Job: {title}")
        leveled, new_lvl, r_coins, r_gems = await self.add_xp(guild_id, user_id, xp_gain)

        await self.check_achievements(guild_id, user_id)

        return {
            "success": True,
            "job": title,
            "scenario": scenario,
            "earned": pay,
            "xp": xp_gain,
            "leveled_up": leveled,
            "new_level": new_lvl,
        }

    async def crime(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        """High-risk criminal heist: 65% success rate, fine on failure (10-min cooldown)."""
        user = await self.get_or_create_user(guild_id, user_id)
        now = time.time()
        cooldown = 600  # 10 min

        if now - user["last_crime"] < cooldown:
            return {"success": False, "remaining_seconds": int(cooldown - (now - user["last_crime"]))}

        await db.execute(
            "UPDATE economy_users SET last_crime = ?, commands_used = commands_used + 1 WHERE guild_id = ? AND user_id = ?",
            (now, guild_id, user_id),
        )

        success = random.random() < 0.65
        if success:
            crimes = [
                ("Hacked a rival crypto wallet and siphoned coins undetected.", random.randint(600, 1200)),
                ("Pickpocketed an arrogant noble at the black market.", random.randint(450, 950)),
                ("Pulled off a midnight jewelry heist in the city center.", random.randint(700, 1500)),
                ("Smuggled forbidden dragon scales past the royal customs guard.", random.randint(800, 1600)),
            ]
            scenario, loot = random.choice(crimes)
            xp_gain = random.randint(25, 50)
            await self.modify_wallet(guild_id, user_id, loot, tx_type="crime", description="Successful Crime Heist")
            leveled, new_lvl, r_coins, r_gems = await self.add_xp(guild_id, user_id, xp_gain)

            return {
                "success": True,
                "won": True,
                "scenario": scenario,
                "amount": loot,
                "xp": xp_gain,
                "leveled_up": leveled,
                "new_level": new_lvl,
            }
        else:
            fails = [
                ("The police caught you climbing the museum fence! You paid a heavy fine.", random.randint(250, 600)),
                ("Your hacking proxy collapsed and federal cyber patrol traced your IP! Fined.", random.randint(300, 700)),
                ("The guard dog bit your ankle and held you until morning guard arrived. Fined.", random.randint(200, 500)),
            ]
            scenario, fine = random.choice(fails)
            fine = min(fine, user["wallet"])
            if fine > 0:
                await self.modify_wallet(guild_id, user_id, -fine, tx_type="crime_fine", description="Police Fine")

            return {
                "success": True,
                "won": False,
                "scenario": scenario,
                "fine": fine,
            }

    async def slut(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        """Classic economy / OwO-style command: humorous high-risk flirtatious encounters (15-min cooldown)."""
        user = await self.get_or_create_user(guild_id, user_id)
        now = time.time()
        cooldown = 900  # 15 min

        if now - user["last_slut"] < cooldown:
            return {"success": False, "remaining_seconds": int(cooldown - (now - user["last_slut"]))}

        await db.execute(
            "UPDATE economy_users SET last_slut = ?, commands_used = commands_used + 1 WHERE guild_id = ? AND user_id = ?",
            (now, guild_id, user_id),
        )

        success = random.random() < 0.70
        if success:
            scenarios = [
                ("You danced on the VIP stage at Club Novexa and patrons showered you with coins!", random.randint(700, 1600)),
                ("A wealthy crypto whale was charmed by your aesthetic and sent you a lavish tip.", random.randint(850, 1800)),
                ("You posed for an exclusive high-fashion server magazine cover and got paid generously.", random.randint(600, 1400)),
                ("You winked at the casino owner and they slipped a bag of gold into your coat pocket.", random.randint(900, 2000)),
            ]
            scenario, payout = random.choice(scenarios)
            xp_gain = random.randint(20, 45)
            await self.modify_wallet(guild_id, user_id, payout, tx_type="slut", description="Slut Payout")
            leveled, new_lvl, _, _ = await self.add_xp(guild_id, user_id, xp_gain)

            return {
                "success": True,
                "won": True,
                "scenario": scenario,
                "amount": payout,
                "xp": xp_gain,
                "leveled_up": leveled,
                "new_level": new_lvl,
            }
        else:
            fails = [
                ("You tripped on high heels right in front of the crowd! Your drink spilled and you paid for damages.", random.randint(300, 600)),
                ("Someone threw a cold soda at you and laughed. You ran away with zero dignity and lost coins.", random.randint(250, 500)),
                ("The bouncer caught you trying to hustle the VIP lounge and confiscated your wallet.", random.randint(350, 750)),
            ]
            scenario, fine = random.choice(fails)
            fine = min(fine, user["wallet"])
            if fine > 0:
                await self.modify_wallet(guild_id, user_id, -fine, tx_type="slut_fail", description="Slut Encounter Fail")

            return {
                "success": True,
                "won": False,
                "scenario": scenario,
                "fine": fine,
            }

    # ==================== GAMBLING GAMES ====================

    async def coinflip(self, guild_id: int, user_id: int, choice: str, bet: int) -> Dict[str, Any]:
        """50/50 Coinflip game."""
        choice = choice.lower().strip()
        if choice not in ("heads", "tails", "h", "t"):
            return {"success": False, "message": "Invalid choice! Pick `heads` or `tails`."}

        user = await self.get_or_create_user(guild_id, user_id)
        if bet <= 0:
            return {"success": False, "message": "Bet must be greater than 0."}
        if user["wallet"] < bet:
            return {"success": False, "message": f"You don't have enough coins! Wallet: **{user['wallet']:,} {CURRENCY_NAME}**."}

        # Deduct bet
        await self.modify_wallet(guild_id, user_id, -bet, tx_type="coinflip_bet", description="Coinflip Bet")

        result = random.choice(["heads", "tails"])
        predicted = "heads" if choice in ("heads", "h") else "tails"
        won = (result == predicted)

        if won:
            payout = bet * 2
            await self.modify_wallet(guild_id, user_id, payout, tx_type="coinflip_win", description="Coinflip Win")
            await db.execute("UPDATE economy_users SET gambles_won = gambles_won + 1 WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
            await self.check_achievements(guild_id, user_id)
            return {"success": True, "won": True, "result": result, "payout": payout, "profit": bet}
        else:
            await db.execute("UPDATE economy_users SET gambles_lost = gambles_lost + 1 WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
            return {"success": True, "won": False, "result": result, "lost": bet}

    async def dice(self, guild_id: int, user_id: int, bet: int, guess: Optional[int] = None) -> Dict[str, Any]:
        """Roll a 6-sided die. If guess provided: 6x payout on exact match. Otherwise player rolls vs Bot."""
        user = await self.get_or_create_user(guild_id, user_id)
        if bet <= 0:
            return {"success": False, "message": "Bet must be greater than 0."}
        if user["wallet"] < bet:
            return {"success": False, "message": f"Insufficient balance! Wallet: **{user['wallet']:,} {CURRENCY_NAME}**."}

        await self.modify_wallet(guild_id, user_id, -bet, tx_type="dice_bet", description="Dice Bet")

        if guess is not None and 1 <= guess <= 6:
            roll = random.randint(1, 6)
            won = (roll == guess)
            if won:
                payout = bet * 6
                await self.modify_wallet(guild_id, user_id, payout, tx_type="dice_win", description="Dice Exact Guess Win")
                await db.execute("UPDATE economy_users SET gambles_won = gambles_won + 1 WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
                return {"success": True, "mode": "exact", "won": True, "roll": roll, "guess": guess, "payout": payout, "profit": payout - bet}
            else:
                await db.execute("UPDATE economy_users SET gambles_lost = gambles_lost + 1 WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
                return {"success": True, "mode": "exact", "won": False, "roll": roll, "guess": guess, "lost": bet}
        else:
            # Player rolls vs Bot
            player_roll = random.randint(1, 6)
            bot_roll = random.randint(1, 6)

            if player_roll > bot_roll:
                payout = bet * 2
                await self.modify_wallet(guild_id, user_id, payout, tx_type="dice_win", description="Dice Beat Bot Win")
                await db.execute("UPDATE economy_users SET gambles_won = gambles_won + 1 WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
                return {"success": True, "mode": "vs_bot", "won": True, "player_roll": player_roll, "bot_roll": bot_roll, "payout": payout, "profit": bet}
            elif player_roll == bot_roll:
                # Tie: refund bet
                await self.modify_wallet(guild_id, user_id, bet, tx_type="dice_tie", description="Dice Tie Refund")
                return {"success": True, "mode": "vs_bot", "won": None, "player_roll": player_roll, "bot_roll": bot_roll, "refund": bet}
            else:
                await db.execute("UPDATE economy_users SET gambles_lost = gambles_lost + 1 WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
                return {"success": True, "mode": "vs_bot", "won": False, "player_roll": player_roll, "bot_roll": bot_roll, "lost": bet}

    async def slots(self, guild_id: int, user_id: int, bet: int) -> Dict[str, Any]:
        """Classic 3-reel slot machine with rich payout multipliers."""
        user = await self.get_or_create_user(guild_id, user_id)
        if bet <= 0:
            return {"success": False, "message": "Bet must be greater than 0."}
        if user["wallet"] < bet:
            return {"success": False, "message": f"Insufficient wallet balance! Wallet: **{user['wallet']:,} {CURRENCY_NAME}**."}

        await self.modify_wallet(guild_id, user_id, -bet, tx_type="slots_bet", description="Slots Bet")

        symbols = ["🍒", "🍋", "🍇", "🔔", "💎", "7️⃣"]
        weights = [35, 25, 20, 12, 6, 2]

        reels = random.choices(symbols, weights=weights, k=3)

        # Evaluate payout
        multiplier = 0.0
        if reels[0] == reels[1] == reels[2]:
            if reels[0] == "7️⃣":
                multiplier = 50.0  # Jackpot!
            elif reels[0] == "💎":
                multiplier = 25.0
            elif reels[0] == "🔔":
                multiplier = 15.0
            elif reels[0] == "🍇":
                multiplier = 8.0
            elif reels[0] == "🍋":
                multiplier = 5.0
            elif reels[0] == "🍒":
                multiplier = 4.0
        elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
            multiplier = 1.5

        won = (multiplier > 0)
        payout = int(bet * multiplier)

        if won:
            await self.modify_wallet(guild_id, user_id, payout, tx_type="slots_win", description=f"Slots Win ({multiplier}x)")
            await db.execute("UPDATE economy_users SET gambles_won = gambles_won + 1 WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
            await self.check_achievements(guild_id, user_id)
            return {"success": True, "won": True, "reels": reels, "multiplier": multiplier, "payout": payout, "profit": payout - bet}
        else:
            await db.execute("UPDATE economy_users SET gambles_lost = gambles_lost + 1 WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
            return {"success": True, "won": False, "reels": reels, "multiplier": 0.0, "lost": bet}

    async def gamble(self, guild_id: int, user_id: int, bet: int) -> Dict[str, Any]:
        """Classic roll 1-100 gambling game."""
        user = await self.get_or_create_user(guild_id, user_id)
        if bet <= 0:
            return {"success": False, "message": "Bet must be greater than 0."}
        if user["wallet"] < bet:
            return {"success": False, "message": f"Insufficient wallet funds! Balance: **{user['wallet']:,} {CURRENCY_NAME}**."}

        await self.modify_wallet(guild_id, user_id, -bet, tx_type="gamble_bet", description="Gamble Bet")

        roll = random.randint(1, 100)

        # Check for equipped Golden Horseshoe
        horseshoe = await db.fetchone(
            "SELECT quantity FROM economy_inventory WHERE guild_id = ? AND user_id = ? AND item_id = 'golden_horseshoe'",
            (guild_id, user_id),
        )
        bonus_mult = 1.15 if horseshoe and horseshoe["quantity"] > 0 else 1.0

        if roll > 90:
            # Super Win 3x
            payout = int(bet * 3 * bonus_mult)
            await self.modify_wallet(guild_id, user_id, payout, tx_type="gamble_win", description="Super Gamble Win (3x)")
            await db.execute("UPDATE economy_users SET gambles_won = gambles_won + 1 WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
            await self.check_achievements(guild_id, user_id)
            return {"success": True, "won": True, "roll": roll, "tier": "Super Win (3x)", "payout": payout, "profit": payout - bet}
        elif roll > 50:
            # Win 2x
            payout = int(bet * 2 * bonus_mult)
            await self.modify_wallet(guild_id, user_id, payout, tx_type="gamble_win", description="Gamble Win (2x)")
            await db.execute("UPDATE economy_users SET gambles_won = gambles_won + 1 WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
            await self.check_achievements(guild_id, user_id)
            return {"success": True, "won": True, "roll": roll, "tier": "Standard Win (2x)", "payout": payout, "profit": payout - bet}
        else:
            await db.execute("UPDATE economy_users SET gambles_lost = gambles_lost + 1 WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
            return {"success": True, "won": False, "roll": roll, "tier": "Loss", "lost": bet}

    # ==================== HUNT SYSTEM ====================

    async def hunt(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        """Hunt for wild animals with equipment and pet luck modifiers."""
        user = await self.get_or_create_user(guild_id, user_id)
        now = time.time()
        cooldown = 15  # 15s fast OwO-style hunt

        if now - user["last_hunt"] < cooldown:
            return {"success": False, "remaining_seconds": int(cooldown - (now - user["last_hunt"]))}

        # Calculate hunting luck modifiers from equipment and pets
        luck_boost = 0
        equipped_items = await self.get_equipped_items(guild_id, user_id)
        for it in equipped_items.values():
            luck_boost += it.get("hunt_luck", 0)

        equipped_pet = await self.get_equipped_pet(guild_id, user_id)
        if equipped_pet and equipped_pet["bonus_type"] == "hunt_luck":
            luck_boost += int(equipped_pet["bonus_value"] * equipped_pet["level"])

        # Fetch all animals
        animals = await db.fetchall("SELECT * FROM economy_animals")
        if not animals:
            return {"success": False, "message": "Animal catalog is currently being populated."}

        # Select animal weighted by rarity and luck
        weighted_list: List[Dict[str, Any]] = []
        for a in animals:
            row_dict = dict(a)
            weight = row_dict["catch_weight"]
            if luck_boost > 0 and row_dict["rarity"] in ("Rare", "Epic", "Legendary", "Mythical"):
                # Scale up rare weights with luck
                weight += int(weight * (luck_boost / 100.0) * 2)
            weighted_list.append(row_dict)

        weights = [max(1, x["catch_weight"]) for x in weighted_list]
        encounter: Dict[str, Any] = random.choices(weighted_list, weights=weights, k=1)[0]

        # Catch probability: Base 85% + luck_boost (capped at 99%)
        catch_chance = min(0.99, 0.85 + (luck_boost / 200.0))
        caught = (random.random() <= catch_chance)

        await db.execute(
            "UPDATE economy_users SET last_hunt = ?, hunts_count = hunts_count + 1 WHERE guild_id = ? AND user_id = ?",
            (now, guild_id, user_id),
        )

        if not caught:
            return {
                "success": True,
                "caught": False,
                "encounter": encounter,
                "reason": f"The wild {encounter['name']} slipped away into the brush!",
            }

        # Record caught animal in user zoo
        existing = await db.fetchone(
            "SELECT count FROM economy_user_animals WHERE guild_id = ? AND user_id = ? AND animal_id = ?",
            (guild_id, user_id, encounter["animal_id"]),
        )
        is_duplicate = False
        new_count = 1

        if existing:
            is_duplicate = True
            new_count = existing["count"] + 1
            await db.execute(
                """
                UPDATE economy_user_animals
                SET count = count + 1, last_caught = CURRENT_TIMESTAMP
                WHERE guild_id = ? AND user_id = ? AND animal_id = ?
                """,
                (guild_id, user_id, encounter["animal_id"]),
            )
        else:
            await db.execute(
                """
                INSERT INTO economy_user_animals (guild_id, user_id, animal_id, count)
                VALUES (?, ?, ?, 1)
                """,
                (guild_id, user_id, encounter["animal_id"]),
            )

        # Award XP and coins
        xp_gain = encounter["base_xp"]
        leveled, new_lvl, r_coins, r_gems = await self.add_xp(guild_id, user_id, xp_gain)

        # Check achievements
        await self.check_achievements(guild_id, user_id)

        return {
            "success": True,
            "caught": True,
            "encounter": encounter,
            "count": new_count,
            "is_duplicate": is_duplicate,
            "xp_gain": xp_gain,
            "leveled_up": leveled,
            "new_level": new_lvl,
        }

    async def sell_animal(
        self,
        guild_id: int,
        user_id: int,
        animal_id: str,
        count_target: str = "1",
    ) -> Tuple[bool, int, int, str]:
        """Sell animals from user collection for Novexa Coins.

        Supports specific number, 'all', or 'duplicates' (keeps 1).
        """
        row = await db.fetchone(
            """
            SELECT ua.count, a.base_value, a.name, a.emoji
            FROM economy_user_animals ua
            JOIN economy_animals a ON ua.animal_id = a.animal_id
            WHERE ua.guild_id = ? AND ua.user_id = ? AND (ua.animal_id = ? OR LOWER(a.name) = ?)
            """,
            (guild_id, user_id, animal_id, animal_id.lower()),
        )
        if not row:
            return False, 0, 0, f"You don't own any animals matching `{animal_id}`!"

        current_count = row["count"]
        val_per_animal = row["base_value"]

        if count_target.lower() in ("all", "max"):
            to_sell = current_count
        elif count_target.lower() in ("duplicate", "duplicates", "dupe"):
            to_sell = max(0, current_count - 1)
            if to_sell == 0:
                return False, 0, 0, f"You only have 1 **{row['name']}**! Keeping your original."
        else:
            try:
                to_sell = int(count_target)
            except ValueError:
                return False, 0, 0, "Invalid count specified. Enter a number, `all`, or `duplicates`."

        if to_sell <= 0:
            return False, 0, 0, "Count must be greater than 0."
        if to_sell > current_count:
            return False, 0, 0, f"You only have **{current_count}** of this animal!"

        total_earned = to_sell * val_per_animal

        if to_sell == current_count:
            await db.execute(
                "DELETE FROM economy_user_animals WHERE guild_id = ? AND user_id = ? AND animal_id = ?",
                (guild_id, user_id, animal_id),
            )
        else:
            await db.execute(
                "UPDATE economy_user_animals SET count = count - ? WHERE guild_id = ? AND user_id = ? AND animal_id = ?",
                (to_sell, guild_id, user_id, animal_id),
            )

        await self.modify_wallet(guild_id, user_id, total_earned, tx_type="sell_animal", description=f"Sold {to_sell}x {row['name']}")
        return True, to_sell, total_earned, f"Sold **{to_sell}x {row['emoji']} {row['name']}** for **{total_earned:,} {CURRENCY_NAME}**!"

    async def get_user_zoo(self, guild_id: int, user_id: int) -> List[Dict[str, Any]]:
        """Fetch all animals collected by a user sorted by rarity and value."""
        rows = await db.fetchall(
            """
            SELECT ua.count, ua.is_favorite, a.*
            FROM economy_user_animals ua
            JOIN economy_animals a ON ua.animal_id = a.animal_id
            WHERE ua.guild_id = ? AND ua.user_id = ?
            ORDER BY
                CASE a.rarity
                    WHEN 'Mythical' THEN 1
                    WHEN 'Legendary' THEN 2
                    WHEN 'Epic' THEN 3
                    WHEN 'Rare' THEN 4
                    WHEN 'Uncommon' THEN 5
                    ELSE 6
                END,
                ua.count DESC
            """,
            (guild_id, user_id),
        )
        return [dict(r) for r in rows]

    async def favorite_animal(self, guild_id: int, user_id: int, animal_id: str) -> Tuple[bool, str]:
        """Toggle favorite status on a caught animal."""
        row = await db.fetchone(
            "SELECT is_favorite FROM economy_user_animals WHERE guild_id = ? AND user_id = ? AND animal_id = ?",
            (guild_id, user_id, animal_id),
        )
        if not row:
            return False, f"You don't own any animal with ID `{animal_id}`!"

        new_fav = 0 if row["is_favorite"] else 1
        await db.execute(
            "UPDATE economy_user_animals SET is_favorite = ? WHERE guild_id = ? AND user_id = ? AND animal_id = ?",
            (new_fav, guild_id, user_id, animal_id),
        )
        status = "favorited" if new_fav else "unfavorited"
        return True, f"Successfully {status} animal `{animal_id}`!"

    # ==================== INVENTORY & EQUIPMENT ====================

    async def give_item(self, guild_id: int, user_id: int, item_id: str, quantity: int = 1) -> bool:
        """Add an item to user inventory atomically."""
        if quantity <= 0:
            return False
        await self.get_or_create_user(guild_id, user_id)

        await db.execute(
            """
            INSERT INTO economy_inventory (guild_id, user_id, item_id, quantity)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id, item_id) DO UPDATE SET quantity = quantity + excluded.quantity
            """,
            (guild_id, user_id, item_id, quantity),
        )
        return True

    async def remove_item(self, guild_id: int, user_id: int, item_id: str, quantity: int = 1) -> bool:
        """Remove item from user inventory atomically."""
        if quantity <= 0:
            return False

        row = await db.fetchone(
            "SELECT quantity FROM economy_inventory WHERE guild_id = ? AND user_id = ? AND item_id = ?",
            (guild_id, user_id, item_id),
        )
        if not row or row["quantity"] < quantity:
            return False

        if row["quantity"] == quantity:
            await db.execute(
                "DELETE FROM economy_inventory WHERE guild_id = ? AND user_id = ? AND item_id = ?",
                (guild_id, user_id, item_id),
            )
        else:
            await db.execute(
                "UPDATE economy_inventory SET quantity = quantity - ? WHERE guild_id = ? AND user_id = ? AND item_id = ?",
                (quantity, guild_id, user_id, item_id),
            )
        return True

    async def buy_item(self, guild_id: int, user_id: int, item_id: str, quantity: int = 1) -> Tuple[bool, str]:
        """Purchase an item from the general shop using Novexa Coins."""
        if quantity <= 0:
            return False, "Quantity must be at least 1."

        item = await db.fetchone("SELECT * FROM economy_items WHERE item_id = ?", (item_id,))
        if not item or item["buy_price"] <= 0:
            return False, f"Item `{item_id}` is not available for purchase in the shop."

        total_cost = item["buy_price"] * quantity
        user = await self.get_or_create_user(guild_id, user_id)
        if user["wallet"] < total_cost:
            return False, f"Insufficient funds! You need **{total_cost:,} {CURRENCY_NAME}**, but only have **{user['wallet']:,}**."

        # Atomic deduction
        deducted = await self.modify_wallet(guild_id, user_id, -total_cost, tx_type="shop_buy", description=f"Bought {quantity}x {item['name']}")
        if not deducted:
            return False, "Purchase failed due to insufficient funds."

        await self.give_item(guild_id, user_id, item_id, quantity)
        return True, f"Successfully purchased **{quantity}x {item['icon']} {item['name']}** for **{total_cost:,} {CURRENCY_NAME}**!"

    async def buy_gem_item(self, guild_id: int, user_id: int, item_id: str, quantity: int = 1) -> Tuple[bool, str]:
        """Purchase an exclusive item from the Gem Shop using Gems."""
        if quantity <= 0:
            return False, "Quantity must be at least 1."

        item = await db.fetchone("SELECT * FROM economy_items WHERE item_id = ?", (item_id,))
        if not item or item["gem_price"] <= 0:
            return False, f"Item `{item_id}` is not available in the Gem Shop."

        total_gems = item["gem_price"] * quantity
        user = await self.get_or_create_user(guild_id, user_id)
        if user["gems"] < total_gems:
            return False, f"Insufficient gems! You need **{total_gems} {GEM_NAME}**, but only have **{user['gems']}**."

        success = await self.modify_gems(guild_id, user_id, -total_gems)
        if not success:
            return False, "Gem purchase failed."

        await self.give_item(guild_id, user_id, item_id, quantity)
        return True, f"Successfully purchased **{quantity}x {item['icon']} {item['name']}** for **{total_gems} {GEM_NAME}**!"

    async def equip_item(self, guild_id: int, user_id: int, item_id: str) -> Tuple[bool, str]:
        """Equip weapon, armor, shield, or hunting equipment."""
        item = await db.fetchone("SELECT * FROM economy_items WHERE item_id = ?", (item_id,))
        if not item or not item["slot"]:
            return False, "This item cannot be equipped."

        inv = await db.fetchone(
            "SELECT quantity FROM economy_inventory WHERE guild_id = ? AND user_id = ? AND item_id = ?",
            (guild_id, user_id, item_id),
        )
        if not inv or inv["quantity"] <= 0:
            return False, "You do not own this item!"

        slot = item["slot"]
        # Unequip existing item in the same slot
        await db.execute(
            """
            UPDATE economy_inventory
            SET is_equipped = 0, slot = NULL
            WHERE guild_id = ? AND user_id = ? AND slot = ?
            """,
            (guild_id, user_id, slot),
        )

        # Equip new item
        await db.execute(
            """
            UPDATE economy_inventory
            SET is_equipped = 1, slot = ?
            WHERE guild_id = ? AND user_id = ? AND item_id = ?
            """,
            (slot, guild_id, user_id, item_id),
        )
        return True, f"Equipped **{item['icon']} {item['name']}** into your `{slot.upper()}` slot!"

    async def unequip_item(self, guild_id: int, user_id: int, slot_or_item: str) -> Tuple[bool, str]:
        """Unequip item from slot or by item ID."""
        target = slot_or_item.lower().strip()
        cursor = await db.execute(
            """
            UPDATE economy_inventory
            SET is_equipped = 0, slot = NULL
            WHERE guild_id = ? AND user_id = ? AND (slot = ? OR item_id = ?)
            """,
            (guild_id, user_id, target, target),
        )
        if cursor.rowcount == 0:
            return False, f"No equipped item found matching `{slot_or_item}`."
        return True, f"Unequipped `{slot_or_item}`."

    async def get_user_inventory(self, guild_id: int, user_id: int, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch user inventory items with full item stats."""
        query = """
            SELECT inv.quantity, inv.is_equipped, inv.slot as equipped_slot, it.*
            FROM economy_inventory inv
            JOIN economy_items it ON inv.item_id = it.item_id
            WHERE inv.guild_id = ? AND inv.user_id = ?
        """
        params: List[Any] = [guild_id, user_id]
        if category and category.lower() != "all":
            query += " AND it.category = ?"
            params.append(category.lower())

        query += " ORDER BY inv.is_equipped DESC, it.rarity, it.name"
        rows = await db.fetchall(query, tuple(params))
        return [dict(r) for r in rows]

    async def get_equipped_items(self, guild_id: int, user_id: int) -> Dict[str, Dict[str, Any]]:
        """Fetch dictionary of currently equipped items keyed by slot."""
        rows = await db.fetchall(
            """
            SELECT inv.slot, it.*
            FROM economy_inventory inv
            JOIN economy_items it ON inv.item_id = it.item_id
            WHERE inv.guild_id = ? AND inv.user_id = ? AND inv.is_equipped = 1
            """,
            (guild_id, user_id),
        )
        res: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            d = dict(r)
            res[d["slot"]] = d
        return res

    # ==================== PET SYSTEM ====================

    async def adopt_pet(self, guild_id: int, user_id: int, pet_type: str, nickname: Optional[str] = None) -> Tuple[bool, str]:
        """Adopt a pet from the shelter/catalog."""
        pet = await db.fetchone("SELECT * FROM economy_pets WHERE pet_type = ?", (pet_type,))
        if not pet:
            return False, f"Pet type `{pet_type}` does not exist!"

        user = await self.get_or_create_user(guild_id, user_id)
        cost = 2000  # 2,000 coins to adopt
        if user["wallet"] < cost:
            return False, f"Adoption fee is **{cost:,} {CURRENCY_NAME}**. You only have **{user['wallet']:,}**."

        # Check if user already owns this pet type
        existing = await db.fetchone(
            "SELECT id FROM economy_user_pets WHERE guild_id = ? AND user_id = ? AND pet_type = ?",
            (guild_id, user_id, pet_type),
        )
        if existing:
            return False, f"You already have a {pet['name']}! You can level them up instead."

        deducted = await self.modify_wallet(guild_id, user_id, -cost, tx_type="adopt_pet", description=f"Adopted {pet['name']}")
        if not deducted:
            return False, "Adoption failed due to insufficient funds."

        pet_nick = nickname.strip() if nickname else pet["name"]
        await db.execute(
            """
            INSERT INTO economy_user_pets (guild_id, user_id, pet_type, nickname, level, xp, happiness, is_equipped, last_fed)
            VALUES (?, ?, ?, ?, 1, 0, 100, 1, ?)
            """,
            (guild_id, user_id, pet_type, pet_nick, time.time()),
        )
        return True, f"🎉 You adopted **{pet['emoji']} {pet_nick}**! They are now your active equipped companion."

    async def feed_pet(self, guild_id: int, user_id: int, pet_type: str) -> Tuple[bool, str]:
        """Feed pet with Gourmet Pet Food from inventory or pay 75 coins directly."""
        user_pet = await db.fetchone(
            """
            SELECT up.*, p.name, p.emoji
            FROM economy_user_pets up
            JOIN economy_pets p ON up.pet_type = p.pet_type
            WHERE up.guild_id = ? AND up.user_id = ? AND up.pet_type = ?
            """,
            (guild_id, user_id, pet_type),
        )
        if not user_pet:
            return False, f"You don't own any pet of type `{pet_type}`."

        # Check if user has pet_food in inventory
        inv_food = await db.fetchone(
            "SELECT quantity FROM economy_inventory WHERE guild_id = ? AND user_id = ? AND item_id = 'pet_food'",
            (guild_id, user_id),
        )

        if inv_food and inv_food["quantity"] > 0:
            await self.remove_item(guild_id, user_id, "pet_food", 1)
        else:
            # Pay 75 coins
            success = await self.modify_wallet(guild_id, user_id, -75, tx_type="feed_pet", description="Pet Food Purchase")
            if not success:
                return False, "You need at least **75 Coins** or `Gourmet Pet Feast` in your inventory to feed your pet!"

        new_happiness = min(100, user_pet["happiness"] + 35)
        new_xp = user_pet["xp"] + 25
        leveled_up = False
        new_level = user_pet["level"]

        # Level up threshold: level * 100 XP
        if new_xp >= (new_level * 100):
            new_level += 1
            new_xp = 0
            leveled_up = True

        await db.execute(
            """
            UPDATE economy_user_pets
            SET happiness = ?, xp = ?, level = ?, last_fed = ?
            WHERE guild_id = ? AND user_id = ? AND pet_type = ?
            """,
            (new_happiness, new_xp, new_level, time.time(), guild_id, user_id, pet_type),
        )

        msg = f"Nom nom! **{user_pet['emoji']} {user_pet['nickname']}** happily ate the feast! (Happiness: **{new_happiness}%**)"
        if leveled_up:
            msg += f"\n⭐ **Level Up!** Your pet reached **Level {new_level}**! Their active bonus increased!"

        await self.check_achievements(guild_id, user_id)
        return True, msg

    async def equip_pet(self, guild_id: int, user_id: int, pet_type: str) -> Tuple[bool, str]:
        """Set active companion pet."""
        exists = await db.fetchone(
            "SELECT nickname FROM economy_user_pets WHERE guild_id = ? AND user_id = ? AND pet_type = ?",
            (guild_id, user_id, pet_type),
        )
        if not exists:
            return False, f"You don't have a pet of type `{pet_type}`!"

        # Unequip all pets
        await db.execute("UPDATE economy_user_pets SET is_equipped = 0 WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        # Equip this pet
        await db.execute(
            "UPDATE economy_user_pets SET is_equipped = 1 WHERE guild_id = ? AND user_id = ? AND pet_type = ?",
            (guild_id, user_id, pet_type),
        )
        return True, f"Equipped **{exists['nickname']}** as your active pet companion!"

    async def rename_pet(self, guild_id: int, user_id: int, pet_type: str, new_name: str) -> Tuple[bool, str]:
        """Rename your pet."""
        clean_name = new_name.strip()[:32]
        if not clean_name:
            return False, "Please provide a valid pet name."

        cursor = await db.execute(
            "UPDATE economy_user_pets SET nickname = ? WHERE guild_id = ? AND user_id = ? AND pet_type = ?",
            (clean_name, guild_id, user_id, pet_type),
        )
        if cursor.rowcount == 0:
            return False, f"You do not own a pet of type `{pet_type}`."
        return True, f"Renamed pet to **{clean_name}**!"

    async def get_user_pets(self, guild_id: int, user_id: int) -> List[Dict[str, Any]]:
        """Fetch all pets owned by user."""
        rows = await db.fetchall(
            """
            SELECT up.*, p.emoji, p.rarity, p.bonus_type, p.bonus_value, p.description as pet_desc
            FROM economy_user_pets up
            JOIN economy_pets p ON up.pet_type = p.pet_type
            WHERE up.guild_id = ? AND up.user_id = ?
            ORDER BY up.is_equipped DESC, up.level DESC
            """,
            (guild_id, user_id),
        )
        return [dict(r) for r in rows]

    async def get_equipped_pet(self, guild_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Fetch the currently active pet for this user."""
        row = await db.fetchone(
            """
            SELECT up.*, p.emoji, p.rarity, p.bonus_type, p.bonus_value
            FROM economy_user_pets up
            JOIN economy_pets p ON up.pet_type = p.pet_type
            WHERE up.guild_id = ? AND up.user_id = ? AND up.is_equipped = 1
            """,
            (guild_id, user_id),
        )
        return dict(row) if row else None

    # ==================== CRATES & LOOT TABLES ====================

    async def open_crate(self, guild_id: int, user_id: int, crate_id: str, amount: int = 1) -> Tuple[bool, List[Dict[str, Any]], str]:
        """Open mystery crates with transparent probability drops."""
        if amount <= 0:
            return False, [], "Amount must be at least 1."

        inv = await db.fetchone(
            "SELECT quantity FROM economy_inventory WHERE guild_id = ? AND user_id = ? AND item_id = ?",
            (guild_id, user_id, crate_id),
        )
        if not inv or inv["quantity"] < amount:
            return False, [], f"You don't have **{amount}x** of `{crate_id}` in your inventory!"

        # Remove crate(s)
        await self.remove_item(guild_id, user_id, crate_id, amount)

        results: List[Dict[str, Any]] = []
        total_coins = 0
        total_gems = 0

        for _ in range(amount):
            if crate_id == "common_crate":
                c = random.randint(300, 800)
                g = random.randint(1, 3)
                total_coins += c
                total_gems += g
                results.append({"coins": c, "gems": g, "special": None})

            elif crate_id == "rare_crate":
                c = random.randint(1500, 4000)
                g = random.randint(4, 10)
                total_coins += c
                total_gems += g
                # 20% chance for rare equipment
                special = None
                if random.random() < 0.20:
                    special = random.choice(["iron_sword", "hunting_bow", "safari_rifle", "lucky_charm"])
                    await self.give_item(guild_id, user_id, special, 1)
                results.append({"coins": c, "gems": g, "special": special})

            elif crate_id == "epic_crate":
                c = random.randint(6000, 15000)
                g = random.randint(15, 30)
                total_coins += c
                total_gems += g
                # 30% chance for epic equipment
                special = None
                if random.random() < 0.30:
                    special = random.choice(["crimson_slayer", "vortex_rifle", "master_net", "golden_horseshoe"])
                    await self.give_item(guild_id, user_id, special, 1)
                results.append({"coins": c, "gems": g, "special": special})

            elif crate_id == "legendary_crate":
                c = random.randint(25000, 60000)
                g = random.randint(40, 100)
                total_coins += c
                total_gems += g
                # 40% chance for legendary/mythical equipment
                special = None
                if random.random() < 0.40:
                    special = random.choice(["antimatter_cannon", "celestial_blade", "golden_lasso", "gulamali_crown"])
                    await self.give_item(guild_id, user_id, special, 1)
                results.append({"coins": c, "gems": g, "special": special})

        await self.modify_wallet(guild_id, user_id, total_coins, tx_type="crate_open", description=f"Opened {amount}x {crate_id}")
        await self.modify_gems(guild_id, user_id, total_gems)

        summary = f"Opened **{amount}x** `{crate_id}`:\nEarned **+{total_coins:,} {CURRENCY_NAME}** and **+{total_gems} {GEM_NAME}**!"
        return True, results, summary

    # ==================== BATTLE & PVP SYSTEM ====================

    async def calculate_battle_stats(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        """Calculate total battle combat stats including equipment and pet buffs."""
        user = await self.get_or_create_user(guild_id, user_id)
        lvl = user["level"]

        hp = 100 + (lvl * 15)
        attack = 15 + (lvl * 3)
        defense = 5 + (lvl * 2)

        equipped = await self.get_equipped_items(guild_id, user_id)
        for item in equipped.values():
            attack += item.get("attack_bonus", 0)
            defense += item.get("defense_bonus", 0)

        equipped_pet = await self.get_equipped_pet(guild_id, user_id)
        if equipped_pet:
            pet_lvl = equipped_pet["level"]
            if equipped_pet["bonus_type"] == "battle_attack":
                attack = int(attack * (1.0 + (equipped_pet["bonus_value"] * pet_lvl) / 100.0))
            elif equipped_pet["bonus_type"] == "battle_defense":
                defense = int(defense * (1.0 + (equipped_pet["bonus_value"] * pet_lvl) / 100.0))

        return {
            "user_id": user_id,
            "level": lvl,
            "max_hp": hp,
            "hp": hp,
            "attack": attack,
            "defense": defense,
            "equipped": equipped,
            "pet": equipped_pet,
        }

    async def resolve_battle(
        self,
        guild_id: int,
        p1_id: int,
        p2_id: int,
        bet: int = 0,
    ) -> Dict[str, Any]:
        """Simulate turn-based combat between two players and resolve bets/rewards."""
        p1 = await self.calculate_battle_stats(guild_id, p1_id)
        p2 = await self.calculate_battle_stats(guild_id, p2_id)

        # Validate bets if present
        if bet > 0:
            u1 = await self.get_or_create_user(guild_id, p1_id)
            u2 = await self.get_or_create_user(guild_id, p2_id)
            if u1["wallet"] < bet or u2["wallet"] < bet:
                return {"success": False, "message": "One of the fighters does not have enough coins for this bet!"}
            await self.modify_wallet(guild_id, p1_id, -bet, tx_type="battle_bet", description="Battle Bet")
            await self.modify_wallet(guild_id, p2_id, -bet, tx_type="battle_bet", description="Battle Bet")

        combat_log: List[str] = []
        turn = 0
        max_turns = 20

        while p1["hp"] > 0 and p2["hp"] > 0 and turn < max_turns:
            turn += 1
            # Player 1 attacks Player 2
            dmg1 = max(5, int((p1["attack"] * random.uniform(0.85, 1.15)) - (p2["defense"] * 0.4)))
            # 10% Critical strike chance
            if random.random() < 0.10:
                dmg1 = int(dmg1 * 1.5)
                combat_log.append(f"💥 **Round {turn}:** <@{p1_id}> landed a **CRITICAL HIT** on <@{p2_id}> for **{dmg1} DMG**!")
            else:
                combat_log.append(f"⚔️ **Round {turn}:** <@{p1_id}> struck <@{p2_id}> for **{dmg1} DMG**!")

            p2["hp"] -= dmg1
            if p2["hp"] <= 0:
                break

            # Player 2 counter-attacks Player 1
            dmg2 = max(5, int((p2["attack"] * random.uniform(0.85, 1.15)) - (p1["defense"] * 0.4)))
            if random.random() < 0.10:
                dmg2 = int(dmg2 * 1.5)
                combat_log.append(f"💥 **Round {turn}:** <@{p2_id}> landed a **CRITICAL COUNTER** on <@{p1_id}> for **{dmg2} DMG**!")
            else:
                combat_log.append(f"🛡️ **Round {turn}:** <@{p2_id}> counter-attacked <@{p1_id}> for **{dmg2} DMG**!")

            p1["hp"] -= dmg2

        if p1["hp"] > p2["hp"]:
            winner_id = p1_id
            loser_id = p2_id
        else:
            winner_id = p2_id
            loser_id = p1_id

        # Update stats
        await db.execute("UPDATE economy_users SET battles_won = battles_won + 1 WHERE guild_id = ? AND user_id = ?", (guild_id, winner_id))
        await db.execute("UPDATE economy_users SET battles_lost = battles_lost + 1 WHERE guild_id = ? AND user_id = ?", (guild_id, loser_id))

        xp_reward = random.randint(60, 120)
        coin_prize = (bet * 2) if bet > 0 else random.randint(200, 500)

        await self.modify_wallet(guild_id, winner_id, coin_prize, tx_type="battle_win", description=f"Battle Victory against {loser_id}")
        await self.add_xp(guild_id, winner_id, xp_reward)
        await self.add_xp(guild_id, loser_id, max(15, xp_reward // 3))

        # Record battle log in DB
        await db.execute(
            """
            INSERT INTO economy_battles (guild_id, challenger_id, opponent_id, winner_id, loser_id, bet_amount, xp_awarded, battle_log)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (guild_id, p1_id, p2_id, winner_id, loser_id, bet, xp_reward, "\n".join(combat_log)),
        )

        await self.check_achievements(guild_id, winner_id)

        return {
            "success": True,
            "winner_id": winner_id,
            "loser_id": loser_id,
            "rounds": turn,
            "log": combat_log,
            "xp_reward": xp_reward,
            "coin_prize": coin_prize,
            "p1_final_hp": max(0, p1["hp"]),
            "p2_final_hp": max(0, p2["hp"]),
        }

    # ==================== SOCIAL & MARRIAGE ====================

    async def marry(self, guild_id: int, user1_id: int, user2_id: int) -> Tuple[bool, str]:
        """Propose marriage using a diamond ring."""
        if user1_id == user2_id:
            return False, "You cannot marry yourself!"

        # Check existing marriage
        m1 = await db.fetchone(
            "SELECT id FROM economy_relationships WHERE guild_id = ? AND (user1_id = ? OR user2_id = ?)",
            (guild_id, user1_id, user1_id),
        )
        if m1:
            return False, "You are already married in this server! You must `/divorce` first."

        m2 = await db.fetchone(
            "SELECT id FROM economy_relationships WHERE guild_id = ? AND (user1_id = ? OR user2_id = ?)",
            (guild_id, user2_id, user2_id),
        )
        if m2:
            return False, "That user is already married to someone else!"

        # Check ring ownership
        ring = await db.fetchone(
            "SELECT quantity FROM economy_inventory WHERE guild_id = ? AND user_id = ? AND item_id = 'diamond_ring'",
            (guild_id, user1_id),
        )
        if not ring or ring["quantity"] <= 0:
            return False, "You need a **💍 Diamond Engagement Ring** to marry! You can purchase one in `/shop special`."

        # Deduct ring
        await self.remove_item(guild_id, user1_id, "diamond_ring", 1)

        await db.execute(
            """
            INSERT INTO economy_relationships (guild_id, user1_id, user2_id)
            VALUES (?, ?, ?)
            """,
            (guild_id, user1_id, user2_id),
        )

        await self.check_achievements(guild_id, user1_id)
        await self.check_achievements(guild_id, user2_id)

        return True, "💍 **Congratulations!** You are now happily married!"

    async def divorce(self, guild_id: int, user_id: int) -> Tuple[bool, str]:
        """Divorce your current partner."""
        rel = await db.fetchone(
            "SELECT id, user1_id, user2_id FROM economy_relationships WHERE guild_id = ? AND (user1_id = ? OR user2_id = ?)",
            (guild_id, user_id, user_id),
        )
        if not rel:
            return False, "You are not married to anyone!"

        await db.execute("DELETE FROM economy_relationships WHERE id = ?", (rel["id"],))
        partner_id = rel["user2_id"] if rel["user1_id"] == user_id else rel["user1_id"]
        return True, f"💔 You have officially divorced <@{partner_id}>."

    async def get_relationship(self, guild_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Fetch relationship info for user."""
        row = await db.fetchone(
            "SELECT * FROM economy_relationships WHERE guild_id = ? AND (user1_id = ? OR user2_id = ?)",
            (guild_id, user_id, user_id),
        )
        if not row:
            return None
        d = dict(row)
        d["partner_id"] = d["user2_id"] if d["user1_id"] == user_id else d["user1_id"]
        return d

    async def give_rep(self, guild_id: int, sender_id: int, receiver_id: int) -> Tuple[bool, str]:
        """Give reputation point to another member (24h cooldown)."""
        if sender_id == receiver_id:
            return False, "You cannot give reputation to yourself!"

        sender = await self.get_or_create_user(guild_id, sender_id)
        now = time.time()
        cooldown = 86400  # 24 Hours

        if now - sender["last_rep"] < cooldown:
            remaining = int(cooldown - (now - sender["last_rep"]))
            hours, rem = divmod(remaining, 3600)
            mins, _ = divmod(rem, 60)
            return False, f"Reputation is on cooldown! You can give rep again in **{hours}h {mins}m**."

        await self.get_or_create_user(guild_id, receiver_id)

        await db.execute(
            "UPDATE economy_users SET last_rep = ? WHERE guild_id = ? AND user_id = ?",
            (now, guild_id, sender_id),
        )
        await db.execute(
            "UPDATE economy_users SET reputation = reputation + 1 WHERE guild_id = ? AND user_id = ?",
            (guild_id, receiver_id),
        )
        return True, f"🌟 You gave **+1 Reputation** to <@{receiver_id}>!"

    # ==================== ACHIEVEMENTS ENGINE ====================

    async def check_achievements(self, guild_id: int, user_id: int) -> List[Dict[str, Any]]:
        """Evaluate and unlock any eligible achievements for this user."""
        user = await self.get_or_create_user(guild_id, user_id)
        unlocked_achievements: List[Dict[str, Any]] = []

        # Get existing unlocked keys
        rows = await db.fetchall(
            "SELECT achievement_key FROM economy_user_achievements WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        existing_keys = {r["achievement_key"] for r in rows}

        conditions = [
            ("first_coin", user["total_earned"] > 0 or user["wallet"] > 500),
            ("first_hunt", user["hunts_count"] >= 1),
            ("hunts_25", user["hunts_count"] >= 25),
            ("hunts_100", user["hunts_count"] >= 100),
            ("first_battle", user["battles_won"] >= 1),
            ("battles_10", user["battles_won"] >= 10),
            ("millionaire", (user["wallet"] + user["bank"]) >= 1000000),
            ("daily_streak_7", user["daily_streak"] >= 7),
            ("daily_streak_30", user["daily_streak"] >= 30),
        ]

        for key, cond in conditions:
            if cond and key not in existing_keys:
                ach = await db.fetchone("SELECT * FROM economy_achievements WHERE key = ?", (key,))
                if ach:
                    await db.execute(
                        """
                        INSERT INTO economy_user_achievements (guild_id, user_id, achievement_key)
                        VALUES (?, ?, ?)
                        ON CONFLICT DO NOTHING
                        """,
                        (guild_id, user_id, key),
                    )
                    # Award rewards
                    await self.modify_wallet(guild_id, user_id, ach["coin_reward"], tx_type="achievement", description=f"Achievement: {ach['name']}")
                    await self.modify_gems(guild_id, user_id, ach["gem_reward"])
                    unlocked_achievements.append(dict(ach))
                    existing_keys.add(key)

        return unlocked_achievements


# Global Economy Service Singleton
economy_service = EconomyService()
