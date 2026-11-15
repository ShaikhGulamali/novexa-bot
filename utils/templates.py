"""NOVEXA - 50 Professional Server Templates Collection.

Provides 50 rich, fully configured server templates spanning:
- Gaming & Esports (8)
- Store & Commerce (6)
- Tech, Coding & AI (6)
- Content Creators & Media (5)
- Anime, Manga & Fandoms (5)
- Social, Hangout & Lifestyle (5)
- Music & Audio Production (4)
- Education, Campus & Stocks (4)
- Business, Startups & Enterprise (4)
- Special Ops, Events & Minimal (3)
"""

from typing import Dict, List, Any

# Standard 11 Roles with colors, permissions, and hierarchy
# Hierarchy: Top is Novexa (Bot), 2nd is Member, followed by Administration & Community Roles
DEFAULT_ROLES: List[Dict[str, Any]] = [
    {
        "name": "👤 Member",
        "color": 0x5865F2,
        "hoist": False,
        "mentionable": False,
        "perms": {"view_channel": True, "send_messages": True, "read_message_history": True, "connect": True, "speak": True},
    },
    {
        "name": "👑 Owner",
        "color": 0xFFD700,
        "hoist": True,
        "mentionable": True,
        "perms": {"administrator": True},
    },
    {
        "name": "🔱 Co-Owner",
        "color": 0xE67E22,
        "hoist": True,
        "mentionable": True,
        "perms": {"administrator": True},
    },
    {
        "name": "🛡️ Administrator",
        "color": 0xE74C3C,
        "hoist": True,
        "mentionable": True,
        "perms": {
            "manage_guild": True,
            "manage_roles": True,
            "manage_channels": True,
            "kick_members": True,
            "ban_members": True,
            "manage_messages": True,
            "view_audit_log": True,
        },
    },
    {
        "name": "🔨 Moderator",
        "color": 0x3498DB,
        "hoist": True,
        "mentionable": True,
        "perms": {
            "kick_members": True,
            "ban_members": True,
            "manage_messages": True,
            "mute_members": True,
            "deafen_members": True,
            "move_members": True,
            "view_audit_log": True,
        },
    },
    {
        "name": "🎫 Support Team",
        "color": 0x2ECC71,
        "hoist": True,
        "mentionable": True,
        "perms": {
            "manage_messages": True,
            "view_channel": True,
            "send_messages": True,
            "attach_files": True,
            "embed_links": True,
            "read_message_history": True,
        },
    },
    {
        "name": "💎 Platinum",
        "color": 0x9B59B6,
        "hoist": True,
        "mentionable": False,
        "perms": {"attach_files": True, "embed_links": True, "priority_speaker": True, "use_external_emojis": True},
    },
    {
        "name": "🥇 Gold",
        "color": 0xF1C40F,
        "hoist": True,
        "mentionable": False,
        "perms": {"attach_files": True, "embed_links": True, "add_reactions": True, "use_external_emojis": True},
    },
    {
        "name": "🥈 Silver",
        "color": 0x95A5A6,
        "hoist": True,
        "mentionable": False,
        "perms": {"attach_files": True, "embed_links": True, "add_reactions": True},
    },
    {
        "name": "✅ Verified",
        "color": 0x1ABC9C,
        "hoist": True,
        "mentionable": False,
        "perms": {
            "view_channel": True,
            "send_messages": True,
            "read_message_history": True,
            "connect": True,
            "speak": True,
            "attach_files": True,
            "embed_links": True,
            "use_external_emojis": True,
            "add_reactions": True,
        },
    },
    {
        "name": "🤖 Bots",
        "color": 0x607D8B,
        "hoist": True,
        "mentionable": False,
        "perms": {"view_channel": True, "send_messages": True, "embed_links": True, "attach_files": True},
    },
]

# Standard Enterprise Logging Category: 🛡️ NOVEXA LOGS (10 channels)
STANDARD_LOGS_CATEGORY: Dict[str, Any] = {
    "name": "🛡️ NOVEXA LOGS",
    "type": "logs",
    "channels": [
        {"name": "📄・transcripts", "type": "text", "topic": "Archived ticket HTML transcripts", "special": "log_transcripts"},
        {"name": "🤖・bot-logs", "type": "text", "topic": "General bot activity and system events", "special": "log_bot"},
        {"name": "🔊・voice-logs", "type": "text", "topic": "Voice channel connect, disconnect and move logs", "special": "log_voice"},
        {"name": "🛡️・antinuke-logs", "type": "text", "topic": "Server raid protection & anti-nuke audit events", "special": "log_antinuke"},
        {"name": "💬・message-logs", "type": "text", "topic": "Deleted and edited message audit trail", "special": "log_message"},
        {"name": "👥・member-logs", "type": "text", "topic": "Member joins, leaves and role updates", "special": "log_member"},
        {"name": "⚙️・update-logs", "type": "text", "topic": "Channel and server setting change audits", "special": "log_update"},
        {"name": "🎫・ticket-logs", "type": "text", "topic": "Ticket open, claim and close lifecycle events", "special": "log_ticket"},
        {"name": "💳・payment-logs", "type": "text", "topic": "UPI/QR payment submission & verification logs", "special": "log_payment"},
        {"name": "🔐・security-logs", "type": "text", "topic": "Bans, kicks, timeouts and verification events", "special": "log_security"},
    ],
}

# The 10 Categories of Templates
TEMPLATE_CATEGORIES = {
    "all": "🌐 Browse All (1-50)",
    "gaming": "🎮 Gaming & Esports",
    "store": "🛍️ Store & Commerce",
    "tech": "💻 Tech, Coding & AI",
    "creators": "🎥 Content Creators & Media",
    "anime": "⛩️ Anime, Manga & Fandoms",
    "social": "💬 Social, Hangout & Lifestyle",
    "music": "🎵 Music & Audio Production",
    "education": "📚 Education, Campus & Stocks",
    "business": "🏢 Business, Startups & Enterprise",
    "special": "⚡ Special Ops, Events & Minimal",
}

TEMPLATES: Dict[str, Dict[str, Any]] = {
    # ==================== GROUP 1: GAMING & ESPORTS ====================
    "gaming": {
        "id": "gaming",
        "name": "Gaming Community",
        "emoji": "🎮",
        "category": "Gaming & Esports",
        "group": "gaming",
        "description": "Multiplayer game lobbies, squad voice rooms, clips & tournament channels.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 INFORMATION",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・rules", "type": "text", "topic": "Community guidelines & server rules", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Member join and leave notifications", "special": "welcome"},
                    {"name": "📌・server-info", "type": "text", "topic": "Server links, ranks, and roles overview"},
                    {"name": "📣・announcements", "type": "text", "topic": "Official announcements & game events", "special": "announcements"},
                ],
            },
            {
                "name": "💬 TEXT CHANNELS",
                "type": "public",
                "channels": [
                    {"name": "💬・general-chat", "type": "text", "topic": "Main hangout text lounge"},
                    {"name": "🎬・clips-and-highlights", "type": "text", "topic": "Share your best gaming clips"},
                    {"name": "🤣・memes", "type": "text", "topic": "Gaming and internet memes"},
                    {"name": "🤖・bot-commands", "type": "text", "topic": "Run bot commands and games"},
                    {"name": "🖥️・setup-showcase", "type": "text", "topic": "Show off your battle stations and PC builds"},
                ],
            },
            {
                "name": "🎮 GAME LOBBIES",
                "type": "public",
                "channels": [
                    {"name": "🎯・valorant", "type": "text", "topic": "Valorant matchmaking and discussions"},
                    {"name": "🚗・gta-v", "type": "text", "topic": "GTA V and FiveM roleplay discussions"},
                    {"name": "⛏️・minecraft", "type": "text", "topic": "Minecraft servers and builds"},
                    {"name": "🪂・pubg-bgmi", "type": "text", "topic": "PUBG / BGMI squad searches"},
                    {"name": "🔫・call-of-duty", "type": "text", "topic": "Warzone and Modern Warfare discussions"},
                    {"name": "⚡・apex-legends", "type": "text", "topic": "Apex Legends squad finder"},
                ],
            },
            {
                "name": "🎧 GENERAL VOICE",
                "type": "public_voice",
                "channels": [
                    {"name": "📢・Public VC 1", "type": "voice"},
                    {"name": "📢・Public VC 2", "type": "voice"},
                    {"name": "☕・Chill Lounge", "type": "voice"},
                    {"name": "🔴・Streamer VC", "type": "voice"},
                    {"name": "🟢・Music VC", "type": "voice"},
                ],
            },
            {
                "name": "👥 SQUAD VOICE",
                "type": "public_voice",
                "channels": [
                    {"name": "👥・Duo 1", "type": "voice", "user_limit": 2},
                    {"name": "👥・Duo 2", "type": "voice", "user_limit": 2},
                    {"name": "👥・Trio", "type": "voice", "user_limit": 3},
                    {"name": "👥・Squad", "type": "voice", "user_limit": 4},
                ],
            },
            {
                "name": "🎫 SUPPORT",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・open-ticket", "type": "text", "topic": "Create support ticket", "special": "ticket_panel"},
                ],
            },
            {
                "name": "👑 MANAGEMENT",
                "type": "staff_only",
                "channels": [
                    {"name": "💬・staff-chat", "type": "text", "topic": "Staff discussion and moderation tasks"},
                    {"name": "🤖・bot-testing", "type": "text", "topic": "Bot configuration and experiments"},
                    {"name": "🔒・Admin VC", "type": "voice"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "esports_clan": {
        "id": "esports_clan",
        "name": "Esports & Clan War",
        "emoji": "⚔️",
        "category": "Gaming & Esports",
        "group": "gaming",
        "description": "Competitive team roster, scrim schedules, tournament results & tactical comms.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 ARENA INFO",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・rules", "type": "text", "topic": "Clan conduct & rules", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "New recruit greetings", "special": "welcome"},
                    {"name": "📣・announcements", "type": "text", "topic": "Tournament announcements", "special": "announcements"},
                    {"name": "🏆・clan-roster", "type": "text", "topic": "Official team line-ups"},
                    {"name": "📅・tournament-schedule", "type": "text", "topic": "Upcoming matches and scrim timings"},
                ],
            },
            {
                "name": "⚔️ SCRIMS & MATCHES",
                "type": "public",
                "channels": [
                    {"name": "🎯・scrim-results", "type": "text", "topic": "Post-match scores and kill leaderboards"},
                    {"name": "📊・leaderboard", "type": "text", "topic": "Player rankings"},
                    {"name": "🎥・match-highlights", "type": "text", "topic": "Ace rounds and clutches"},
                    {"name": "⚔️・strategy-room", "type": "text", "topic": "Tactics, callouts and lineups"},
                ],
            },
            {
                "name": "💬 CLAN LOUNGE",
                "type": "public",
                "channels": [
                    {"name": "💬・clan-chat", "type": "text", "topic": "General team conversation"},
                    {"name": "🎮・other-games", "type": "text", "topic": "Casual gaming hangout"},
                    {"name": "🤖・bot-commands", "type": "text", "topic": "Bot fun and music controls"},
                ],
            },
            {
                "name": "🔊 COMPETITIVE COMMS",
                "type": "public_voice",
                "channels": [
                    {"name": "🎙️・Team Alpha VC", "type": "voice", "user_limit": 5},
                    {"name": "🎙️・Team Bravo VC", "type": "voice", "user_limit": 5},
                    {"name": "🎯・Scrim Comms", "type": "voice", "user_limit": 5},
                    {"name": "🎧・Casual Lounge", "type": "voice"},
                ],
            },
            {
                "name": "👑 LEADERSHIP",
                "type": "staff_only",
                "channels": [
                    {"name": "💬・officers-chat", "type": "text", "topic": "Management and roster discussions"},
                    {"name": "🔒・Leadership VC", "type": "voice"},
                ],
            },
            {
                "name": "🎫 TRYOUTS & TICKETS",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・apply-tryout", "type": "text", "topic": "Submit clan tryout application", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "minecraft_network": {
        "id": "minecraft_network",
        "name": "Minecraft SMP & Network",
        "emoji": "⛏️",
        "category": "Gaming & Esports",
        "group": "gaming",
        "description": "SMP factions, server status, whitelist applications, texture packs & build showcases.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 NETWORK INFO",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・server-rules", "type": "text", "topic": "Griefing and SMP rules", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "New player greetings", "special": "welcome"},
                    {"name": "🌐・server-ip", "type": "text", "topic": "IP, Bedrock port and dynmap"},
                    {"name": "📣・patch-notes", "type": "text", "topic": "Server updates and resets", "special": "announcements"},
                ],
            },
            {
                "name": "⛏️ SURVIVAL SMP",
                "type": "public",
                "channels": [
                    {"name": "💬・smp-chat", "type": "text", "topic": "In-game synced chat"},
                    {"name": "🏰・towns-factions", "type": "text", "topic": "Clan alliances and wars"},
                    {"name": "💎・trade-market", "type": "text", "topic": "Diamond and item trading"},
                    {"name": "📸・build-showcase", "type": "text", "topic": "Show off your megabases"},
                    {"name": "🎨・texture-packs", "type": "text", "topic": "Recommended shaders and packs"},
                ],
            },
            {
                "name": "🎧 VOICE CHANNELS",
                "type": "public_voice",
                "channels": [
                    {"name": "🔊・Mining Lounge", "type": "voice"},
                    {"name": "⚔️・PvP Arena VC", "type": "voice"},
                    {"name": "🌾・Farming Chill", "type": "voice"},
                    {"name": "🟢・Music VC", "type": "voice"},
                ],
            },
            {
                "name": "🎫 WHITELIST & TICKETS",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・whitelist-apply", "type": "text", "topic": "Apply for SMP whitelist", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "gta_fivem": {
        "id": "gta_fivem",
        "name": "GTA V & FiveM Roleplay",
        "emoji": "🚗",
        "category": "Gaming & Esports",
        "group": "gaming",
        "description": "FiveM city RP, Police / EMS departments, gang territories & civilian economy.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 CITY HALL",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・city-laws", "type": "text", "topic": "Penal code and RP rules", "special": "rules"},
                    {"name": "🌸・arrival-hall", "type": "text", "topic": "Welcome to Los Santos", "special": "welcome"},
                    {"name": "📣・city-bulletin", "type": "text", "topic": "Government announcements", "special": "announcements"},
                    {"name": "📰・daily-globe", "type": "text", "topic": "Weazel News headlines"},
                ],
            },
            {
                "name": "🚓 EMERGENCY SERVICES",
                "type": "staff_only",
                "channels": [
                    {"name": "🚨・police-dispatch", "type": "text", "topic": "LSPD active 10-codes"},
                    {"name": "🚑・ems-hospital", "type": "text", "topic": "EMS medical logs"},
                    {"name": "⚖️・doj-court", "type": "text", "topic": "Court hearings and trials"},
                ],
            },
            {
                "name": "🏙️ CIVILIAN & CRIME",
                "type": "public",
                "channels": [
                    {"name": "💬・twitter-rp", "type": "text", "topic": "In-character social feed"},
                    {"name": "💼・business-classifieds", "type": "text", "topic": "Mechanics, dealerships, clubs"},
                    {"name": "🕶️・black-market", "type": "text", "topic": "Dark web trade"},
                    {"name": "🏎️・car-meets", "type": "text", "topic": "Showcasing tuned rides"},
                ],
            },
            {
                "name": "🎧 RADIO FREQUENCIES",
                "type": "public_voice",
                "channels": [
                    {"name": "📻・Radio 1 (Civilian)", "type": "voice"},
                    {"name": "📻・Radio 2 (Public)", "type": "voice"},
                    {"name": "☕・Burger Shot Chill", "type": "voice"},
                ],
            },
            {
                "name": "🎫 IMMIGRATION VISA",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・apply-visa", "type": "text", "topic": "Apply for citizenship/whitelist", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "fps_tactical": {
        "id": "fps_tactical",
        "name": "Tactical FPS Hub (Val / CS2)",
        "emoji": "🎯",
        "category": "Gaming & Esports",
        "group": "gaming",
        "description": "Ranked 5v5 matchmaking, lineup guides, utility spots & pro coaching.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 BRIEFING",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・rules", "type": "text", "topic": "Competitive standards", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Agent arrivals", "special": "welcome"},
                    {"name": "📣・patch-notes", "type": "text", "topic": "Weapon balancing updates", "special": "announcements"},
                ],
            },
            {
                "name": "🎯 TACTICAL COMMS",
                "type": "public",
                "channels": [
                    {"name": "💬・lounge", "type": "text", "topic": "General FPS discussion"},
                    {"name": "🗺️・lineups-guides", "type": "text", "topic": "Sova recon, smoke spots, flash timings"},
                    {"name": "🔥・clutch-clips", "type": "text", "topic": "1v4 and 1v5 clutches"},
                    {"name": "📈・rank-flex", "type": "text", "topic": "Showcase your Immortal / Radiant ranks"},
                ],
            },
            {
                "name": "🔊 5V5 SQUAD VOICES",
                "type": "public_voice",
                "channels": [
                    {"name": "🎯・Ranked Team 1", "type": "voice", "user_limit": 5},
                    {"name": "🎯・Ranked Team 2", "type": "voice", "user_limit": 5},
                    {"name": "🎯・Ranked Team 3", "type": "voice", "user_limit": 5},
                    {"name": "☕・Aim Lab Chill", "type": "voice"},
                ],
            },
            {
                "name": "🎫 COACHING & REPORTS",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・request-coaching", "type": "text", "topic": "VOD reviews and coaching tickets", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "battle_royale": {
        "id": "battle_royale",
        "name": "Battle Royale Pro Hub",
        "emoji": "🪂",
        "category": "Gaming & Esports",
        "group": "gaming",
        "description": "BGMI, PUBG Mobile, Apex Legends & Warzone squad coordination.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 DROP ZONE",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・rules", "type": "text", "topic": "Server rules", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "New recruit arrivals", "special": "welcome"},
                    {"name": "📣・announcements", "type": "text", "topic": "Custom room IDs and schedules", "special": "announcements"},
                ],
            },
            {
                "name": "🪂 SQUAD RECRUITMENT",
                "type": "public",
                "channels": [
                    {"name": "💬・lobby-chat", "type": "text", "topic": "General chat"},
                    {"name": "🔍・looking-for-duo", "type": "text", "topic": "Find your duo partner"},
                    {"name": "👥・looking-for-squad", "type": "text", "topic": "Complete your 4-man roster"},
                    {"name": "🍗・chicken-dinners", "type": "text", "topic": "Post your Victory Royales"},
                ],
            },
            {
                "name": "🔊 DROP COMMS",
                "type": "public_voice",
                "channels": [
                    {"name": "🪂・Squad Alpha", "type": "voice", "user_limit": 4},
                    {"name": "🪂・Squad Bravo", "type": "voice", "user_limit": 4},
                    {"name": "🪂・Squad Charlie", "type": "voice", "user_limit": 4},
                    {"name": "👥・Duo Comms", "type": "voice", "user_limit": 2},
                ],
            },
            {
                "name": "🎫 CUSTOM ROOM TICKETS",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・room-slot-ticket", "type": "text", "topic": "Book custom tournament slots", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "roblox_studio": {
        "id": "roblox_studio",
        "name": "Roblox Community & Dev",
        "emoji": "🧱",
        "category": "Gaming & Esports",
        "group": "gaming",
        "description": "Roblox developers, Lua scripters, 3D modeling, game testing & trade hub.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 HUB INFO",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・rules", "type": "text", "topic": "Developer ethics and trading safety", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "New builders", "special": "welcome"},
                    {"name": "📣・announcements", "type": "text", "topic": "Game launch events", "special": "announcements"},
                ],
            },
            {
                "name": "🛠️ ROBLOX STUDIO",
                "type": "public",
                "channels": [
                    {"name": "💻・lua-scripting", "type": "text", "topic": "Scripts, functions and debugging"},
                    {"name": "🎨・3d-modeling-blender", "type": "text", "topic": "Meshes and avatar accessories"},
                    {"name": "🏗️・map-building", "type": "text", "topic": "Level design and terrain"},
                    {"name": "🎮・game-testing", "type": "text", "topic": "Playtest upcoming experiences"},
                ],
            },
            {
                "name": "💬 COMMUNITY & TRADING",
                "type": "public",
                "channels": [
                    {"name": "💬・general-chat", "type": "text", "topic": "Roblox discussions"},
                    {"name": "🤝・hiring-devs", "type": "text", "topic": "Paid commissions and partnerships"},
                    {"name": "💰・limiteds-trading", "type": "text", "topic": "RAP and limited trade talk"},
                ],
            },
            {
                "name": "🎧 STUDIO VOICE",
                "type": "public_voice",
                "channels": [
                    {"name": "🧱・Dev Collab VC", "type": "voice"},
                    {"name": "🎮・Playtest VC", "type": "voice"},
                    {"name": "🟢・Music VC", "type": "voice"},
                ],
            },
            {
                "name": "🎫 COMMISSION TICKETS",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・order-commission", "type": "text", "topic": "Hire staff or order assets", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "free_fire": {
        "id": "free_fire",
        "name": "Free Fire Esports & Community",
        "emoji": "🔥",
        "category": "Gaming & Esports",
        "group": "gaming",
        "description": "Custom Rooms, CS Ranked Scrims, Tournaments, Guild Wars & Team VCs.",
        "roles": [
            {
                "name": "👑 Guild Leader",
                "color": 0xFFD700,
                "hoist": True,
                "mentionable": True,
                "perms": {"administrator": True},
            },
            {
                "name": "🔱 Co-Leader",
                "color": 0xF39C12,
                "hoist": True,
                "mentionable": True,
                "perms": {"administrator": True},
            },
            {
                "name": "🛡️ Scrims Manager",
                "color": 0xE74C3C,
                "hoist": True,
                "mentionable": True,
                "perms": {"manage_channels": True, "manage_messages": True, "move_members": True, "mute_members": True},
            },
            {
                "name": "🔨 Scrims Host",
                "color": 0xE67E22,
                "hoist": True,
                "mentionable": True,
                "perms": {"manage_messages": True, "move_members": True, "mute_members": True},
            },
            {
                "name": "🏆 Tier-1 Esports",
                "color": 0x9B59B6,
                "hoist": True,
                "mentionable": True,
                "perms": {"view_channel": True, "send_messages": True, "connect": True, "speak": True},
            },
            {
                "name": "🎖️ Lineup Alpha",
                "color": 0x3498DB,
                "hoist": True,
                "mentionable": True,
                "perms": {"view_channel": True, "send_messages": True, "connect": True, "speak": True},
            },
            {
                "name": "🎖️ Lineup Bravo",
                "color": 0x1ABC9C,
                "hoist": True,
                "mentionable": True,
                "perms": {"view_channel": True, "send_messages": True, "connect": True, "speak": True},
            },
            {
                "name": "⚡ Guild Member",
                "color": 0x2ECC71,
                "hoist": True,
                "mentionable": False,
                "perms": {"view_channel": True, "send_messages": True, "connect": True, "speak": True},
            },
            {
                "name": "💎 VIP Supporter",
                "color": 0xFF69B4,
                "hoist": True,
                "mentionable": False,
                "perms": {"view_channel": True, "send_messages": True, "attach_files": True, "connect": True, "speak": True},
            },
            {
                "name": "✅ Verified Player",
                "color": 0x00BCD4,
                "hoist": True,
                "mentionable": False,
                "perms": {"view_channel": True, "send_messages": True, "connect": True, "speak": True, "attach_files": True, "embed_links": True},
            },
            {
                "name": "👤 Member",
                "color": 0x95A5A6,
                "hoist": False,
                "mentionable": False,
                "perms": {"view_channel": True, "send_messages": True, "connect": True, "speak": True},
            },
            {
                "name": "🤖 Bots",
                "color": 0x607D8B,
                "hoist": True,
                "mentionable": False,
                "perms": {"view_channel": True, "send_messages": True, "embed_links": True, "attach_files": True},
            },
        ],
        "categories": [
            {
                "name": "📢 FF INFORMATION",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・rules", "type": "text", "topic": "Free Fire community & tournament rules", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Welcome survivor!", "special": "welcome"},
                    {"name": "📣・announcements", "type": "text", "topic": "Guild updates and official news", "special": "announcements"},
                    {"name": "📌・guild-info", "type": "text", "topic": "Official Free Fire guild UID & requirements"},
                    {"name": "🎁・giveaways", "type": "text", "topic": "Weekly diamond & air-drop giveaways"},
                ],
            },
            {
                "name": "🔥 ESPORTS & SCRIMS",
                "type": "public",
                "channels": [
                    {"name": "📋・scrims-schedule", "type": "text", "topic": "Daily T1/T2 scrims timing & map rotation"},
                    {"name": "🎟️・slot-booking", "type": "text", "topic": "Book custom room slots for your squad"},
                    {"name": "🔑・room-id-pass", "type": "text", "topic": "Custom room ID & password"},
                    {"name": "📊・points-table", "type": "text", "topic": "Match results, kill points & standings"},
                    {"name": "🏆・tournaments", "type": "text", "topic": "Major tournament announcements & prize pools"},
                ],
            },
            {
                "name": "👥 GUILD & LINEUPS",
                "type": "public",
                "channels": [
                    {"name": "⚡・guild-recruitment", "type": "text", "topic": "Apply for official guild with KD & level"},
                    {"name": "🎯・tryout-announcements", "type": "text", "topic": "Dates and timing for 1v1 & 4v4 tryouts"},
                    {"name": "🎖️・lineup-rosters", "type": "text", "topic": "Active Lineup Alpha & Lineup Bravo players"},
                    {"name": "⚔️・guild-wars", "type": "text", "topic": "Weekend Guild Wars coordination"},
                ],
            },
            {
                "name": "💬 COMMUNITY LOBBY",
                "type": "public",
                "channels": [
                    {"name": "💬・general-chat", "type": "text", "topic": "Main Free Fire community chat"},
                    {"name": "🔥・cs-ranked-lfg", "type": "text", "topic": "Find Clash Squad ranked teammates"},
                    {"name": "⚔️・1v1-custom-challenge", "type": "text", "topic": "Challenge other players for 1v1 custom room"},
                    {"name": "🎬・montage-clips", "type": "text", "topic": "Share one-tap headshots & highlights"},
                    {"name": "⚙️・hud-sensi", "type": "text", "topic": "Share DPI, HUD layout and sensitivity settings"},
                    {"name": "🤖・bot-commands", "type": "text", "topic": "Use bot commands, music & games"},
                ],
            },
            {
                "name": "🎧 MATCH VOICE COMMS",
                "type": "public_voice",
                "channels": [
                    {"name": "🔊・Squad VC 1", "type": "voice", "user_limit": 4},
                    {"name": "🔊・Squad VC 2", "type": "voice", "user_limit": 4},
                    {"name": "🔊・Squad VC 3", "type": "voice", "user_limit": 4},
                    {"name": "👥・Duo VC 1", "type": "voice", "user_limit": 2},
                    {"name": "👥・Duo VC 2", "type": "voice", "user_limit": 2},
                    {"name": "⚔️・1v1 Custom Room VC", "type": "voice", "user_limit": 2},
                    {"name": "🎵・Chill & Music VC", "type": "voice"},
                ],
            },
            {
                "name": "👑 LINEUP & STAFF HQ",
                "type": "staff_only",
                "channels": [
                    {"name": "💬・lineup-chat", "type": "text", "topic": "Competitive lineup internal strategy"},
                    {"name": "🛡️・staff-chat", "type": "text", "topic": "Moderators & scrims hosts discussion"},
                    {"name": "🔊・Lineup Alpha VC", "type": "voice", "user_limit": 5},
                    {"name": "🔊・Lineup Bravo VC", "type": "voice", "user_limit": 5},
                    {"name": "🔒・Management VC", "type": "voice"},
                ],
            },
            {
                "name": "🎫 SUPPORT & APPLY",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・guild-apply-ticket", "type": "text", "topic": "Open ticket to submit KD & apply for guild", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },

    # ==================== GROUP 2: STORE, MARKET & COMMERCE ====================
    "digital_store": {
        "id": "digital_store",
        "name": "Novexa Digital Store",
        "emoji": "🛍️",
        "category": "Store & Commerce",
        "group": "store",
        "description": "Complete digital products store with EMI, payments, catalog & VIP support.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 INFORMATION",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・rules", "type": "text", "topic": "Store rules and terms of service", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Member join and greetings", "special": "welcome"},
                    {"name": "📌・server-info", "type": "text", "topic": "Store overview, guarantees and working hours"},
                    {"name": "📣・announcements", "type": "text", "topic": "Discounts, updates and new products", "special": "announcements"},
                ],
            },
            {
                "name": "💰 PURCHASE",
                "type": "public_read_only",
                "channels": [
                    {"name": "💵・buy", "type": "text", "topic": "How to purchase digital products"},
                    {"name": "💳・emi", "type": "text", "topic": "Flexible EMI payment plans"},
                    {"name": "💎・payment-methods", "type": "text", "topic": "Supported UPI, Crypto & Card options"},
                    {"name": "🧾・payment-proofs", "type": "text", "topic": "Verified customer purchase receipts"},
                ],
            },
            {
                "name": "🛍️ NOVEXA EXE STORE",
                "type": "public_read_only",
                "channels": [
                    {"name": "🛒・cover-silent-aim", "type": "text", "topic": "Cover Silent Aim feature & pricing"},
                    {"name": "🛒・silent-aim", "type": "text", "topic": "Silent Aim editions"},
                    {"name": "🛒・internal", "type": "text", "topic": "Internal bypass package"},
                    {"name": "🛒・elite", "type": "text", "topic": "Elite VIP tools"},
                    {"name": "🛒・uid-bypass", "type": "text", "topic": "UID Bypass system"},
                    {"name": "🛒・streamer", "type": "text", "topic": "Streamer safe overlays"},
                    {"name": "🛒・aimkill", "type": "text", "topic": "Aimkill editions"},
                    {"name": "🛒・ios", "type": "text", "topic": "iOS configuration files"},
                    {"name": "🛒・custom-panel", "type": "text", "topic": "Custom reseller & admin panels"},
                    {"name": "🛒・projects", "type": "text", "topic": "Featured digital projects"},
                    {"name": "🛒・codes", "type": "text", "topic": "Source codes & redemption vouchers"},
                ],
            },
            {
                "name": "📄 LOBBY",
                "type": "public",
                "channels": [
                    {"name": "💬・chat", "type": "text", "topic": "Community general chat"},
                    {"name": "⚒️・problems", "type": "text", "topic": "Product troubleshooting & user discussion"},
                    {"name": "🎮・gaming", "type": "text", "topic": "Customer gaming hangout"},
                ],
            },
            {
                "name": "🎧 GENERAL VOICE",
                "type": "public_voice",
                "channels": [
                    {"name": "📢・public-vc", "type": "voice"},
                    {"name": "🎮・gaming-vc", "type": "voice"},
                    {"name": "👥・duo-vc", "type": "voice", "user_limit": 2},
                    {"name": "👥・trio-vc", "type": "voice", "user_limit": 3},
                    {"name": "👥・squad-vc", "type": "voice", "user_limit": 4},
                    {"name": "🟢・music-vc", "type": "voice"},
                    {"name": "🔊・panel-setup-vc", "type": "voice"},
                ],
            },
            {
                "name": "👑 OWNER AREA",
                "type": "owner_only",
                "channels": [
                    {"name": "👤・owner-vc", "type": "voice"},
                    {"name": "👑・owner-only-vc", "type": "voice"},
                    {"name": "🔒・hidden-vc", "type": "voice"},
                ],
            },
            {
                "name": "🔧 FREE RESOURCES",
                "type": "public_read_only",
                "channels": [
                    {"name": "⚙️・emulators", "type": "text", "topic": "Optimized emulators & settings"},
                    {"name": "⚙️・ff-apks", "type": "text", "topic": "Game APK packages"},
                    {"name": "⚙️・requirements", "type": "text", "topic": "System & driver requirements"},
                    {"name": "⚙️・tools", "type": "text", "topic": "Free utilities & cleaners"},
                ],
            },
            {
                "name": "💎 PAYMENT ARCHIVE",
                "type": "staff_only",
                "channels": [
                    {"name": "💎・payment-proofs", "type": "text", "topic": "Archived transaction records"},
                    {"name": "💳・payment-methods", "type": "text", "topic": "Internal payment gate configs"},
                ],
            },
            {
                "name": "🛡️ STAFF AREA",
                "type": "staff_only",
                "channels": [
                    {"name": "📜・staff-rules", "type": "text", "topic": "Staff protocol & sales ethics"},
                    {"name": "💬・staff-chats", "type": "text", "topic": "Internal staff team discussions"},
                    {"name": "📢・staff-announcements", "type": "text", "topic": "Management announcements"},
                ],
            },
            {
                "name": "🎫 TICKETS",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・open-ticket", "type": "text", "topic": "Purchase & billing support tickets", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "crypto_nft": {
        "id": "crypto_nft",
        "name": "Web3, Crypto & NFT Alpha",
        "emoji": "🪙",
        "category": "Store & Commerce",
        "group": "store",
        "description": "Bitcoin, Solana, Ethereum trading, market calls, whitelist spots & DeFi guides.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 GENESIS",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・disclaimer-rules", "type": "text", "topic": "NFA / DYOR rules and security", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "New holders arrivals", "special": "welcome"},
                    {"name": "🚨・security-alerts", "type": "text", "topic": "Scam warnings and phishing flags"},
                    {"name": "📣・announcements", "type": "text", "topic": "Alpha calls and mint updates", "special": "announcements"},
                ],
            },
            {
                "name": "📈 MARKET ALPHA",
                "type": "public",
                "channels": [
                    {"name": "💬・general-trading", "type": "text", "topic": "Macro market discussions"},
                    {"name": "📊・btc-eth-ta", "type": "text", "topic": "Technical analysis & charting"},
                    {"name": "⚡・solana-degens", "type": "text", "topic": "Solana memecoins & microcaps"},
                    {"name": "🎁・airdrop-guides", "type": "text", "topic": "Testnet farming and free drops"},
                ],
            },
            {
                "name": "💎 VIP TRADERS",
                "type": "staff_only",
                "channels": [
                    {"name": "👑・whale-room", "type": "text", "topic": "Exclusive high-volume calls"},
                    {"name": "🎯・future-signals", "type": "text", "topic": "Leverage entry & exit targets"},
                ],
            },
            {
                "name": "🔊 ALPHA VOICE",
                "type": "public_voice",
                "channels": [
                    {"name": "🎙️・Daily Market Open", "type": "voice"},
                    {"name": "☕・Degen Lounge", "type": "voice"},
                    {"name": "🟢・Music VC", "type": "voice"},
                ],
            },
            {
                "name": "🎫 OTC & TICKETS",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・otc-desk", "type": "text", "topic": "Escrow and OTC desk tickets", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "clothing_brand": {
        "id": "clothing_brand",
        "name": "Streetwear & Fashion Brand",
        "emoji": "👕",
        "category": "Store & Commerce",
        "group": "store",
        "description": "Clothing drop countdowns, fit checks, lookbooks, VIP discounts & order tracking.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 BRAND INFO",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・store-terms", "type": "text", "topic": "Shipping and return policy", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Welcome to the family", "special": "welcome"},
                    {"name": "📣・drop-alerts", "type": "text", "topic": "Seasonal collection launch dates", "special": "announcements"},
                    {"name": "📖・lookbook", "type": "text", "topic": "High-fashion lookbook images"},
                ],
            },
            {
                "name": "👗 COMMUNITY & FASHION",
                "type": "public",
                "channels": [
                    {"name": "💬・fashion-talk", "type": "text", "topic": "Streetwear and trends"},
                    {"name": "📸・fit-checks", "type": "text", "topic": "Post your outfits wearing our brand"},
                    {"name": "👟・sneakerhead", "type": "text", "topic": "Kicks and matching pieces"},
                    {"name": "💡・design-feedback", "type": "text", "topic": "Vote on future sample designs"},
                ],
            },
            {
                "name": "🎫 ORDER SUPPORT",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・order-tracking", "type": "text", "topic": "Track shipping or exchange sizes", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "service_freelance": {
        "id": "service_freelance",
        "name": "Freelancer & Agency Desk",
        "emoji": "💼",
        "category": "Store & Commerce",
        "group": "store",
        "description": "Client intake desk, design/video/dev portfolios, quote requests & invoice support.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 AGENCY OVERVIEW",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・terms-of-service", "type": "text", "topic": "Contract and payment policies", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Client onboarding", "special": "welcome"},
                    {"name": "🌟・portfolio", "type": "text", "topic": "Past client case studies and work"},
                    {"name": "⭐・client-reviews", "type": "text", "topic": "5-star testimonials"},
                ],
            },
            {
                "name": "💼 SERVICES CATALOG",
                "type": "public_read_only",
                "channels": [
                    {"name": "🎨・graphic-design", "type": "text", "topic": "Logos, banners and brand kits"},
                    {"name": "🎬・video-editing", "type": "text", "topic": "Shorts, long-form and effects"},
                    {"name": "💻・web-development", "type": "text", "topic": "React, WordPress and Shopify sites"},
                ],
            },
            {
                "name": "💬 CLIENT LOUNGE",
                "type": "public",
                "channels": [
                    {"name": "💬・client-chat", "type": "text", "topic": "General discussion"},
                    {"name": "💡・creative-ideas", "type": "text", "topic": "Inspiration and moodboards"},
                ],
            },
            {
                "name": "🎫 HIRE US & INVOICING",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・request-quote", "type": "text", "topic": "Request a project quote", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "game_reseller": {
        "id": "game_reseller",
        "name": "Gaming Keys & Accounts",
        "emoji": "💳",
        "category": "Store & Commerce",
        "group": "store",
        "description": "Game redemption codes, gaming currency, bulk keys & automated stock alerts.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 STOREFRONT",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・warranty-terms", "type": "text", "topic": "Replacement and warranty rules", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Buyer greetings", "special": "welcome"},
                    {"name": "📣・stock-updates", "type": "text", "topic": "Fresh inventory restocking", "special": "announcements"},
                    {"name": "🧾・vouchers-proofs", "type": "text", "topic": "Delivered orders proof"},
                ],
            },
            {
                "name": "🎮 PRODUCTS IN STOCK",
                "type": "public_read_only",
                "channels": [
                    {"name": "🔑・steam-game-keys", "type": "text", "topic": "Global Steam CD-keys"},
                    {"name": "🪙・in-game-credits", "type": "text", "topic": "V-Bucks, Robux, VP, UC top-up"},
                    {"name": "🕹️・playstation-xbox", "type": "text", "topic": "Console gift cards"},
                ],
            },
            {
                "name": "💬 CUSTOMER LOBBY",
                "type": "public",
                "channels": [
                    {"name": "💬・customer-chat", "type": "text", "topic": "Hangout and questions"},
                    {"name": "🎁・daily-freebies", "type": "text", "topic": "Free key giveaways"},
                ],
            },
            {
                "name": "🎫 BUY & REDEEM",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・order-ticket", "type": "text", "topic": "Purchase keys or request delivery", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "subscription_vip": {
        "id": "subscription_vip",
        "name": "VIP Subscription Club",
        "emoji": "💎",
        "category": "Store & Commerce",
        "group": "store",
        "description": "Exclusive subscriber tiers, VIP private chats, alpha research & executive audio.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 INFORMATION",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・rules", "type": "text", "topic": "Member guidelines", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "VIP onboarding", "special": "welcome"},
                    {"name": "📣・announcements", "type": "text", "topic": "Member bulletins", "special": "announcements"},
                    {"name": "💎・perks-info", "type": "text", "topic": "Tier benefits and perks breakdown"},
                ],
            },
            {
                "name": "💎 VIP LOUNGE",
                "type": "public",
                "channels": [
                    {"name": "💬・vip-general", "type": "text", "topic": "Executive lounge"},
                    {"name": "📈・insider-alpha", "type": "text", "topic": "Exclusive trends and alpha insights"},
                    {"name": "🎁・exclusive-drops", "type": "text", "topic": "Member-only perks and downloads"},
                ],
            },
            {
                "name": "🎫 VIP SUPPORT",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・vip-tickets", "type": "text", "topic": "Priority concierge support tickets", "special": "ticket_panel"},
                ],
            },
            {
                "name": "🔊 VIP AUDIO",
                "type": "public_voice",
                "channels": [
                    {"name": "🎙️・VIP Executive VC", "type": "voice"},
                    {"name": "🎧・Private Lounge", "type": "voice", "user_limit": 6},
                    {"name": "🟢・Music VC", "type": "voice"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },

    # ==================== GROUP 3: TECH, CODING & AI ====================
    "developer": {
        "id": "developer",
        "name": "Full-Stack Developer Hub",
        "emoji": "💻",
        "category": "Tech, Coding & AI",
        "group": "tech",
        "description": "Multi-stack programming community with language channels, pair programming & code help.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 INFORMATION",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・rules", "type": "text", "topic": "Community standards", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Developer onboarding", "special": "welcome"},
                    {"name": "📣・announcements", "type": "text", "topic": "Hackathons & release news", "special": "announcements"},
                    {"name": "🔗・github-updates", "type": "text", "topic": "Open-source commits & releases"},
                ],
            },
            {
                "name": "💻 CODING LOUNGE",
                "type": "public",
                "channels": [
                    {"name": "💬・general-dev", "type": "text", "topic": "General programming chat"},
                    {"name": "🐍・python", "type": "text", "topic": "Python, Django, FastAPI & discord.py"},
                    {"name": "🌐・javascript-web", "type": "text", "topic": "JS, TypeScript, React, Next.js"},
                    {"name": "⚙️・c-cpp-rust", "type": "text", "topic": "Systems programming in C, C++ & Rust"},
                    {"name": "📱・mobile-dev", "type": "text", "topic": "Flutter, React Native, Swift & Kotlin"},
                    {"name": "🗄️・database-cloud", "type": "text", "topic": "SQL, NoSQL, Docker, AWS & DevOps"},
                ],
            },
            {
                "name": "🚀 SHOWCASE & COLLAB",
                "type": "public",
                "channels": [
                    {"name": "💡・project-ideas", "type": "text", "topic": "Brainstorming new projects"},
                    {"name": "🌟・showcase", "type": "text", "topic": "Showcase your apps, sites and bots"},
                    {"name": "🤝・looking-for-devs", "type": "text", "topic": "Find team members and contributors"},
                    {"name": "🐛・code-help", "type": "text", "topic": "Ask for debugging assistance"},
                ],
            },
            {
                "name": "🎧 DEV SESSIONS",
                "type": "public_voice",
                "channels": [
                    {"name": "🔊・Pair Programming", "type": "voice", "user_limit": 3},
                    {"name": "☕・Code & Chill", "type": "voice"},
                    {"name": "🎙️・Tech Talks", "type": "voice"},
                    {"name": "🟢・Music VC", "type": "voice"},
                ],
            },
            {
                "name": "🎫 SUPPORT",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・open-ticket", "type": "text", "topic": "Contact admin or moderators", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "ai_ml_hub": {
        "id": "ai_ml_hub",
        "name": "AI, ML & Data Science",
        "emoji": "🤖",
        "category": "Tech, Coding & AI",
        "group": "tech",
        "description": "LLM fine-tuning, PyTorch, computer vision, prompt engineering & research papers.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 RESEARCH LAB",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・lab-guidelines", "type": "text", "topic": "Research ethics and rules", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "AI researcher introductions", "special": "welcome"},
                    {"name": "📣・breakthroughs", "type": "text", "topic": "New papers, models and releases", "special": "announcements"},
                ],
            },
            {
                "name": "🧠 NEURAL NETWORKS",
                "type": "public",
                "channels": [
                    {"name": "💬・ai-discussions", "type": "text", "topic": "General machine learning chatter"},
                    {"name": "🔥・pytorch-tensorflow", "type": "text", "topic": "Model architectures and training"},
                    {"name": "🤖・llm-and-agents", "type": "text", "topic": "Llama, GPT, Gemini, RAG pipelines"},
                    {"name": "👁️・computer-vision", "type": "text", "topic": "YOLO, diffusion models and OpenCV"},
                    {"name": "✍️・prompt-craft", "type": "text", "topic": "System prompts and context optimization"},
                ],
            },
            {
                "name": "🎧 RESEARCH SESSIONS",
                "type": "public_voice",
                "channels": [
                    {"name": "🎙️・Paper Reading Group", "type": "voice"},
                    {"name": "☕・GPU Training Chill", "type": "voice"},
                ],
            },
            {
                "name": "🎫 COMPUTE & TICKETS",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・cluster-access", "type": "text", "topic": "Request compute cluster credentials", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "cyber_security": {
        "id": "cyber_security",
        "name": "Cybersecurity & CTF Hub",
        "emoji": "🔐",
        "category": "Tech, Coding & AI",
        "group": "tech",
        "description": "Ethical hacking, CTF challenges, red team / blue team ops, malware analysis.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 PROTOCOL",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・ethical-rules", "type": "text", "topic": "Strict white-hat ethics disclaimer", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "SecOps introductions", "special": "welcome"},
                    {"name": "🚨・cve-disclosures", "type": "text", "topic": "Zero-day alerts and advisories", "special": "announcements"},
                ],
            },
            {
                "name": "🛡️ RED & BLUE TEAM",
                "type": "public",
                "channels": [
                    {"name": "🚩・ctf-writeups", "type": "text", "topic": "HackTheBox, TryHackMe, CTF guides"},
                    {"name": "⚔️・penetration-testing", "type": "text", "topic": "Web app and network exploits"},
                    {"name": "🛡️・blue-defense-soc", "type": "text", "topic": "SIEM, threat hunting and forensics"},
                    {"name": "🦠・reverse-engineering", "type": "text", "topic": "Ghidra, IDA Pro and binary analysis"},
                ],
            },
            {
                "name": "🎧 WAR ROOMS",
                "type": "public_voice",
                "channels": [
                    {"name": "🔒・Live CTF VC 1", "type": "voice"},
                    {"name": "🔒・Live CTF VC 2", "type": "voice"},
                    {"name": "☕・Sec Chill", "type": "voice"},
                ],
            },
            {
                "name": "🎫 PRIVATE BOUNTY DESK",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・private-ticket", "type": "text", "topic": "Confidential security inquiries", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "ui_ux_design": {
        "id": "ui_ux_design",
        "name": "UI/UX Design Studio",
        "emoji": "🎨",
        "category": "Tech, Coding & AI",
        "group": "tech",
        "description": "Figma design systems, mobile app wireframes, web UI critiques & motion design.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 STUDIO OVERVIEW",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・design-rules", "type": "text", "topic": "Constructive critique guidelines", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Designer welcomes", "special": "welcome"},
                    {"name": "📣・design-trends", "type": "text", "topic": "Modern UI inspiration & articles", "special": "announcements"},
                ],
            },
            {
                "name": "🎨 WORKBENCH",
                "type": "public",
                "channels": [
                    {"name": "💬・designer-lounge", "type": "text", "topic": "General design chatter"},
                    {"name": "💡・figma-tips", "type": "text", "topic": "Auto-layout, tokens, components"},
                    {"name": "🌟・portfolio-critique", "type": "text", "topic": "Share screens for peer feedback"},
                    {"name": "✨・motion-and-3d", "type": "text", "topic": "Lottie, Spline and After Effects"},
                ],
            },
            {
                "name": "🎧 DESIGN SPRINT",
                "type": "public_voice",
                "channels": [
                    {"name": "🎨・Figma Co-Working", "type": "voice"},
                    {"name": "🟢・Design Lofi VC", "type": "voice"},
                ],
            },
            {
                "name": "🎫 CLIENT COMMISSIONS",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・hire-designer", "type": "text", "topic": "Request design services", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "bot_developer": {
        "id": "bot_developer",
        "name": "Discord Bot Development",
        "emoji": "⚡",
        "category": "Tech, Coding & AI",
        "group": "tech",
        "description": "discord.py, discord.js, slash command tree, embeds, buttons & bot hosting.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 BOT CENTRAL",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・developer-rules", "type": "text", "topic": "Discord API compliance", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Bot engineer welcomes", "special": "welcome"},
                    {"name": "📣・api-updates", "type": "text", "topic": "Discord API changes & deprecations", "special": "announcements"},
                ],
            },
            {
                "name": "💻 FRAMEWORKS & CODE",
                "type": "public",
                "channels": [
                    {"name": "🐍・discord-py", "type": "text", "topic": "Python 3.12+ and discord.py 2.x"},
                    {"name": "📜・discord-js", "type": "text", "topic": "Node.js and discord.js v14"},
                    {"name": "🎛️・buttons-and-modals", "type": "text", "topic": "Interactive components and views"},
                    {"name": "☁️・vps-and-hosting", "type": "text", "topic": "Linux, systemd, PM2, Docker"},
                ],
            },
            {
                "name": "🎧 PAIR CODING",
                "type": "public_voice",
                "channels": [
                    {"name": "🔊・Bot Lab VC", "type": "voice"},
                    {"name": "🟢・Music VC", "type": "voice"},
                ],
            },
            {
                "name": "🎫 BOT COMMISSIONS",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・order-bot", "type": "text", "topic": "Commission a custom Discord bot", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "game_dev": {
        "id": "game_dev",
        "name": "Game Dev (Unity / Unreal)",
        "emoji": "🕹️",
        "category": "Tech, Coding & AI",
        "group": "tech",
        "description": "Indie game studios, C# Unity scripting, Unreal Engine 5 Blueprints & Game Jams.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 ENGINE ROOM",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・rules", "type": "text", "topic": "Indie dev guidelines", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Game dev welcomes", "special": "welcome"},
                    {"name": "📣・game-jams", "type": "text", "topic": "Upcoming itch.io & Ludum Dare jams", "special": "announcements"},
                ],
            },
            {
                "name": "🎮 ENGINES & ASSETS",
                "type": "public",
                "channels": [
                    {"name": "🔷・unity-engine", "type": "text", "topic": "Unity C# scripting and physics"},
                    {"name": "🔶・unreal-engine", "type": "text", "topic": "UE5 Lumen, Nanite, C++ & Blueprints"},
                    {"name": "👾・pixel-art-and-vfx", "type": "text", "topic": "Spine, Aseprite, shaders"},
                    {"name": "🎵・game-audio-sfx", "type": "text", "topic": "FMOD, Wwise and chiptunes"},
                ],
            },
            {
                "name": "🎧 DEV SPRINTS",
                "type": "public_voice",
                "channels": [
                    {"name": "🕹️・Game Jam VC", "type": "voice"},
                    {"name": "☕・Dev Chill", "type": "voice"},
                ],
            },
            {
                "name": "🎫 PUBLISHING TICKETS",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・publisher-ticket", "type": "text", "topic": "Pitch to publishers and investors", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },

    # ==================== GROUP 4: CONTENT CREATORS & STREAMING ====================
    "creator": {
        "id": "creator",
        "name": "Creator Community",
        "emoji": "🎥",
        "category": "Content Creators & Media",
        "group": "creators",
        "description": "YouTuber/Streamer hub with live alerts, fan art, subscriber tiers & on-stream voice.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 WELCOME & UPDATES",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・rules", "type": "text", "topic": "Community guidelines", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Fan greetings", "special": "welcome"},
                    {"name": "📣・announcements", "type": "text", "topic": "Channel news and events", "special": "announcements"},
                    {"name": "🎥・new-videos", "type": "text", "topic": "Latest uploads and shorts"},
                    {"name": "🔴・stream-alerts", "type": "text", "topic": "Live stream notifications"},
                ],
            },
            {
                "name": "💬 FAN LOUNGE",
                "type": "public",
                "channels": [
                    {"name": "💬・fan-chat", "type": "text", "topic": "Main fan discussion lounge"},
                    {"name": "🎨・fan-art", "type": "text", "topic": "Drawings, edits and thumbnails"},
                    {"name": "💡・video-ideas", "type": "text", "topic": "Suggest topics for next videos"},
                    {"name": "📷・memes", "type": "text", "topic": "Community memes"},
                ],
            },
            {
                "name": "💎 EXCLUSIVE TIERS",
                "type": "staff_only",
                "channels": [
                    {"name": "💎・vip-chat", "type": "text", "topic": "Exclusive chat for subscribers"},
                    {"name": "🎁・exclusive-leaks", "type": "text", "topic": "Sneak peeks and unlisted videos"},
                ],
            },
            {
                "name": "🎙️ COMMUNITY VOICE",
                "type": "public_voice",
                "channels": [
                    {"name": "🎙️・Community Hangout", "type": "voice"},
                    {"name": "🔴・On-Stream Guests", "type": "voice", "user_limit": 4},
                    {"name": "🟢・Music VC", "type": "voice"},
                ],
            },
            {
                "name": "🎫 BUSINESS & SPONSORS",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・contact-creator", "type": "text", "topic": "Sponsorships and business tickets", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "twitch_streamer": {
        "id": "twitch_streamer",
        "name": "Twitch Streamer Lounge",
        "emoji": "🟣",
        "category": "Content Creators & Media",
        "group": "creators",
        "description": "Twitch Affiliate/Partner community with emote submissions, raids & sub badges.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 STREAM CENTRAL",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・rules", "type": "text", "topic": "Stream etiquette", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "New chatters", "special": "welcome"},
                    {"name": "🟣・went-live", "type": "text", "topic": "Automatic Twitch live notifications", "special": "announcements"},
                    {"name": "📅・weekly-schedule", "type": "text", "topic": "Streaming timetable"},
                ],
            },
            {
                "name": "💬 CHATTERS LOUNGE",
                "type": "public",
                "channels": [
                    {"name": "💬・general-chat", "type": "text", "topic": "Off-stream conversation"},
                    {"name": "🤣・stream-clips", "type": "text", "topic": "Funny and epic stream clips"},
                    {"name": "✨・emote-suggestions", "type": "text", "topic": "Suggest new sub emotes"},
                ],
            },
            {
                "name": "🎙️ STREAM VOICE",
                "type": "public_voice",
                "channels": [
                    {"name": "🎙️・Stream Squad", "type": "voice", "user_limit": 5},
                    {"name": "☕・Viewer Hangout", "type": "voice"},
                ],
            },
            {
                "name": "🎫 MODERATOR TICKETS",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・unban-request", "type": "text", "topic": "Twitch chat unban appeals", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "podcast_network": {
        "id": "podcast_network",
        "name": "Podcast Network & Shows",
        "emoji": "🎙️",
        "category": "Content Creators & Media",
        "group": "creators",
        "description": "Episode drops, Spotify/Apple feeds, guest speaker green rooms & Q&A sessions.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 BROADCAST INFO",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・rules", "type": "text", "topic": "Respectful dialogue policy", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Listener greetings", "special": "welcome"},
                    {"name": "🎧・new-episodes", "type": "text", "topic": "Links to Spotify and Apple Podcasts", "special": "announcements"},
                ],
            },
            {
                "name": "💬 EPISODE DISCUSSIONS",
                "type": "public",
                "channels": [
                    {"name": "💬・general-talk", "type": "text", "topic": "Listener discussion"},
                    {"name": "💡・topic-suggestions", "type": "text", "topic": "Vote on future episode topics"},
                    {"name": "❓・listener-q-and-a", "type": "text", "topic": "Ask questions for upcoming episodes"},
                ],
            },
            {
                "name": "🎙️ LIVE RECORDING ROOMS",
                "type": "public_voice",
                "channels": [
                    {"name": "🎙️・Live Recording Stage", "type": "voice"},
                    {"name": "🔒・Guest Green Room", "type": "voice"},
                    {"name": "☕・Post-Show Lounge", "type": "voice"},
                ],
            },
            {
                "name": "🎫 GUEST BOOKING",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・be-a-guest", "type": "text", "topic": "Apply to be interviewed on show", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "vlogger_lifestyle": {
        "id": "vlogger_lifestyle",
        "name": "Daily Vlogging & Lifestyle",
        "emoji": "📷",
        "category": "Content Creators & Media",
        "group": "creators",
        "description": "Travel logs, behind-the-scenes photography, gear setups & community meetups.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 THE JOURNEY",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・rules", "type": "text", "topic": "Community guidelines", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Welcome friends", "special": "welcome"},
                    {"name": "📣・vlog-drops", "type": "text", "topic": "New Sunday vlog notifications", "special": "announcements"},
                ],
            },
            {
                "name": "🌍 LIFESTYLE & ADVENTURE",
                "type": "public",
                "channels": [
                    {"name": "💬・daily-chatter", "type": "text", "topic": "How was your day?"},
                    {"name": "✈️・travel-diaries", "type": "text", "topic": "Photos from across the world"},
                    {"name": "📷・gear-and-cameras", "type": "text", "topic": "Sony, Canon, drones and lenses"},
                ],
            },
            {
                "name": "🎧 CHILLOUT",
                "type": "public_voice",
                "channels": [
                    {"name": "☕・Coffee Hangout", "type": "voice"},
                    {"name": "🟢・Music VC", "type": "voice"},
                ],
            },
            {
                "name": "🎫 COLLAB TICKETS",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・brand-partnerships", "type": "text", "topic": "Brand inquiries", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "tiktok_reels": {
        "id": "tiktok_reels",
        "name": "Short-Form Creators",
        "emoji": "🎬",
        "category": "Content Creators & Media",
        "group": "creators",
        "description": "TikTok, Instagram Reels & YouTube Shorts creators, trending audios & hooks.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 CREATOR CENTRAL",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・rules", "type": "text", "topic": "Creator terms", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "New creators", "special": "welcome"},
                    {"name": "📣・algorithm-news", "type": "text", "topic": "Updates on algorithm changes", "special": "announcements"},
                ],
            },
            {
                "name": "⚡ VIRAL STRATEGIES",
                "type": "public",
                "channels": [
                    {"name": "💬・creator-talk", "type": "text", "topic": "Daily short-form discussions"},
                    {"name": "🎵・trending-sounds", "type": "text", "topic": "High-growth audio tracks"},
                    {"name": "🎣・viral-hooks", "type": "text", "topic": "First 3-second retention hooks"},
                    {"name": "📊・analytics-review", "type": "text", "topic": "Retention graphs and watch time"},
                ],
            },
            {
                "name": "🎧 BRAINSTORM VOICE",
                "type": "public_voice",
                "channels": [
                    {"name": "🎙️・Brainstorm VC", "type": "voice"},
                    {"name": "☕・Late Night Editing", "type": "voice"},
                ],
            },
            {
                "name": "🎫 CONSULTATION",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・growth-audit", "type": "text", "topic": "Get your account audited", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },

    # ==================== GROUP 5: ANIME, MANGA & FANDOMS ====================
    "anime_lounge": {
        "id": "anime_lounge",
        "name": "Anime Oasis & Manga Den",
        "emoji": "⛩️",
        "category": "Anime, Manga & Fandoms",
        "group": "anime",
        "description": "Seasonal anime watch parties, manga chapters, cosplay showcase & waifu games.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "⛩️ SHRINE GATE",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・rules", "type": "text", "topic": "Spoiler policies and etiquette", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Welcome otaku friends", "special": "welcome"},
                    {"name": "📣・announcements", "type": "text", "topic": "Anime release schedules", "special": "announcements"},
                ],
            },
            {
                "name": "🌸 OTAKU CHATTER",
                "type": "public",
                "channels": [
                    {"name": "💬・anime-discussion", "type": "text", "topic": "Jujutsu Kaisen, One Piece, Demon Slayer"},
                    {"name": "📖・manga-and-manhwa", "type": "text", "topic": "Latest chapter scans and webtoons"},
                    {"name": "⚠️・spoiler-zone", "type": "text", "topic": "Unrestricted spoiler talk"},
                    {"name": "🎨・anime-art", "type": "text", "topic": "Drawings and wallpaper art"},
                    {"name": "🤖・mudae-and-games", "type": "text", "topic": "Waifu claiming and card bots"},
                ],
            },
            {
                "name": "🎧 SAKURA LOUNGES",
                "type": "public_voice",
                "channels": [
                    {"name": "🌸・Sakura Lounge", "type": "voice"},
                    {"name": "🎬・Anime Stream VC", "type": "voice"},
                    {"name": "🟢・Anime OSTs VC", "type": "voice"},
                ],
            },
            {
                "name": "🎫 MODERATOR DESK",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・open-ticket", "type": "text", "topic": "Contact shrine maiden staff", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "genshin_honkai": {
        "id": "genshin_honkai",
        "name": "Genshin & Gacha Haven",
        "emoji": "🌸",
        "category": "Anime, Manga & Fandoms",
        "group": "anime",
        "description": "Genshin Impact, Honkai Star Rail & Zenless Zone Zero builds, lore & co-op help.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 ASTRAL EXPRESS",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・rules", "type": "text", "topic": "Co-op and trading safety", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Travelers and Trailblazers", "special": "welcome"},
                    {"name": "📣・banner-news", "type": "text", "topic": "Upcoming version previews and codes", "special": "announcements"},
                ],
            },
            {
                "name": "💫 GACHA LIFE",
                "type": "public",
                "channels": [
                    {"name": "💬・teyvat-lounge", "type": "text", "topic": "General game discussions"},
                    {"name": "✨・gacha-flex-and-salt", "type": "text", "topic": "Early 5-stars and lost 50/50s"},
                    {"name": "⚔️・character-builds", "type": "text", "topic": "Artifacts, light cones and rotations"},
                    {"name": "🤝・co-op-help", "type": "text", "topic": "Domain and boss fight assistance"},
                    {"name": "📜・lore-theories", "type": "text", "topic": "Archon quests and deep lore"},
                ],
            },
            {
                "name": "🎧 CO-OP VOICE",
                "type": "public_voice",
                "channels": [
                    {"name": "🔊・Abyss Grind VC", "type": "voice"},
                    {"name": "☕・Mondstadt Tavern", "type": "voice"},
                    {"name": "🟢・Hoyomix Music", "type": "voice"},
                ],
            },
            {
                "name": "🎫 CO-OP TICKETS",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・carry-ticket", "type": "text", "topic": "Ask veteran players for boss help", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "cosplay_hub": {
        "id": "cosplay_hub",
        "name": "Cosplay Creators Guild",
        "emoji": "🎭",
        "category": "Anime, Manga & Fandoms",
        "group": "anime",
        "description": "Costume crafting, EVA foam armor, wig styling, makeup masterclasses & con meetups.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 GUILD ENTRANCE",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・rules", "type": "text", "topic": "Cosplay consent and anti-harassment", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Welcome cosplayers", "special": "welcome"},
                    {"name": "📣・convention-calendar", "type": "text", "topic": "Anime Expo, Comic-Con dates", "special": "announcements"},
                ],
            },
            {
                "name": "🪡 WORKSHOP",
                "type": "public",
                "channels": [
                    {"name": "💬・cosplay-general", "type": "text", "topic": "Costume discussion"},
                    {"name": "🛡️・armor-and-props", "type": "text", "topic": "EVA foam, 3D printing and painting"},
                    {"name": "💇・wigs-and-makeup", "type": "text", "topic": "Styling, crimping and SFX makeup"},
                    {"name": "📸・finished-cosplays", "type": "text", "topic": "Professional photoshoot photos"},
                ],
            },
            {
                "name": "🎧 SEWING CIRCLE",
                "type": "public_voice",
                "channels": [
                    {"name": "🪡・Late Night Crafting", "type": "voice"},
                    {"name": "☕・Convention Hype VC", "type": "voice"},
                ],
            },
            {
                "name": "🎫 COMMISSION TICKETS",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・prop-commission", "type": "text", "topic": "Order custom props and wigs", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "lofi_cafe": {
        "id": "lofi_cafe",
        "name": "Midnight Lofi Cafe",
        "emoji": "☕",
        "category": "Anime, Manga & Fandoms",
        "group": "anime",
        "description": "Chill aesthetic hangout, 24/7 lofi hip-hop radio, warm tea talks & midnight journaling.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 CAFE DOORS",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・cafe-rules", "type": "text", "topic": "Warm and kind vibes only", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Find a seat", "special": "welcome"},
                    {"name": "📣・specials", "type": "text", "topic": "Daily menu and playlist updates", "special": "announcements"},
                ],
            },
            {
                "name": "☕ WARM TALKS",
                "type": "public",
                "channels": [
                    {"name": "💬・cafe-lounge", "type": "text", "topic": "Gentle daily conversations"},
                    {"name": "🌧️・rainy-thoughts", "type": "text", "topic": "Cozy introspective musings"},
                    {"name": "📸・coffee-and-sweets", "type": "text", "topic": "Share your tea and snacks"},
                    {"name": "📝・poems-and-quotes", "type": "text", "topic": "Inspiring literature and thoughts"},
                ],
            },
            {
                "name": "🎧 LOFI RADIOS",
                "type": "public_voice",
                "channels": [
                    {"name": "🟢・24/7 Lofi Beats", "type": "voice"},
                    {"name": "🌧️・Rain & Coffee VC", "type": "voice"},
                    {"name": "☕・Whisper Lounge", "type": "voice"},
                ],
            },
            {
                "name": "🎫 BARISTA HELP",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・talk-to-barista", "type": "text", "topic": "Private staff assistance", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "pokemon_club": {
        "id": "pokemon_club",
        "name": "Pokemon League & Trading",
        "emoji": "⚡",
        "category": "Anime, Manga & Fandoms",
        "group": "anime",
        "description": "Competitive VGC battles, TCG card collecting, Pokemon GO raids & shiny hunting.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 POKEMON CENTER",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・gym-rules", "type": "text", "topic": "Battle rules & trading ethics", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "New trainers arriving", "special": "welcome"},
                    {"name": "📣・league-news", "type": "text", "topic": "Gym leader tournament schedules", "special": "announcements"},
                ],
            },
            {
                "name": "⚡ TRAINER BATTLES",
                "type": "public",
                "channels": [
                    {"name": "💬・trainer-chat", "type": "text", "topic": "Pokemon discussions"},
                    {"name": "⚔️・vgc-showdown", "type": "text", "topic": "Smogon & Scarlet/Violet competitive"},
                    {"name": "✨・shiny-brags", "type": "text", "topic": "Post your shiny encounters"},
                    {"name": "🃏・tcg-pulls-and-trade", "type": "text", "topic": "Card collections, booster packs"},
                    {"name": "🌐・pokemon-go-raids", "type": "text", "topic": "Remote raid coordinates"},
                ],
            },
            {
                "name": "🎧 GYM ARENAS",
                "type": "public_voice",
                "channels": [
                    {"name": "⚡・Battle Arena 1", "type": "voice"},
                    {"name": "🔥・Battle Arena 2", "type": "voice"},
                    {"name": "☕・Trainer Lounge", "type": "voice"},
                ],
            },
            {
                "name": "🎫 GYM BADGE TICKETS",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・challenge-gym", "type": "text", "topic": "Challenge verified gym leaders", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },

    # ==================== GROUP 6: SOCIAL, HANGOUT & LIFESTYLE ====================
    "social": {
        "id": "social",
        "name": "Ultimate Social Hangout",
        "emoji": "💬",
        "category": "Social, Hangout & Lifestyle",
        "group": "social",
        "description": "Friendly social hub with active chit-chat, photo sharing, pets, trivia & chill voice.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 WELCOME",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・rules", "type": "text", "topic": "Community guidelines", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Welcome new friends", "special": "welcome"},
                    {"name": "📣・announcements", "type": "text", "topic": "Server updates and events", "special": "announcements"},
                    {"name": "📌・roles-assignment", "type": "text", "topic": "Pick your hobby and notification roles"},
                ],
            },
            {
                "name": "💬 GENERAL",
                "type": "public",
                "channels": [
                    {"name": "💬・chit-chat", "type": "text", "topic": "Day-to-day conversation"},
                    {"name": "📷・media-photos", "type": "text", "topic": "Share your photography and moments"},
                    {"name": "🍕・food-and-pets", "type": "text", "topic": "Delicious meals and cute animals"},
                    {"name": "🎨・art-and-creativity", "type": "text", "topic": "Share your artwork and hobbies"},
                    {"name": "💭・deep-thoughts", "type": "text", "topic": "Late night discussions and musings"},
                ],
            },
            {
                "name": "🤖 ENTERTAINMENT",
                "type": "public",
                "channels": [
                    {"name": "🎮・gaming", "type": "text", "topic": "Video games and casual co-op"},
                    {"name": "🤖・bot-commands", "type": "text", "topic": "Commands and bot mini-games"},
                    {"name": "🎲・trivia-quiz", "type": "text", "topic": "Daily trivia and quizzes"},
                    {"name": "🎵・music-room", "type": "text", "topic": "Song suggestions and lyrics"},
                ],
            },
            {
                "name": "🎧 SOCIAL HANGOUT",
                "type": "public_voice",
                "channels": [
                    {"name": "☕・Coffee Chat", "type": "voice"},
                    {"name": "🎧・Chill VC 1", "type": "voice"},
                    {"name": "🎧・Chill VC 2", "type": "voice"},
                    {"name": "🎬・Watch Party", "type": "voice"},
                    {"name": "🟢・Music VC", "type": "voice"},
                ],
            },
            {
                "name": "🎫 HELP & FEEDBACK",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・help-ticket", "type": "text", "topic": "Contact moderators", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "study_cafe": {
        "id": "study_cafe",
        "name": "24/7 Virtual Study Cafe",
        "emoji": "📚",
        "category": "Social, Hangout & Lifestyle",
        "group": "social",
        "description": "Silent cam/screenshare study rooms, Pomodoro timers, study streaks & todo goals.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 RECEPTION",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・library-rules", "type": "text", "topic": "Silent study code of conduct", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "New studiers", "special": "welcome"},
                    {"name": "📣・daily-goals", "type": "text", "topic": "Community motivation", "special": "announcements"},
                ],
            },
            {
                "name": "📝 PRODUCTIVITY",
                "type": "public",
                "channels": [
                    {"name": "📋・daily-todos", "type": "text", "topic": "Write your daily checklist"},
                    {"name": "🔥・study-streaks", "type": "text", "topic": "Log your daily study hours"},
                    {"name": "🍅・pomodoro-chat", "type": "text", "topic": "Break time chat"},
                ],
            },
            {
                "name": "🎧 STUDY ROOMS",
                "type": "public_voice",
                "channels": [
                    {"name": "🤫・Strictly Silent VC 1", "type": "voice"},
                    {"name": "🤫・Strictly Silent VC 2", "type": "voice"},
                    {"name": "📹・Cam / Screenshare Only", "type": "voice"},
                    {"name": "🟢・Lofi Study Radio", "type": "voice"},
                ],
            },
            {
                "name": "🎫 REPORT AN ISSUE",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・report-disruption", "type": "text", "topic": "Report noise in silent rooms", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "fitness_gym": {
        "id": "fitness_gym",
        "name": "Fitness, Calisthenics & Gym",
        "emoji": "🏋️",
        "category": "Social, Hangout & Lifestyle",
        "group": "social",
        "description": "Workout splits, form checks, high-protein recipes, PR celebrations & daily motivation.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 GYM LOBBY",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・gym-rules", "type": "text", "topic": "Supportive and positive gym culture", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Athlete welcomes", "special": "welcome"},
                    {"name": "📣・monthly-challenges", "type": "text", "topic": "Push-up & step count challenges", "special": "announcements"},
                ],
            },
            {
                "name": "💪 THE IRON DEN",
                "type": "public",
                "channels": [
                    {"name": "💬・gym-talk", "type": "text", "topic": "General fitness discussion"},
                    {"name": "🏋️・pr-celebration", "type": "text", "topic": "Share your new Bench, Squat, Deadlift PRs"},
                    {"name": "🎥・form-checks", "type": "text", "topic": "Post videos for technique feedback"},
                    {"name": "🥗・meal-prep-and-diet", "type": "text", "topic": "High-protein recipes & macros"},
                    {"name": "🤸・calisthenics-skills", "type": "text", "topic": "Muscle-ups, handstands, planches"},
                ],
            },
            {
                "name": "🎧 GYM AUDIO",
                "type": "public_voice",
                "channels": [
                    {"name": "🔥・Workout Hype VC", "type": "voice"},
                    {"name": "🟢・Hardstyle Gym Beats", "type": "voice"},
                ],
            },
            {
                "name": "🎫 COACHING TICKETS",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・custom-routine", "type": "text", "topic": "Request a tailored workout split", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "book_club": {
        "id": "book_club",
        "name": "Bookworms & Writers Guild",
        "emoji": "📖",
        "category": "Social, Hangout & Lifestyle",
        "group": "social",
        "description": "Monthly book club, genre discussions, creative writing workshops & poetry nights.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 LIBRARY ENTRANCE",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・rules", "type": "text", "topic": "Book club guidelines", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "New readers arriving", "special": "welcome"},
                    {"name": "📖・book-of-the-month", "type": "text", "topic": "Current community read selection", "special": "announcements"},
                ],
            },
            {
                "name": "📚 BOOKSHELF",
                "type": "public",
                "channels": [
                    {"name": "💬・book-discussion", "type": "text", "topic": "Active chapter discussions"},
                    {"name": "🌟・reviews-and-ratings", "type": "text", "topic": "Goodreads reviews and 5-star picks"},
                    {"name": "✍️・creative-writing", "type": "text", "topic": "Share original stories and chapters"},
                    {"name": "📜・poetry-corner", "type": "text", "topic": "Original poems and stanzas"},
                ],
            },
            {
                "name": "🎧 READING ROOMS",
                "type": "public_voice",
                "channels": [
                    {"name": "📖・Silent Reading VC", "type": "voice"},
                    {"name": "🎙️・Live Poetry Slam", "type": "voice"},
                ],
            },
            {
                "name": "🎫 WORKSHOP TICKETS",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・manuscript-feedback", "type": "text", "topic": "Private beta reader tickets", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "cinema_club": {
        "id": "cinema_club",
        "name": "Movie Buffs & Cinema Lounge",
        "emoji": "🍿",
        "category": "Social, Hangout & Lifestyle",
        "group": "social",
        "description": "Film discussions, Letterboxd reviews, trailer drops & scheduled watch parties.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 MARQUEE",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・rules", "type": "text", "topic": "Cinema etiquette & spoilers", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Welcome movie lovers", "special": "welcome"},
                    {"name": "🎬・showtimes", "type": "text", "topic": "Friday watch party schedules", "special": "announcements"},
                ],
            },
            {
                "name": "🍿 THE AUDITORIUM",
                "type": "public",
                "channels": [
                    {"name": "💬・movie-chat", "type": "text", "topic": "General film and TV series talk"},
                    {"name": "⭐・letterboxd-ratings", "type": "text", "topic": "Post your movie ratings and reviews"},
                    {"name": "🎥・new-trailers", "type": "text", "topic": "Latest Hollywood & international trailers"},
                    {"name": "📺・binge-worthy-series", "type": "text", "topic": "Netflix, HBO, Disney+ discussions"},
                ],
            },
            {
                "name": "🎧 SCREENING ROOMS",
                "type": "public_voice",
                "channels": [
                    {"name": "🎬・Watch Party Cinema 1", "type": "voice"},
                    {"name": "🎬・Watch Party Cinema 2", "type": "voice"},
                    {"name": "☕・Post-Credits Discussion", "type": "voice"},
                ],
            },
            {
                "name": "🎫 FILMMAKER DESK",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・host-screening", "type": "text", "topic": "Request to host an indie film screening", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },

    # ==================== GROUP 7: MUSIC & AUDIO PRODUCTION ====================
    "music": {
        "id": "music",
        "name": "Music Production & Beats",
        "emoji": "🎵",
        "category": "Music & Audio Production",
        "group": "music",
        "description": "Musicians and listeners hub with production DAWs, track showcases & jam session VCs.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 HARMONY",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・rules", "type": "text", "topic": "Music community conduct", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Artist greetings", "special": "welcome"},
                    {"name": "📣・announcements", "type": "text", "topic": "Album releases & live events", "special": "announcements"},
                    {"name": "🎵・featured-tracks", "type": "text", "topic": "Staff curated music picks"},
                ],
            },
            {
                "name": "🎶 DISCUSSIONS",
                "type": "public",
                "channels": [
                    {"name": "💬・music-talk", "type": "text", "topic": "Favorite bands, genres and albums"},
                    {"name": "🎸・instruments-gear", "type": "text", "topic": "Guitars, synths, mics and hardware"},
                    {"name": "🎚️・production-daw", "type": "text", "topic": "FL Studio, Ableton, Logic & mixing"},
                    {"name": "✍️・songwriting-lyrics", "type": "text", "topic": "Rhymes, poetry and compositions"},
                ],
            },
            {
                "name": "🌟 SHARE YOUR MUSIC",
                "type": "public",
                "channels": [
                    {"name": "🎵・my-tracks", "type": "text", "topic": "Post your original songs and beats"},
                    {"name": "💡・feedback-critique", "type": "text", "topic": "Constructive audio feedback"},
                    {"name": "🤝・collabs", "type": "text", "topic": "Find vocalists, producers and beatmakers"},
                ],
            },
            {
                "name": "🎧 LISTENING LOUNGES",
                "type": "public_voice",
                "channels": [
                    {"name": "🟢・Lofi 24/7", "type": "voice"},
                    {"name": "🎧・Listening Party", "type": "voice"},
                    {"name": "🎙️・Jam Session VC", "type": "voice"},
                    {"name": "📻・Radio Stream", "type": "voice"},
                ],
            },
            {
                "name": "🎫 SUPPORT",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・open-ticket", "type": "text", "topic": "Contact staff", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "dj_electronic": {
        "id": "dj_electronic",
        "name": "EDM, DJ & Electronic Sound",
        "emoji": "🎛️",
        "category": "Music & Audio Production",
        "group": "music",
        "description": "House, Techno, Dubstep, Trance, DJ mixsets, festival schedules & live DJ sets.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 MAIN STAGE",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・rules", "type": "text", "topic": "Stage rules", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Raver arrivals", "special": "welcome"},
                    {"name": "📣・festival-lineups", "type": "text", "topic": "Tomorrowland, Ultra, EDC schedules", "special": "announcements"},
                ],
            },
            {
                "name": "🎛️ THE DECKS",
                "type": "public",
                "channels": [
                    {"name": "💬・edm-lounge", "type": "text", "topic": "Electronic dance music chatter"},
                    {"name": "🎧・live-dj-sets", "type": "text", "topic": "SoundCloud and YouTube mix links"},
                    {"name": "🎹・synth-sound-design", "type": "text", "topic": "Serum, Vital, Massive presets"},
                    {"name": "🔥・unreleased-ids", "type": "text", "topic": "ID track IDs and festival rips"},
                ],
            },
            {
                "name": "🔊 LIVE STAGE VOICES",
                "type": "public_voice",
                "channels": [
                    {"name": "🎛️・Live DJ Deck (Stage)", "type": "voice"},
                    {"name": "⚡・Rave VC", "type": "voice"},
                ],
            },
            {
                "name": "🎫 BOOKINGS",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・book-dj", "type": "text", "topic": "Book a guest DJ set", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "acoustic_indie": {
        "id": "acoustic_indie",
        "name": "Acoustic, Rock & Indie",
        "emoji": "🎸",
        "category": "Music & Audio Production",
        "group": "music",
        "description": "Singer-songwriters, guitar tabs, vocal training, vinyl collections & indie bands.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 COFFEEHOUSE",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・rules", "type": "text", "topic": "Respectful music sharing", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Welcome musicians", "special": "welcome"},
                    {"name": "📣・open-mic-nights", "type": "text", "topic": "Upcoming live acoustic nights", "special": "announcements"},
                ],
            },
            {
                "name": "🎸 STRINGS & CHORDS",
                "type": "public",
                "channels": [
                    {"name": "💬・indie-talk", "type": "text", "topic": "Indie rock, folk and alternative"},
                    {"name": "🎼・chords-and-tabs", "type": "text", "topic": "Guitar and piano sheet music"},
                    {"name": "🎤・vocal-tips", "type": "text", "topic": "Warmups, breath support and range"},
                    {"name": "💿・vinyl-records", "type": "text", "topic": "Show off your turntable and vinyls"},
                ],
            },
            {
                "name": "🎧 LIVE ACOUSTIC",
                "type": "public_voice",
                "channels": [
                    {"name": "🎙️・Open Mic Acoustic Stage", "type": "voice"},
                    {"name": "☕・Campfire Jam VC", "type": "voice"},
                ],
            },
            {
                "name": "🎫 BAND FORMATION",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・join-band", "type": "text", "topic": "Audition for community band", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "voice_acting": {
        "id": "voice_acting",
        "name": "Voice Acting Guild",
        "emoji": "🎭",
        "category": "Music & Audio Production",
        "group": "music",
        "description": "VA casting calls, demo reels, character impressions, mic setups & audio dramas.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 THE BOOTH",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・rules", "type": "text", "topic": "Professional conduct and NDAs", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "New voice talent", "special": "welcome"},
                    {"name": "📢・casting-calls", "type": "text", "topic": "Paid and indie voice acting auditions", "special": "announcements"},
                ],
            },
            {
                "name": "🎙️ AUDIO LAB",
                "type": "public",
                "channels": [
                    {"name": "💬・va-lounge", "type": "text", "topic": "Industry talk and agencies"},
                    {"name": "🌟・demo-reels", "type": "text", "topic": "Post your commercial & character reels"},
                    {"name": "🎙️・mic-and-acoustics", "type": "text", "topic": "XLR mics, preamps and soundproofing"},
                    {"name": "🎭・impressions", "type": "text", "topic": "Anime, movie and video game impressions"},
                ],
            },
            {
                "name": "🎧 RECORDING BOOTHS",
                "type": "public_voice",
                "channels": [
                    {"name": "🎙️・Live Audition Booth 1", "type": "voice"},
                    {"name": "🎙️・Live Audition Booth 2", "type": "voice"},
                    {"name": "☕・Green Room", "type": "voice"},
                ],
            },
            {
                "name": "🎫 CASTING TICKETS",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・private-audition", "type": "text", "topic": "Submit NDA demo directly to directors", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },

    # ==================== GROUP 8: EDUCATION, CAMPUS & STOCKS ====================
    "education": {
        "id": "education",
        "name": "University & STEM Campus",
        "emoji": "📚",
        "category": "Education, Campus & Stocks",
        "group": "education",
        "description": "Academic study halls, subject text channels, homework assistance & silent focus VCs.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 CAMPUS INFO",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・rules", "type": "text", "topic": "Academic code of conduct", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Student introductions", "special": "welcome"},
                    {"name": "📣・announcements", "type": "text", "topic": "Exam schedules and study events", "special": "announcements"},
                    {"name": "📚・syllabus-resources", "type": "text", "topic": "Free textbooks and study guides"},
                ],
            },
            {
                "name": "📖 STUDY HALLS",
                "type": "public",
                "channels": [
                    {"name": "💬・general-study", "type": "text", "topic": "All-around student discussions"},
                    {"name": "📐・mathematics", "type": "text", "topic": "Algebra, calculus, statistics and proofs"},
                    {"name": "🔬・natural-sciences", "type": "text", "topic": "Physics, chemistry and biology"},
                    {"name": "💻・cs-and-it", "type": "text", "topic": "Algorithms, data structures and code"},
                    {"name": "📝・literature-humanities", "type": "text", "topic": "Essays, history and philosophy"},
                ],
            },
            {
                "name": "🤝 COLLABORATION",
                "type": "public",
                "channels": [
                    {"name": "❓・homework-help", "type": "text", "topic": "Peer review and problem solving"},
                    {"name": "💡・study-groups", "type": "text", "topic": "Coordinate study partners"},
                    {"name": "📄・notes-sharing", "type": "text", "topic": "Upload summary notes and cheat sheets"},
                ],
            },
            {
                "name": "🎧 STUDY ROOMS",
                "type": "public_voice",
                "channels": [
                    {"name": "🤫・Silent Study VC", "type": "voice"},
                    {"name": "👥・Group Study VC", "type": "voice"},
                    {"name": "🎙️・Lecture Hall", "type": "voice"},
                    {"name": "🟢・Lofi Study VC", "type": "voice"},
                ],
            },
            {
                "name": "🎫 STUDENT SUPPORT",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・open-ticket", "type": "text", "topic": "Contact educator / admin", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "language_learning": {
        "id": "language_learning",
        "name": "Polyglot Language Exchange",
        "emoji": "🌐",
        "category": "Education, Campus & Stocks",
        "group": "education",
        "description": "English, Spanish, Japanese, French, German practice rooms & native speaker voice chats.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 EMBASSY",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・guidelines", "type": "text", "topic": "Language learning guidelines", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Introduce yourself in target language", "special": "welcome"},
                    {"name": "📣・language-events", "type": "text", "topic": "Weekly native speaker speaking clubs", "special": "announcements"},
                ],
            },
            {
                "name": "🗣️ PRACTICE CHATS",
                "type": "public",
                "channels": [
                    {"name": "🇬🇧・english-practice", "type": "text", "topic": "Daily English grammar and writing"},
                    {"name": "🇪🇸・spanish-espanol", "type": "text", "topic": "Practica de espanol"},
                    {"name": "🇯🇵・japanese-nihongo", "type": "text", "topic": "Kanji, vocabulary and JLPT prep"},
                    {"name": "🇫🇷・french-francais", "type": "text", "topic": "Pratique du francais"},
                    {"name": "🇩🇪・german-deutsch", "type": "text", "topic": "Deutsche Konversation"},
                ],
            },
            {
                "name": "🎧 SPEAKING CAFES",
                "type": "public_voice",
                "channels": [
                    {"name": "🇬🇧・English Speaking Lounge", "type": "voice"},
                    {"name": "🇪🇸・Spanish Speaking Lounge", "type": "voice"},
                    {"name": "🇯🇵・Japanese Speaking Lounge", "type": "voice"},
                ],
            },
            {
                "name": "🎫 TUTORING TICKETS",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・request-tutor", "type": "text", "topic": "1-on-1 private language tutor", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "medical_health": {
        "id": "medical_health",
        "name": "Pre-Med & Health Sciences",
        "emoji": "🩺",
        "category": "Education, Campus & Stocks",
        "group": "education",
        "description": "Medical school students, MCAT prep, anatomy flashcards, pathology & nursing study.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 CLINICAL OVERVIEW",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・disclaimer", "type": "text", "topic": "Educational use only / not medical advice", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Future doctors and nurses", "special": "welcome"},
                    {"name": "📣・announcements", "type": "text", "topic": "Medical school deadlines and webinars", "special": "announcements"},
                ],
            },
            {
                "name": "🩺 SPECIALTIES",
                "type": "public",
                "channels": [
                    {"name": "💬・premed-lounge", "type": "text", "topic": "MCAT, GPA, admissions strategy"},
                    {"name": "🧬・anatomy-physiology", "type": "text", "topic": "Organ systems and histology"},
                    {"name": "💊・pharmacology", "type": "text", "topic": "Drug mechanisms and interactions"},
                    {"name": "🧠・case-studies", "type": "text", "topic": "Differential diagnosis practice"},
                ],
            },
            {
                "name": "🎧 RESIDENCY STUDY",
                "type": "public_voice",
                "channels": [
                    {"name": "🩺・Anki Flashcard Grind", "type": "voice"},
                    {"name": "☕・Doctor Breakroom", "type": "voice"},
                ],
            },
            {
                "name": "🎫 MENTORSHIP",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・match-mentor", "type": "text", "topic": "Connect with an attending or resident", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "finance_stocks": {
        "id": "finance_stocks",
        "name": "Stocks & Financial Markets",
        "emoji": "📈",
        "category": "Education, Campus & Stocks",
        "group": "education",
        "description": "Wall Street equities, options trading, dividend portfolios, earnings reports & macro news.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 TRADING FLOOR",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・disclaimer-rules", "type": "text", "topic": "Not financial advice / risk management", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Welcome traders and investors", "special": "welcome"},
                    {"name": "📣・economic-calendar", "type": "text", "topic": "Fed rate decisions, CPI & earnings", "special": "announcements"},
                ],
            },
            {
                "name": "📈 MARKET DISCUSSIONS",
                "type": "public",
                "channels": [
                    {"name": "💬・stocks-general", "type": "text", "topic": "S&P 500, Nasdaq and daily movers"},
                    {"name": "🎯・options-flow", "type": "text", "topic": "Calls, puts, spreads and implied volatility"},
                    {"name": "💰・dividend-investing", "type": "text", "topic": "Long term compound growth & index funds"},
                    {"name": "📊・chart-analysis", "type": "text", "topic": "Support, resistance, VWAP, moving averages"},
                ],
            },
            {
                "name": "🎧 MARKET AUDIO",
                "type": "public_voice",
                "channels": [
                    {"name": "🔔・Market Open Bells (9:30 AM)", "type": "voice"},
                    {"name": "☕・Power Hour Lounge", "type": "voice"},
                ],
            },
            {
                "name": "🎫 VIP ALERTS",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・vip-trade-alerts", "type": "text", "topic": "Inquire about premium trade alerts", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },

    # ==================== GROUP 9: BUSINESS, STARTUPS & ENTERPRISE ====================
    "business": {
        "id": "business",
        "name": "Business & Enterprise",
        "emoji": "🏢",
        "category": "Business, Startups & Enterprise",
        "group": "business",
        "description": "Corporate departments, B2B networking, boardroom audio & pitch decks.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 CORPORATE",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・rules", "type": "text", "topic": "Corporate code of ethics", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Professional onboarding", "special": "welcome"},
                    {"name": "📣・company-bulletin", "type": "text", "topic": "Corporate bulletins", "special": "announcements"},
                    {"name": "📌・directory", "type": "text", "topic": "Company department directory"},
                ],
            },
            {
                "name": "💼 DEPARTMENTS",
                "type": "public",
                "channels": [
                    {"name": "💬・sales-marketing", "type": "text", "topic": "Growth and campaigns"},
                    {"name": "💡・product-strategy", "type": "text", "topic": "Product roadmaps and design"},
                    {"name": "💵・finance-accounting", "type": "text", "topic": "Budgets and financial strategy"},
                    {"name": "👥・human-resources", "type": "text", "topic": "Talent, culture and hiring"},
                ],
            },
            {
                "name": "🤝 NETWORKING",
                "type": "public",
                "channels": [
                    {"name": "🤝・b2b-networking", "type": "text", "topic": "Partnership opportunities"},
                    {"name": "💡・startup-pitches", "type": "text", "topic": "Share and review pitch decks"},
                    {"name": "📊・market-insights", "type": "text", "topic": "Industry reports and analysis"},
                ],
            },
            {
                "name": "🎙️ CONFERENCE ROOMS",
                "type": "public_voice",
                "channels": [
                    {"name": "🎙️・Boardroom VC", "type": "voice"},
                    {"name": "💼・Meeting Room 1", "type": "voice", "user_limit": 6},
                    {"name": "💼・Meeting Room 2", "type": "voice", "user_limit": 6},
                    {"name": "☕・Watercooler VC", "type": "voice"},
                ],
            },
            {
                "name": "🎫 HELP DESK",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・it-tickets", "type": "text", "topic": "Internal support and IT tickets", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "startup_incubator": {
        "id": "startup_incubator",
        "name": "Startup & Founder Hub",
        "emoji": "🚀",
        "category": "Business, Startups & Enterprise",
        "group": "business",
        "description": "SaaS builders, venture capital pitches, product launch countdowns & co-founders.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 INCUBATOR HQ",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・founder-code", "type": "text", "topic": "Confidentiality and peer support", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Introduce your startup and MRR", "special": "welcome"},
                    {"name": "📣・demo-days", "type": "text", "topic": "Upcoming investor pitch events", "special": "announcements"},
                ],
            },
            {
                "name": "🚀 BUILD IN PUBLIC",
                "type": "public",
                "channels": [
                    {"name": "💬・founder-chat", "type": "text", "topic": "Daily founder struggles & wins"},
                    {"name": "📈・mrr-milestones", "type": "text", "topic": "Celebrating $1k, $10k, $100k MRR"},
                    {"name": "🤝・find-co-founder", "type": "text", "topic": "Tech & business co-founder search"},
                    {"name": "🚀・product-hunt-launches", "type": "text", "topic": "Support community launches"},
                ],
            },
            {
                "name": "🎙️ PITCH ROOMS",
                "type": "public_voice",
                "channels": [
                    {"name": "🎙️・Live Investor Pitch VC", "type": "voice"},
                    {"name": "☕・Founder Mastermind", "type": "voice"},
                ],
            },
            {
                "name": "🎫 VC OFFICE HOURS",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・pitch-deck-review", "type": "text", "topic": "Submit deck to partner VCs", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "real_estate": {
        "id": "real_estate",
        "name": "Real Estate & Investors",
        "emoji": "🏛️",
        "category": "Business, Startups & Enterprise",
        "group": "business",
        "description": "Property flipping, Airbnb arbitrage, rental cash flow, commercial REITs & deal analysis.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 BROKERAGE DESK",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・investor-rules", "type": "text", "topic": "Compliance and deal vetting", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Welcome investors and agents", "special": "welcome"},
                    {"name": "📣・market-reports", "type": "text", "topic": "Interest rates and housing trends", "special": "announcements"},
                ],
            },
            {
                "name": "🏛️ PROPERTY DEALS",
                "type": "public",
                "channels": [
                    {"name": "💬・investor-lounge", "type": "text", "topic": "General real estate discussions"},
                    {"name": "🏡・residential-and-flips", "type": "text", "topic": "BRRRR method and fix-and-flips"},
                    {"name": "🏢・commercial-multifamily", "type": "text", "topic": "Apartment complexes and syndications"},
                    {"name": "🏖️・short-term-rentals", "type": "text", "topic": "Airbnb, VRBO, occupancy and superhosts"},
                ],
            },
            {
                "name": "🎧 CLOSING ROOMS",
                "type": "public_voice",
                "channels": [
                    {"name": "🎙️・Deal Underwriting VC", "type": "voice"},
                    {"name": "☕・Investor Networking", "type": "voice"},
                ],
            },
            {
                "name": "🎫 PRIVATE DEALS",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・submit-off-market-deal", "type": "text", "topic": "Submit off-market wholesale deals", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "charity_ngo": {
        "id": "charity_ngo",
        "name": "Non-Profit & Volunteer NGO",
        "emoji": "🌍",
        "category": "Business, Startups & Enterprise",
        "group": "business",
        "description": "Global aid missions, fundraising transparency, volunteer campaigns & community outreach.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 MISSION HQ",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・charter", "type": "text", "topic": "Non-profit mission and ethical charter", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Volunteer welcomes", "special": "welcome"},
                    {"name": "📣・campaign-updates", "type": "text", "topic": "Active relief efforts and goals", "special": "announcements"},
                    {"name": "🧾・financial-transparency", "type": "text", "topic": "Audited donation usage records"},
                ],
            },
            {
                "name": "🌍 OUTREACH & VOLUNTEERS",
                "type": "public",
                "channels": [
                    {"name": "💬・volunteer-chat", "type": "text", "topic": "General team discussion"},
                    {"name": "🤝・campaign-organizing", "type": "text", "topic": "Food drives, education, shelters"},
                    {"name": "📸・field-photos", "type": "text", "topic": "Photos from ground operations"},
                ],
            },
            {
                "name": "🎧 STRATEGY ROOMS",
                "type": "public_voice",
                "channels": [
                    {"name": "🎙️・Townhall Stage", "type": "voice"},
                    {"name": "☕・Volunteer Hangout", "type": "voice"},
                ],
            },
            {
                "name": "🎫 DONATION INQUIRIES",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・donor-ticket", "type": "text", "topic": "Corporate sponsorships & major gifts", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },

    # ==================== GROUP 10: SPECIAL OPS, EVENTS & MINIMAL ====================
    "staff_management": {
        "id": "staff_management",
        "name": "Staff Management HQ",
        "emoji": "🛡️",
        "category": "Special Ops, Events & Minimal",
        "group": "special",
        "description": "Private operations HQ, shift check-ins, case escalations & leadership meetings.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 HEADQUARTERS",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・staff-policy", "type": "text", "topic": "Staff policies and handbook", "special": "rules"},
                    {"name": "🌸・onboarding", "type": "text", "topic": "New staff induction", "special": "welcome"},
                    {"name": "📣・staff-bulletin", "type": "text", "topic": "Management directives", "special": "announcements"},
                    {"name": "📌・hierarchy-guide", "type": "text", "topic": "Role hierarchy and department leads"},
                ],
            },
            {
                "name": "🛡️ OPERATIONS",
                "type": "staff_only",
                "channels": [
                    {"name": "💬・staff-general", "type": "text", "topic": "Daily staff chatter"},
                    {"name": "🔨・moderation-cases", "type": "text", "topic": "Ban disputes and active cases"},
                    {"name": "📝・meeting-notes", "type": "text", "topic": "Weekly meeting summaries"},
                    {"name": "🚨・escalations", "type": "text", "topic": "High-priority incidents"},
                ],
            },
            {
                "name": "📊 PERFORMANCE & SHIFTS",
                "type": "staff_only",
                "channels": [
                    {"name": "⏱️・clock-in-out", "type": "text", "topic": "Shift time tracking"},
                    {"name": "📈・activity-logs", "type": "text", "topic": "Moderator activity metrics"},
                    {"name": "🏆・staff-of-the-month", "type": "text", "topic": "Recognitions and bonuses"},
                ],
            },
            {
                "name": "🎙️ STAFF COMMS",
                "type": "staff_only",
                "channels": [
                    {"name": "🎙️・Staff Meeting VC", "type": "voice"},
                    {"name": "🔒・Leadership Only VC", "type": "voice"},
                    {"name": "☕・Staff Breakroom", "type": "voice"},
                ],
            },
            {
                "name": "🎫 INTERNAL TICKETS",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・hr-tickets", "type": "text", "topic": "Confidential HR and management tickets", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "giveaway_events": {
        "id": "giveaway_events",
        "name": "Mega Giveaway & Events",
        "emoji": "🎉",
        "category": "Special Ops, Events & Minimal",
        "group": "special",
        "description": "Daily flash drops, mega giveaways, winner proofs, stage events & mini-games.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 EVENT CENTRAL",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・rules", "type": "text", "topic": "Giveaway terms & claim policies", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "Member welcomes", "special": "welcome"},
                    {"name": "📣・event-announcements", "type": "text", "topic": "Big giveaway announcements", "special": "announcements"},
                    {"name": "🏆・hall-of-fame", "type": "text", "topic": "Previous champions and winners"},
                ],
            },
            {
                "name": "🎁 ACTIVE GIVEAWAYS",
                "type": "public_read_only",
                "channels": [
                    {"name": "🎉・daily-giveaways", "type": "text", "topic": "24h entry giveaways"},
                    {"name": "💎・mega-giveaways", "type": "text", "topic": "High-value seasonal prizes"},
                    {"name": "🎟️・flash-drops", "type": "text", "topic": "Quick speed-reaction drops"},
                    {"name": "🧾・winner-proofs", "type": "text", "topic": "Verified prize delivery screenshots"},
                ],
            },
            {
                "name": "💬 EVENT CHAT",
                "type": "public",
                "channels": [
                    {"name": "💬・giveaway-chat", "type": "text", "topic": "General chat during events"},
                    {"name": "🎲・minigames", "type": "text", "topic": "Interactive bot games"},
                    {"name": "🤖・bot-games", "type": "text", "topic": "Trivia and coin drops"},
                ],
            },
            {
                "name": "🎧 STAGE & VC",
                "type": "public_voice",
                "channels": [
                    {"name": "🎙️・Event Stage", "type": "voice"},
                    {"name": "🎧・Giveaway VC", "type": "voice"},
                    {"name": "🟢・Chill Lounge", "type": "voice"},
                ],
            },
            {
                "name": "🎫 CLAIM TICKETS",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・claim-prize-ticket", "type": "text", "topic": "Open ticket to claim giveaway prize", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
    "minimal_professional": {
        "id": "minimal_professional",
        "name": "Minimalist Dark Executive",
        "emoji": "⚡",
        "category": "Special Ops, Events & Minimal",
        "group": "special",
        "description": "Clean, uncluttered, high-speed Discord server structure for modern teams.",
        "roles": DEFAULT_ROLES,
        "categories": [
            {
                "name": "📢 MAIN",
                "type": "public_read_only",
                "channels": [
                    {"name": "📜・rules", "type": "text", "topic": "Essential server rules", "special": "rules"},
                    {"name": "🌸・welcome", "type": "text", "topic": "New member greetings", "special": "welcome"},
                    {"name": "📣・announcements", "type": "text", "topic": "Key announcements", "special": "announcements"},
                ],
            },
            {
                "name": "💬 DISCUSSION",
                "type": "public",
                "channels": [
                    {"name": "💬・general", "type": "text", "topic": "Main discussion"},
                    {"name": "💡・ideas", "type": "text", "topic": "Suggestions and feedback"},
                    {"name": "🤖・commands", "type": "text", "topic": "Bot interactions"},
                ],
            },
            {
                "name": "🎧 VOICE",
                "type": "public_voice",
                "channels": [
                    {"name": "🎧・General VC", "type": "voice"},
                    {"name": "🔒・Private VC", "type": "voice", "user_limit": 4},
                ],
            },
            {
                "name": "🎫 SUPPORT",
                "type": "ticket_desk",
                "channels": [
                    {"name": "📩・support-ticket", "type": "text", "topic": "Need help? Open a ticket", "special": "ticket_panel"},
                ],
            },
            STANDARD_LOGS_CATEGORY,
        ],
    },
}
