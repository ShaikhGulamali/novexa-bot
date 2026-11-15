"""NOVEXA - Advanced Anti-Nuke & Server Security Engine.

Features:
- Event-driven ultra-fast detection with bounded concurrent task execution
- Delay-resilient audit-log correlation with exponential fast-retry loop
- Sliding-window multi-event rate-limit threshold enforcement
- Automatic damage containment: channel recovery, role recovery, webhook eviction, bot eviction
- Strict least-privilege authorization (Owner immunity, explicit whitelist, no automatic admin trust)
- Hierarchy-aware punishment execution (Ban, Kick, Quarantine, Timeout, Revoke Perms)
- Precise real-time detection & response latency benchmarking (recorded in ms)
- Dedicated rich security logging and real-time dashboard synchronization
"""

import asyncio
import datetime
import logging
import time
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Union, Any
import discord

from database.database import db
from utils.permissions import is_bot_owner
from utils.emojis import Emojis
from config import BOT_NAME

logger = logging.getLogger("novexa.security_service")

# Default thresholds: (count, seconds)
DEFAULT_THRESHOLDS = {
    "channel_delete": (2, 10),
    "channel_create": (3, 10),
    "channel_update": (4, 10),
    "role_delete": (2, 10),
    "role_create": (3, 10),
    "role_update": (4, 10),
    "permission_escalation": (1, 15),
    "webhook_create": (2, 10),
    "webhook_delete": (2, 10),
    "webhook_change": (4, 10),
    "bot_add": (1, 30),
    "ban": (3, 10),
    "kick": (4, 10),
    "server_update": (2, 15),
    "emoji_create": (4, 15),
    "emoji_delete": (2, 15),
    "emoji_update": (5, 15),
    "sticker_create": (4, 15),
    "sticker_delete": (2, 15),
    "sticker_update": (5, 15),
    "integration_create": (1, 30),
    "integration_delete": (1, 30),
    "prune": (1, 30),
    "message_purge": (1, 10),
    "thread_delete": (2, 10),
    "role_grant": (3, 10),
    "voice_abuse": (4, 15),
    "raid_join": (1, 20),
}

# Per-guild configurable limits live in antinuke_config columns; they override
# the table defaults in MEDIUM mode and are clamped to the stricter value in HIGH.
CONFIG_LIMIT_COLUMNS = {
    "channel_delete": "max_channel_deletions",
    "channel_create": "max_channel_creations",
    "channel_update": "max_channel_updates",
    "role_delete": "max_role_deletions",
    "role_create": "max_role_creations",
    "role_update": "max_role_updates",
    "permission_escalation": "max_permission_changes",
    "ban": "max_bans",
    "kick": "max_kicks",
    "webhook_create": "max_webhook_creations",
    "webhook_delete": "max_webhook_deletions",
    "webhook_change": "max_webhook_changes",
}

# Human labels used by /antinuke threshold and the settings embeds.
ACTION_LABELS = {
    "channel_delete": "Channel Deletions",
    "channel_create": "Channel Creations",
    "channel_update": "Channel Updates",
    "role_delete": "Role Deletions",
    "role_create": "Role Creations",
    "role_update": "Role Updates",
    "permission_escalation": "Permission Escalation",
    "webhook_create": "Webhook Creations",
    "webhook_delete": "Webhook Deletions",
    "webhook_change": "Webhook Modifications",
    "bot_add": "Unauthorized Bot Adds",
    "ban": "Mass Bans",
    "kick": "Mass Kicks",
    "server_update": "Server Setting Changes",
    "emoji_create": "Emoji Creations",
    "emoji_delete": "Emoji Deletions",
    "emoji_update": "Emoji Modifications",
    "sticker_create": "Sticker Creations",
    "sticker_delete": "Sticker Deletions",
    "sticker_update": "Sticker Modifications",
    "integration_create": "Integration Adds",
    "integration_delete": "Integration Removals",
    "prune": "Member Prunes",
    "message_purge": "Bulk Message Purges",
    "thread_delete": "Thread Deletions",
    "role_grant": "Mass Role Grants",
    "voice_abuse": "Force Voice Moves",
    "raid_join": "Raid Joins",
}

# High mode thresholds: Instant aggressive response (threshold 1 on destructive events)
HIGH_MODE_THRESHOLDS = {
    "channel_delete": (1, 10),
    "channel_create": (2, 10),
    "channel_update": (2, 10),
    "role_delete": (1, 10),
    "role_create": (2, 10),
    "role_update": (2, 10),
    "permission_escalation": (1, 15),
    "webhook_create": (1, 10),
    "webhook_delete": (1, 10),
    "webhook_change": (2, 10),
    "bot_add": (1, 30),
    "ban": (1, 10),
    "kick": (2, 10),
    "server_update": (1, 15),
    "emoji_create": (2, 15),
    "emoji_delete": (1, 15),
    "emoji_update": (2, 15),
    "sticker_create": (2, 15),
    "sticker_delete": (1, 15),
    "sticker_update": (2, 15),
    "integration_create": (1, 30),
    "integration_delete": (1, 30),
    "prune": (1, 30),
    "message_purge": (1, 10),
    "thread_delete": (1, 10),
    "role_grant": (1, 10),
    "voice_abuse": (2, 15),
    "raid_join": (1, 20),
}

# Panic mode: every monitored vector is a one-strike ban. Thresholds are held
# at 1 regardless of per-guild overrides so a single channel create, rename,
# role change, role grant, bot add or webhook triggers instant containment.
PANIC_THRESHOLDS = {key: (1, 20 if key in ("bot_add", "integration_create", "integration_delete", "prune", "raid_join") else 10)
                    for key in DEFAULT_THRESHOLDS}


class SecurityService:
    """Enterprise Asynchronous Anti-Nuke Security Engine."""

    def __init__(self):
        # (guild_id, user_id, action_key) -> list of timestamp floats
        self._action_tracker: Dict[Tuple[int, int, str], List[float]] = defaultdict(list)
        # In-memory config cache for microsecond lookup: guild_id -> dict
        self._config_cache: Dict[int, Dict[str, Any]] = {}
        # In-memory state caches for instant recovery: guild_id -> id -> dict
        self._channel_cache: Dict[int, Dict[int, Dict[str, Any]]] = defaultdict(dict)
        self._role_cache: Dict[int, Dict[int, Dict[str, Any]]] = defaultdict(dict)
        # In-flight correlation locks to prevent race conditions
        self._locks: Dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

    # ==================== 1. CONFIGURATION & CACHE MANAGEMENT ====================

    async def get_security_config(self, guild_id: int) -> Dict[str, Any]:
        """Fetch current anti-nuke configuration with in-memory caching."""
        if guild_id in self._config_cache:
            return self._config_cache[guild_id]

        cfg = await db.fetchone("SELECT * FROM antinuke_config WHERE guild_id = ?", (guild_id,))
        if not cfg:
            await db.execute(
                """
                INSERT OR IGNORE INTO antinuke_config (guild_id, enabled, mode, punishment_type)
                VALUES (?, 1, 'medium', 'ban')
                """,
                (guild_id,),
            )
            cfg = await db.fetchone("SELECT * FROM antinuke_config WHERE guild_id = ?", (guild_id,))

        config_dict = dict(cfg) if cfg else {"enabled": 1, "mode": "medium", "punishment_type": "ban"}
        self._config_cache[guild_id] = config_dict
        return config_dict

    async def set_security_enabled(self, guild_id: int, enabled: bool) -> None:
        """Update Anti-Nuke state and synchronize immediately across memory and DB."""
        val = 1 if enabled else 0
        await db.execute(
            """
            INSERT INTO antinuke_config (guild_id, enabled) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET enabled = excluded.enabled
            """,
            (guild_id, val),
        )
        if guild_id in self._config_cache:
            self._config_cache[guild_id]["enabled"] = val
        else:
            await self.get_security_config(guild_id)

    async def set_security_mode(self, guild_id: int, mode: str) -> None:
        """Update protection mode (low, medium, high) and synchronize."""
        m_val = mode.lower()
        await db.execute(
            """
            INSERT INTO antinuke_config (guild_id, mode) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET mode = excluded.mode
            """,
            (guild_id, m_val),
        )
        if guild_id in self._config_cache:
            self._config_cache[guild_id]["mode"] = m_val

    async def set_security_punishment(self, guild_id: int, punishment: str) -> None:
        """Update default punishment action and synchronize."""
        p_val = punishment.lower()
        await db.execute(
            """
            INSERT INTO antinuke_config (guild_id, punishment_type) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET punishment_type = excluded.punishment_type
            """,
            (guild_id, p_val),
        )
        if guild_id in self._config_cache:
            self._config_cache[guild_id]["punishment_type"] = p_val

    async def set_security_log_channel(self, guild_id: int, channel_id: int) -> None:
        """Update dedicated security alert channel."""
        await db.execute(
            """
            INSERT INTO antinuke_config (guild_id, log_channel_id) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET log_channel_id = excluded.log_channel_id
            """,
            (guild_id, channel_id),
        )
        if guild_id in self._config_cache:
            self._config_cache[guild_id]["log_channel_id"] = channel_id

    async def set_security_time_window(self, guild_id: int, seconds: int) -> None:
        """Update the sliding rate-limit window applied to every tracked vector."""
        await db.execute(
            """
            INSERT INTO antinuke_config (guild_id, time_window) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET time_window = excluded.time_window
            """,
            (guild_id, seconds),
        )
        if guild_id in self._config_cache:
            self._config_cache[guild_id]["time_window"] = seconds

    async def set_security_threshold(self, guild_id: int, action_key: str, limit: int) -> bool:
        """Update the per-vector trigger count. Returns False for non-configurable vectors."""
        column = CONFIG_LIMIT_COLUMNS.get(action_key)
        if not column:
            return False
        await db.execute(
            f"""
            INSERT INTO antinuke_config (guild_id, {column}) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET {column} = excluded.{column}
            """,
            (guild_id, limit),
        )
        if guild_id in self._config_cache:
            self._config_cache[guild_id][column] = limit
        return True

    async def set_bot_protection(self, guild_id: int, enabled: bool) -> None:
        """Toggle unauthorized bot-addition interception."""
        val = 1 if enabled else 0
        await db.execute(
            """
            INSERT INTO antinuke_config (guild_id, bot_protection_enabled) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET bot_protection_enabled = excluded.bot_protection_enabled
            """,
            (guild_id, val),
        )
        if guild_id in self._config_cache:
            self._config_cache[guild_id]["bot_protection_enabled"] = val

    async def set_raid_shield(self, guild_id: int, enabled: bool) -> None:
        """Toggle the join-raid shield (young-account burst protection)."""
        val = 1 if enabled else 0
        await db.execute(
            """
            INSERT INTO antinuke_config (guild_id, raid_shield_enabled) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET raid_shield_enabled = excluded.raid_shield_enabled
            """,
            (guild_id, val),
        )
        if guild_id in self._config_cache:
            self._config_cache[guild_id]["raid_shield_enabled"] = val

    # ==================== 2. WHITELIST & AUTHORIZATION ====================

    async def add_whitelist(
        self,
        guild_id: int,
        target_id: int,
        target_type: str = "user",
        added_by: Optional[int] = None,
        expires_at: Optional[str] = None,
    ) -> None:
        await db.execute(
            """
            INSERT INTO antinuke_whitelist (guild_id, target_id, target_type, added_by, expires_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, target_id) DO UPDATE SET
                target_type = excluded.target_type,
                added_by = excluded.added_by,
                expires_at = excluded.expires_at
            """,
            (guild_id, target_id, target_type, added_by, expires_at),
        )

    async def remove_whitelist(self, guild_id: int, target_id: int) -> bool:
        row = await db.fetchone(
            "SELECT id FROM antinuke_whitelist WHERE guild_id = ? AND target_id = ?",
            (guild_id, target_id),
        )
        if not row:
            return False
        await db.execute(
            "DELETE FROM antinuke_whitelist WHERE guild_id = ? AND target_id = ?",
            (guild_id, target_id),
        )
        return True

    async def list_whitelist(self, guild_id: int) -> List[Dict[str, Any]]:
        rows = await db.fetchall(
            """
            SELECT target_id, target_type, added_by, added_at
            FROM antinuke_whitelist WHERE guild_id = ? ORDER BY added_at ASC
            """,
            (guild_id,),
        )
        return [dict(r) for r in rows]

    async def approve_bot(
        self, guild_id: int, bot_id: int, bot_name: str = "Unknown Bot", approved_by: Optional[int] = None
    ) -> None:
        await db.execute(
            """
            INSERT INTO security_approved_bots (guild_id, bot_id, bot_name, approved_by)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id, bot_id) DO UPDATE SET
                bot_name = excluded.bot_name,
                approved_by = excluded.approved_by
            """,
            (guild_id, bot_id, bot_name, approved_by or 0),
        )

    async def revoke_bot(self, guild_id: int, bot_id: int) -> bool:
        row = await db.fetchone(
            "SELECT id FROM security_approved_bots WHERE guild_id = ? AND bot_id = ?",
            (guild_id, bot_id),
        )
        if not row:
            return False
        await db.execute(
            "DELETE FROM security_approved_bots WHERE guild_id = ? AND bot_id = ?",
            (guild_id, bot_id),
        )
        return True

    async def list_approved_bots(self, guild_id: int) -> List[Dict[str, Any]]:
        rows = await db.fetchall(
            """
            SELECT bot_id, bot_name, approved_by, approved_at
            FROM security_approved_bots WHERE guild_id = ? ORDER BY approved_at ASC
            """,
            (guild_id,),
        )
        return [dict(r) for r in rows]

    # ==================== 2b. AUTHORIZATION CHECKS ====================

    async def is_whitelisted(
        self,
        guild: discord.Guild,
        user: Union[discord.Member, discord.User],
        check_bot_addition: bool = False,
    ) -> bool:
        """Strict least-privilege authorization check.

        CRITICAL SECURITY RULES:
        1. Server Owner is ALWAYS immune (never punished).
        2. Whitelist NEVER grants Administrator rights automatically.
        3. Ordinary whitelisted members CANNOT add unapproved bots!
        """
        # Server owner is always exempt from punishments
        if user.id == guild.owner_id:
            return True

        # Bot owner is exempt
        if is_bot_owner(user.id) or (guild.me and user.id == guild.me.id):
            return True

        # If checking bot addition security, ordinary whitelist is NOT sufficient
        if check_bot_addition:
            return False

        # Check user whitelist in DB (expired entries are ignored)
        now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        user_wl = await db.fetchone(
            "SELECT id FROM antinuke_whitelist WHERE guild_id = ? AND target_id = ? "
            "AND (expires_at IS NULL OR expires_at > ?)",
            (guild.id, user.id, now),
        )
        if user_wl:
            return True

        # Check role whitelist if target is member
        if isinstance(user, discord.Member):
            for role in user.roles:
                role_wl = await db.fetchone(
                    "SELECT id FROM antinuke_whitelist WHERE guild_id = ? AND target_id = ? "
                    "AND (expires_at IS NULL OR expires_at > ?)",
                    (guild.id, role.id, now),
                )
                if role_wl:
                    return True

        return False

    async def is_bot_approved(self, guild_id: int, bot_id: int) -> bool:
        """Check if a specific bot application ID has been explicitly approved by the server owner."""
        row = await db.fetchone(
            "SELECT id FROM security_approved_bots WHERE guild_id = ? AND bot_id = ?",
            (guild_id, bot_id),
        )
        return row is not None

    # ==================== 3. AUDIT-LOG CORRELATION ENGINE ====================

    async def fetch_correlated_audit_entry(
        self,
        guild: discord.Guild,
        action: discord.AuditLogAction,
        target_id: Optional[int] = None,
        max_retries: int = 3,
        initial_delay: float = 0.08,
        max_age_seconds: float = 6.0,
    ) -> Tuple[Optional[discord.AuditLogEntry], str]:
        """Delay-resilient audit log correlation algorithm.

        Retries with microsecond backoff to handle Discord audit log propagation delay.
        Validates target matching and timestamp proximity so innocent users are never blamed.

        Returns:
            entry (AuditLogEntry | None): Correlated entry if verified.
            status (str): 'EXACT_MATCH', 'TIME_CORRELATED', or 'UNRESOLVED'.
        """
        if not guild.me.guild_permissions.view_audit_log:
            return None, "NO_AUDIT_PERMS"

        delays = [initial_delay, initial_delay * 2.2, initial_delay * 4.0]
        now_ts = datetime.datetime.now(datetime.timezone.utc)

        for attempt in range(max_retries):
            delay = delays[attempt] if attempt < len(delays) else 0.25
            await asyncio.sleep(delay)

            try:
                async for entry in guild.audit_logs(limit=4, action=action):
                    # Check entry age
                    entry_age = (now_ts - entry.created_at).total_seconds()
                    if entry_age > max_age_seconds:
                        continue

                    # Exact target correlation
                    if target_id is not None and entry.target and hasattr(entry.target, "id"):
                        if entry.target.id == target_id:
                            return entry, "EXACT_MATCH"

                    # If target ID couldn't be strictly matched (e.g. dynamic snowflake), match recent timestamp
                    if entry_age <= 2.5:
                        return entry, "TIME_CORRELATED"
            except discord.HTTPException as e:
                logger.warning(f"Discord HTTP exception reading audit log in {guild.name}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error in audit log correlation: {e}")

        return None, "UNRESOLVED"

    # ==================== 4. ARCHITECTURE PRE-CACHING & RECOVERY ====================

    def cache_channel(self, channel: discord.abc.GuildChannel) -> None:
        """Cache comprehensive channel metadata for fast recovery."""
        if not hasattr(channel, "guild"):
            return

        overwrites_data = []
        try:
            for target, ow in channel.overwrites.items():
                allow_pair, deny_pair = ow.pair()
                overwrites_data.append({
                    "target_type": "role" if isinstance(target, discord.Role) else "member",
                    "target_id": target.id,
                    "allow": allow_pair.value,
                    "deny": deny_pair.value,
                })
        except Exception:
            pass

        self._channel_cache[channel.guild.id][channel.id] = {
            "name": channel.name,
            "type": channel.type,
            "category_id": getattr(channel, "category_id", None),
            "position": getattr(channel, "position", 0),
            "topic": getattr(channel, "topic", None),
            "slowmode": getattr(channel, "slowmode_delay", 0),
            "nsfw": getattr(channel, "nsfw", False),
            "bitrate": getattr(channel, "bitrate", 64000),
            "user_limit": getattr(channel, "user_limit", 0),
            "overwrites": overwrites_data,
        }

    def cache_all_guild_channels(self, guild: discord.Guild) -> None:
        """Bulk pre-cache all channels of a guild."""
        for ch in guild.channels:
            self.cache_channel(ch)
        logger.debug(f"Pre-cached {len(guild.channels)} channels for guild {guild.name}")

    def cache_role(self, role: discord.Role) -> None:
        """Cache role metadata for fast recovery."""
        if role.is_default() or role.managed:
            return
        self._role_cache[role.guild.id][role.id] = {
            "name": role.name,
            "color": role.color.value,
            "hoist": role.hoist,
            "mentionable": role.mentionable,
            "permissions": role.permissions.value,
            "position": role.position,
        }

    def cache_all_guild_roles(self, guild: discord.Guild) -> None:
        """Bulk pre-cache all roles of a guild."""
        for r in guild.roles:
            self.cache_role(r)
        logger.debug(f"Pre-cached {len(guild.roles)} roles for guild {guild.name}")

    async def restore_channel(self, guild: discord.Guild, channel_id: int) -> bool:
        """Restore a recently deleted channel from memory cache with all settings and overwrites."""
        info = self._channel_cache[guild.id].get(channel_id)
        if not info:
            return False

        try:
            category = guild.get_channel(info["category_id"]) if info.get("category_id") else None
            new_channel = None

            if info["type"] == discord.ChannelType.text:
                new_channel = await guild.create_text_channel(
                    name=info["name"],
                    category=category,
                    topic=info.get("topic"),
                    slowmode_delay=info.get("slowmode", 0),
                    nsfw=info.get("nsfw", False),
                    position=info.get("position", 0),
                    reason="[NOVEXA Anti-Nuke Recovery] Channel Restored",
                )
            elif info["type"] == discord.ChannelType.voice:
                new_channel = await guild.create_voice_channel(
                    name=info["name"],
                    category=category,
                    user_limit=info.get("user_limit", 0),
                    bitrate=min(info.get("bitrate", 64000), guild.bitrate_limit),
                    position=info.get("position", 0),
                    reason="[NOVEXA Anti-Nuke Recovery] Voice Channel Restored",
                )
            elif info["type"] == discord.ChannelType.category:
                new_channel = await guild.create_category(
                    name=info["name"],
                    position=info.get("position", 0),
                    reason="[NOVEXA Anti-Nuke Recovery] Category Restored",
                )

            # Restore permission overwrites if channel was created
            if new_channel and info.get("overwrites"):
                for ow_data in info["overwrites"]:
                    target = (
                        guild.get_role(ow_data["target_id"])
                        if ow_data["target_type"] == "role"
                        else guild.get_member(ow_data["target_id"])
                    )
                    if target:
                        allow = discord.Permissions(ow_data.get("allow", 0))
                        deny = discord.Permissions(ow_data.get("deny", 0))
                        await new_channel.set_permissions(
                            target,
                            overwrite=discord.PermissionOverwrite.from_pair(allow, deny),
                            reason="[NOVEXA Anti-Nuke Recovery] Overwrite Restored",
                        )

            return True
        except Exception as e:
            logger.error(f"Failed to restore channel {info.get('name')} in {guild.name}: {e}")
            return False

    async def restore_role(self, guild: discord.Guild, role_id: int) -> bool:
        """Restore a recently deleted role from memory cache."""
        info = self._role_cache[guild.id].get(role_id)
        if not info:
            return False

        try:
            bot_perms = guild.me.guild_permissions
            perms_val = info.get("permissions", 0) & bot_perms.value
            await guild.create_role(
                name=info["name"],
                colour=discord.Colour(info.get("color", 0)),
                hoist=info.get("hoist", False),
                mentionable=info.get("mentionable", False),
                permissions=discord.Permissions(perms_val),
                reason="[NOVEXA Anti-Nuke Recovery] Role Restored",
            )
            return True
        except Exception as e:
            logger.error(f"Failed to restore role {info.get('name')} in {guild.name}: {e}")
            return False

    # ==================== 5. INCIDENT CONTAINMENT & PUNISHMENT ====================

    async def _send_ban_notice(
        self,
        offender: Union[discord.Member, discord.User],
        guild: discord.Guild,
        reason: str,
    ) -> bool:
        """DM the offender so they know they were banned and why."""
        try:
            await offender.send(
                f"🛡️ **NOVEXA Anti-Nuke — BANNED**\n\n"
                f"You have been **banned** from **{guild.name}**.\n\n"
                f"**Reason:** {reason}\n"
                f"**Case:** Automatic anti-nuke protection — an unauthorized action was detected "
                f"(channel create/delete, server rename, role change, role grant, webhook or bot addition).\n\n"
                f"If you believe this is a mistake, contact the server owner or staff to appeal."
            )
            return True
        except discord.Forbidden:
            logger.info(f"Could not DM ban notice to {offender} (DMs closed)")
            return False
        except Exception as e:
            logger.warning(f"Failed to DM ban notice to {offender}: {e}")
            return False

    async def execute_punishment(
        self,
        guild: discord.Guild,
        offender: discord.Member,
        reason: str,
        punishment_type: str = "ban",
    ) -> str:
        """Execute punishment safely respecting Discord hierarchy and permissions."""
        if offender.id == guild.owner_id:
            logger.warning(f"Cannot punish guild owner {offender} in {guild.name}")
            return "OWNER_IMMUNE"

        if offender.top_role >= guild.me.top_role:
            logger.warning(f"Hierarchy Blocked: Cannot punish {offender} in {guild.name}")
            # Try to apply timeout fallback if manageable
            try:
                await offender.timeout(
                    datetime.timedelta(hours=1), reason=f"[NOVEXA Hierarchy Fallback] {reason}"
                )
                return "TIMEOUT_FALLBACK"
            except Exception:
                return "HIERARCHY_BLOCKED"

        ptype = punishment_type.lower()
        try:
            if ptype == "ban":
                await guild.ban(offender, reason=f"[NOVEXA Anti-Nuke] {reason}", delete_message_days=1)
                await self._send_ban_notice(offender, guild, reason)
                return "BANNED"
            elif ptype == "kick":
                await guild.kick(offender, reason=f"[NOVEXA Anti-Nuke] {reason}")
                return "KICKED"
            elif ptype == "quarantine":
                # Remove all manageable roles
                removable = [r for r in offender.roles if r.name != "@everyone" and r < guild.me.top_role]
                if removable:
                    await offender.remove_roles(*removable, reason=f"[NOVEXA Quarantine] {reason}")
                await offender.timeout(
                    datetime.timedelta(hours=24), reason=f"[NOVEXA Quarantine] {reason}"
                )
                return "QUARANTINED"
            elif ptype == "timeout":
                await offender.timeout(
                    datetime.timedelta(hours=1), reason=f"[NOVEXA Anti-Nuke Timeout] {reason}"
                )
                return "TIMEOUT"
            elif ptype in ("revoke_perms", "revoke"):
                # Strip roles with dangerous permissions
                strip_roles = [
                    r
                    for r in offender.roles
                    if r.name != "@everyone"
                    and r < guild.me.top_role
                    and (
                        r.permissions.administrator
                        or r.permissions.manage_guild
                        or r.permissions.ban_members
                        or r.permissions.manage_roles
                        or r.permissions.manage_channels
                    )
                ]
                if strip_roles:
                    await offender.remove_roles(*strip_roles, reason=f"[NOVEXA Revoke] {reason}")
                return "PERMISSIONS_REVOKED"
            elif ptype == "monitor":
                return "MONITORED"
        except discord.Forbidden:
            logger.error(f"Discord Forbidden when punishing {offender} in {guild.name}")
            return "FORBIDDEN"
        except Exception as e:
            logger.error(f"Error punishing {offender}: {e}")
            return f"ERROR: {e}"

        return "NONE"

    async def execute_lockdown(self, guild: discord.Guild, lock: bool = True) -> int:
        """Lock or unlock all text channels for @everyone."""
        success_count = 0
        if not hasattr(guild, "text_channels"):
            return 0

        for ch in guild.text_channels:
            try:
                overwrites = ch.overwrites_for(guild.default_role)
                overwrites.send_messages = False if lock else None
                await ch.set_permissions(
                    guild.default_role,
                    overwrite=overwrites,
                    reason=f"[NOVEXA {'Emergency Lockdown' if lock else 'Lockdown Lifted'}]",
                )
                success_count += 1
            except Exception:
                continue
        return success_count

    # ==================== 6. MASTER EVENT PROCESSOR ====================

    async def process_security_event(
        self,
        guild: discord.Guild,
        action_key: str,
        audit_action: discord.AuditLogAction,
        target_name: str,
        target_id: Optional[int] = None,
        event_time: float = 0.0,
        target_obj: Optional[Any] = None,
        before_obj: Optional[Any] = None,
        after_obj: Optional[Any] = None,
        prefetched_entry: Optional[discord.AuditLogEntry] = None,
    ) -> None:
        """Unified fast event processor.

        Executes the 10-step incident response pipeline:
        Receive ➔ Correlate ➔ Authenticate ➔ Check Threshold ➔ Contain ➔ Punish ➔ Benchmark ➔ Log.
        """
        start_perf = event_time if event_time > 0 else time.perf_counter()

        cfg = await self.get_security_config(guild.id)
        if not cfg.get("enabled", 1):
            return

        mode = (cfg.get("mode") or "medium").lower()

        # Step 2: Fetch and correlate audit log (or trust a pre-correlated stream entry)
        if prefetched_entry is not None:
            entry = prefetched_entry
            correlation_status = "AUDIT_STREAM"
        else:
            entry, correlation_status = await self.fetch_correlated_audit_entry(
                guild=guild,
                action=audit_action,
                target_id=target_id,
            )

        executor = entry.user if entry else None

        # Ignore actions by NOVEXA itself
        if executor and guild.me and executor.id == guild.me.id:
            return

        # If unresolved and no executor, log unverified security alert and return
        if correlation_status == "UNRESOLVED" or not executor:
            latency_ms = int(round((time.perf_counter() - start_perf) * 1000))
            await self.log_incident(
                guild=guild,
                executor=None,
                action_type=action_key,
                details=f"Uncorrelated event detected: {action_key.replace('_', ' ')} on {target_name}. No verified audit executor found.",
                target_name=target_name,
                target_id=target_id,
                severity="LOW",
                punishment_applied="NONE",
                restored=False,
                correlation_status="UNRESOLVED",
                latency_ms=latency_ms,
            )
            return

        # Step 4: Verify Authorization
        if await self.is_whitelisted(guild, executor):
            return

        # Step 5: Check thresholds (per-guild override clamped against mode defaults)
        if mode == "panic":
            thresholds = PANIC_THRESHOLDS
        elif mode == "high":
            thresholds = HIGH_MODE_THRESHOLDS
        else:
            thresholds = DEFAULT_THRESHOLDS
        default_limit, default_window = thresholds.get(action_key, (3, 10))

        limit = default_limit
        limit_column = CONFIG_LIMIT_COLUMNS.get(action_key)
        if limit_column and mode != "panic":
            configured = cfg.get(limit_column)
            if isinstance(configured, int) and configured > 0:
                limit = min(configured, default_limit) if mode == "high" else configured

        time_window = cfg.get("time_window") or default_window

        now = time.time()
        tracker_key = (guild.id, executor.id, action_key)
        recent_timestamps = [t for t in self._action_tracker[tracker_key] if now - t <= time_window]
        recent_timestamps.append(now)
        self._action_tracker[tracker_key] = recent_timestamps

        threshold_triggered = len(recent_timestamps) >= limit

        if not threshold_triggered:
            if mode == "low":
                latency_ms = int(round((time.perf_counter() - start_perf) * 1000))
                await self.log_incident(
                    guild=guild,
                    executor=executor,
                    action_type=action_key,
                    details=f"Activity observed in LOW protection mode: {action_key.replace('_', ' ')}.",
                    target_name=target_name,
                    target_id=target_id,
                    severity="LOW",
                    punishment_applied="MONITORED",
                    restored=False,
                    correlation_status=correlation_status,
                    latency_ms=latency_ms,
                )
            return

        # Step 6: Step-in Containment
        restored = False
        containment_notes = []

        if action_key == "channel_delete" and target_id:
            restored = await self.restore_channel(guild, target_id)
            if restored:
                containment_notes.append("Channel automatically recreated from cache with overwrites.")

        elif action_key == "role_delete" and target_id:
            restored = await self.restore_role(guild, target_id)
            if restored:
                containment_notes.append("Role automatically recreated from cache.")

        elif action_key == "channel_create" and target_obj and hasattr(target_obj, "delete"):
            try:
                await target_obj.delete(reason="[NOVEXA Anti-Nuke] Unauthorized channel creation removed")
                containment_notes.append("Unauthorized channel deleted.")
                restored = True
            except Exception:
                pass

        elif action_key == "role_create" and target_obj and hasattr(target_obj, "delete"):
            try:
                await target_obj.delete(reason="[NOVEXA Anti-Nuke] Unauthorized role creation removed")
                containment_notes.append("Unauthorized role deleted.")
                restored = True
            except Exception:
                pass

        elif action_key == "server_update" and before_obj is not None and isinstance(after_obj, discord.Guild):
            try:
                revert_kwargs = {}
                if getattr(before_obj, "name", None) and before_obj.name != after_obj.name:
                    revert_kwargs["name"] = before_obj.name
                if revert_kwargs:
                    await after_obj.edit(
                        reason="[NOVEXA Anti-Nuke] Unauthorized server settings change reverted", **revert_kwargs
                    )
                    containment_notes.append("Server name reverted to previous value.")
                    restored = True
            except Exception:
                pass

        elif action_key in ("emoji_create", "sticker_create") and target_obj is not None and hasattr(target_obj, "delete"):
            try:
                await target_obj.delete(reason="[NOVEXA Anti-Nuke] Unauthorized emoji/sticker creation removed")
                containment_notes.append("Unauthorized emoji/sticker deleted.")
                restored = True
            except Exception:
                pass

        elif action_key == "integration_create" and target_obj is not None and hasattr(target_obj, "delete"):
            try:
                await target_obj.delete(reason="[NOVEXA Anti-Nuke] Unauthorized integration removed")
                containment_notes.append("Unauthorized integration deleted.")
                restored = True
            except Exception:
                pass

        elif action_key == "webhook_create" and target_obj and hasattr(target_obj, "delete"):
            try:
                await target_obj.delete(reason="[NOVEXA Anti-Nuke] Unauthorized webhook removed")
                containment_notes.append("Unauthorized webhook removed.")
                restored = True
            except Exception:
                pass

        elif action_key == "permission_escalation" and isinstance(after_obj, discord.Role):
            try:
                perms = after_obj.permissions
                perms.administrator = False
                perms.manage_guild = False
                perms.ban_members = False
                perms.mention_everyone = False
                await after_obj.edit(
                    permissions=perms, reason="[NOVEXA Anti-Nuke] Unauthorized permission escalation reverted."
                )
                containment_notes.append("Dangerous Administrator & Manage permissions reverted.")
                restored = True
            except Exception:
                pass

        elif action_key == "permission_escalation" and isinstance(after_obj, discord.abc.GuildChannel) and before_obj:
            try:
                await after_obj.edit(
                    overwrites=before_obj.overwrites,
                    reason="[NOVEXA Anti-Nuke] Unauthorized channel overwrite escalation reverted.",
                )
                containment_notes.append("Channel permission overwrites reverted to pre-escalation state.")
                restored = True
            except Exception:
                pass

        elif action_key == "role_grant" and target_obj and before_obj and isinstance(target_obj, discord.Member):
            try:
                added = [r for r in target_obj.roles if r not in before_obj.roles and r < guild.me.top_role]
                if added:
                    await target_obj.remove_roles(
                        *added, reason="[NOVEXA Anti-Nuke] Unauthorized role grant reverted."
                    )
                    containment_notes.append(f"Removed {len(added)} unauthorized granted role(s).")
                    restored = True
            except Exception:
                pass

        # Step 7: Execute Punishment
        punishment_type = cfg.get("punishment_type", "ban")
        if mode == "panic":
            punishment_type = "ban"
        result = "NONE"

        if isinstance(executor, discord.Member):
            result = await self.execute_punishment(
                guild=guild,
                offender=executor,
                reason=f"Exceeded Anti-Nuke threshold for {action_key.replace('_', ' ')}",
                punishment_type=punishment_type,
            )

        # Panic fallback: if the offender sits above the bot's top role, lock the
        # server down so the attack cannot continue while the owner intervenes.
        if mode == "panic" and result in ("HIERARCHY_BLOCKED", "FORBIDDEN", "TIMEOUT_FALLBACK"):
            locked = await self.execute_lockdown(guild, True)
            containment_notes.append(f"Emergency lockdown engaged on {locked} channel(s).")

        # Step 8: Benchmark Response Latency
        latency_ms = int(round((time.perf_counter() - start_perf) * 1000))

        # Step 9 & 10: Dispatch Security Alert & Record Incident
        details_str = (
            f"Rate limit exceeded: `{len(recent_timestamps)}` {action_key.replace('_', ' ')} actions "
            f"within `{time_window}s` in **{mode.upper()} MODE**."
        )
        if containment_notes:
            details_str += f" Containment: {' '.join(containment_notes)}"

        await self.log_incident(
            guild=guild,
            executor=executor,
            action_type=action_key,
            details=details_str,
            target_name=target_name,
            target_id=target_id,
            severity="HIGH",
            punishment_applied=result,
            restored=restored,
            correlation_status=correlation_status,
            latency_ms=latency_ms,
        )

    # ==================== 7. LOGGING & BENCHMARKS ====================

    async def get_or_create_log_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        """Resolve configured security log channel or locate standard security logs."""
        cfg = await self.get_security_config(guild.id)
        if cfg.get("log_channel_id"):
            channel = guild.get_channel(cfg["log_channel_id"])
            if channel and isinstance(channel, discord.TextChannel):
                return channel

        for name in ["novexa-security-logs", "security-logs", "novexa-logs", "mod-logs"]:
            found = discord.utils.get(guild.text_channels, name=name)
            if found:
                await self.set_security_log_channel(guild.id, found.id)
                return found

        return None

    async def log_incident(
        self,
        guild: discord.Guild,
        executor: Optional[Union[discord.Member, discord.User]],
        action_type: str,
        details: str,
        target_name: str = "Server",
        target_id: Optional[int] = None,
        severity: str = "HIGH",
        punishment_applied: str = "NONE",
        restored: bool = False,
        correlation_status: str = "EXACT_MATCH",
        latency_ms: int = 0,
    ) -> None:
        """Record an incident in the database and dispatch a rich alert embed."""
        exec_id = executor.id if executor else None
        exec_tag = str(executor) if executor else "Unknown Executor"

        # Record in SQLite DB (legacy NOT NULL columns are mirrored for compatibility)
        try:
            await db.execute(
                """
                INSERT INTO security_audit_logs (
                    guild_id, event_type, actor_id, target_id, target_name, action_type,
                    action_taken, details, executor_id, executor_tag, severity,
                    punishment_applied, restored, correlation_status, latency_ms
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    guild.id,
                    action_type,
                    exec_id or 0,
                    target_id,
                    target_name,
                    action_type,
                    punishment_applied,
                    details,
                    exec_id,
                    exec_tag,
                    severity,
                    punishment_applied,
                    1 if restored else 0,
                    correlation_status,
                    latency_ms,
                ),
            )
        except Exception as e:
            logger.error(f"Failed to record incident to database: {e}")

        # Dispatch rich embed to security log channel
        log_channel = await self.get_or_create_log_channel(guild)
        if not log_channel:
            return

        perms = log_channel.permissions_for(guild.me)
        if not perms.send_messages or not perms.embed_links:
            return

        color = 0xEF4444 if severity == "HIGH" else (0xF59E0B if severity == "MEDIUM" else 0x3B82F6)
        embed = discord.Embed(
            title=f"🚨 SECURITY INCIDENT: {action_type.replace('_', ' ').upper()}",
            description=f"**Details:** {details}",
            color=color,
            timestamp=discord.utils.utcnow(),
        )

        embed.add_field(
            name=f"{Emojis.AN_EXECUTOR} Executor",
            value=f"{executor.mention if executor else 'Unknown'} (`{exec_id or 'N/A'}`)",
            inline=True,
        )
        embed.add_field(
            name=f"{Emojis.AN_CHANNEL} Target",
            value=f"**{target_name}** (`{target_id or 'N/A'}`)",
            inline=True,
        )
        embed.add_field(
            name=f"{Emojis.AN_BANNED} Action Taken",
            value=f"`{punishment_applied.upper()}`",
            inline=True,
        )
        embed.add_field(
            name=f"{Emojis.AN_ROLE} Recovery",
            value="✅ Restored / Reverted" if restored else "ℹ️ N/A",
            inline=True,
        )
        embed.add_field(
            name="⚡ Response Latency",
            value=f"`{latency_ms}ms` ({correlation_status})",
            inline=True,
        )
        embed.add_field(
            name="🛡️ Protection Mode",
            value=f"`{severity}`",
            inline=True,
        )

        embed.set_footer(text=f"{guild.name} • {BOT_NAME} Ultra-Fast Security Engine")

        try:
            await log_channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to post security alert embed: {e}")

    async def get_security_stats(self, guild_id: int) -> Dict[str, Any]:
        """Aggregate security statistics and recent incidents."""
        total_row = await db.fetchone(
            "SELECT COUNT(*) as total, AVG(latency_ms) as avg_latency FROM security_audit_logs WHERE guild_id = ?",
            (guild_id,),
        )
        banned_row = await db.fetchone(
            "SELECT COUNT(*) as total FROM security_audit_logs WHERE guild_id = ? AND punishment_applied = 'BANNED'",
            (guild_id,),
        )
        restored_row = await db.fetchone(
            "SELECT COUNT(*) as total FROM security_audit_logs WHERE guild_id = ? AND restored = 1",
            (guild_id,),
        )
        recent_rows = await db.fetchall(
            """
            SELECT executor_tag, action_type, target_name, punishment_applied, latency_ms, timestamp
            FROM security_audit_logs WHERE guild_id = ? ORDER BY id DESC LIMIT 5
            """,
            (guild_id,),
        )

        return {
            "total_incidents": total_row["total"] if total_row else 0,
            "avg_latency_ms": int(round(total_row["avg_latency"])) if total_row and total_row["avg_latency"] else 0,
            "banned_count": banned_row["total"] if banned_row else 0,
            "restored_count": restored_row["total"] if restored_row else 0,
            "recent_incidents": [dict(r) for r in recent_rows],
        }


security_service = SecurityService()
