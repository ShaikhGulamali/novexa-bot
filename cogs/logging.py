"""NOVEXA - Real-Time Server Event Audit, Security & Automated Channel Logging Suite.

Features:
- Complete A-to-Z Discord Audit Log Gateway Interception (on_audit_log_entry_create):
  Logs EVERY SINGLE action performed in the server with the responsible Executor:
  • Bot Additions (bot added + who invited it)
  • Webhook Creation, Updates & Deletions
  • Integrations Added, Updated & Removed
  • Server Configuration Updates (Name, Icon, Banner, Splash, Afk, Rules, Verification, 2FA)
  • Channel Creations, Updates, Deletions & Permission Overwrites (Allow/Deny)
  • Role Creations, Updates, Deletions & Permission Escalations
  • Invites Created & Deleted (Code, Inviter, Expiry, Uses)
  • Emojis, Stickers & Soundboard Sounds Created / Deleted / Renamed
  • AutoMod Rules Created, Updated, Deleted & Filter Trigger Violations
  • Threads Created, Archived, Updated & Deleted
  • Scheduled Events Created, Updated & Cancelled
  • Inactive Member Mass Prunes
  • Message Pins & Unpins
- Instant Automated Setup on Guild Join (on_guild_join) and Retroactive Auto-Provisioning:
  Automatically creates '📊 NOVEXA LOGS' category and 6 dedicated locked channels.
- Granular Slash & Prefix Commands: /logs autoconfig, /logs view, n!setup-logs, n!autologs.
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
import datetime
import time
from typing import Optional, Dict, Tuple, Any, List, Set

from database.database import db
from config import BOT_NAME, BOT_PREFIX
from utils.embeds import primary_embed, success_embed, error_embed, warning_embed, info_embed
from utils.permissions import has_admin_or_owner

logger = logging.getLogger("novexa.logging")

# Color branding
COLOR_LOG_VOICE = 0x1ABC9C     # Cyan / Aqua
COLOR_LOG_MEMBER = 0x3498DB    # Blue
COLOR_LOG_MESSAGE = 0xE67E22   # Orange
COLOR_LOG_UPDATE = 0x9B59B6    # Purple
COLOR_LOG_AUDIT = 0x5865F2     # Blurple
COLOR_LOG_SECURITY = 0xE74C3C  # Crimson Red
COLOR_LOG_GOLD = 0xF1C40F      # Gold

CATEGORY_NAME = "📊 NOVEXA LOGS"

LOG_CHANNEL_SPECS = [
    {
        "name": "🔊・voice-logs",
        "key": "voice_logs_channel_id",
        "topic": "Logs voice channel joins, leaves, moves, deafen, mute, and streaming.",
    },
    {
        "name": "👥・member-logs",
        "key": "member_logs_channel_id",
        "topic": "Logs member joins, leaves, role updates, and nickname changes.",
    },
    {
        "name": "💬・message-logs",
        "key": "message_deletes_channel_id",
        "topic": "Logs deleted messages, edits, and bulk message purges.",
    },
    {
        "name": "⚙️・update-logs",
        "key": "channel_changes_channel_id",
        "topic": "Logs channel creations, updates, role modifications, and permissions.",
    },
    {
        "name": "🛡️・audit-logs",
        "key": "server_logs_channel_id",
        "topic": "Logs server configuration changes, bot integrations, emojis, and audit entries.",
    },
    {
        "name": "🚨・security-logs",
        "key": "antinuke_channel_id",
        "topic": "Logs bans, kicks, timeouts, unbans, and Anti-Nuke security incidents.",
    },
]

# Action title and icon mapping for audit log entries
AUDIT_ACTION_MAP = {
    # Bots & Integrations
    "bot_add": ("🤖 Bot Added to Server", COLOR_LOG_SECURITY),
    "integration_create": ("🔌 Integration Added", COLOR_LOG_AUDIT),
    "integration_update": ("🔌 Integration Modified", COLOR_LOG_UPDATE),
    "integration_delete": ("🗑️ Integration Removed", COLOR_LOG_SECURITY),
    # Webhooks
    "webhook_create": ("🔗 Webhook Created", COLOR_LOG_UPDATE),
    "webhook_update": ("🔗 Webhook Modified", COLOR_LOG_UPDATE),
    "webhook_delete": ("🗑️ Webhook Deleted", COLOR_LOG_SECURITY),
    # Server configuration
    "guild_update": ("🏛️ Server Settings Updated", COLOR_LOG_AUDIT),
    # Channels
    "channel_create": ("📁 Channel Created", COLOR_LOG_VOICE),
    "channel_update": ("⚙️ Channel Settings Updated", COLOR_LOG_UPDATE),
    "channel_delete": ("🗑️ Channel Deleted", COLOR_LOG_SECURITY),
    # Permissions overwrites
    "overwrite_create": ("🔒 Channel Permissions Overwrite Created", COLOR_LOG_UPDATE),
    "overwrite_update": ("🔒 Channel Permissions Overwrite Modified", COLOR_LOG_UPDATE),
    "overwrite_delete": ("🔓 Channel Permissions Overwrite Removed", COLOR_LOG_SECURITY),
    # Roles
    "role_create": ("🛡️ Role Created", COLOR_LOG_VOICE),
    "role_update": ("🛡️ Role Modified", COLOR_LOG_UPDATE),
    "role_delete": ("🗑️ Role Deleted", COLOR_LOG_SECURITY),
    # Invites
    "invite_create": ("📨 Invite Link Created", COLOR_LOG_MEMBER),
    "invite_update": ("📨 Invite Link Modified", COLOR_LOG_UPDATE),
    "invite_delete": ("🗑️ Invite Link Deleted", COLOR_LOG_MESSAGE),
    # Emojis & Stickers
    "emoji_create": ("😃 Emoji Added", COLOR_LOG_VOICE),
    "emoji_update": ("😃 Emoji Renamed / Modified", COLOR_LOG_UPDATE),
    "emoji_delete": ("🗑️ Emoji Deleted", COLOR_LOG_MESSAGE),
    "sticker_create": ("🎨 Sticker Added", COLOR_LOG_VOICE),
    "sticker_update": ("🎨 Sticker Updated", COLOR_LOG_UPDATE),
    "sticker_delete": ("🗑️ Sticker Deleted", COLOR_LOG_MESSAGE),
    "soundboard_sound_create": ("🎵 Soundboard Sound Added", COLOR_LOG_VOICE),
    "soundboard_sound_update": ("🎵 Soundboard Sound Updated", COLOR_LOG_UPDATE),
    "soundboard_sound_delete": ("🗑️ Soundboard Sound Deleted", COLOR_LOG_MESSAGE),
    # Moderation & Prune
    "kick": ("👢 Member Kicked", COLOR_LOG_SECURITY),
    "member_prune": ("🧹 Inactive Members Pruned", COLOR_LOG_SECURITY),
    "ban": ("🚨 Member Banned", COLOR_LOG_SECURITY),
    "unban": ("🕊️ Member Unbanned", COLOR_LOG_VOICE),
    "member_update": ("👤 Member Updated", COLOR_LOG_MEMBER),
    "member_role_update": ("🛡️ Member Roles Updated", COLOR_LOG_MEMBER),
    "member_move": ("🔀 Member Voice Disconnected / Moved", COLOR_LOG_VOICE),
    "member_disconnect": ("🔇 Member Voice Disconnected", COLOR_LOG_MESSAGE),
    # Messages
    "message_delete": ("🗑️ Message Deleted by Moderator", COLOR_LOG_MESSAGE),
    "message_bulk_delete": ("🧹 Bulk Messages Purged", COLOR_LOG_MESSAGE),
    "message_pin": ("📌 Message Pinned", COLOR_LOG_MEMBER),
    "message_unpin": ("📌 Message Unpinned", COLOR_LOG_MEMBER),
    # AutoMod
    "automod_rule_create": ("🛡️ AutoMod Rule Created", COLOR_LOG_VOICE),
    "automod_rule_update": ("🛡️ AutoMod Rule Modified", COLOR_LOG_UPDATE),
    "automod_rule_delete": ("🗑️ AutoMod Rule Deleted", COLOR_LOG_SECURITY),
    "automod_block_message": ("🚫 AutoMod Message Blocked", COLOR_LOG_SECURITY),
    "automod_flag_message": ("🚩 AutoMod Message Flagged", COLOR_LOG_MESSAGE),
    "automod_timeout_member": ("⏳ AutoMod Member Timed Out", COLOR_LOG_SECURITY),
    # Scheduled Events
    "scheduled_event_create": ("📅 Scheduled Event Created", COLOR_LOG_MEMBER),
    "scheduled_event_update": ("📅 Scheduled Event Updated", COLOR_LOG_UPDATE),
    "scheduled_event_delete": ("🗑️ Scheduled Event Cancelled", COLOR_LOG_SECURITY),
    # Threads
    "thread_create": ("🧵 Thread Created", COLOR_LOG_VOICE),
    "thread_update": ("🧵 Thread Updated", COLOR_LOG_UPDATE),
    "thread_delete": ("🗑️ Thread Deleted", COLOR_LOG_SECURITY),
    # Stages
    "stage_instance_create": ("🎙️ Stage Instance Started", COLOR_LOG_VOICE),
    "stage_instance_update": ("🎙️ Stage Instance Updated", COLOR_LOG_UPDATE),
    "stage_instance_delete": ("🎙️ Stage Instance Ended", COLOR_LOG_SECURITY),
    # App command permissions
    "app_command_permission_update": ("🤖 Slash Command Permissions Updated", COLOR_LOG_UPDATE),
}


class Logging(commands.Cog):
    """Granular Real-Time Server Event Audit & Logging Suite."""

    # Any role holding one of these is treated as staff for log visibility.
    STAFF_PERMISSION_FLAGS = (
        "administrator",
        "manage_guild",
        "manage_messages",
        "view_audit_log",
        "kick_members",
        "ban_members",
        "manage_roles",
        "moderate_members",
        "manage_channels",
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._bg_task: Optional[asyncio.Task] = None
        self._recent_audit_ids: Set[int] = set()
        self._privacy_ok: Set[int] = set()

    def _build_staff_overwrites(self, guild: discord.Guild) -> Dict[discord.abc.Snowflake, discord.PermissionOverwrite]:
        """Everyone denied; bot full control; staff/admin roles read-only."""
        overwrites: Dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                embed_links=True,
                attach_files=True,
                manage_channels=True,
                manage_messages=True,
                read_message_history=True,
            ),
        }
        for role in guild.roles:
            if role.is_default() or role.managed:
                continue
            if any(getattr(role.permissions, flag, False) for flag in self.STAFF_PERMISSION_FLAGS):
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    read_message_history=True,
                    send_messages=False,
                    add_reactions=False,
                )
        return overwrites

    async def _ensure_private(self, channel: discord.TextChannel) -> bool:
        """Make a log channel staff-only. Returns False if it can't be secured."""
        if channel.id in self._privacy_ok:
            return True
        guild = channel.guild
        if channel.overwrites_for(guild.default_role).view_channel is False:
            self._privacy_ok.add(channel.id)
            return True
        if not guild.me.guild_permissions.manage_channels:
            return False
        try:
            await channel.edit(
                overwrites=self._build_staff_overwrites(guild),
                reason="NOVEXA: restrict audit logs to administrators and staff",
            )
            self._privacy_ok.add(channel.id)
            return True
        except Exception as e:
            logger.debug(f"Failed to lock log channel #{channel.name}: {e}")
            return False

    async def enforce_log_privacy(self, guild: discord.Guild) -> int:
        """Re-lock the logs category and every configured log channel."""
        targets: List[discord.abc.GuildChannel] = []
        category = discord.utils.get(guild.categories, name=CATEGORY_NAME) or discord.utils.get(
            guild.categories, name="NOVEXA LOGS"
        )
        if category:
            targets.append(category)

        cfg = await db.fetchone("SELECT * FROM logging_config WHERE guild_id = ?", (guild.id,))
        if cfg:
            legacy_columns = (
                "joins_channel_id",
                "leaves_channel_id",
                "message_edits_channel_id",
                "role_changes_channel_id",
                "bans_channel_id",
                "kicks_channel_id",
                "timeouts_channel_id",
            )
            for key in [spec["key"] for spec in LOG_CHANNEL_SPECS] + list(legacy_columns):
                cid = cfg[key] if key in cfg.keys() else None
                if not cid:
                    continue
                ch = guild.get_channel(cid)
                if isinstance(ch, discord.TextChannel):
                    targets.append(ch)

        overwrites = self._build_staff_overwrites(guild)
        locked = 0
        seen = set()
        for target in targets:
            if target.id in seen:
                continue
            seen.add(target.id)
            if target.overwrites_for(guild.default_role).view_channel is False:
                self._privacy_ok.add(target.id)
                continue
            try:
                await target.edit(
                    overwrites=overwrites,
                    reason="NOVEXA: restrict audit logs to administrators and staff",
                )
                self._privacy_ok.add(target.id)
                locked += 1
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.debug(f"Failed to lock logs target {target.name} in {guild.name}: {e}")
        return locked

    async def cog_load(self):
        """Schedule retroactive automatic provisioning for all currently connected servers."""
        self._bg_task = asyncio.create_task(self._auto_provision_all_guilds())

    async def cog_unload(self):
        if self._bg_task and not self._bg_task.done():
            self._bg_task.cancel()

    async def _send_log(self, guild: Optional[discord.Guild], column_name: str, embed: discord.Embed):
        """Send embed to configured channel for the specific event type."""
        if not guild:
            return

        cfg = await db.fetchone(f"SELECT {column_name} FROM logging_config WHERE guild_id = ?", (guild.id,))
        if not cfg or not cfg[column_name]:
            return

        channel = guild.get_channel(cfg[column_name])
        if channel and isinstance(channel, discord.TextChannel):
            if not await self._ensure_private(channel):
                logger.warning(f"Skipping log dispatch to #{channel.name}: channel is not private.")
                return
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                pass
            except Exception as e:
                logger.debug(f"Failed to dispatch log to #{channel.name} in {guild.name}: {e}")

    # ==================== AUTO PROVISIONING LOGIC ====================

    async def auto_provision_guild(self, guild: discord.Guild) -> Tuple[bool, str, Dict[str, discord.TextChannel]]:
        """Automatically create the '📊 NOVEXA LOGS' category and 6 dedicated logging channels."""
        # 1. Permission check
        if not guild.me.guild_permissions.manage_channels:
            return False, "Bot is missing `Manage Channels` permission.", {}

        # 2. Find or create the Category
        category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
        if not category:
            category = discord.utils.get(guild.categories, name="NOVEXA LOGS")

        overwrites = self._build_staff_overwrites(guild)

        if not category:
            try:
                category = await guild.create_category(
                    CATEGORY_NAME,
                    overwrites=overwrites,
                    reason="NOVEXA Automated Audit Logging Suite Initialization",
                )
                logger.info(f"Created category '{CATEGORY_NAME}' in {guild.name} ({guild.id})")
            except Exception as e:
                return False, f"Failed to create logs category: {e}", {}
        else:
            # Existing category — force it private if it is still visible to members
            if category.overwrites_for(guild.default_role).view_channel is not False:
                try:
                    await category.edit(
                        overwrites=overwrites,
                        reason="NOVEXA: restrict audit logs to administrators and staff",
                    )
                except Exception as e:
                    logger.debug(f"Could not lock existing logs category in {guild.name}: {e}")

        # 3. Create or resolve individual logging channels
        created_channels: Dict[str, discord.TextChannel] = {}

        for spec in LOG_CHANNEL_SPECS:
            c_name = spec["name"]
            c_topic = spec["topic"]

            # Look for existing channel in category first
            existing = discord.utils.get(category.text_channels, name=c_name)
            if not existing:
                # Also check normalized name (e.g. without emoji: voice-logs)
                plain_name = c_name.split("・")[-1] if "・" in c_name else c_name
                existing = discord.utils.get(category.text_channels, name=plain_name)

            if not existing:
                try:
                    existing = await category.create_text_channel(
                        name=c_name,
                        topic=c_topic,
                        reason="NOVEXA Automated Audit Logging Channel",
                    )
                    logger.info(f"Created channel '{c_name}' in {guild.name}")
                except Exception as e:
                    logger.warning(f"Error creating channel {c_name} in {guild.name}: {e}")
                    continue

            # Existing channels keep the inheritance from a locked category;
            # explicit overwrites are only needed when the category was unlocked.
            if existing.overwrites_for(guild.default_role).view_channel is not False:
                try:
                    await existing.edit(
                        overwrites=overwrites,
                        reason="NOVEXA: restrict audit logs to administrators and staff",
                    )
                except Exception as e:
                    logger.debug(f"Could not lock channel '{c_name}' in {guild.name}: {e}")

            self._privacy_ok.add(existing.id)
            created_channels[spec["key"]] = existing

        # 4. Save mapped channel IDs into database
        voice_id = created_channels.get("voice_logs_channel_id")
        member_id = created_channels.get("member_logs_channel_id")
        msg_id = created_channels.get("message_deletes_channel_id")
        update_id = created_channels.get("channel_changes_channel_id")
        audit_id = created_channels.get("server_logs_channel_id")
        sec_id = created_channels.get("antinuke_channel_id")

        await db.execute(
            """
            INSERT INTO logging_config (
                guild_id, category_id,
                voice_logs_channel_id,
                member_logs_channel_id, joins_channel_id, leaves_channel_id,
                message_deletes_channel_id, message_edits_channel_id,
                channel_changes_channel_id, role_changes_channel_id,
                server_logs_channel_id,
                antinuke_channel_id, bans_channel_id, kicks_channel_id, timeouts_channel_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                category_id = excluded.category_id,
                voice_logs_channel_id = excluded.voice_logs_channel_id,
                member_logs_channel_id = excluded.member_logs_channel_id,
                joins_channel_id = excluded.joins_channel_id,
                leaves_channel_id = excluded.leaves_channel_id,
                message_deletes_channel_id = excluded.message_deletes_channel_id,
                message_edits_channel_id = excluded.message_edits_channel_id,
                channel_changes_channel_id = excluded.channel_changes_channel_id,
                role_changes_channel_id = excluded.role_changes_channel_id,
                server_logs_channel_id = excluded.server_logs_channel_id,
                antinuke_channel_id = excluded.antinuke_channel_id,
                bans_channel_id = excluded.bans_channel_id,
                kicks_channel_id = excluded.kicks_channel_id,
                timeouts_channel_id = excluded.timeouts_channel_id
            """,
            (
                guild.id, category.id,
                voice_id.id if voice_id else None,
                member_id.id if member_id else None, member_id.id if member_id else None, member_id.id if member_id else None,
                msg_id.id if msg_id else None, msg_id.id if msg_id else None,
                update_id.id if update_id else None, update_id.id if update_id else None,
                audit_id.id if audit_id else None,
                sec_id.id if sec_id else None, sec_id.id if sec_id else None, sec_id.id if sec_id else None, sec_id.id if sec_id else None,
            ),
        )

        # 5. Send welcome intro embed into the audit-logs channel
        if audit_id:
            try:
                has_intro = False
                async for m in audit_id.history(limit=5):
                    if m.author.id == self.bot.user.id and m.embeds:
                        has_intro = True
                        break

                if not has_intro:
                    intro_embed = discord.Embed(
                        title=f"🛡️ {BOT_NAME} Automated Audit & Security Logging Active",
                        description=(
                            f"**Welcome to the official NOVEXA Security & Audit Suite for {guild.name}!**\n\n"
                            f"All server activities, audit log entries, and security events are now continuously monitored:\n\n"
                            f"• {voice_id.mention if voice_id else '`#voice-logs`'} — Voice joins, leaves, moves, deafen & stream status\n"
                            f"• {member_id.mention if member_id else '`#member-logs`'} — Member joins, leaves, nickname changes & role updates\n"
                            f"• {msg_id.mention if msg_id else '`#message-logs`'} — Deleted messages, edits, and bulk purge logs\n"
                            f"• {update_id.mention if update_id else '`#update-logs`'} — Channel & role creation, edits & deletions\n"
                            f"• {audit_id.mention} — Server configuration changes, bot integrations, webhooks & audit logs\n"
                            f"• {sec_id.mention if sec_id else '`#security-logs`'} — Bans, kicks, timeouts, unbans & Anti-Nuke security\n\n"
                            f"🔒 *This category is private and accessible only to Server Administrators and {BOT_NAME}.*"
                        ),
                        color=COLOR_LOG_AUDIT,
                        timestamp=datetime.datetime.now(datetime.timezone.utc),
                    )
                    intro_embed.set_thumbnail(url=guild.icon.url if guild.icon else self.bot.user.display_avatar.url)
                    intro_embed.set_footer(text=f"{BOT_NAME} v2.0.0 • Comprehensive A-to-Z Audit Active")
                    await audit_id.send(embed=intro_embed)
            except Exception:
                pass

        return True, "Automated logging system successfully provisioned.", created_channels

    async def _auto_provision_all_guilds(self):
        """Retroactively ensure all servers the bot is currently in have the logs category and channels."""
        await self.bot.wait_until_ready()
        await asyncio.sleep(2.0)

        logger.info(f"Checking automated logging provisioning across {len(self.bot.guilds)} guilds...")
        count_success = 0

        for guild in self.bot.guilds:
            try:
                if not guild.me.guild_permissions.manage_channels:
                    continue
                ok, msg, chans = await self.auto_provision_guild(guild)
                if ok:
                    count_success += 1
                await self.enforce_log_privacy(guild)
                await asyncio.sleep(1.0)
            except Exception as e:
                logger.warning(f"Error provisioning logs in guild {guild.name} ({guild.id}): {e}")

        logger.info(f"Automated logging check complete. Configured in {count_success}/{len(self.bot.guilds)} guilds.")

    # ==================== MASTER AUDIT LOG ENTRY LISTENER ====================
    # Catches 100% of all events with Executor, Target, Changes & Reason directly from Discord Audit Logs!

    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry):
        """Master audit log gateway listener — intercepts and logs EVERY action in the server."""
        guild = entry.guild
        if not guild:
            return

        # Deduplicate recent entries (cache ID for 60 seconds)
        if entry.id in self._recent_audit_ids:
            return
        self._recent_audit_ids.add(entry.id)
        if len(self._recent_audit_ids) > 1000:
            self._recent_audit_ids.clear()

        action_name = entry.action.name if hasattr(entry.action, "name") else str(entry.action)
        title, color = AUDIT_ACTION_MAP.get(
            action_name,
            (f"📋 Audit Log: {action_name.replace('_', ' ').title()}", COLOR_LOG_AUDIT),
        )

        embed = discord.Embed(
            title=title,
            color=color,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )

        # 1. Executor (The User who performed the action)
        executor = entry.user
        if executor:
            embed.set_author(
                name=f"{executor.name} ({executor.id})",
                icon_url=executor.display_avatar.url,
            )
            embed.add_field(
                name="👤 Responsible Executor",
                value=f"{executor.mention} (`{executor.name}`) • ID: `{executor.id}`",
                inline=True,
            )
        else:
            embed.add_field(
                name="👤 Responsible Executor",
                value="*Unknown / Discord System*",
                inline=True,
            )

        # 2. Target identification
        target_str = "*None*"
        target_obj = entry.target

        if isinstance(target_obj, (discord.User, discord.Member)):
            target_str = f"{target_obj.mention} (`{target_obj.name}`) • ID: `{target_obj.id}`"
            if target_obj.bot:
                target_str += " 🤖 *(Bot)*"
        elif isinstance(target_obj, (discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.CategoryChannel, discord.ForumChannel)):
            target_str = f"{target_obj.mention} (`#{target_obj.name}`) • ID: `{target_obj.id}`"
        elif isinstance(target_obj, discord.Role):
            target_str = f"{target_obj.mention} (`@{target_obj.name}`) • ID: `{target_obj.id}`"
        elif isinstance(target_obj, (discord.Emoji, discord.GuildSticker)):
            target_str = f"`:{target_obj.name}:` • ID: `{target_obj.id}`"
        elif isinstance(target_obj, discord.Webhook):
            target_str = f"Webhook `{target_obj.name}` • ID: `{target_obj.id}`"
        elif isinstance(target_obj, discord.Invite):
            target_str = f"Invite Code: `{target_obj.code}`"
        elif hasattr(target_obj, "name") and hasattr(target_obj, "id"):
            target_str = f"`{target_obj.name}` • ID: `{target_obj.id}`"
        elif target_obj is not None:
            target_str = f"`{str(target_obj)}`"

        embed.add_field(name="🎯 Affected Target", value=target_str, inline=True)

        # 3. Action-specific Extra Details
        details_lines = []

        # Extra proxy handling
        if entry.extra:
            if hasattr(entry.extra, "channel") and entry.extra.channel:
                details_lines.append(f"• **Channel:** <#{entry.extra.channel.id}>")
            if hasattr(entry.extra, "count") and entry.extra.count is not None:
                details_lines.append(f"• **Count / Messages:** `{entry.extra.count}`")
            if hasattr(entry.extra, "delete_member_days"):
                details_lines.append(f"• **Prune Window:** `{entry.extra.delete_member_days} days` (Removed: `{entry.extra.members_removed}` members)")
            if hasattr(entry.extra, "automod_rule_name"):
                details_lines.append(f"• **AutoMod Rule:** `{entry.extra.automod_rule_name}`")

        # Changes inspection
        changes_dict = {}
        try:
            if entry.changes:
                # Iterate changes
                for change in getattr(entry.changes, "before", {}).__dict__.keys():
                    pass
        except Exception:
            pass

        # Raw changes from entry._changes
        raw_changes = getattr(entry, "_changes", [])
        if raw_changes and isinstance(raw_changes, list):
            for ch in raw_changes[:8]:  # display top 8 field alterations
                key = ch.get("key", "attribute")
                old_v = ch.get("old_value", "None")
                new_v = ch.get("new_value", "None")
                # Format permissions nicely
                if "permissions" in key.lower():
                    details_lines.append(f"• **Permissions:** Modified")
                else:
                    details_lines.append(f"• **{key.replace('_', ' ').capitalize()}:** `{str(old_v)[:30]}` ➔ `{str(new_v)[:30]}`")

        if details_lines:
            embed.add_field(
                name="📝 Modifications & Context",
                value="\n".join(details_lines[:6]),
                inline=False,
            )

        # 4. Audit Reason
        if entry.reason:
            embed.add_field(name="📄 Audit Reason", value=f"> *{entry.reason}*", inline=False)

        embed.set_footer(text=f"Audit Log ID: {entry.id} • Real-Time Gateway Event")

        # 5. Route to appropriate channels!
        # Always send to 🛡️・audit-logs (server_logs_channel_id)
        await self._send_log(guild, "server_logs_channel_id", embed)

        # If it's a security or dangerous event, also alert in 🚨・security-logs!
        if action_name in (
            "bot_add", "ban", "unban", "kick", "member_prune",
            "webhook_create", "webhook_delete", "automod_timeout_member",
            "automod_block_message", "automod_rule_delete"
        ):
            await self._send_log(guild, "antinuke_channel_id", embed)

        # If it's a channel or role modification, also alert in ⚙️・update-logs!
        if action_name in (
            "channel_create", "channel_update", "channel_delete",
            "role_create", "role_update", "role_delete",
            "overwrite_create", "overwrite_update", "overwrite_delete"
        ):
            await self._send_log(guild, "channel_changes_channel_id", embed)

    # ==================== DISCORD GATEWAY EVENT LISTENERS ====================

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Trigger instant auto-provisioning the second bot joins a new server."""
        logger.info(f"Bot joined new guild: {guild.name} ({guild.id})! Running instant logs setup...")
        await asyncio.sleep(1.5)
        await self.auto_provision_guild(guild)

    # 1. VOICE LOGS
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Real-time voice activity audit logging."""
        guild = member.guild

        # A. Voice Channel Join
        if before.channel is None and after.channel is not None:
            embed = discord.Embed(
                title="🔊 Voice Channel Joined",
                description=(
                    f"**Member:** {member.mention} (`{member.id}`)\n"
                    f"**Channel:** {after.channel.mention} (`{after.channel.name}`)\n"
                    f"**Occupants:** `{len(after.channel.members)} members`"
                ),
                color=COLOR_LOG_VOICE,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await self._send_log(guild, "voice_logs_channel_id", embed)
            return

        # B. Voice Channel Leave
        if before.channel is not None and after.channel is None:
            embed = discord.Embed(
                title="🔇 Voice Channel Left",
                description=(
                    f"**Member:** {member.mention} (`{member.id}`)\n"
                    f"**Channel:** {before.channel.mention} (`{before.channel.name}`)"
                ),
                color=COLOR_LOG_MESSAGE,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await self._send_log(guild, "voice_logs_channel_id", embed)
            return

        # C. Voice Channel Move / Switch
        if before.channel is not None and after.channel is not None and before.channel.id != after.channel.id:
            embed = discord.Embed(
                title="🔀 Voice Channel Switched",
                description=(
                    f"**Member:** {member.mention} (`{member.id}`)\n"
                    f"**From:** {before.channel.mention} (`{before.channel.name}`)\n"
                    f"**To:** {after.channel.mention} (`{after.channel.name}`)"
                ),
                color=COLOR_LOG_VOICE,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await self._send_log(guild, "voice_logs_channel_id", embed)
            return

        # D. Deafen / Mute / Stream changes
        changes = []
        if before.self_mute != after.self_mute:
            changes.append(f"• **Microphone:** {'Muted 🔴' if after.self_mute else 'Unmuted 🟢'}")
        if before.self_deaf != after.self_deaf:
            changes.append(f"• **Headphones:** {'Deafened 🔇' if after.self_deaf else 'Undeafened 🔊'}")
        if before.self_stream != after.self_stream:
            changes.append(f"• **Screen Share:** {'Started Streaming 📺' if after.self_stream else 'Stopped Streaming ⏹️'}")
        if before.self_video != after.self_video:
            changes.append(f"• **Camera:** {'Turned On 📹' if after.self_video else 'Turned Off 📷'}")

        if changes and after.channel:
            embed = discord.Embed(
                title="🎙️ Voice State Updated",
                description=(
                    f"**Member:** {member.mention} (`{member.id}`)\n"
                    f"**Channel:** {after.channel.mention}\n\n"
                    + "\n".join(changes)
                ),
                color=COLOR_LOG_VOICE,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await self._send_log(guild, "voice_logs_channel_id", embed)

    # 2. MEMBER LOGS
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        embed = discord.Embed(
            title="📥 Member Joined",
            description=(
                f"**Member:** {member.mention} (`{member.name}`)\n"
                f"**ID:** `{member.id}`\n"
                f"**Account Created:** <t:{int(member.created_at.timestamp())}:R>\n"
                f"**Total Server Members:** **{member.guild.member_count:,}**"
            ),
            color=COLOR_LOG_MEMBER,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await self._send_log(member.guild, "member_logs_channel_id", embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        roles_str = ", ".join(r.name for r in member.roles if not r.is_default()) or "None"
        embed = discord.Embed(
            title="📤 Member Left",
            description=(
                f"**Member:** {member.mention} (`{member.name}`)\n"
                f"**ID:** `{member.id}`\n"
                f"**Roles Held:** `{roles_str}`\n"
                f"**Remaining Members:** **{member.guild.member_count:,}**"
            ),
            color=COLOR_LOG_MESSAGE,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await self._send_log(member.guild, "member_logs_channel_id", embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        guild = after.guild

        # A. Nickname Change
        if before.nick != after.nick:
            embed = discord.Embed(
                title="✏️ Nickname Changed",
                description=(
                    f"**Member:** {after.mention} (`{after.id}`)\n"
                    f"**Before:** `{before.nick or before.name}`\n"
                    f"**After:** `{after.nick or after.name}`"
                ),
                color=COLOR_LOG_MEMBER,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
            )
            embed.set_thumbnail(url=after.display_avatar.url)
            await self._send_log(guild, "member_logs_channel_id", embed)

        # B. Timeout detection (Send to security-logs)
        if before.timed_out_until != after.timed_out_until:
            if after.timed_out_until:
                embed = discord.Embed(
                    title="⏳ Member Timed Out",
                    description=(
                        f"**Target:** {after.mention} (`{after.id}`)\n"
                        f"**Duration:** Until <t:{int(after.timed_out_until.timestamp())}:F> (<t:{int(after.timed_out_until.timestamp())}:R>)"
                    ),
                    color=COLOR_LOG_SECURITY,
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                )
                await self._send_log(guild, "antinuke_channel_id", embed)
            else:
                embed = discord.Embed(
                    title="🔓 Member Timeout Removed",
                    description=f"**Target:** {after.mention} (`{after.id}`) had their timeout cleared.",
                    color=COLOR_LOG_VOICE,
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                )
                await self._send_log(guild, "antinuke_channel_id", embed)

        # C. Role Add / Remove
        if before.roles != after.roles:
            added = [r for r in after.roles if r not in before.roles]
            removed = [r for r in before.roles if r not in after.roles]

            lines = [f"**Member:** {after.mention} (`{after.id}`)"]
            if added:
                lines.append(f"➕ **Roles Added:** {', '.join(r.mention for r in added)}")
            if removed:
                lines.append(f"➖ **Roles Removed:** {', '.join(r.mention for r in removed)}")

            embed = discord.Embed(
                title="🛡️ Member Roles Updated",
                description="\n".join(lines),
                color=COLOR_LOG_MEMBER,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
            )
            embed.set_thumbnail(url=after.display_avatar.url)
            await self._send_log(guild, "member_logs_channel_id", embed)

    # 3. MESSAGE LOGS
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        clean_text = message.clean_content[:1500] if message.clean_content else "*[No text content — Embed or Attachment]*"
        att_urls = [a.url for a in message.attachments]

        embed = discord.Embed(
            title="🗑️ Message Deleted",
            description=(
                f"**Author:** {message.author.mention} (`{message.author.id}`)\n"
                f"**Channel:** {message.channel.mention}\n\n"
                f"**Content:**\n```{clean_text}```"
                + (f"\n📎 **Attachments:** {', '.join(att_urls[:3])}" if att_urls else "")
            ),
            color=COLOR_LOG_MESSAGE,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.set_thumbnail(url=message.author.display_avatar.url)
        await self._send_log(message.guild, "message_deletes_channel_id", embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild or before.content == after.content:
            return

        embed = discord.Embed(
            title="✏️ Message Edited",
            description=(
                f"**Author:** {before.author.mention} (`{before.author.id}`)\n"
                f"**Channel:** {before.channel.mention} • [Jump to Message]({after.jump_url})\n\n"
                f"**Before:**\n```{before.clean_content[:700]}```\n"
                f"**After:**\n```{after.clean_content[:700]}```"
            ),
            color=COLOR_LOG_UPDATE,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.set_thumbnail(url=before.author.display_avatar.url)
        await self._send_log(before.guild, "message_deletes_channel_id", embed)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: List[discord.Message]):
        if not messages or not messages[0].guild:
            return
        guild = messages[0].guild
        channel = messages[0].channel

        embed = discord.Embed(
            title="🧹 Bulk Messages Purged",
            description=(
                f"**Channel:** {channel.mention}\n"
                f"**Total Deleted:** `{len(messages)} messages`\n"
                f"**Unique Authors:** `{len(set(m.author.id for m in messages))} users`"
            ),
            color=COLOR_LOG_MESSAGE,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        await self._send_log(guild, "message_deletes_channel_id", embed)

    # 4. WEBHOOKS & INTEGRATIONS DIRECT GATEWAY LISTENERS
    @commands.Cog.listener()
    async def on_webhooks_update(self, channel: discord.abc.GuildChannel):
        """Fires whenever webhooks are modified or created in a channel."""
        embed = discord.Embed(
            title="🔗 Channel Webhooks Updated",
            description=f"Webhooks were updated or created in channel {channel.mention} (`#{channel.name}`).",
            color=COLOR_LOG_UPDATE,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        await self._send_log(channel.guild, "server_logs_channel_id", embed)

    @commands.Cog.listener()
    async def on_guild_integrations_update(self, guild: discord.Guild):
        """Fires whenever guild integrations or bots are updated."""
        embed = discord.Embed(
            title="🔌 Server Integrations Updated",
            description=f"Server integrations were modified in **{guild.name}**.",
            color=COLOR_LOG_AUDIT,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        await self._send_log(guild, "server_logs_channel_id", embed)

    # 5. INVITES
    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        inviter_str = invite.inviter.mention if invite.inviter else "*Unknown*"
        embed = discord.Embed(
            title="📨 Invite Link Created",
            description=(
                f"**Code:** `{invite.code}`\n"
                f"**Creator:** {inviter_str}\n"
                f"**Channel:** {invite.channel.mention if invite.channel else 'None'}\n"
                f"**Max Uses:** `{invite.max_uses or 'Unlimited'}`\n"
                f"**Temporary:** `{'Yes' if invite.temporary else 'No'}`"
            ),
            color=COLOR_LOG_MEMBER,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        await self._send_log(invite.guild, "server_logs_channel_id", embed)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        embed = discord.Embed(
            title="🗑️ Invite Link Deleted",
            description=f"**Invite Code:** `{invite.code}` was deleted.",
            color=COLOR_LOG_MESSAGE,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        await self._send_log(invite.guild, "server_logs_channel_id", embed)

    # 6. AUTOMOD RULES
    @commands.Cog.listener()
    async def on_automod_rule_create(self, rule: discord.AutoModRule):
        embed = discord.Embed(
            title="🛡️ AutoMod Rule Created",
            description=(
                f"**Rule Name:** `{rule.name}`\n"
                f"**Creator:** <@{rule.creator_id}>\n"
                f"**Enabled:** `{'Yes' if rule.enabled else 'No'}`"
            ),
            color=COLOR_LOG_VOICE,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        await self._send_log(rule.guild, "server_logs_channel_id", embed)

    @commands.Cog.listener()
    async def on_automod_rule_delete(self, rule: discord.AutoModRule):
        embed = discord.Embed(
            title="🗑️ AutoMod Rule Deleted",
            description=f"**Rule Name:** `{rule.name}` has been deleted.",
            color=COLOR_LOG_SECURITY,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        await self._send_log(rule.guild, "server_logs_channel_id", embed)

    # ==================== SLASH COMMANDS ====================

    logs_group = app_commands.Group(name="logs", description="Configure server event audit logging")

    @logs_group.command(
        name="autoconfig",
        description="Automatically create '📊 NOVEXA LOGS' category and 6 dedicated audit channels",
    )
    @has_admin_or_owner()
    async def slash_logs_autoconfig(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        ok, msg, created = await self.auto_provision_guild(interaction.guild)

        if not ok:
            return await interaction.followup.send(embed=error_embed("Setup Failed", msg))

        ch_list = [f"• **{ch.mention}** (`#{ch.name}`)" for ch in created.values()]
        embed = discord.Embed(
            title="🎉 Automated Logs Category & Channels Configured!",
            description=(
                f"Successfully set up **{CATEGORY_NAME}** and linked real-time audit logging:\n\n"
                + "\n".join(ch_list)
                + "\n\n🔒 *All channels have been locked to Administrators and NOVEXA for maximum security.*"
            ),
            color=COLOR_LOG_VOICE,
        )
        await interaction.followup.send(embed=embed)

    @logs_group.command(name="setup", description="Assign a log channel for a specific event type")
    @has_admin_or_owner()
    @app_commands.choices(event_type=[
        app_commands.Choice(name="Voice Activity", value="voice_logs_channel_id"),
        app_commands.Choice(name="Member Joins & Leaves", value="member_logs_channel_id"),
        app_commands.Choice(name="Message Edits & Deletions", value="message_deletes_channel_id"),
        app_commands.Choice(name="Channel & Role Updates", value="channel_changes_channel_id"),
        app_commands.Choice(name="Server & Audit Events", value="server_logs_channel_id"),
        app_commands.Choice(name="Bans, Timeouts & Anti-Nuke", value="antinuke_channel_id"),
    ])
    @app_commands.describe(event_type="The type of event to log", channel="Channel where logs should be posted")
    async def slash_logs_setup(self, interaction: discord.Interaction, event_type: app_commands.Choice[str], channel: discord.TextChannel):
        col = event_type.value
        await db.execute(
            f"""
            INSERT INTO logging_config (guild_id, {col})
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET {col} = excluded.{col}
            """,
            (interaction.guild_id, channel.id),
        )
        if not await self._ensure_private(channel):
            await interaction.response.send_message(
                embed=error_embed(
                    "Channel Not Private",
                    f"I could not lock {channel.mention} to staff only. Give me `Manage Channels` there.",
                ),
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            embed=success_embed(
                "Log Channel Set",
                f"**{event_type.name}** will now be logged to {channel.mention} — visible only to administrators and staff.",
            ),
            ephemeral=True,
        )

    @logs_group.command(name="view", description="View current server logging channel assignments")
    @has_admin_or_owner()
    async def slash_logs_view(self, interaction: discord.Interaction):
        cfg = await db.fetchone("SELECT * FROM logging_config WHERE guild_id = ?", (interaction.guild_id,))
        embed = primary_embed(title=f"📋 Audit Logging Channels — {interaction.guild.name}")

        fields = [
            ("🔊 Voice Logs", "voice_logs_channel_id"),
            ("👥 Member Logs", "member_logs_channel_id"),
            ("💬 Message Logs", "message_deletes_channel_id"),
            ("⚙️ Update Logs", "channel_changes_channel_id"),
            ("🛡️ Audit Logs", "server_logs_channel_id"),
            ("🚨 Security Logs", "antinuke_channel_id"),
        ]

        for label, col in fields:
            cid = cfg[col] if cfg else None
            ch = interaction.guild.get_channel(cid) if cid else None
            embed.add_field(name=label, value=ch.mention if ch else "*Disabled*", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ==================== PREFIX COMMANDS ====================
    @commands.command(name="setup-logs", aliases=["autologs", "logsetup"])
    @commands.has_permissions(manage_channels=True)
    async def prefix_setup_logs(self, ctx: commands.Context):
        """Automatically create NOVEXA LOGS category and all channels."""
        try:
            await ctx.message.delete()
        except Exception:
            pass

        msg = await ctx.send("⏳ Initializing NOVEXA Automated Logging category and channels...")
        ok, res_msg, created = await self.auto_provision_guild(ctx.guild)
        if not ok:
            return await msg.edit(content=f"❌ Setup failed: {res_msg}")

        await self.enforce_log_privacy(ctx.guild)

        ch_list = [f"• **{ch.mention}** (`#{ch.name}`)" for ch in created.values()]
        embed = discord.Embed(
            title="🎉 Automated Logs Category & Channels Configured!",
            description=(
                f"Successfully created **{CATEGORY_NAME}** and linked real-time audit logging:\n\n"
                + "\n".join(ch_list)
                + "\n\n🔒 *Locked to Administrators and staff only — members cannot see these channels.*"
            ),
            color=COLOR_LOG_VOICE,
        )
        await msg.edit(content=None, embed=embed)
        asyncio.create_task(self._auto_delete_message(msg, 15))

    @staticmethod
    async def _auto_delete_message(message: discord.Message, delay: float):
        await asyncio.sleep(delay)
        try:
            await message.delete()
        except Exception:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Logging(bot))
