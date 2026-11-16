"""NOVEXA - Authoritative Two-Way Configuration Service.

Shared singleton providing atomic configuration read/writes for both:
1. Discord Bot Slash Commands
2. Official Web Dashboard REST APIs

Features:
- Single source of truth via SQLite transactions
- Configuration change audit trail logging (config_audit_logs)
- In-memory event dispatching for Server-Sent Events (SSE) real-time streaming
- Cog cache invalidation notifications
"""

import logging
import json
import asyncio
from typing import Dict, Any, List, Optional, Set
from database.database import db

logger = logging.getLogger("novexa.config_service")


class ConfigEventBroadcaster:
    """Pub-Sub broadcaster delivering real-time SSE events to connected web browsers."""

    def __init__(self):
        # guild_id -> Set of asyncio.Queue
        self._listeners: Dict[int, Set[asyncio.Queue]] = {}

    def subscribe(self, guild_id: int) -> asyncio.Queue:
        queue = asyncio.Queue(maxsize=100)
        if guild_id not in self._listeners:
            self._listeners[guild_id] = set()
        self._listeners[guild_id].add(queue)
        logger.debug(f"Subscribed SSE client to guild {guild_id} (active: {len(self._listeners[guild_id])})")
        return queue

    def unsubscribe(self, guild_id: int, queue: asyncio.Queue):
        if guild_id in self._listeners and queue in self._listeners[guild_id]:
            self._listeners[guild_id].remove(queue)
            if not self._listeners[guild_id]:
                del self._listeners[guild_id]
        logger.debug(f"Unsubscribed SSE client from guild {guild_id}")

    async def broadcast(self, guild_id: int, event_type: str, data: Dict[str, Any]):
        """Dispatch real-time event to all active dashboard sessions for this guild."""
        if guild_id not in self._listeners:
            return
        payload = {
            "event": event_type,
            "guild_id": guild_id,
            "data": data,
        }
        dead_queues = set()
        for queue in self._listeners[guild_id]:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                dead_queues.add(queue)
            except Exception:
                dead_queues.add(queue)
        for q in dead_queues:
            self.unsubscribe(guild_id, q)


class ConfigService:
    """Authoritative Configuration Management Service for NOVEXA."""

    def __init__(self, bot=None):
        self.bot = bot
        self.broadcaster = ConfigEventBroadcaster()

    def set_bot(self, bot):
        self.bot = bot

    async def _log_audit(
        self,
        guild_id: int,
        module: str,
        setting_key: str,
        old_val: Any,
        new_val: Any,
        actor_id: Optional[int] = None,
        actor_tag: Optional[str] = None,
        source: str = "WEBSITE",
    ):
        """Record configuration update in config_audit_logs."""
        try:
            query = """
            INSERT INTO config_audit_logs (guild_id, actor_id, actor_tag, source, module, setting_key, old_value, new_value)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """
            await db.execute(
                query,
                (
                    guild_id,
                    actor_id,
                    actor_tag or "Authorized User",
                    source,
                    module,
                    setting_key,
                    str(old_val) if old_val is not None else "",
                    str(new_val) if new_val is not None else "",
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to write config audit log: {e}")

    # ==================== 1. OVERVIEW & GUILD STATS ====================
    async def get_overview(self, guild_id: int) -> Dict[str, Any]:
        """Aggregate high-level status across all modules for a guild."""
        welcome = await self.get_welcome_config(guild_id)
        antinuke = await self.get_antinuke_config(guild_id)
        antispam = await self.get_antispam_config(guild_id)
        premium = await self.get_premium_status(guild_id)

        guild_obj = self.bot.get_guild(guild_id) if self.bot else None

        return {
            "guild_id": guild_id,
            "name": guild_obj.name if guild_obj else f"Guild {guild_id}",
            "member_count": guild_obj.member_count if guild_obj else 0,
            "icon_url": str(guild_obj.icon.url) if (guild_obj and guild_obj.icon) else None,
            "welcome_enabled": bool(welcome.get("enabled", True)),
            "antinuke_enabled": bool(antinuke.get("enabled", True)),
            "antinuke_mode": antinuke.get("mode", "medium"),
            "antispam_enabled": bool(antispam.get("enabled", True)),
            "premium_tier": premium.get("plan_id", "free"),
            "is_premium": premium.get("is_premium", False),
        }

    # ==================== 2. WELCOME & GOODBYE ====================
    async def get_welcome_config(self, guild_id: int) -> Dict[str, Any]:
        query = "SELECT * FROM welcome_config WHERE guild_id = ?;"
        row = await db.fetchone(query, (guild_id,))
        if not row:
            return {
                "guild_id": guild_id,
                "enabled": True,
                "channel_id": None,
                "template_id": "novexa_exclusive",
                "banner_enabled": True,
                "embed_enabled": True,
                "title": "Welcome to {server}!",
                "message_template": "Hey {user}, welcome to **{server}**! You are member #{member_count}.",
                "custom_color": "#5865F2",
                "dm_enabled": False,
                "dm_template": "Welcome to **{server}**, {user}! Read our rules to get started.",
                "autorole_enabled": False,
                "autorole_id": None,
                "goodbye_enabled": True,
                "leave_channel_id": None,
                "goodbye_template_id": "minimal_dark",
                "leave_embed_enabled": True,
                "leave_message_template": "**{username}** has left {server}. We now have {member_count} members.",
            }
        d = dict(row)
        d["enabled"] = bool(d.get("banner_enabled", 1) or d.get("embed_enabled", 1))
        return d

    async def update_welcome_config(
        self,
        guild_id: int,
        updates: Dict[str, Any],
        actor_id: Optional[int] = None,
        actor_tag: Optional[str] = None,
        source: str = "WEBSITE",
    ) -> Dict[str, Any]:
        current = await self.get_welcome_config(guild_id)

        # Ensure record exists
        await db.execute("INSERT OR IGNORE INTO welcome_config (guild_id) VALUES (?);", (guild_id,))

        allowed = [
            "channel_id", "template_id", "banner_enabled", "embed_enabled",
            "title", "message_template", "custom_color", "dm_enabled", "dm_template",
            "autorole_enabled", "autorole_id", "goodbye_enabled", "leave_channel_id",
            "goodbye_template_id", "leave_embed_enabled", "leave_message_template"
        ]

        clauses = []
        params = []
        for k in allowed:
            if k in updates:
                new_v = updates[k]
                old_v = current.get(k)
                if new_v != old_v:
                    clauses.append(f"{k} = ?")
                    # boolean conversion
                    if isinstance(new_v, bool):
                        params.append(1 if new_v else 0)
                    else:
                        params.append(new_v)
                    await self._log_audit(guild_id, "welcome", k, old_v, new_v, actor_id, actor_tag, source)

        if clauses:
            params.append(guild_id)
            query = f"UPDATE welcome_config SET {', '.join(clauses)} WHERE guild_id = ?;"
            await db.execute(query, tuple(params))
        await self.broadcaster.broadcast(guild_id, "welcome_updated", updates)

        return await self.get_welcome_config(guild_id)

    # ==================== 3. ANTI-NUKE ====================
    async def get_antinuke_config(self, guild_id: int) -> Dict[str, Any]:
        query = "SELECT * FROM antinuke_config WHERE guild_id = ?;"
        row = await db.fetchone(query, (guild_id,))
        if not row:
            return {
                "guild_id": guild_id,
                "enabled": True,
                "mode": "medium",
                "punishment_type": "quarantine",
                "max_channel_deletions": 2,
                "max_channel_creations": 3,
                "max_role_deletions": 3,
                "max_role_creations": 3,
                "max_webhook_changes": 4,
                "max_bans": 3,
                "max_kicks": 4,
                "max_permission_changes": 3,
                "log_channel_id": None,
                "bot_protection_enabled": True,
            }
        d = dict(row)
        d["enabled"] = bool(d.get("enabled", 1))
        d["bot_protection_enabled"] = bool(d.get("bot_protection_enabled", 1))
        return d

    async def update_antinuke_config(
        self,
        guild_id: int,
        updates: Dict[str, Any],
        actor_id: Optional[int] = None,
        actor_tag: Optional[str] = None,
        source: str = "WEBSITE",
    ) -> Dict[str, Any]:
        current = await self.get_antinuke_config(guild_id)
        await db.execute("INSERT OR IGNORE INTO antinuke_config (guild_id) VALUES (?);", (guild_id,))

        allowed = [
            "enabled", "mode", "punishment_type", "max_channel_deletions",
            "max_channel_creations", "max_role_deletions", "max_role_creations",
            "max_webhook_changes", "max_bans", "max_kicks", "max_permission_changes",
            "log_channel_id", "bot_protection_enabled"
        ]

        clauses = []
        params = []
        for k in allowed:
            if k in updates:
                new_v = updates[k]
                old_v = current.get(k)
                if new_v != old_v:
                    clauses.append(f"{k} = ?")
                    params.append(1 if new_v is True else (0 if new_v is False else new_v))
                    await self._log_audit(guild_id, "antinuke", k, old_v, new_v, actor_id, actor_tag, source)

        if clauses:
            params.append(guild_id)
            query = f"UPDATE antinuke_config SET {', '.join(clauses)} WHERE guild_id = ?;"
            await db.execute(query, tuple(params))
        await self.broadcaster.broadcast(guild_id, "antinuke_updated", updates)

        return await self.get_antinuke_config(guild_id)

    # ==================== 4. ANTI-SPAM & AUTOMOD ====================
    async def get_antispam_config(self, guild_id: int) -> Dict[str, Any]:
        query = "SELECT * FROM antispam_config WHERE guild_id = ?;"
        row = await db.fetchone(query, (guild_id,))
        if not row:
            return {
                "guild_id": guild_id,
                "enabled": True,
                "max_mentions": 5,
                "max_emojis": 8,
                "max_duplicates": 3,
                "block_invites": True,
                "block_links": True,
                "timeout_duration_minutes": 10,
                "caps_filter_enabled": False,
                "blocked_words": "",
                "attachment_spam_limit": 5,
                "automod_action": "warn",
            }
        d = dict(row)
        d["enabled"] = bool(d.get("enabled", 1))
        d["block_invites"] = bool(d.get("block_invites", 1))
        d["block_links"] = bool(d.get("block_links", 1))
        d["max_duplicates"] = d.get("max_messages_per_window", 3)
        return d

    async def update_antispam_config(
        self,
        guild_id: int,
        updates: Dict[str, Any],
        actor_id: Optional[int] = None,
        actor_tag: Optional[str] = None,
        source: str = "WEBSITE",
    ) -> Dict[str, Any]:
        current = await self.get_antispam_config(guild_id)
        await db.execute("INSERT OR IGNORE INTO antispam_config (guild_id) VALUES (?);", (guild_id,))

        key_mapping = {
            "max_duplicates": "max_messages_per_window"
        }

        clauses = []
        params = []
        for k, v in updates.items():
            db_col = key_mapping.get(k, k)
            if db_col in [
                "enabled", "max_mentions", "max_emojis", "max_messages_per_window",
                "time_window", "block_invites", "block_links", "timeout_duration_minutes",
                "caps_filter_enabled", "blocked_words", "attachment_spam_limit", "automod_action"
            ]:
                old_v = current.get(k)
                if v != old_v:
                    clauses.append(f"{db_col} = ?")
                    params.append(1 if v is True else (0 if v is False else v))
                    await self._log_audit(guild_id, "antispam", k, old_v, v, actor_id, actor_tag, source)

        if clauses:
            params.append(guild_id)
            query = f"UPDATE antispam_config SET {', '.join(clauses)} WHERE guild_id = ?;"
            await db.execute(query, tuple(params))
            await self.broadcaster.broadcast(guild_id, "antispam_updated", updates)

        return await self.get_antispam_config(guild_id)

    # ==================== 5. WHITELIST & APPROVED BOTS ====================
    async def get_whitelist(self, guild_id: int) -> List[Dict[str, Any]]:
        query = "SELECT * FROM antinuke_whitelist WHERE guild_id = ? ORDER BY added_at DESC;"
        rows = await db.fetchall(query, (guild_id,))
        return [dict(r) for r in rows]

    async def add_whitelist(self, guild_id: int, target_id: int, target_type: str, actor_id: int, actor_tag: str, source: str = "WEBSITE"):
        query = "INSERT OR IGNORE INTO antinuke_whitelist (guild_id, target_id, target_type, added_by) VALUES (?, ?, ?, ?);"
        await db.execute(query, (guild_id, target_id, target_type, actor_id))
        await self._log_audit(guild_id, "whitelist", "add", "", f"{target_type}:{target_id}", actor_id, actor_tag, source)
        await self.broadcaster.broadcast(guild_id, "whitelist_updated", {"action": "add", "target_id": target_id})

    async def remove_whitelist(self, guild_id: int, target_id: int, actor_id: int, actor_tag: str, source: str = "WEBSITE"):
        query = "DELETE FROM antinuke_whitelist WHERE guild_id = ? AND target_id = ?;"
        await db.execute(query, (guild_id, target_id))
        await self._log_audit(guild_id, "whitelist", "remove", f"{target_id}", "", actor_id, actor_tag, source)
        await self.broadcaster.broadcast(guild_id, "whitelist_updated", {"action": "remove", "target_id": target_id})

    async def get_approved_bots(self, guild_id: int) -> List[Dict[str, Any]]:
        query = "SELECT * FROM security_approved_bots WHERE guild_id = ? ORDER BY approved_at DESC;"
        rows = await db.fetchall(query, (guild_id,))
        return [dict(r) for r in rows]

    async def approve_bot(self, guild_id: int, bot_id: int, bot_name: str, actor_id: int, actor_tag: str, source: str = "WEBSITE"):
        query = "INSERT OR REPLACE INTO security_approved_bots (guild_id, bot_id, bot_name, approved_by) VALUES (?, ?, ?, ?);"
        await db.execute(query, (guild_id, bot_id, bot_name, actor_id))
        await self._log_audit(guild_id, "approved_bots", "approve", "", f"{bot_name} ({bot_id})", actor_id, actor_tag, source)
        await self.broadcaster.broadcast(guild_id, "approved_bots_updated", {"action": "approve", "bot_id": bot_id})

    async def revoke_bot(self, guild_id: int, bot_id: int, actor_id: int, actor_tag: str, source: str = "WEBSITE"):
        query = "DELETE FROM security_approved_bots WHERE guild_id = ? AND bot_id = ?;"
        await db.execute(query, (guild_id, bot_id))
        await self._log_audit(guild_id, "approved_bots", "revoke", f"{bot_id}", "", actor_id, actor_tag, source)
        await self.broadcaster.broadcast(guild_id, "approved_bots_updated", {"action": "revoke", "bot_id": bot_id})

    # ==================== 5B. WALLPAPER STUDIO ====================
    async def get_wallpaper_channels(self, guild_id: int) -> List[Dict[str, Any]]:
        query = "SELECT channel_id, created_by, created_at FROM wallpaper_channels WHERE guild_id = ? ORDER BY created_at DESC;"
        rows = await db.fetchall(query, (guild_id,))
        return [dict(r) for r in rows]

    async def add_wallpaper_channel(self, guild_id: int, channel_id: int, actor_id: int, actor_tag: str, source: str = "WEBSITE"):
        await db.execute(
            "INSERT INTO wallpaper_channels (guild_id, channel_id, created_by) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, channel_id) DO NOTHING",
            (guild_id, channel_id, actor_id),
        )
        await self._log_audit(guild_id, "wallpaper", "add_channel", "", str(channel_id), actor_id, actor_tag, source)
        await self.broadcaster.broadcast(guild_id, "wallpaper_updated", {"action": "add", "channel_id": channel_id})

    async def remove_wallpaper_channel(self, guild_id: int, channel_id: int, actor_id: int, actor_tag: str, source: str = "WEBSITE"):
        await db.execute(
            "DELETE FROM wallpaper_channels WHERE guild_id = ? AND channel_id = ?",
            (guild_id, channel_id),
        )
        await self._log_audit(guild_id, "wallpaper", "remove_channel", str(channel_id), "", actor_id, actor_tag, source)
        await self.broadcaster.broadcast(guild_id, "wallpaper_updated", {"action": "remove", "channel_id": channel_id})

    # ==================== 5C. DROPPER SUITE ====================
    async def get_dropper_members(self, guild_id: int) -> List[Dict[str, Any]]:
        query = "SELECT user_id, added_by, added_at FROM server_droppers WHERE guild_id = ? ORDER BY added_at DESC;"
        rows = await db.fetchall(query, (guild_id,))
        return [dict(r) for r in rows]

    async def add_dropper_member(self, guild_id: int, user_id: int, actor_id: int, actor_tag: str, source: str = "WEBSITE"):
        await db.execute(
            "INSERT INTO server_droppers (guild_id, user_id, added_by) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET added_by = excluded.added_by",
            (guild_id, user_id, actor_id),
        )
        await self._log_audit(guild_id, "dropper", "grant", "", str(user_id), actor_id, actor_tag, source)
        await self.broadcaster.broadcast(guild_id, "dropper_updated", {"action": "grant", "user_id": user_id})

    async def remove_dropper_member(self, guild_id: int, user_id: int, actor_id: int, actor_tag: str, source: str = "WEBSITE"):
        await db.execute(
            "DELETE FROM server_droppers WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        await self._log_audit(guild_id, "dropper", "revoke", str(user_id), "", actor_id, actor_tag, source)
        await self.broadcaster.broadcast(guild_id, "dropper_updated", {"action": "revoke", "user_id": user_id})

    # ==================== 8. MUSIC CONFIG ====================
    async def get_music_config(self, guild_id: int) -> Dict[str, Any]:
        row = await db.fetchone("SELECT * FROM music_config WHERE guild_id = ?;", (guild_id,))
        if not row:
            return {
                "guild_id": guild_id,
                "is_247": False,
                "voice_channel_id": None,
                "text_channel_id": None,
                "default_volume": 100,
            }
        d = dict(row)
        d["is_247"] = bool(d.get("is_247", 0))
        d["default_volume"] = 100
        return d

    async def update_music_config(
        self,
        guild_id: int,
        updates: Dict[str, Any],
        actor_id: Optional[int] = None,
        actor_tag: Optional[str] = None,
        source: str = "WEBSITE",
    ) -> Dict[str, Any]:
        await db.execute("INSERT OR IGNORE INTO music_config (guild_id) VALUES (?);", (guild_id,))
        clauses, params = [], []
        for k in ["is_247", "voice_channel_id", "text_channel_id"]:
            if k in updates:
                clauses.append(f"{k} = ?")
                params.append(1 if updates[k] is True else (0 if updates[k] is False else updates[k]))
                await self._log_audit(guild_id, "music", k, "", updates[k], actor_id, actor_tag, source)
        if clauses:
            params.append(guild_id)
            await db.execute(f"UPDATE music_config SET {', '.join(clauses)} WHERE guild_id = ?;", tuple(params))
            await self.broadcaster.broadcast(guild_id, "music_updated", updates)
        return await self.get_music_config(guild_id)

    # ==================== 9. ECONOMY & GAMES ====================
    async def get_economy_settings(self, guild_id: int) -> Dict[str, Any]:
        row = await db.fetchone("SELECT * FROM economy_guild_settings WHERE guild_id = ?;", (guild_id,))
        if not row:
            return {
                "guild_id": guild_id,
                "is_enabled": True,
                "currency_name": "NOVEXA COINS",
                "currency_symbol": "🪙",
                "daily_reward": 1000,
                "streak_bonus_per_day": 25,
                "work_cooldown": 300,
                "crime_cooldown": 600,
                "games_enabled": True,
                "crime_success_rate": 65,
                "max_bet_amount": 50000,
                "hunt_cooldown": 15,
                "mythical_drop_rate": 1,
                "pet_adoption_enabled": True,
            }
        d = dict(row)
        d["is_enabled"] = bool(d.get("is_enabled", 1))
        d["games_enabled"] = True
        d["crime_success_rate"] = 65
        d["max_bet_amount"] = 50000
        d["hunt_cooldown"] = 15
        d["mythical_drop_rate"] = 1
        d["pet_adoption_enabled"] = True
        return d

    async def update_economy_settings(
        self,
        guild_id: int,
        updates: Dict[str, Any],
        actor_id: Optional[int] = None,
        actor_tag: Optional[str] = None,
        source: str = "WEBSITE",
    ) -> Dict[str, Any]:
        await db.execute("INSERT OR IGNORE INTO economy_guild_settings (guild_id) VALUES (?);", (guild_id,))
        allowed = ["is_enabled", "currency_name", "currency_symbol", "daily_reward", "streak_bonus_per_day", "work_cooldown", "crime_cooldown"]
        clauses, params = [], []
        for k in allowed:
            if k in updates:
                clauses.append(f"{k} = ?")
                params.append(1 if updates[k] is True else (0 if updates[k] is False else updates[k]))
                await self._log_audit(guild_id, "economy", k, "", updates[k], actor_id, actor_tag, source)
        if clauses:
            params.append(guild_id)
            await db.execute(f"UPDATE economy_guild_settings SET {', '.join(clauses)} WHERE guild_id = ?;", tuple(params))
            await self.broadcaster.broadcast(guild_id, "economy_updated", updates)
        return await self.get_economy_settings(guild_id)

    # ==================== 10. PREMIUM SUBSCRIPTIONS ====================
    async def get_premium_status(self, guild_id: int) -> Dict[str, Any]:
        query = """
        SELECT ps.*, pp.name as plan_name, pp.tier_level, pp.price_inr, pp.max_backups, pp.max_ai_daily, pp.perks_json
        FROM premium_subscriptions ps
        JOIN premium_plans pp ON ps.plan_id = pp.plan_id
        WHERE ps.guild_id = ? AND ps.status = 'ACTIVE' AND ps.expires_at > CURRENT_TIMESTAMP
        ORDER BY pp.tier_level DESC LIMIT 1;
        """
        row = await db.fetchone(query, (guild_id,))
        if not row:
            return {
                "guild_id": guild_id,
                "is_premium": False,
                "plan_id": "free",
                "plan_name": "Standard Free Tier",
                "tier_level": 0,
                "max_backups": 3,
                "max_ai_daily": 30,
            }
        d = dict(row)
        d["is_premium"] = True
        return d

    async def get_premium_plans(self) -> List[Dict[str, Any]]:
        rows = await db.fetchall("SELECT * FROM premium_plans ORDER BY tier_level ASC;")
        plans = []
        for r in rows:
            d = dict(r)
            try:
                d["perks"] = json.loads(d.get("perks_json", "[]"))
            except Exception:
                d["perks"] = []
            plans.append(d)
        return plans

    # ==================== 11. AUDIT HISTORY ====================
    async def get_audit_history(self, guild_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        query = "SELECT * FROM config_audit_logs WHERE guild_id = ? ORDER BY timestamp DESC LIMIT ?;"
        rows = await db.fetchall(query, (guild_id, limit))
        return [dict(r) for r in rows]


    # ==================== 12. GOODBYE CONFIG ====================
    async def get_goodbye_config(self, guild_id: int) -> Dict[str, Any]:
        row = await db.fetchone("SELECT goodbye_enabled, leave_channel_id, goodbye_template_id, leave_embed_enabled, leave_message_template FROM welcome_config WHERE guild_id = ?;", (guild_id,))
        if not row:
            return {
                "goodbye_enabled": True,
                "leave_channel_id": None,
                "goodbye_template_id": "minimal_dark",
                "leave_embed_enabled": True,
                "leave_message_template": "**{username}** has left {server}. We now have {member_count} members.",
            }
        d = dict(row)
        d["goodbye_enabled"] = bool(d.get("goodbye_enabled", 1))
        d["leave_embed_enabled"] = bool(d.get("leave_embed_enabled", 1))
        d["goodbye_template_id"] = d.get("goodbye_template_id") or "minimal_dark"
        d["leave_message_template"] = d.get("leave_message_template") or "**{username}** has left {server}. We now have {member_count} members."
        return d

    async def update_goodbye_config(self, guild_id: int, updates: Dict[str, Any], actor_id: Optional[int] = None, actor_tag: Optional[str] = None, source: str = "WEBSITE") -> Dict[str, Any]:
        await db.execute("INSERT OR IGNORE INTO welcome_config (guild_id) VALUES (?);", (guild_id,))
        allowed = ["goodbye_enabled", "leave_channel_id", "goodbye_template_id", "leave_embed_enabled", "leave_message_template"]
        clauses, params = [], []
        for k in allowed:
            if k in updates:
                clauses.append(f"{k} = ?")
                params.append(1 if updates[k] is True else (0 if updates[k] is False else updates[k]))
                await self._log_audit(guild_id, "goodbye", k, "", updates[k], actor_id, actor_tag, source)
        if clauses:
            params.append(guild_id)
            await db.execute(f"UPDATE welcome_config SET {', '.join(clauses)} WHERE guild_id = ?;", tuple(params))
        await self.broadcaster.broadcast(guild_id, "goodbye_updated", updates)
        return await self.get_goodbye_config(guild_id)

    # ==================== 13. AUTOROLES CONFIG ====================
    async def get_autoroles_config(self, guild_id: int) -> Dict[str, Any]:
        row = await db.fetchone("SELECT autorole_enabled, autorole_id FROM welcome_config WHERE guild_id = ?;", (guild_id,))
        d = dict(row) if row else {"autorole_enabled": False, "autorole_id": None}
        d["autorole_enabled"] = bool(d.get("autorole_enabled", 0))
        # Also fetch list of auto_roles
        ar_rows = await db.fetchall("SELECT role_id FROM auto_roles WHERE guild_id = ?;", (guild_id,))
        d["role_ids"] = [r["role_id"] for r in ar_rows]
        return d

    async def update_autoroles_config(self, guild_id: int, updates: Dict[str, Any], actor_id: Optional[int] = None, actor_tag: Optional[str] = None, source: str = "WEBSITE") -> Dict[str, Any]:
        await db.execute("INSERT OR IGNORE INTO welcome_config (guild_id) VALUES (?);", (guild_id,))
        if "autorole_id" in updates or "autorole_enabled" in updates:
            rid = updates.get("autorole_id")
            en = 1 if updates.get("autorole_enabled", True) else 0
            await db.execute("UPDATE welcome_config SET autorole_enabled = ?, autorole_id = ? WHERE guild_id = ?;", (en, rid, guild_id))
            if rid:
                await db.execute("INSERT OR IGNORE INTO auto_roles (guild_id, role_id) VALUES (?, ?);", (guild_id, rid))
            await self._log_audit(guild_id, "autoroles", "autorole_id", "", rid, actor_id, actor_tag, source)
        await self.broadcaster.broadcast(guild_id, "autoroles_updated", updates)
        return await self.get_autoroles_config(guild_id)

    # ==================== 14. AUTOMOD CONFIG ====================
    async def get_automod_config(self, guild_id: int) -> Dict[str, Any]:
        row = await db.fetchone("SELECT caps_filter_enabled, blocked_words, attachment_spam_limit, automod_action FROM antispam_config WHERE guild_id = ?;", (guild_id,))
        if not row:
            return {
                "caps_filter_enabled": False,
                "blocked_words": "",
                "attachment_spam_limit": 5,
                "automod_action": "warn",
            }
        d = dict(row)
        d["caps_filter_enabled"] = bool(d.get("caps_filter_enabled", 0))
        return d

    async def update_automod_config(self, guild_id: int, updates: Dict[str, Any], actor_id: Optional[int] = None, actor_tag: Optional[str] = None, source: str = "WEBSITE") -> Dict[str, Any]:
        await db.execute("INSERT OR IGNORE INTO antispam_config (guild_id) VALUES (?);", (guild_id,))
        allowed = ["caps_filter_enabled", "blocked_words", "attachment_spam_limit", "automod_action"]
        clauses, params = [], []
        for k in allowed:
            if k in updates:
                clauses.append(f"{k} = ?")
                params.append(1 if updates[k] is True else (0 if updates[k] is False else updates[k]))
                await self._log_audit(guild_id, "automod", k, "", updates[k], actor_id, actor_tag, source)
        if clauses:
            params.append(guild_id)
            await db.execute(f"UPDATE antispam_config SET {', '.join(clauses)} WHERE guild_id = ?;", tuple(params))
        await self.broadcaster.broadcast(guild_id, "automod_updated", updates)
        return await self.get_automod_config(guild_id)

    # ==================== 15. MODERATION CONFIG & LOGS ====================
    async def get_moderation_config(self, guild_id: int) -> Dict[str, Any]:
        row = await db.fetchone("SELECT mod_log_channel_id, dm_on_punish, max_warnings_kick, max_warnings_ban FROM guild_settings WHERE guild_id = ?;", (guild_id,))
        if not row:
            return {
                "mod_log_channel_id": None,
                "dm_on_punish": True,
                "max_warnings_kick": 3,
                "max_warnings_ban": 5,
            }
        d = dict(row)
        d["dm_on_punish"] = bool(d.get("dm_on_punish", 1))
        return d

    async def update_moderation_config(self, guild_id: int, updates: Dict[str, Any], actor_id: Optional[int] = None, actor_tag: Optional[str] = None, source: str = "WEBSITE") -> Dict[str, Any]:
        await db.execute("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?);", (guild_id,))
        allowed = ["mod_log_channel_id", "dm_on_punish", "max_warnings_kick", "max_warnings_ban"]
        clauses, params = [], []
        for k in allowed:
            if k in updates:
                clauses.append(f"{k} = ?")
                params.append(1 if updates[k] is True else (0 if updates[k] is False else updates[k]))
                await self._log_audit(guild_id, "moderation", k, "", updates[k], actor_id, actor_tag, source)
        if clauses:
            params.append(guild_id)
            await db.execute(f"UPDATE guild_settings SET {', '.join(clauses)} WHERE guild_id = ?;", tuple(params))
        await self.broadcaster.broadcast(guild_id, "moderation_updated", updates)
        return await self.get_moderation_config(guild_id)

    async def get_moderation_logs(self, guild_id: int, limit: int = 15) -> List[Dict[str, Any]]:
        rows = await db.fetchall("SELECT * FROM moderation_logs WHERE guild_id = ? ORDER BY created_at DESC LIMIT ?;", (guild_id, limit))
        return [dict(r) for r in rows]

    # ==================== 16. TICKETS CONFIG ====================
    async def get_tickets_config(self, guild_id: int) -> Dict[str, Any]:
        panel_row = await db.fetchone("SELECT * FROM ticket_panels WHERE guild_id = ? LIMIT 1;", (guild_id,))
        settings_row = await db.fetchone("SELECT tickets_enabled FROM guild_settings WHERE guild_id = ?;", (guild_id,))
        d = {
            "tickets_enabled": bool(settings_row["tickets_enabled"]) if settings_row else True,
            "category_id": panel_row["category_id"] if panel_row else None,
            "support_role_id": panel_row["support_role_id"] if panel_row else None,
            "transcript_channel_id": panel_row["transcript_channel_id"] if panel_row else None,
            "panel_title": panel_row["title"] if panel_row else "🎫 NOVEXA Support Portal",
            "panel_description": panel_row["description"] if panel_row else "Click the button below to connect with staff.",
        }
        return d

    async def update_tickets_config(self, guild_id: int, updates: Dict[str, Any], actor_id: Optional[int] = None, actor_tag: Optional[str] = None, source: str = "WEBSITE") -> Dict[str, Any]:
        if "tickets_enabled" in updates:
            en = 1 if updates["tickets_enabled"] else 0
            await db.execute("UPDATE guild_settings SET tickets_enabled = ? WHERE guild_id = ?;", (en, guild_id))
        # Update or insert panel
        existing = await db.fetchone("SELECT panel_id FROM ticket_panels WHERE guild_id = ?;", (guild_id,))
        if existing:
            clauses, params = [], []
            for k in ["category_id", "support_role_id", "transcript_channel_id", "panel_title", "panel_description"]:
                if k in updates:
                    db_col = "title" if k == "panel_title" else ("description" if k == "panel_description" else k)
                    clauses.append(f"{db_col} = ?")
                    params.append(updates[k])
            if clauses:
                params.append(guild_id)
                await db.execute(f"UPDATE ticket_panels SET {', '.join(clauses)} WHERE guild_id = ?;", tuple(params))
        await self.broadcaster.broadcast(guild_id, "tickets_updated", updates)
        return await self.get_tickets_config(guild_id)

    # ==================== 17. LOGGING CONFIG ====================
    async def get_logging_config(self, guild_id: int) -> Dict[str, Any]:
        row = await db.fetchone("SELECT * FROM logging_config WHERE guild_id = ?;", (guild_id,))
        if not row:
            return {
                "joins_channel_id": None,
                "leaves_channel_id": None,
                "message_edits_channel_id": None,
                "message_deletes_channel_id": None,
                "role_changes_channel_id": None,
                "channel_changes_channel_id": None,
                "bans_channel_id": None,
            }
        return dict(row)

    async def update_logging_config(self, guild_id: int, updates: Dict[str, Any], actor_id: Optional[int] = None, actor_tag: Optional[str] = None, source: str = "WEBSITE") -> Dict[str, Any]:
        await db.execute("INSERT OR IGNORE INTO logging_config (guild_id) VALUES (?);", (guild_id,))
        allowed = ["joins_channel_id", "leaves_channel_id", "message_edits_channel_id", "message_deletes_channel_id", "role_changes_channel_id", "channel_changes_channel_id", "bans_channel_id"]
        clauses, params = [], []
        for k in allowed:
            if k in updates:
                clauses.append(f"{k} = ?")
                params.append(updates[k])
                await self._log_audit(guild_id, "logging", k, "", updates[k], actor_id, actor_tag, source)
        if clauses:
            params.append(guild_id)
            await db.execute(f"UPDATE logging_config SET {', '.join(clauses)} WHERE guild_id = ?;", tuple(params))
        await self.broadcaster.broadcast(guild_id, "logging_updated", updates)
        return await self.get_logging_config(guild_id)

    # ==================== 19. LEVELING CONFIG ====================
    async def get_leveling_config(self, guild_id: int) -> Dict[str, Any]:
        row = await db.fetchone("SELECT leveling_enabled, level_up_channel_id, xp_per_message, xp_cooldown FROM guild_settings WHERE guild_id = ?;", (guild_id,))
        if not row:
            return {
                "leveling_enabled": True,
                "level_up_channel_id": None,
                "xp_per_message": 15,
                "xp_cooldown": 60,
            }
        d = dict(row)
        d["leveling_enabled"] = bool(d.get("leveling_enabled", 1))
        return d

    async def update_leveling_config(self, guild_id: int, updates: Dict[str, Any], actor_id: Optional[int] = None, actor_tag: Optional[str] = None, source: str = "WEBSITE") -> Dict[str, Any]:
        allowed = ["leveling_enabled", "level_up_channel_id", "xp_per_message", "xp_cooldown"]
        clauses, params = [], []
        for k in allowed:
            if k in updates:
                clauses.append(f"{k} = ?")
                params.append(1 if updates[k] is True else (0 if updates[k] is False else updates[k]))
                await self._log_audit(guild_id, "leveling", k, "", updates[k], actor_id, actor_tag, source)
        if clauses:
            params.append(guild_id)
            await db.execute(f"UPDATE guild_settings SET {', '.join(clauses)} WHERE guild_id = ?;", tuple(params))
        await self.broadcaster.broadcast(guild_id, "leveling_updated", updates)
        return await self.get_leveling_config(guild_id)

    # ==================== 20. GIVEAWAYS ====================
    async def get_giveaways(self, guild_id: int) -> List[Dict[str, Any]]:
        rows = await db.fetchall("SELECT * FROM giveaways WHERE guild_id = ? ORDER BY end_time DESC LIMIT 20;", (guild_id,))
        return [dict(r) for r in rows]

    # ==================== 21. AUTO RESPONDERS ====================
    async def get_auto_responders(self, guild_id: int) -> List[Dict[str, Any]]:
        rows = await db.fetchall("SELECT * FROM auto_responders WHERE guild_id = ? ORDER BY id DESC;", (guild_id,))
        return [dict(r) for r in rows]

    async def add_auto_responder(self, guild_id: int, trigger: str, response: str, match_type: str = "contains", actor_id: Optional[int] = None, actor_tag: Optional[str] = None, source: str = "WEBSITE") -> Dict[str, Any]:
        cursor = await db.execute("INSERT INTO auto_responders (guild_id, trigger, response, match_type) VALUES (?, ?, ?, ?);", (guild_id, trigger, response, match_type))
        await self._log_audit(guild_id, "auto_responder", "add", "", trigger, actor_id, actor_tag, source)
        await self.broadcaster.broadcast(guild_id, "autoresponder_updated", {"action": "add", "trigger": trigger})
        return {"id": cursor.lastrowid, "trigger": trigger, "response": response, "match_type": match_type}

    async def delete_auto_responder(self, guild_id: int, responder_id: int, actor_id: Optional[int] = None, actor_tag: Optional[str] = None, source: str = "WEBSITE"):
        await db.execute("DELETE FROM auto_responders WHERE guild_id = ? AND id = ?;", (guild_id, responder_id))
        await self._log_audit(guild_id, "auto_responder", "delete", str(responder_id), "", actor_id, actor_tag, source)
        await self.broadcaster.broadcast(guild_id, "autoresponder_updated", {"action": "delete", "id": responder_id})

    # ==================== 22. INTEGRATIONS (PAYMENTS) ====================
    async def get_integrations_config(self, guild_id: int) -> Dict[str, Any]:
        row = await db.fetchone("SELECT * FROM payments_config WHERE guild_id = ?;", (guild_id,))
        if not row:
            return {
                "upi_id": "",
                "qr_image_url": "",
                "instructions": "Scan QR or send to UPI ID, then submit transaction ID.",
                "staff_role_id": None,
                "log_channel_id": None,
            }
        return dict(row)

    async def update_integrations_config(self, guild_id: int, updates: Dict[str, Any], actor_id: Optional[int] = None, actor_tag: Optional[str] = None, source: str = "WEBSITE") -> Dict[str, Any]:
        await db.execute("INSERT OR IGNORE INTO payments_config (guild_id) VALUES (?);", (guild_id,))
        allowed = ["upi_id", "qr_image_url", "instructions", "staff_role_id", "log_channel_id"]
        clauses, params = [], []
        for k in allowed:
            if k in updates:
                clauses.append(f"{k} = ?")
                params.append(updates[k])
                await self._log_audit(guild_id, "integrations", k, "", updates[k], actor_id, actor_tag, source)
        if clauses:
            params.append(guild_id)
            await db.execute(f"UPDATE payments_config SET {', '.join(clauses)} WHERE guild_id = ?;", tuple(params))
        await self.broadcaster.broadcast(guild_id, "integrations_updated", updates)
        return await self.get_integrations_config(guild_id)

    # ==================== 23. SETTINGS CONFIG ====================
    async def get_settings_config(self, guild_id: int) -> Dict[str, Any]:
        row = await db.fetchone("SELECT prefix FROM guild_settings WHERE guild_id = ?;", (guild_id,))
        return {"prefix": row["prefix"] if row else "/"}

    async def update_settings_config(self, guild_id: int, updates: Dict[str, Any], actor_id: Optional[int] = None, actor_tag: Optional[str] = None, source: str = "WEBSITE") -> Dict[str, Any]:
        await db.execute("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?);", (guild_id,))
        if "prefix" in updates:
            pfx = updates["prefix"]
            await db.execute("UPDATE guild_settings SET prefix = ? WHERE guild_id = ?;", (pfx, guild_id))
            await self._log_audit(guild_id, "settings", "prefix", "", pfx, actor_id, actor_tag, source)
        await self.broadcaster.broadcast(guild_id, "settings_updated", updates)
        return await self.get_settings_config(guild_id)

    # ==================== 24. RPG & PETS CONFIGS ====================
    async def get_rpg_games_config(self, guild_id: int) -> Dict[str, Any]:
        row = await db.fetchone("SELECT is_enabled, crime_cooldown FROM economy_guild_settings WHERE guild_id = ?;", (guild_id,))
        return {
            "games_enabled": bool(row[0]) if row else True,
            "crime_success_rate": 65,
            "max_bet_amount": 100000,
            "crime_cooldown": row[1] if row else 180,
        }

    async def update_rpg_games_config(self, guild_id: int, updates: Dict[str, Any], actor_id: Optional[int] = None, actor_tag: Optional[str] = None, source: str = "WEBSITE") -> Dict[str, Any]:
        await db.execute("INSERT OR IGNORE INTO economy_guild_settings (guild_id) VALUES (?);", (guild_id,))
        if "games_enabled" in updates:
            await db.execute("UPDATE economy_guild_settings SET is_enabled = ? WHERE guild_id = ?;", (1 if updates["games_enabled"] else 0, guild_id))
        if "crime_cooldown" in updates:
            await db.execute("UPDATE economy_guild_settings SET crime_cooldown = ? WHERE guild_id = ?;", (int(updates["crime_cooldown"]), guild_id))
        await self._log_audit(guild_id, "rpg_games", "config_updated", "", json.dumps(updates), actor_id, actor_tag, source)
        await self.broadcaster.broadcast(guild_id, "rpg_games_updated", updates)
        return await self.get_rpg_games_config(guild_id)

    async def get_pets_hunting_config(self, guild_id: int) -> Dict[str, Any]:
        row = await db.fetchone("SELECT hunt_cooldown FROM economy_guild_settings WHERE guild_id = ?;", (guild_id,))
        return {
            "hunt_cooldown": row[0] if row else 15,
            "mythical_drop_rate": 1,
            "pet_adoption_enabled": True,
        }

    async def update_pets_hunting_config(self, guild_id: int, updates: Dict[str, Any], actor_id: Optional[int] = None, actor_tag: Optional[str] = None, source: str = "WEBSITE") -> Dict[str, Any]:
        await db.execute("INSERT OR IGNORE INTO economy_guild_settings (guild_id) VALUES (?);", (guild_id,))
        if "hunt_cooldown" in updates:
            await db.execute("UPDATE economy_guild_settings SET hunt_cooldown = ? WHERE guild_id = ?;", (int(updates["hunt_cooldown"]), guild_id))
        await self._log_audit(guild_id, "pets_hunting", "config_updated", "", json.dumps(updates), actor_id, actor_tag, source)
        await self.broadcaster.broadcast(guild_id, "pets_hunting_updated", updates)
        return await self.get_pets_hunting_config(guild_id)

    # ==================== 25. ROLES & VOICE & SETUP ====================
    async def get_roles_config(self, guild_id: int) -> Dict[str, Any]:
        return {"enforce_hierarchy": True}

    async def update_roles_config(self, guild_id: int, updates: Dict[str, Any], actor_id: Optional[int] = None, actor_tag: Optional[str] = None, source: str = "WEBSITE") -> Dict[str, Any]:
        await self._log_audit(guild_id, "roles", "hierarchy_toggle", "", json.dumps(updates), actor_id, actor_tag, source)
        await self.broadcaster.broadcast(guild_id, "roles_updated", updates)
        return await self.get_roles_config(guild_id)

    async def get_reaction_roles(self, guild_id: int) -> List[Dict[str, Any]]:
        rows = await db.fetchall("SELECT id, message_id, channel_id, emoji, role_id FROM reaction_roles WHERE guild_id = ?;", (guild_id,))
        return [dict(r) for r in rows]

    async def add_reaction_role(self, guild_id: int, message_id: int, channel_id: int, emoji: str, role_id: int) -> int:
        cur = await db.execute("INSERT INTO reaction_roles (guild_id, message_id, channel_id, emoji, role_id) VALUES (?, ?, ?, ?, ?);",
                               (guild_id, message_id, channel_id, emoji, role_id))
        return cur.lastrowid

    async def delete_reaction_role(self, guild_id: int, rr_id: int) -> bool:
        await db.execute("DELETE FROM reaction_roles WHERE guild_id = ? AND id = ?;", (guild_id, rr_id))
        return True

    async def get_voice_channels_config(self, guild_id: int) -> Dict[str, Any]:
        music_cfg = await self.get_music_config(guild_id)
        return {
            "is_247": music_cfg.get("is_247", False),
            "voice_channel_id": music_cfg.get("voice_channel_id"),
        }

    async def update_voice_channels_config(self, guild_id: int, updates: Dict[str, Any], actor_id: Optional[int] = None, actor_tag: Optional[str] = None, source: str = "WEBSITE") -> Dict[str, Any]:
        return await self.update_music_config(guild_id, updates, actor_id, actor_tag, source)

    # ==================== JOIN TO CREATE (J2C) VOICE SYSTEM ====================

    async def get_voice_j2c_config(self, guild_id: int) -> Dict[str, Any]:
        row = await db.fetchone("SELECT * FROM voice_config WHERE guild_id = ?;", (guild_id,))
        if not row:
            return {
                "guild_id": guild_id,
                "generator_channel_id": None,
                "category_id": None,
                "channel_name_format": "🔊・{username}",
                "default_user_limit": 0,
                "default_bitrate": 64000,
                "delete_when_empty": True,
                "is_enabled": True,
                "configured": False,
            }
        d = dict(row)
        d["is_enabled"] = bool(d.get("is_enabled", 1))
        d["delete_when_empty"] = bool(d.get("delete_when_empty", 1))
        d["configured"] = bool(d.get("generator_channel_id"))
        return d

    async def update_voice_j2c_config(self, guild_id: int, updates: Dict[str, Any], actor_id: Optional[int] = None, actor_tag: Optional[str] = None, source: str = "WEBSITE") -> Dict[str, Any]:
        current = await self.get_voice_j2c_config(guild_id)
        exists = await db.fetchone("SELECT guild_id FROM voice_config WHERE guild_id = ?;", (guild_id,))
        if not exists:
            await db.execute(
                "INSERT INTO voice_config (guild_id, channel_name_format, default_user_limit, default_bitrate, delete_when_empty, is_enabled) VALUES (?, ?, ?, ?, 1, 1);",
                (guild_id, current["channel_name_format"], 0, 64000),
            )

        clauses, params = [], []
        for k in ["generator_channel_id", "category_id", "channel_name_format", "default_user_limit", "default_bitrate", "delete_when_empty", "is_enabled"]:
            if k not in updates:
                continue
            val = updates[k]
            if k in ("is_enabled", "delete_when_empty"):
                val = 1 if val else 0
            elif k in ("generator_channel_id", "category_id", "default_user_limit", "default_bitrate"):
                val = int(val) if val not in (None, "") else None
            clauses.append(f"{k} = ?")
            params.append(val)
            await self._log_audit(guild_id, "voice_j2c", k, str(current.get(k)), str(val), actor_id, actor_tag, source)

        if clauses:
            params.append(guild_id)
            await db.execute(f"UPDATE voice_config SET {', '.join(clauses)} WHERE guild_id = ?;", tuple(params))

        result = await self.get_voice_j2c_config(guild_id)
        if not result.get("generator_channel_id"):
            result["is_enabled"] = False
        await self.broadcaster.broadcast(guild_id, "voice_j2c_updated", result)
        return result

    async def get_server_setup_config(self, guild_id: int) -> Dict[str, Any]:
        row = await db.fetchone("SELECT template_id FROM server_setups WHERE guild_id = ?;", (guild_id,))
        return {"template_id": row[0] if row else "gaming"}

    async def update_server_setup_config(self, guild_id: int, updates: Dict[str, Any], actor_id: Optional[int] = None, actor_tag: Optional[str] = None, source: str = "WEBSITE") -> Dict[str, Any]:
        tid = updates.get("template_id", "gaming")
        await db.execute("INSERT INTO server_setups (guild_id, template_id, template_name) VALUES (?, ?, ?) ON CONFLICT(guild_id) DO UPDATE SET template_id = excluded.template_id, template_name = excluded.template_name;",
                         (guild_id, tid, tid.replace('_', ' ').title()))
        await self._log_audit(guild_id, "server_setup", "template_selected", "", tid, actor_id, actor_tag, source)
        return {"template_id": tid}

    async def get_custom_embeds_config(self, guild_id: int) -> Dict[str, Any]:
        return {"channel_id": None, "title": "", "description": "", "color": "#5865F2"}

    async def update_custom_embeds_config(self, guild_id: int, updates: Dict[str, Any], actor_id: Optional[int] = None, actor_tag: Optional[str] = None, source: str = "WEBSITE") -> Dict[str, Any]:
        await self._log_audit(guild_id, "custom_embeds", "embed_dispatched", "", json.dumps(updates), actor_id, actor_tag, source)
        return updates

    # ==================== 26. GENERIC DISPATCHER ====================
    async def get_module_config(self, guild_id: int, module: str) -> Dict[str, Any]:
        dispatch = {
            "overview": self.get_overview,
            "welcome": self.get_welcome_config,
            "goodbye": self.get_goodbye_config,
            "autoroles": self.get_autoroles_config,
            "antinuke": self.get_antinuke_config,
            "antispam": self.get_antispam_config,
            "automod": self.get_automod_config,
            "moderation": self.get_moderation_config,
            "tickets": self.get_tickets_config,
            "logging": self.get_logging_config,
            "roles": self.get_roles_config,
            "server_setup": self.get_server_setup_config,
            "music": self.get_music_config,
            "economy": self.get_economy_settings,
            "rpg_games": self.get_rpg_games_config,
            "pets_hunting": self.get_pets_hunting_config,
            "leveling": self.get_leveling_config,
            "voice_channels": self.get_voice_channels_config,
            "voice_j2c": self.get_voice_j2c_config,
            "custom_embeds": self.get_custom_embeds_config,
            "integrations": self.get_integrations_config,
            "settings": self.get_settings_config,
            "premium": self.get_premium_status,
        }
        if module in dispatch:
            return await dispatch[module](guild_id)
        return {"guild_id": guild_id, "module": module, "status": "active"}

    async def update_module_config(self, guild_id: int, module: str, updates: Dict[str, Any], actor_id: Optional[int] = None, actor_tag: Optional[str] = None, source: str = "WEBSITE") -> Dict[str, Any]:
        dispatch = {
            "welcome": self.update_welcome_config,
            "goodbye": self.update_goodbye_config,
            "autoroles": self.update_autoroles_config,
            "antinuke": self.update_antinuke_config,
            "antispam": self.update_antispam_config,
            "automod": self.update_automod_config,
            "moderation": self.update_moderation_config,
            "tickets": self.update_tickets_config,
            "logging": self.update_logging_config,
            "roles": self.update_roles_config,
            "server_setup": self.update_server_setup_config,
            "music": self.update_music_config,
            "economy": self.update_economy_settings,
            "rpg_games": self.update_rpg_games_config,
            "pets_hunting": self.update_pets_hunting_config,
            "leveling": self.update_leveling_config,
            "voice_channels": self.update_voice_channels_config,
            "voice_j2c": self.update_voice_j2c_config,
            "custom_embeds": self.update_custom_embeds_config,
            "integrations": self.update_integrations_config,
            "settings": self.update_settings_config,
        }
        if module in dispatch:
            return await dispatch[module](guild_id, updates, actor_id, actor_tag, source)
        await self._log_audit(guild_id, module, "generic_update", "", json.dumps(updates), actor_id, actor_tag, source)
        await self.broadcaster.broadcast(guild_id, f"{module}_updated", updates)
        return updates


# Global singleton instance
config_service = ConfigService()
