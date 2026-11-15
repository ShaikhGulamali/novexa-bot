"""NOVEXA - Central Feature Registry for Server Dashboard and Controls.

Defines all 32 supported modules, their categories, editable fields,
endpoints, and authoritative schemas. The Dashboard UI and API
generate navigation and validation directly from this registry.
"""

from typing import Dict, List, Any
from dataclasses import dataclass, field


@dataclass
class DashboardField:
    name: str
    label: str
    type: str  # 'boolean', 'text', 'number', 'select', 'textarea', 'color', 'role_select', 'channel_select'
    description: str = ""
    default: Any = None
    options: List[Dict[str, str]] = field(default_factory=list)
    min_val: int = None
    max_val: int = None


@dataclass
class DashboardFeature:
    key: str
    title: str
    icon: str
    category: str
    description: str
    status: str = "active"  # 'active' or 'planned'
    badge: str = ""
    fields: List[DashboardField] = field(default_factory=list)


FEATURE_CATEGORIES = [
    "Overview",
    "Security & Protection",
    "Community & Engagement",
    "Intelligence & Automation",
    "Economy & RPG",
    "Server Administration",
]

FEATURE_REGISTRY: Dict[str, DashboardFeature] = {
    # 1. Overview
    "overview": DashboardFeature(
        key="overview",
        title="Overview",
        icon="📊",
        category="Overview",
        description="Server health, active defenses, member stats, and module toggles.",
    ),

    # 2. Welcome
    "welcome": DashboardFeature(
        key="welcome",
        title="Welcome",
        icon="🎨",
        category="Community & Engagement",
        description="20 professional visual themes, dynamic banner graphics, custom messages, and autoroles.",
        fields=[
            DashboardField("enabled", "Enable Welcome System", "boolean", "Broadcast welcome messages when new members join.", True),
            DashboardField("channel_id", "Welcome Channel", "channel_select", "Channel where welcome messages are dispatched."),
            DashboardField("template_id", "Banner Template (20 Styles)", "select", "Visual design for generated card.", "novexa_exclusive", [
                {"value": "novexa_exclusive", "label": "👑 NOVEXA Exclusive"},
                {"value": "minimal", "label": "⚪ Minimal Clean"},
                {"value": "premium_blue", "label": "💎 Premium Blue"},
                {"value": "black_silver", "label": "⚔️ Black & Silver"},
                {"value": "cyberpunk", "label": "⚡ Cyberpunk 2077"},
                {"value": "neon_gaming", "label": "🎮 Neon Gaming"},
                {"value": "purple_luxury", "label": "🔮 Purple Luxury"},
                {"value": "gold_vip", "label": "🏆 Gold VIP"},
                {"value": "modern_gradient", "label": "🌅 Modern Gradient"},
                {"value": "glassmorphism", "label": "🪟 Glassmorphism"},
                {"value": "anime_style", "label": "🌸 Anime Aesthetic"},
                {"value": "cute_community", "label": "🧸 Cute Community"},
                {"value": "pro_business", "label": "💼 Professional Business"},
                {"value": "discord_gaming", "label": "👾 Discord Gaming"},
                {"value": "royal_theme", "label": "👑 Royal Imperial"},
                {"value": "space_theme", "label": "🌌 Cosmic Space"},
                {"value": "futuristic_ai", "label": "🤖 Futuristic AI"},
                {"value": "minimal_dark", "label": "🌑 Minimal Dark"},
                {"value": "elegant_white", "label": "🕊️ Elegant White"},
                {"value": "rgb_gaming", "label": "🌈 RGB Spectrum"},
            ]),
            DashboardField("banner_enabled", "Enable Graphic Banner Card", "boolean", "Generate dynamic high-res PIL card with member avatar.", True),
            DashboardField("embed_enabled", "Enable Welcome Embed", "boolean", "Send rich embed message alongside card.", True),
            DashboardField("title", "Welcome Title", "text", "Title text header.", "Welcome to {server}!"),
            DashboardField("message_template", "Welcome Message Template", "textarea", "Supports {user}, {username}, {server}, {member_count}, etc.", "Hey {user}, welcome to **{server}**! You are member #{member_count}."),
            DashboardField("custom_color", "Accent Color (Hex)", "color", "Border and card highlight color.", "#5865F2"),
            DashboardField("dm_enabled", "Send Direct Message to Member", "boolean", "Send a warm private greeting in DM upon joining.", False),
            DashboardField("dm_template", "DM Welcome Message", "textarea", "DM message body.", "Welcome to **{server}**, {user}! Read our rules to get started."),
            DashboardField("autorole_enabled", "Assign Role on Join", "boolean", "Automatically give a verified or member role.", False),
            DashboardField("autorole_id", "Join Auto-Role", "role_select", "Role to assign new members."),
        ]
    ),

    # 3. Goodbye
    "goodbye": DashboardFeature(
        key="goodbye",
        title="Goodbye",
        icon="🚪",
        category="Community & Engagement",
        description="Track departing members with custom leave cards and departure logs.",
        fields=[
            DashboardField("goodbye_enabled", "Enable Goodbye System", "boolean", "Post notifications when a member leaves.", True),
            DashboardField("leave_channel_id", "Goodbye Channel", "channel_select", "Channel for departure notifications."),
            DashboardField("goodbye_template_id", "Goodbye Style Template", "select", "Design theme for departure card.", "minimal_dark", [
                {"value": "minimal_dark", "label": "🌑 Minimal Dark"},
                {"value": "black_silver", "label": "⚔️ Black & Silver"},
                {"value": "purple_luxury", "label": "🔮 Purple Luxury"},
                {"value": "novexa_exclusive", "label": "👑 NOVEXA Exclusive"},
            ]),
            DashboardField("leave_embed_enabled", "Enable Goodbye Embed", "boolean", "Send formatted departure embed.", True),
            DashboardField("leave_message_template", "Goodbye Message Template", "textarea", "Supports {username}, {server}, {member_count}.", "**{username}** has left {server}. We now have {member_count} members."),
        ]
    ),

    # 4. Auto Roles
    "autoroles": DashboardFeature(
        key="autoroles",
        title="Auto Roles",
        icon="🏷️",
        category="Community & Engagement",
        description="Instant automated role assignment for new users, bots, and verified guests.",
        fields=[
            DashboardField("auto_roles", "Default Join Roles", "role_select", "Roles assigned to all incoming human members."),
            DashboardField("bot_role_id", "Bot Join Role", "role_select", "Specific role assigned to newly added bot accounts."),
        ]
    ),

    # 6. Anti-Nuke
    "antinuke": DashboardFeature(
        key="antinuke",
        title="Anti-Nuke",
        icon="🚨",
        category="Security & Protection",
        description="Sub-second interception against mass channel/role deletion, webhook spam, and rogue admin attacks.",
        fields=[
            DashboardField("enabled", "Enable Anti-Nuke Engine", "boolean", "Actively guard server against mass destructive operations.", True),
            DashboardField("mode", "Protection Posture", "select", "Strictness level for responses.", "medium", [
                {"value": "low", "label": "🟢 LOW — Audit logging & warnings only"},
                {"value": "medium", "label": "🟡 MEDIUM — Automated progressive mitigation (Recommended)"},
                {"value": "high", "label": "🔴 HIGH — Strict zero-tolerance lockdown"},
            ]),
            DashboardField("punishment_type", "Automated Action on Breach", "select", "Punishment applied to rogue executor.", "quarantine", [
                {"value": "quarantine", "label": "🔒 Quarantine (Strip dangerous roles)"},
                {"value": "kick", "label": "👢 Kick Executor"},
                {"value": "ban", "label": "🔨 Ban Executor from Server"},
            ]),
            DashboardField("max_channel_deletions", "Max Channel Deletions", "number", "Allowed channel deletions within 10s window.", 2, min_val=1, max_val=20),
            DashboardField("max_channel_creations", "Max Channel Creations", "number", "Allowed channel creations within 10s window.", 3, min_val=1, max_val=20),
            DashboardField("max_role_deletions", "Max Role Deletions", "number", "Allowed role deletions within 10s window.", 3, min_val=1, max_val=20),
            DashboardField("max_role_creations", "Max Role Creations", "number", "Allowed role creations within 10s window.", 3, min_val=1, max_val=20),
            DashboardField("max_webhook_changes", "Max Webhook Changes", "number", "Allowed webhook modifications within 10s window.", 4, min_val=1, max_val=20),
            DashboardField("max_bans", "Max Ban Actions", "number", "Allowed member bans within 10s window.", 3, min_val=1, max_val=20),
            DashboardField("max_kicks", "Max Kick Actions", "number", "Allowed member kicks within 10s window.", 4, min_val=1, max_val=20),
            DashboardField("max_permission_changes", "Max Permission Escalations", "number", "Admin grants or dangerous overwrites in 15s window.", 3, min_val=1, max_val=20),
            DashboardField("log_channel_id", "Security Incident Log Channel", "channel_select", "Channel to dispatch red alerts with executor details."),
        ]
    ),

    # 7. Anti-Spam
    "antispam": DashboardFeature(
        key="antispam",
        title="Anti-Spam",
        icon="💬",
        category="Security & Protection",
        description="Sliding-window heuristics blocking mass mentions, copypasta bursts, invites, and emoji floods.",
        fields=[
            DashboardField("enabled", "Enable Anti-Spam Scanning", "boolean", "Inspect messages in real-time.", True),
            DashboardField("max_mentions", "Max Mentions per Message", "number", "Block messages exceeding this user/role mention limit.", 5, min_val=1, max_val=30),
            DashboardField("max_duplicates", "Duplicate Message Burst Limit", "number", "Block identical messages repeated in 5s window.", 3, min_val=1, max_val=10),
            DashboardField("max_emojis", "Max Emojis per Message", "number", "Ceiling for emoji flooding.", 8, min_val=2, max_val=50),
            DashboardField("block_invites", "Block Discord Invite Links", "boolean", "Auto-delete unauthorized server invites.", True),
            DashboardField("block_links", "Block Suspicious URLs & Phishing", "boolean", "Filter known token loggers and phishing heuristics.", True),
            DashboardField("timeout_duration_minutes", "Punishment Timeout Duration", "number", "Minutes to timeout offenders.", 10, min_val=1, max_val=10080),
        ]
    ),

    # 8. AutoMod
    "automod": DashboardFeature(
        key="automod",
        title="AutoMod",
        icon="🤖",
        category="Security & Protection",
        description="Filter profanity, blocked keywords, all-caps yelling, and malicious attachments.",
        fields=[
            DashboardField("caps_filter_enabled", "Filter Excessive Caps", "boolean", "Delete messages with >70% capital letters.", False),
            DashboardField("blocked_words", "Blocked Words List", "textarea", "Comma-separated list of prohibited words and regex patterns."),
            DashboardField("attachment_spam_limit", "Max Attachments per Minute", "number", "Max files uploaded per user per minute.", 5, min_val=1, max_val=20),
            DashboardField("automod_action", "AutoMod Violation Action", "select", "Disciplinary action taken.", "warn", [
                {"value": "delete", "label": "🗑️ Delete Message Only"},
                {"value": "warn", "label": "⚠️ Delete & Issue Warning"},
                {"value": "timeout", "label": "⏱️ Delete & Timeout 10 Minutes"},
            ]),
        ]
    ),

    # 9. Whitelist
    "whitelist": DashboardFeature(
        key="whitelist",
        title="Whitelist",
        icon="📋",
        category="Security & Protection",
        description="Trusted administrators and roles exempt from Anti-Nuke and Anti-Spam rate-limits.",
        fields=[
            DashboardField("whitelist_members", "Whitelisted Members", "text", "Comma-separated Discord User IDs."),
            DashboardField("whitelist_roles", "Whitelisted Roles", "role_select", "Roles completely immune to security limits."),
        ]
    ),

    # 10. Approved Bots
    "approved_bots": DashboardFeature(
        key="approved_bots",
        title="Approved Bots",
        icon="🤖",
        category="Security & Protection",
        description="Bot addition gatekeeper: rogue or unapproved bots are instantly kicked from the server.",
        fields=[
            DashboardField("bot_protection_enabled", "Strict Bot Addition Protection", "boolean", "Instantly kick any external bot not pre-approved here.", True),
            DashboardField("approved_bot_ids", "Pre-Approved Bot Application IDs", "textarea", "List of allowed bot client IDs (one per line)."),
        ]
    ),

    # 11. Moderation
    "moderation": DashboardFeature(
        key="moderation",
        title="Moderation",
        icon="⚖️",
        category="Server Administration",
        description="Case history, warnings log, slowmode defaults, and staff disciplinary controls.",
        fields=[
            DashboardField("mod_log_channel_id", "Moderation Case Channel", "channel_select", "Channel where bans, kicks, and timeouts are logged."),
            DashboardField("dm_on_punish", "DM Punished Members", "boolean", "Send an official notice to members with the reason for discipline.", True),
            DashboardField("max_warnings_before_kick", "Max Warnings Before Kick", "number", "Automated kick threshold.", 3, min_val=1, max_val=10),
            DashboardField("max_warnings_before_ban", "Max Warnings Before Ban", "number", "Automated ban threshold.", 5, min_val=2, max_val=20),
        ]
    ),

    # 12. Tickets
    "tickets": DashboardFeature(
        key="tickets",
        title="Tickets",
        icon="🎫",
        category="Community & Engagement",
        description="Persistent interactive ticket panels, support categories, HTML transcripts, and staff review.",
        fields=[
            DashboardField("tickets_enabled", "Enable Ticket System", "boolean", "Allow members to open private support tickets.", True),
            DashboardField("category_id", "Ticket Channel Category", "channel_select", "Discord category where new ticket channels are created."),
            DashboardField("support_role_id", "Staff / Support Team Role", "role_select", "Role granted view/send access to all tickets."),
            DashboardField("transcript_channel_id", "Transcripts Channel", "channel_select", "Channel where dark-mode HTML transcripts are saved."),
            DashboardField("panel_title", "Ticket Panel Title", "text", "Title displayed on panel embed.", "🎫 NOVEXA Support Portal"),
            DashboardField("panel_description", "Ticket Panel Message", "textarea", "Instructions for opening a ticket.", "Click the button below to connect directly with our support team."),
        ]
    ),

    # 13. Logging
    "logging": DashboardFeature(
        key="logging",
        title="Logging",
        icon="📜",
        category="Server Administration",
        description="Granular event dispatching for joins, leaves, message edits, deletes, voice states, and roles.",
        fields=[
            DashboardField("joins_channel_id", "Member Joins Channel", "channel_select", "Log new member accounts and join timestamps."),
            DashboardField("leaves_channel_id", "Member Departures Channel", "channel_select", "Log departures and roles previously held."),
            DashboardField("message_edits_channel_id", "Message Edits Channel", "channel_select", "Log original content vs edited content."),
            DashboardField("message_deletes_channel_id", "Message Deletions Channel", "channel_select", "Log purged and deleted text."),
            DashboardField("role_changes_channel_id", "Role Hierarchy Logs", "channel_select", "Log created, modified, or assigned roles."),
            DashboardField("channel_changes_channel_id", "Channel Changes Channel", "channel_select", "Log created, renamed, or deleted channels."),
            DashboardField("bans_channel_id", "Bans & Unbans Channel", "channel_select", "Log ban reasons and moderator responsible."),
        ]
    ),

    # 14. Roles
    "roles": DashboardFeature(
        key="roles",
        title="Roles",
        icon="👑",
        category="Server Administration",
        description="Role hierarchy inspector, self-assignable button panels, and permission safety checks.",
        fields=[
            DashboardField("enforce_hierarchy", "Enforce Discord Role Hierarchy", "boolean", "Prevent lower staff from modifying higher roles.", True),
        ]
    ),

    # 15. Server Setup
    "server_setup": DashboardFeature(
        key="server_setup",
        title="Server Setup",
        icon="🏗️",
        category="Server Administration",
        description="50 pre-built enterprise Discord server templates across 10 categories with safe 1-click rollback.",
        fields=[
            DashboardField("template_id", "Select Architecture Preset", "select", "Choose from 50 professionally built layouts.", "developer", [
                {"value": "developer", "label": "💻 Software Engineering HQ"},
                {"value": "gaming", "label": "🎮 Gaming Community Hub"},
                {"value": "esports_clan", "label": "🏆 Competitive Esports Team"},
                {"value": "digital_store", "label": "🛍️ Digital Store & Commerce"},
                {"value": "crypto_nft", "label": "🪙 Crypto & Web3 Alpha"},
                {"value": "creator", "label": "🎥 YouTuber & Streamer HQ"},
                {"value": "anime_lounge", "label": "🌸 Anime & Manga Haven"},
                {"value": "social", "label": "💬 Friendly Hangout Community"},
                {"value": "music", "label": "🎵 Musicians & Studio Guild"},
                {"value": "business", "label": "🏢 Enterprise Business HQ"},
                {"value": "minimal_professional", "label": "⚡ Minimalist Dark Executive"},
            ]),
        ]
    ),

    # 18. Music
    "music": DashboardFeature(
        key="music",
        title="Music",
        icon="🎵",
        category="Community & Engagement",
        description="High-fidelity voice streaming powered by yt-dlp, FFmpeg, interactive player, and 24/7 VC mode.",
        fields=[
            DashboardField("is_247", "Enable 24/7 Voice Mode", "boolean", "Stay connected in voice channel permanently across restarts.", False),
            DashboardField("voice_channel_id", "Default 24/7 Voice Channel", "channel_select", "Target voice room."),
            DashboardField("text_channel_id", "Designated Music Command Channel", "channel_select", "Channel to restrict music commands and player cards."),
            DashboardField("default_volume", "Default Playback Volume (%)", "number", "Standard starting volume.", 100, min_val=1, max_val=150),
        ]
    ),

    # 19. Economy
    "economy": DashboardFeature(
        key="economy",
        title="Economy",
        icon="💰",
        category="Economy & RPG",
        description="Virtual currency system, banking deposits, net worth leaderboards, and daily streaks.",
        fields=[
            DashboardField("is_enabled", "Enable Virtual Economy", "boolean", "Activate currency and banking features.", True),
            DashboardField("currency_name", "Currency Name", "text", "Display name of coins.", "NOVEXA COINS"),
            DashboardField("currency_symbol", "Currency Emoji / Symbol", "text", "Symbol prefixed to numbers.", "🪙"),
            DashboardField("daily_reward", "Base Daily Reward", "number", "Base coins given by /daily.", 1000, min_val=100, max_val=100000),
            DashboardField("streak_bonus_per_day", "Streak Multiplier per Day", "number", "Additional coins per consecutive day.", 25, min_val=1, max_val=1000),
            DashboardField("work_cooldown", "Work Cooldown (Seconds)", "number", "Time between /work commands.", 300, min_val=30, max_val=3600),
        ]
    ),

    # 20. RPG and Games
    "rpg_games": DashboardFeature(
        key="rpg_games",
        title="RPG & Games",
        icon="🎲",
        category="Economy & RPG",
        description="Coinflip, 6-sided dice, slots with 50x jackpot, high-risk crime heists, and PvP turn battles.",
        fields=[
            DashboardField("games_enabled", "Enable Gambling & Mini-Games", "boolean", "Allow coinflip, slots, dice, and crime.", True),
            DashboardField("crime_success_rate", "Crime Success Rate (%)", "number", "Probability of successful heist.", 65, min_val=10, max_val=90),
            DashboardField("max_bet_amount", "Max Bet Amount", "number", "Ceiling for coinflip and slots wagers (0 for unlimited).", 50000, min_val=0, max_val=10000000),
        ]
    ),

    # 21. Pets and Hunting
    "pets_hunting": DashboardFeature(
        key="pets_hunting",
        title="Pets & Hunting",
        icon="🐾",
        category="Economy & RPG",
        description="Safari hunting across 49 wild animal species, zoo collection rarity tiers, and loyal pet companions.",
        fields=[
            DashboardField("hunt_cooldown", "Hunting Cooldown (Seconds)", "number", "Delay between /hunt encounters.", 15, min_val=5, max_val=300),
            DashboardField("mythical_drop_rate", "Mythical Animal Chance (%)", "number", "Probability of catching Mythical beast.", 1, min_val=1, max_val=10),
            DashboardField("pet_adoption_enabled", "Enable Pet Adoption Bazaar", "boolean", "Allow adopting dogs, dragons, and griffins.", True),
        ]
    ),

    # 22. Leveling
    "leveling": DashboardFeature(
        key="leveling",
        title="Leveling",
        icon="⭐",
        category="Community & Engagement",
        description="Chat activity XP progression, customizable rank cards, and 50-rank server leaderboards.",
        fields=[
            DashboardField("leveling_enabled", "Enable Chat XP Leveling", "boolean", "Award XP for meaningful server messages.", True),
            DashboardField("xp_per_message", "Base XP per Message", "number", "XP gained per valid chat message.", 15, min_val=1, max_val=100),
            DashboardField("xp_cooldown", "XP Anti-Spam Cooldown (Seconds)", "number", "Delay before a user can gain XP again.", 60, min_val=5, max_val=300),
            DashboardField("level_up_channel_id", "Level-Up Announcement Channel", "channel_select", "Channel to broadcast rank milestones (or leave empty for current channel)."),
        ]
    ),

    # 23. Giveaways
    "giveaways": DashboardFeature(
        key="giveaways",
        title="Giveaways",
        icon="🎉",
        category="Community & Engagement",
        description="Automated server giveaways, reaction entry, countdown timers, and fair winner picking.",
        fields=[
            DashboardField("giveaway_log_channel_id", "Giveaways Log Channel", "channel_select", "Log winners and prize claims."),
        ]
    ),

    # 24. Reaction Roles
    "reaction_roles": DashboardFeature(
        key="reaction_roles",
        title="Reaction Roles",
        icon="✨",
        category="Community & Engagement",
        description="Interactive button and reaction role menus for colors, notification pings, and vanity tags.",
    ),

    # 25. Custom Embeds
    "custom_embeds": DashboardFeature(
        key="custom_embeds",
        title="Custom Embeds",
        icon="🖼️",
        category="Server Administration",
        description="Studio embed builder: author headers, description markdown, fields, color pickers, and broadcasts.",
    ),

    # 26. Auto Responder
    "auto_responder": DashboardFeature(
        key="auto_responder",
        title="Auto Responder",
        icon="⚡",
        category="Intelligence & Automation",
        description="Automatic custom keyword replies with exact, contains, or starts-with trigger patterns.",
    ),

    # 27. Voice Channels
    "voice_channels": DashboardFeature(
        key="voice_channels",
        title="Voice Channels",
        icon="🎙️",
        category="Community & Engagement",
        description="Dynamic voice rooms, 24/7 dedicated streaming rooms, and bit-rate management.",
    ),

    # 28. Backups
    "backups": DashboardFeature(
        key="backups",
        title="Backups",
        icon="💾",
        category="Security & Protection",
        description="Instant disaster recovery snapshots capturing roles, categories, channels, and permission overwrites.",
    ),

    # 29. Integrations
    "integrations": DashboardFeature(
        key="integrations",
        title="Integrations",
        icon="🔌",
        category="Server Administration",
        description="UPI / QR code payment review gateway, custom webhooks, and third-party API connections.",
    ),

    # 30. Premium
    "premium": DashboardFeature(
        key="premium",
        title="Premium",
        icon="💎",
        category="Server Administration",
        description="Silver (₹299), Gold (₹599), and Platinum (₹999) VIP subscription tiers and perk management.",
    ),

    # 31. Audit History
    "audit_history": DashboardFeature(
        key="audit_history",
        title="Audit History",
        icon="🔍",
        category="Server Administration",
        description="Live real-time feed of all configuration updates made via Discord commands and Web Dashboard.",
    ),

    # 32. Settings
    "settings": DashboardFeature(
        key="settings",
        title="Settings",
        icon="⚙️",
        category="Server Administration",
        description="Server prefix, default language, timezone, bot permissions inspector, and danger zone.",
        fields=[
            DashboardField("prefix", "Bot Command Prefix", "text", "Prefix for legacy text commands.", "/"),
        ]
    ),

    # 33. Wallpaper Studio
    "wallpaper": DashboardFeature(
        key="wallpaper",
        title="Wallpaper Studio",
        icon="🖼️",
        category="Server Administration",
        description="AI wallpaper channels: every message in a designated channel becomes an image prompt with size keywords.",
    ),

    # 34. Dropper Suite
    "dropper": DashboardFeature(
        key="dropper",
        title="Dropper Suite",
        icon="💧",
        category="Server Administration",
        description="Grant or revoke the Dropper upload role for developer channels, and monitor active droppers.",
    ),
}

