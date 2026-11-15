"""NOVEXA - Ultra-Fast Advanced Anti-Nuke Security Suite Cog.

Features:
- Real-time interactive Anti-Nuke Control Panel dashboard with live buttons and selectors
- Delay-resilient audit log correlation with millisecond latency benchmarking
- Monitored Vectors: Channels (Create/Delete/Update), Roles (Create/Delete/Update/Perms),
  Webhooks (Create/Delete/Update), Bots (Unauthorized Invites), Mass Bans, Mass Kicks, Settings
- Instant damage containment (Channel auto-restore, Role auto-restore, Webhook deletion, Bot eviction)
- Strict least-privilege authorization (Owner immunity, explicit whitelist, no automatic admin trust)
- Hierarchy-aware punishment execution (Ban, Kick, Quarantine, Timeout, Revoke Perms)
- Confirmation dialog before disabling protection
"""

import asyncio
import datetime
import logging
import time
from types import SimpleNamespace
from typing import Dict, List, Tuple, Optional, Union, Any
import discord
from discord import app_commands
from discord.ext import commands

from database.database import db
from services.security_service import security_service, CONFIG_LIMIT_COLUMNS, ACTION_LABELS
from utils.permissions import has_admin_or_owner
from utils.embeds import primary_embed, success_embed, error_embed, warning_embed, info_embed
from utils.emojis import Emojis
from config import BOT_NAME

logger = logging.getLogger("novexa.antinuke")


# ==================== CONTROL PANEL VIEWS & COMPONENTS ====================

class AntiNukeDisableConfirmView(discord.ui.View):
    """Explicit confirmation view required before disabling Anti-Nuke protection."""

    def __init__(self, parent_view: "AntiNukeControlPanelView", author_id: int):
        super().__init__(timeout=60)
        self.parent_view = parent_view
        self.author_id = author_id

    @discord.ui.button(label="Confirm Disable Protection", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def btn_confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("Only the command initiator can confirm this.", ephemeral=True)

        await security_service.set_security_enabled(interaction.guild_id, False)
        for child in self.children:
            child.disabled = True

        embed = warning_embed(
            title=f"{Emojis.AN_DISABLED} Anti-Nuke Protection Deactivated",
            description=(
                f"**Anti-Nuke security has been disabled for this server.**\n\n"
                f"• Destruction vectors are now unmonitored.\n"
                f"• Automatic channel/role restoration is halted.\n"
                f"• You can re-enable protection anytime via `/antinuke panel`."
            ),
        )
        await interaction.response.edit_message(embed=embed, view=None)

        # Refresh parent panel if available
        try:
            await self.parent_view.refresh_panel()
        except Exception:
            pass

    @discord.ui.button(label="Keep Protection Active (Cancel)", style=discord.ButtonStyle.success, emoji="🛡️")
    async def btn_cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content=f"{Emojis.AN_ENABLED} Anti-Nuke protection remains active and enforcing.",
            embed=None,
            view=None,
        )


class ActionPolicySelect(discord.ui.Select):
    """Select menu to configure default punishment action."""

    def __init__(self, current_action: str):
        options = [
            discord.SelectOption(
                label="Ban Offender",
                value="ban",
                description="Immediately ban executor (Verified & Permitted)",
                emoji=Emojis.PARTIAL_AN_BANNED,
                default=(current_action == "ban"),
            ),
            discord.SelectOption(
                label="Kick Offender",
                value="kick",
                description="Evict offender from the server",
                emoji="👢",
                default=(current_action == "kick"),
            ),
            discord.SelectOption(
                label="Quarantine Offender",
                value="quarantine",
                description="Strip roles and apply 24h timeout",
                emoji="☣️",
                default=(current_action == "quarantine"),
            ),
            discord.SelectOption(
                label="1-Hour Timeout",
                value="timeout",
                description="Apply temporary communication restriction",
                emoji="⏳",
                default=(current_action == "timeout"),
            ),
            discord.SelectOption(
                label="Revoke Permissions",
                value="revoke_perms",
                description="Strip dangerous admin roles",
                emoji="🔒",
                default=(current_action == "revoke_perms"),
            ),
            discord.SelectOption(
                label="Monitor Only",
                value="monitor",
                description="Log security events without punishing",
                emoji="👁️",
                default=(current_action == "monitor"),
            ),
        ]
        super().__init__(placeholder="Select Offender Action Policy...", min_values=1, max_values=1, options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        view: AntiNukeControlPanelView = self.view  # type: ignore
        if interaction.user.id != view.author_id:
            return await interaction.response.send_message("Only the command initiator can adjust settings.", ephemeral=True)

        chosen = self.values[0]
        await security_service.set_security_punishment(interaction.guild_id, chosen)
        await interaction.response.send_message(
            embed=success_embed("Action Policy Updated", f"Default punishment policy set to: **{chosen.upper()}**"),
            ephemeral=True,
        )
        await view.refresh_panel()


class ProtectionModeSelect(discord.ui.Select):
    """Select menu to configure operating mode (LOW, MEDIUM, HIGH, PANIC)."""

    def __init__(self, current_mode: str):
        options = [
            discord.SelectOption(
                label="PANIC: One Strike = Instant Ban",
                value="panic",
                description="Any create/delete/rename/role/webhook = instant ban + revert",
                emoji=Emojis.PARTIAL_AN_BOMB,
                default=(current_mode == "panic"),
            ),
            discord.SelectOption(
                label="HIGH: Instant Aggressive Protection",
                value="high",
                description="Threshold 1 on critical actions; instant containment",
                emoji=Emojis.PARTIAL_AN_BOMB,
                default=(current_mode == "high"),
            ),
            discord.SelectOption(
                label="MEDIUM: Balanced Multi-Strike Guard",
                value="medium",
                description="Default production guard (Recommended)",
                emoji=Emojis.PARTIAL_AN_ENABLED,
                default=(current_mode == "medium"),
            ),
            discord.SelectOption(
                label="LOW: Audit Log & Alert Only",
                value="low",
                description="Observe activity without auto-punishments",
                emoji=Emojis.PARTIAL_AN_PAPER,
                default=(current_mode == "low"),
            ),
        ]
        super().__init__(placeholder="Select Protection Operating Mode...", min_values=1, max_values=1, options=options, row=2)

    async def callback(self, interaction: discord.Interaction):
        view: AntiNukeControlPanelView = self.view  # type: ignore
        if interaction.user.id != view.author_id:
            return await interaction.response.send_message("Only the command initiator can adjust settings.", ephemeral=True)

        chosen = self.values[0]
        await security_service.set_security_mode(interaction.guild_id, chosen)
        await interaction.response.send_message(
            embed=success_embed("Protection Mode Updated", f"Operating mode set to: **{chosen.upper()} MODE**"),
            ephemeral=True,
        )
        await view.refresh_panel()


class AlertChannelSelect(discord.ui.ChannelSelect):
    """Channel select menu to configure dedicated security log channel."""

    def __init__(self):
        super().__init__(
            placeholder="Select Security Alert Log Channel...",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1,
            row=3,
        )

    async def callback(self, interaction: discord.Interaction):
        view: AntiNukeControlPanelView = self.view  # type: ignore
        if interaction.user.id != view.author_id:
            return await interaction.response.send_message("Only the command initiator can adjust settings.", ephemeral=True)

        selected_channel = self.values[0]
        await security_service.set_security_log_channel(interaction.guild_id, selected_channel.id)
        await interaction.response.send_message(
            embed=success_embed("Alert Channel Updated", f"Security incident alerts will be posted in {selected_channel.mention}."),
            ephemeral=True,
        )
        await view.refresh_panel()


class AntiNukeControlPanelView(discord.ui.View):
    """Real-time interactive dashboard view for Anti-Nuke control."""

    def __init__(self, cog: "AntiNuke", guild: discord.Guild, author_id: int):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild = guild
        self.author_id = author_id
        self.message: Optional[discord.Message] = None

    async def init_components(self):
        """Asynchronously build dynamic select menus reflecting current database state."""
        self.clear_items()

        cfg = await security_service.get_security_config(self.guild.id)
        is_enabled = bool(cfg.get("enabled", 1))
        curr_punishment = cfg.get("punishment_type", "ban")
        curr_mode = cfg.get("mode", "medium")

        # Row 0: Primary Action Buttons
        btn_enable = discord.ui.Button(
            label="Enable Protection",
            style=discord.ButtonStyle.success,
            emoji=Emojis.PARTIAL_AN_ENABLED,
            disabled=is_enabled,
            custom_id="an_panel_enable",
            row=0,
        )
        btn_enable.callback = self.btn_enable_callback
        self.add_item(btn_enable)

        btn_disable = discord.ui.Button(
            label="Disable Protection",
            style=discord.ButtonStyle.danger,
            emoji=Emojis.PARTIAL_AN_DISABLED,
            disabled=not is_enabled,
            custom_id="an_panel_disable",
            row=0,
        )
        btn_disable.callback = self.btn_disable_callback
        self.add_item(btn_disable)

        btn_lockdown = discord.ui.Button(
            label="Emergency Lockdown",
            style=discord.ButtonStyle.primary,
            emoji=Emojis.PARTIAL_AN_BOMB,
            custom_id="an_panel_lockdown",
            row=0,
        )
        btn_lockdown.callback = self.btn_lockdown_callback
        self.add_item(btn_lockdown)

        btn_refresh = discord.ui.Button(
            label="Refresh Stats",
            style=discord.ButtonStyle.secondary,
            emoji="🔄",
            custom_id="an_panel_refresh",
            row=0,
        )
        btn_refresh.callback = self.btn_refresh_callback
        self.add_item(btn_refresh)

        # Row 1: Action Policy Select
        self.add_item(ActionPolicySelect(curr_punishment))

        # Row 2: Protection Mode Select
        self.add_item(ProtectionModeSelect(curr_mode))

        # Row 3: Alert Channel Select
        self.add_item(AlertChannelSelect())

        # Row 4: Shield Toggles
        raid_on = bool(cfg.get("raid_shield_enabled", 1))
        btn_raid = discord.ui.Button(
            label=f"Raid Shield: {'ON' if raid_on else 'OFF'}",
            style=discord.ButtonStyle.success if raid_on else discord.ButtonStyle.secondary,
            emoji="🚨",
            custom_id="an_panel_raid",
            row=4,
        )
        btn_raid.callback = self.btn_raid_callback
        self.add_item(btn_raid)

        bot_on = bool(cfg.get("bot_protection_enabled", 1))
        btn_bots = discord.ui.Button(
            label=f"Bot Guard: {'ON' if bot_on else 'OFF'}",
            style=discord.ButtonStyle.success if bot_on else discord.ButtonStyle.secondary,
            emoji="🤖",
            custom_id="an_panel_bots",
            row=4,
        )
        btn_bots.callback = self.btn_bots_callback
        self.add_item(btn_bots)

        btn_wl = discord.ui.Button(
            label="Whitelist",
            style=discord.ButtonStyle.secondary,
            emoji="📋",
            custom_id="an_panel_whitelist",
            row=4,
        )
        btn_wl.callback = self.btn_whitelist_callback
        self.add_item(btn_wl)

    async def btn_raid_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("Only the command initiator can control this panel.", ephemeral=True)

        cfg = await security_service.get_security_config(self.guild.id)
        new_state = not bool(cfg.get("raid_shield_enabled", 1))
        await security_service.set_raid_shield(self.guild.id, new_state)
        await interaction.response.send_message(
            embed=success_embed(
                "Raid Shield Updated",
                f"Join-burst protection is now **{'ENABLED' if new_state else 'DISABLED'}**.",
            ),
            ephemeral=True,
        )
        await self.refresh_panel()

    async def btn_bots_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("Only the command initiator can control this panel.", ephemeral=True)

        cfg = await security_service.get_security_config(self.guild.id)
        new_state = not bool(cfg.get("bot_protection_enabled", 1))
        await security_service.set_bot_protection(self.guild.id, new_state)
        await interaction.response.send_message(
            embed=success_embed(
                "Bot Guard Updated",
                f"Unauthorized bot interception is now **{'ENABLED' if new_state else 'DISABLED'}**.",
            ),
            ephemeral=True,
        )
        await self.refresh_panel()

    async def btn_whitelist_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("Only the command initiator can control this panel.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        rows = await security_service.list_whitelist(self.guild.id)
        if not rows:
            body = "*Whitelist is empty.*\nUse `/whitelist add user:@user` to exempt a trusted staff member."
        else:
            lines = []
            for row in rows[:25]:
                target = self.guild.get_member(row["target_id"]) or self.guild.get_role(row["target_id"])
                label = target.mention if target else f"`{row['target_id']}`"
                lines.append(f"• {label} — `{row.get('target_type', 'user')}`")
            body = "\n".join(lines)
        await interaction.followup.send(
            embed=info_embed("📋 Anti-Nuke Whitelist", body), ephemeral=True
        )

    async def btn_enable_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("Only the command initiator can control this panel.", ephemeral=True)

        await security_service.set_security_enabled(self.guild.id, True)
        await interaction.response.send_message(
            embed=success_embed(
                f"{Emojis.AN_ENABLED} Anti-Nuke Protection Active",
                "Anti-Nuke protection has been enabled! All gateway events and destruction vectors are actively protected."
            ),
            ephemeral=True,
        )
        await self.refresh_panel()

    async def btn_disable_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("Only the command initiator can control this panel.", ephemeral=True)

        confirm_view = AntiNukeDisableConfirmView(self, self.author_id)
        embed = warning_embed(
            "⚠️ Confirmation Required: Disable Anti-Nuke?",
            "Are you sure you want to disable Anti-Nuke protection?\n"
            "This will leave the server vulnerable to unauthorized channel, role, and webhook deletions."
        )
        await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)

    async def btn_lockdown_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("Only the command initiator can control this panel.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        count = await security_service.execute_lockdown(self.guild, lock=True)
        await interaction.followup.send(
            embed=warning_embed(
                f"{Emojis.AN_LOCKDOWN} Emergency Lockdown Activated",
                f"Successfully restricted `@everyone` in **{count}** text channels.\n"
                f"Use `/antinuke lockdown disable` to lift the lockdown when secure."
            ),
            ephemeral=True,
        )
        await self.refresh_panel()

    async def btn_refresh_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("Only the command initiator can control this panel.", ephemeral=True)

        await interaction.response.defer()
        await self.refresh_panel()

    async def refresh_panel(self):
        """Re-render the control panel embed and components."""
        if not self.message:
            return
        await self.init_components()
        embed = await self.cog.generate_control_panel_embed(self.guild)
        try:
            await self.message.edit(embed=embed, view=self)
        except Exception as e:
            logger.warning(f"Could not refresh control panel message: {e}")


# ==================== MAIN ANTI-NUKE COG ====================

class AntiNuke(commands.Cog):
    """Enterprise Server Protection & Anti-Nuke Security Suite."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # guild_id -> list[(joined_at_ts, member)]
        self._join_tracker: Dict[int, List[Tuple[float, discord.Member]]] = {}

    # ==================== STARTUP PRE-CACHING ====================

    @commands.Cog.listener()
    async def on_ready(self):
        """Pre-cache channels and roles for all connected guilds so recovery data is hot."""
        logger.info("Anti-Nuke initializing pre-cache for all connected guilds...")
        for guild in self.bot.guilds:
            try:
                security_service.cache_all_guild_channels(guild)
                security_service.cache_all_guild_roles(guild)
            except Exception as e:
                logger.warning(f"Could not pre-cache guild {guild.name}: {e}")
        logger.info("Anti-Nuke architecture pre-cache ready.")

    # ==================== DISCORD EVENT LISTENERS ====================

    # --- 1. CHANNEL CREATION / DELETION / UPDATE ---

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        event_time = time.perf_counter()
        security_service.cache_channel(channel)
        asyncio.create_task(
            security_service.process_security_event(
                guild=channel.guild,
                action_key="channel_create",
                audit_action=discord.AuditLogAction.channel_create,
                target_name=f"#{channel.name}",
                target_id=channel.id,
                event_time=event_time,
                target_obj=channel,
            )
        )

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        event_time = time.perf_counter()
        asyncio.create_task(
            security_service.process_security_event(
                guild=channel.guild,
                action_key="channel_delete",
                audit_action=discord.AuditLogAction.channel_delete,
                target_name=f"#{channel.name}",
                target_id=channel.id,
                event_time=event_time,
            )
        )

    @commands.Cog.listener()
    async def on_guild_channel_update(
        self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel
    ):
        event_time = time.perf_counter()
        security_service.cache_channel(after)

        # Channel-level overwrite escalation only counts server-wide dangerous grants;
        # routine staff overwrites (manage_messages, manage_channels on one channel) stay
        # on the normal channel_update vector so legitimate setup is not punished.
        dangerous = ("administrator", "manage_guild")
        escalated = False
        for target, after_ow in after.overwrites.items():
            before_ow = before.overwrites.get(target)
            for perm in dangerous:
                after_val = getattr(after_ow, perm)
                before_val = getattr(before_ow, perm) if before_ow else None
                if after_val is True and before_val is not True:
                    escalated = True
                    break
            if escalated:
                break

        asyncio.create_task(
            security_service.process_security_event(
                guild=before.guild,
                action_key="permission_escalation" if escalated else "channel_update",
                audit_action=discord.AuditLogAction.channel_update,
                target_name=f"#{after.name}",
                target_id=after.id,
                event_time=event_time,
                before_obj=before,
                after_obj=after,
            )
        )

    # --- 1b. AUDIT STREAM: VECTORS WITHOUT A GATEWAY EVENT ---

    AUDIT_STREAM_ROUTES = {
        "emoji_create": "emoji_create",
        "emoji_delete": "emoji_delete",
        "emoji_update": "emoji_update",
        "sticker_create": "sticker_create",
        "sticker_delete": "sticker_delete",
        "sticker_update": "sticker_update",
        "integration_create": "integration_create",
        "integration_delete": "integration_delete",
        "webhook_create": "webhook_create",
        "webhook_delete": "webhook_delete",
        "webhook_update": "webhook_change",
        "prune": "prune",
        "member_role_update": "role_grant",
        "member_move": "voice_abuse",
    }

    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry):
        """Feed audit-only vectors (emoji, sticker, integrations, webhooks, prune,
        role grants, force voice moves) into the same containment pipeline."""
        action_name = getattr(entry.action, "name", "")
        action_key = self.AUDIT_STREAM_ROUTES.get(action_name)
        if not action_key or not entry.guild:
            return

        target = entry.target
        target_name = getattr(target, "name", None) or str(target) or action_name
        target_id = getattr(target, "id", None)

        target_obj = None
        before_obj = None
        if action_key in ("webhook_create", "emoji_create", "sticker_create", "integration_create"):
            target_obj = target
        if action_key == "role_grant" and isinstance(target, discord.Member):
            try:
                before_roles = entry.changes.before.roles if entry.changes and entry.changes.before else None
            except Exception:
                before_roles = None
            if before_roles is not None:
                target_obj = target
                before_obj = SimpleNamespace(roles=before_roles)

        event_time = time.perf_counter()
        asyncio.create_task(
            security_service.process_security_event(
                guild=entry.guild,
                action_key=action_key,
                audit_action=entry.action,
                target_name=str(target_name),
                target_id=target_id,
                event_time=event_time,
                target_obj=target_obj,
                before_obj=before_obj,
                after_obj=target if action_key == "role_grant" else None,
                prefetched_entry=entry,
            )
        )

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: List[discord.Message]):
        """Mass purge detection on the gateway path (fastest signal)."""
        if not messages:
            return
        guild = messages[0].guild
        if guild is None:
            return
        event_time = time.perf_counter()
        asyncio.create_task(
            security_service.process_security_event(
                guild=guild,
                action_key="message_purge",
                audit_action=discord.AuditLogAction.message_bulk_delete,
                target_name=f"#{getattr(messages[0].channel, 'name', 'channel')}",
                target_id=messages[0].channel.id,
                event_time=event_time,
            )
        )

    @commands.Cog.listener()
    async def on_thread_delete(self, thread: discord.Thread):
        event_time = time.perf_counter()
        asyncio.create_task(
            security_service.process_security_event(
                guild=thread.guild,
                action_key="thread_delete",
                audit_action=discord.AuditLogAction.thread_delete,
                target_name=f"#{thread.name}",
                target_id=thread.id,
                event_time=event_time,
            )
        )

    # --- 2. ROLE CREATION / DELETION / UPDATE ---

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        event_time = time.perf_counter()
        security_service.cache_role(role)
        asyncio.create_task(
            security_service.process_security_event(
                guild=role.guild,
                action_key="role_create",
                audit_action=discord.AuditLogAction.role_create,
                target_name=f"@{role.name}",
                target_id=role.id,
                event_time=event_time,
                target_obj=role,
            )
        )

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        event_time = time.perf_counter()
        asyncio.create_task(
            security_service.process_security_event(
                guild=role.guild,
                action_key="role_delete",
                audit_action=discord.AuditLogAction.role_delete,
                target_name=f"@{role.name}",
                target_id=role.id,
                event_time=event_time,
            )
        )

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        event_time = time.perf_counter()
        security_service.cache_role(after)

        # Check for dangerous permission escalation
        is_escalation = (
            (not before.permissions.administrator and after.permissions.administrator)
            or (not before.permissions.manage_guild and after.permissions.manage_guild)
            or (not before.permissions.ban_members and after.permissions.ban_members)
            or (not before.permissions.mention_everyone and after.permissions.mention_everyone)
        )

        action_key = "permission_escalation" if is_escalation else "role_update"

        asyncio.create_task(
            security_service.process_security_event(
                guild=before.guild,
                action_key=action_key,
                audit_action=discord.AuditLogAction.role_update,
                target_name=f"@{after.name}",
                target_id=after.id,
                event_time=event_time,
                before_obj=before,
                after_obj=after,
            )
        )

    # --- 3. WEBHOOK PROTECTION (routed through the audit stream for exact action keys) ---

    # --- 4. MASS BANS & KICKS ---

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: Union[discord.User, discord.Member]):
        event_time = time.perf_counter()
        asyncio.create_task(
            security_service.process_security_event(
                guild=guild,
                action_key="ban",
                audit_action=discord.AuditLogAction.ban,
                target_name=str(user),
                target_id=user.id,
                event_time=event_time,
            )
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        event_time = time.perf_counter()
        guild = member.guild
        try:
            entry, status = await security_service.fetch_correlated_audit_entry(
                guild=guild,
                action=discord.AuditLogAction.kick,
                target_id=member.id,
                max_retries=2,
                initial_delay=0.1,
            )
            if entry and entry.user:
                asyncio.create_task(
                    security_service.process_security_event(
                        guild=guild,
                        action_key="kick",
                        audit_action=discord.AuditLogAction.kick,
                        target_name=str(member),
                        target_id=member.id,
                        event_time=event_time,
                    )
                )
        except Exception:
            pass

    # --- 5. SERVER SETTINGS & VANITY URL PROTECTION ---

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        diffs = []
        if before.name != after.name:
            diffs.append(f"Name changed from '{before.name}' to '{after.name}'")
        if before.icon != after.icon:
            diffs.append("Server icon modified")
        if hasattr(before, "vanity_url_code") and before.vanity_url_code != after.vanity_url_code:
            diffs.append(f"Vanity URL modified to '{after.vanity_url_code}'")

        if diffs:
            event_time = time.perf_counter()
            asyncio.create_task(
                security_service.process_security_event(
                    guild=after,
                    action_key="server_update",
                    audit_action=discord.AuditLogAction.guild_update,
                    target_name="Server Settings",
                    target_id=after.id,
                    event_time=event_time,
                    before_obj=before,
                    after_obj=after,
                )
            )

    # --- 6. BOT ADDITION & RAID SHIELD PROTECTION ---

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Intercept unauthorized bot additions and join raids immediately."""
        if not member.bot:
            await self._raid_shield_check(member)
            return

        guild = member.guild
        cfg = await security_service.get_security_config(guild.id)
        if not cfg.get("enabled", 1) or not cfg.get("bot_protection_enabled", 1):
            return

        # Check if the bot application is explicitly in approved bots
        if await security_service.is_bot_approved(guild.id, member.id):
            return

        event_time = time.perf_counter()

        # Correlate inviter
        entry, status = await security_service.fetch_correlated_audit_entry(
            guild=guild,
            action=discord.AuditLogAction.bot_add,
            target_id=member.id,
            max_retries=3,
        )
        inviter = entry.user if entry else None

        # Server owner is always exempt
        if inviter and inviter.id == guild.owner_id:
            return

        # Unauthorized bot detected: Evict bot immediately
        evicted = False
        try:
            await member.ban(reason="[NOVEXA Anti-Nuke] Unauthorized bot addition evicted")
            evicted = True
        except Exception:
            try:
                await member.kick(reason="[NOVEXA Anti-Nuke] Unauthorized bot addition evicted")
                evicted = True
            except Exception as e:
                logger.error(f"Failed to evict unauthorized bot {member} in {guild.name}: {e}")

        # Punish the inviter if member
        punishment_result = "NONE"
        if inviter and isinstance(inviter, discord.Member):
            inviter_punishment = "ban" if (cfg.get("mode") or "").lower() == "panic" else cfg.get("punishment_type", "ban")
            punishment_result = await security_service.execute_punishment(
                guild=guild,
                offender=inviter,
                reason=f"Added unauthorized bot {member.name}",
                punishment_type=inviter_punishment,
            )

        latency_ms = int(round((time.perf_counter() - event_time) * 1000))
        await security_service.log_incident(
            guild=guild,
            executor=inviter,
            action_type="bot_add",
            details=(
                f"Unauthorized bot addition detected: {member.mention} (`{member.id}`). "
                f"Bot eviction: {'SUCCESS' if evicted else 'FAILED'}."
            ),
            target_name=str(member),
            target_id=member.id,
            severity="HIGH",
            punishment_applied=punishment_result,
            restored=evicted,
            correlation_status=status,
            latency_ms=latency_ms,
        )

    async def _raid_shield_check(self, member: discord.Member):
        """Track joins per guild and evict young-account bursts during a raid."""
        guild = member.guild
        try:
            cfg = await security_service.get_security_config(guild.id)
        except Exception:
            return
        if not cfg.get("enabled", 1) or not cfg.get("raid_shield_enabled", 1):
            return

        threshold = int(cfg.get("raid_join_threshold") or 6)
        window = int(cfg.get("raid_window") or 15)
        min_age_days = int(cfg.get("raid_min_age_days") or 7)

        now = time.time()
        tracked = [item for item in self._join_tracker.get(guild.id, []) if now - item[0] <= window]
        tracked.append((now, member))
        self._join_tracker[guild.id] = tracked

        if len(tracked) < threshold:
            return

        cutoff = discord.utils.utcnow() - datetime.timedelta(days=min_age_days)
        suspects = [m for _, m in tracked if m.created_at > cutoff]
        if not suspects:
            return

        evicted = 0
        for suspect in suspects:
            try:
                await suspect.kick(
                    reason=f"[NOVEXA Anti-Nuke] Raid shield: account younger than {min_age_days} days during join burst"
                )
                evicted += 1
            except Exception:
                continue

        self._join_tracker[guild.id] = []

        await security_service.log_incident(
            guild=guild,
            executor=member,
            action_type="raid_join",
            details=(
                f"Join burst detected: `{len(tracked)}` joins within `{window}s` "
                f"(threshold `{threshold}`). Accounts younger than `{min_age_days}` days evicted: `{evicted}/{len(suspects)}`."
            ),
            target_name=str(member),
            target_id=member.id,
            severity="HIGH",
            punishment_applied="RAID_SHIELD",
            restored=evicted > 0,
            correlation_status="GATEWAY",
            latency_ms=0,
        )

    # ==================== EMBED GENERATOR ====================

    async def generate_control_panel_embed(self, guild: discord.Guild) -> discord.Embed:
        """Construct the live Anti-Nuke dashboard embed."""
        cfg = await security_service.get_security_config(guild.id)
        stats = await security_service.get_security_stats(guild.id)

        is_enabled = bool(cfg.get("enabled", 1))
        mode = str(cfg.get("mode", "medium")).upper()
        punishment = str(cfg.get("punishment_type", "ban")).replace("_", " ").upper()
        log_ch = guild.get_channel(cfg.get("log_channel_id", 0)) if cfg.get("log_channel_id") else None

        status_str = f"{Emojis.AN_ENABLED} **ACTIVE & ENFORCING**" if is_enabled else f"{Emojis.AN_DISABLED} **DISABLED / INACTIVE**"
        color = 0x10B981 if is_enabled else 0xEF4444

        embed = discord.Embed(
            title=f"🛡️ NOVEXA ADVANCED ANTI-NUKE CONTROL PANEL",
            description=(
                f"**Server:** `{guild.name}` (`{guild.id}`)\n"
                f"**Protection Status:** {status_str}\n"
                f"**Operating Mode:** `{mode} MODE` • **Action Policy:** `**{punishment}**`\n"
                f"**Alert Log Channel:** {log_ch.mention if log_ch else '`Auto-Detect / Not Set`'}\n"
            ),
            color=color,
            timestamp=discord.utils.utcnow(),
        )

        embed.add_field(
            name="⚡ Real-Time Benchmarks",
            value=(
                f"• Intercepted Attacks: **`{stats['total_incidents']}`**\n"
                f"• Executors Punished: **`{stats['banned_count']}`**\n"
                f"• Auto-Restored Objects: **`{stats['restored_count']}`**\n"
                f"• Avg Response Latency: **`{stats['avg_latency_ms']}ms`**"
            ),
            inline=True,
        )

        embed.add_field(
            name="🛡️ Monitored Vectors (26 Detection Routes)",
            value=(
                f"• **Channels:** Create / Delete / Rename / Overwrite Escalation\n"
                f"• **Roles:** Create / Delete / Perm Escalation / Mass Role Grants\n"
                f"• **Webhooks:** Create / Delete / Edit\n"
                f"• **Emoji & Stickers:** Create / Delete / Edit\n"
                f"• **Integrations:** Create / Delete\n"
                f"• **Messages:** Bulk Purge / Thread Deletion\n"
                f"• **Members:** Mass Bans / Kicks / Prune / Force Voice Moves\n"
                f"• **Bots:** Unauthorized Integrations\n"
                f"• **Raid Shield:** {'🟢 ON' if cfg.get('raid_shield_enabled', 1) else '🔴 OFF'}"
                f" • **Bot Guard:** {'🟢 ON' if cfg.get('bot_protection_enabled', 1) else '🔴 OFF'}"
            ),
            inline=True,
        )

        recent = stats.get("recent_incidents", [])
        if recent:
            lines = []
            for inc in recent[:3]:
                lines.append(
                    f"• `{inc.get('action_type', 'event')}` on **{inc.get('target_name', 'target')}** "
                    f"by `{inc.get('executor_tag', 'user')}` ➔ `{inc.get('punishment_applied', 'NONE')}` (`{inc.get('latency_ms', 0)}ms`)"
                )
            embed.add_field(name="📜 Recent Security Incidents", value="\n".join(lines), inline=False)
        else:
            embed.add_field(
                name="📜 Recent Security Incidents",
                value="*No attacks detected. All security parameters normal.*",
                inline=False,
            )

        embed.set_footer(text=f"{guild.name} • {BOT_NAME} Enterprise Security Core • Real-Time Protection")
        return embed

    # ==================== SLASH COMMANDS ====================

    antinuke_group = app_commands.Group(
        name="antinuke", description="Configure server security and anti-nuke protection"
    )

    @antinuke_group.command(
        name="panel", description="Open the real-time interactive Anti-Nuke Control Panel dashboard"
    )
    @has_admin_or_owner()
    async def slash_panel(self, interaction: discord.Interaction):
        """Interactive control panel entrypoint."""
        await interaction.response.defer()
        guild = interaction.guild
        embed = await self.generate_control_panel_embed(guild)
        view = AntiNukeControlPanelView(self, guild, interaction.user.id)
        await view.init_components()
        msg = await interaction.followup.send(embed=embed, view=view)
        view.message = msg

    @antinuke_group.command(
        name="settings", description="View current Anti-Nuke configurations and active thresholds"
    )
    @has_admin_or_owner()
    async def antinuke_settings(self, interaction: discord.Interaction):
        guild = interaction.guild
        cfg = await security_service.get_security_config(guild.id)
        stats = await security_service.get_security_stats(guild.id)

        embed = primary_embed(title=f"🛡️ Anti-Nuke Security — {guild.name}")
        status = f"{Emojis.AN_ENABLED} Active" if cfg.get("enabled", 1) else f"{Emojis.AN_DISABLED} Disabled"
        mode = str(cfg.get("mode", "medium")).upper()
        punishment = str(cfg.get("punishment_type", "ban")).replace("_", " ").upper()
        window = cfg.get("time_window", 10)

        embed.add_field(name="Protection Status", value=status, inline=True)
        embed.add_field(name="Security Mode", value=f"`{mode}`", inline=True)
        embed.add_field(name="Active Punishment", value=f"**{punishment}**", inline=True)

        embed.add_field(
            name="Channel Deletions",
            value=f"{cfg.get('max_channel_deletions', 2)} / {window}s",
            inline=True,
        )
        embed.add_field(
            name="Channel Creations", value=f"{cfg.get('max_channel_creations', 3)} / {window}s", inline=True
        )
        embed.add_field(
            name="Channel Updates", value=f"{cfg.get('max_channel_updates', 4)} / {window}s", inline=True
        )
        embed.add_field(
            name="Role Deletions", value=f"{cfg.get('max_role_deletions', 2)} / {window}s", inline=True
        )
        embed.add_field(
            name="Role Creations", value=f"{cfg.get('max_role_creations', 3)} / {window}s", inline=True
        )
        embed.add_field(
            name="Permission Escalation", value=f"{cfg.get('max_permission_changes', 5)} / 15s", inline=True
        )

        embed.add_field(name="Mass Bans Limit", value=f"{cfg.get('max_bans', 3)} / {window}s", inline=True)
        embed.add_field(name="Mass Kicks Limit", value=f"{cfg.get('max_kicks', 4)} / {window}s", inline=True)
        embed.add_field(
            name="Webhook Creations", value=f"{cfg.get('max_webhook_creations', 2)} / {window}s", inline=True
        )
        embed.add_field(
            name="Webhook Deletions", value=f"{cfg.get('max_webhook_deletions', 2)} / {window}s", inline=True
        )

        raid_on = bool(cfg.get("raid_shield_enabled", 1))
        bot_on = bool(cfg.get("bot_protection_enabled", 1))
        embed.add_field(
            name="Raid Shield",
            value=f"{'🟢 ON' if raid_on else '🔴 OFF'} ({cfg.get('raid_join_threshold', 6)} joins / {cfg.get('raid_window', 15)}s)",
            inline=True,
        )
        embed.add_field(name="Bot Guard", value=f"{'🟢 ON' if bot_on else '🔴 OFF'}", inline=True)

        whitelist = await security_service.list_whitelist(guild.id)
        approved = await security_service.list_approved_bots(guild.id)
        embed.add_field(
            name="Access Entries",
            value=f"Whitelist: **{len(whitelist)}** • Approved Bots: **{len(approved)}**",
            inline=True,
        )

        embed.add_field(
            name="Avg Response Latency",
            value=f"`{stats['avg_latency_ms']}ms`",
            inline=True,
        )
        log_ch = guild.get_channel(cfg.get("log_channel_id", 0)) if cfg.get("log_channel_id") else None
        embed.add_field(
            name="Log Channel", value=log_ch.mention if log_ch else "*Not set (Auto-Detect)*", inline=True
        )

        embed.set_footer(text=f"{BOT_NAME} Enterprise Anti-Nuke Engine • Use /antinuke panel for dashboard")
        await interaction.response.send_message(embed=embed)

    @antinuke_group.command(name="toggle", description="Enable or disable the Anti-Nuke security suite")
    @has_admin_or_owner()
    @app_commands.describe(enabled="Turn anti-nuke protection on or off")
    async def antinuke_toggle(self, interaction: discord.Interaction, enabled: bool):
        if not enabled:
            # Require confirmation before disabling
            confirm_view = AntiNukeDisableConfirmView(None, interaction.user.id)  # type: ignore
            embed = warning_embed(
                "⚠️ Confirmation Required: Disable Anti-Nuke?",
                "Are you sure you want to disable Anti-Nuke protection?\n"
                "This leaves your server unprotected against mass deletions and permission escalations.",
            )
            return await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)

        await security_service.set_security_enabled(interaction.guild_id, True)
        await interaction.response.send_message(
            embed=success_embed(
                f"{Emojis.AN_ENABLED} Anti-Nuke Enabled",
                "Anti-Nuke protection has been successfully activated for this server.",
            ),
            ephemeral=True,
        )

    @antinuke_group.command(name="enable", description="Turn Anti-Nuke protection ON (all detection routes armed)")
    @has_admin_or_owner()
    async def antinuke_enable(self, interaction: discord.Interaction):
        await security_service.set_security_enabled(interaction.guild_id, True)
        cfg = await security_service.get_security_config(interaction.guild_id)
        await interaction.response.send_message(
            embed=success_embed(
                f"{Emojis.AN_ENABLED} Anti-Nuke Protection Enabled",
                f"All detection routes are armed in **{str(cfg.get('mode', 'medium')).upper()} MODE**.\n"
                f"Punishment policy: **{str(cfg.get('punishment_type', 'ban')).replace('_', ' ').upper()}**.\n"
                f"Raid Shield: **{'ON' if cfg.get('raid_shield_enabled', 1) else 'OFF'}** • "
                f"Bot Guard: **{'ON' if cfg.get('bot_protection_enabled', 1) else 'OFF'}**.",
            ),
            ephemeral=True,
        )

    @antinuke_group.command(name="disable", description="Turn Anti-Nuke protection OFF (requires confirmation)")
    @has_admin_or_owner()
    async def antinuke_disable(self, interaction: discord.Interaction):
        cfg = await security_service.get_security_config(interaction.guild_id)
        if not cfg.get("enabled", 1):
            return await interaction.response.send_message(
                embed=info_embed("Already Disabled", "Anti-Nuke protection is currently OFF. Use `/antinuke enable` to arm it."),
                ephemeral=True,
            )

        confirm_view = AntiNukeDisableConfirmView(None, interaction.user.id)  # type: ignore
        embed = warning_embed(
            "⚠️ Confirmation Required: Disable Anti-Nuke?",
            "Are you sure you want to disable Anti-Nuke protection?\n"
            "This leaves your server unprotected against mass deletions, permission escalations, "
            "webhook injection, bot additions and join raids.",
        )
        await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)

    # --- THRESHOLD TUNING ---

    @antinuke_group.command(name="threshold", description="Set the trigger count for a detection vector")
    @has_admin_or_owner()
    @app_commands.describe(
        vector="Detection vector to tune",
        limit="Number of actions that triggers containment (1-25)",
        window="Optional: sliding window in seconds (5-120)",
    )
    @app_commands.choices(
        vector=[
            app_commands.Choice(name=ACTION_LABELS[key], value=key)
            for key in sorted(CONFIG_LIMIT_COLUMNS, key=lambda k: ACTION_LABELS.get(k, k))
        ]
    )
    async def antinuke_threshold(
        self,
        interaction: discord.Interaction,
        vector: app_commands.Choice[str],
        limit: app_commands.Range[int, 1, 25],
        window: Optional[app_commands.Range[int, 5, 120]] = None,
    ):
        ok = await security_service.set_security_threshold(interaction.guild_id, vector.value, limit)
        if not ok:
            return await interaction.response.send_message(
                embed=error_embed("Not Configurable", "That vector has a fixed threshold."), ephemeral=True
            )
        if window is not None:
            await security_service.set_security_time_window(interaction.guild_id, window)

        cfg = await security_service.get_security_config(interaction.guild_id)
        await interaction.response.send_message(
            embed=success_embed(
                "Threshold Updated",
                f"**{vector.name}** now triggers after **{limit}** action(s) within "
                f"**{cfg.get('time_window', 30)}s**.",
            ),
            ephemeral=True,
        )

    @antinuke_group.command(name="thresholds", description="Show every active detection threshold")
    @has_admin_or_owner()
    async def antinuke_thresholds(self, interaction: discord.Interaction):
        cfg = await security_service.get_security_config(interaction.guild_id)
        window = cfg.get("time_window", 30)
        lines = []
        for key, column in CONFIG_LIMIT_COLUMNS.items():
            lines.append(f"• **{ACTION_LABELS.get(key, key)}** — `{cfg.get(column, '?')}` / `{window}s`")
        embed = primary_embed(
            title=f"🎚️ Detection Thresholds — {interaction.guild.name}",
            description="\n".join(lines),
        )
        embed.set_footer(text=f"{cfg.get('mode', 'medium').upper()} MODE • Use /antinuke threshold to tune")
        await interaction.response.send_message(embed=embed)

    # --- RAID SHIELD ---

    @antinuke_group.command(name="raid-enable", description="Enable join-burst raid protection")
    @has_admin_or_owner()
    async def antinuke_raid_enable(self, interaction: discord.Interaction):
        await security_service.set_raid_shield(interaction.guild_id, True)
        cfg = await security_service.get_security_config(interaction.guild_id)
        await interaction.response.send_message(
            embed=success_embed(
                "Raid Shield Enabled",
                f"Join bursts of **{cfg.get('raid_join_threshold', 6)}** members within "
                f"**{cfg.get('raid_window', 15)}s** evict accounts younger than "
                f"**{cfg.get('raid_min_age_days', 7)} days**.",
            ),
            ephemeral=True,
        )

    @antinuke_group.command(name="raid-disable", description="Disable join-burst raid protection")
    @has_admin_or_owner()
    async def antinuke_raid_disable(self, interaction: discord.Interaction):
        await security_service.set_raid_shield(interaction.guild_id, False)
        await interaction.response.send_message(
            embed=warning_embed("Raid Shield Disabled", "Join-burst protection is now OFF."),
            ephemeral=True,
        )

    @antinuke_group.command(
        name="mode", description="Switch Anti-Nuke protection mode (LOW, MEDIUM, HIGH, PANIC)"
    )
    @has_admin_or_owner()
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="LOW — Log suspicious activity without auto-punishment", value="low"),
            app_commands.Choice(
                name="MEDIUM — Standard balanced threshold response (Recommended)", value="medium"
            ),
            app_commands.Choice(
                name="HIGH — Instant aggressive response on any destructive action", value="high"
            ),
            app_commands.Choice(
                name="PANIC — One strike: instant ban + revert of every change", value="panic"
            ),
        ]
    )
    async def antinuke_mode(self, interaction: discord.Interaction, mode: app_commands.Choice[str]):
        await security_service.set_security_mode(interaction.guild_id, mode.value)
        await interaction.response.send_message(
            embed=success_embed(
                f"Protection Mode Set: {mode.value.upper()}",
                f"Anti-Nuke is now operating in **{mode.name}**.",
            ),
            ephemeral=True,
        )

    @antinuke_group.command(name="punishment", description="Set offender punishment policy")
    @has_admin_or_owner()
    @app_commands.choices(
        punishment=[
            app_commands.Choice(name="Ban Offender (Permanent eviction)", value="ban"),
            app_commands.Choice(name="Kick Offender", value="kick"),
            app_commands.Choice(name="Quarantine (Strip Roles + 24h Timeout)", value="quarantine"),
            app_commands.Choice(name="1-Hour Timeout", value="timeout"),
            app_commands.Choice(name="Revoke Permissions (Strip dangerous admin roles)", value="revoke_perms"),
            app_commands.Choice(name="Monitor Only (Log alerts without punishing)", value="monitor"),
        ]
    )
    async def antinuke_punishment(
        self, interaction: discord.Interaction, punishment: app_commands.Choice[str]
    ):
        await security_service.set_security_punishment(interaction.guild_id, punishment.value)
        await interaction.response.send_message(
            embed=success_embed(
                "Punishment Policy Updated", f"Anti-nuke punishment set to: **{punishment.name}**"
            ),
            ephemeral=True,
        )

    @antinuke_group.command(
        name="lockdown", description="Emergency lockdown: Restrict all normal members from chatting"
    )
    @has_admin_or_owner()
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Enable Emergency Lockdown", value="enable"),
            app_commands.Choice(name="Disable Lockdown (Restore)", value="disable"),
        ]
    )
    async def antinuke_lockdown(
        self, interaction: discord.Interaction, action: app_commands.Choice[str]
    ):
        await interaction.response.defer()
        lock = action.value == "enable"
        count = await security_service.execute_lockdown(interaction.guild, lock=lock)

        status_text = (
            f"{Emojis.AN_LOCKDOWN} Emergency Lockdown Activated" if lock else "🔓 Lockdown Lifted"
        )
        embed = warning_embed(
            status_text,
            f"Successfully updated **{count}** text channels.\n"
            f"Chatting permissions for `@everyone` have been {'revoked' if lock else 'restored'}.",
        )
        await interaction.followup.send(embed=embed)

    @antinuke_group.command(name="channel", description="Configure dedicated security alert channel")
    @has_admin_or_owner()
    @app_commands.describe(channel="Text channel to receive security incident embeds")
    async def antinuke_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await security_service.set_security_log_channel(interaction.guild_id, channel.id)
        await interaction.response.send_message(
            embed=success_embed(
                "Alert Channel Configured", f"Security incident logs will now be posted in {channel.mention}."
            ),
            ephemeral=True,
        )

    @antinuke_group.command(name="setup-logs", description="Auto-provision the private 'novexa-security-logs' channel")
    @has_admin_or_owner()
    async def antinuke_setup_logs(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        existing = await security_service.get_or_create_log_channel(guild)
        if existing:
            return await interaction.followup.send(
                embed=info_embed("Log Channel Ready", f"Security alerts are dispatched to {existing.mention}.")
            )

        category = discord.utils.get(guild.categories, name="🛡️ NOVEXA SECURITY")
        if not category:
            category = await guild.create_category(
                name="🛡️ NOVEXA SECURITY",
                reason="[NOVEXA] Security logs provisioning",
            )
            await category.edit(
                overwrites={
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True),
                }
            )

        channel = await guild.create_text_channel(
            name="novexa-security-logs",
            category=category,
            topic="Official real-time security alerts, incident logs, and anti-nuke audit records.",
            reason="[NOVEXA] Security logs channel creation",
        )
        await security_service.set_security_log_channel(guild.id, channel.id)
        await interaction.followup.send(
            embed=success_embed(
                "Security Logs Provisioned",
                f"Created private channel {channel.mention} under **{category.name}**.\n"
                f"All security alerts will now be dispatched there automatically.",
            )
        )

    @antinuke_group.command(name="stats", description="View detection latency benchmarks and attack logs")
    @has_admin_or_owner()
    async def antinuke_stats(self, interaction: discord.Interaction):
        stats = await security_service.get_security_stats(interaction.guild_id)
        embed = primary_embed(
            title=f"📊 Anti-Nuke Latency & Benchmarks — {interaction.guild.name}",
            description=(
                f"**Total Incidents Intercepted:** `{stats['total_incidents']}`\n"
                f"**Rogue Executors Punished:** `{stats['banned_count']}`\n"
                f"**Auto-Restored Channels & Roles:** `{stats['restored_count']}`\n"
                f"**Average Response Latency:** `{stats['avg_latency_ms']}ms`\n\n"
                f"*(Real-time measurement from Discord gateway event receipt to containment completion)*"
            ),
        )

        recent = stats.get("recent_incidents", [])
        if recent:
            lines = []
            for inc in recent[:5]:
                lines.append(
                    f"• **{inc.get('action_type', 'event')}** on `{inc.get('target_name', 'target')}` "
                    f"by `{inc.get('executor_tag', 'user')}` ➔ `{inc.get('punishment_applied')}` (`{inc.get('latency_ms', 0)}ms`)"
                )
            embed.add_field(name="Recent Intercepted Incidents", value="\n".join(lines), inline=False)

        await interaction.response.send_message(embed=embed)

    # ==================== PREFIX COMMAND COMPATIBILITY ====================

    @commands.command(name="antinuke", aliases=["an", "securitypanel"])
    @commands.has_permissions(administrator=True)
    async def prefix_antinuke(self, ctx: commands.Context, state: Optional[str] = None):
        """Prefix command: panel, or `antinuke on|off` for a fast enable/disable."""
        lowered = (state or "").lower()
        if lowered in ("on", "enable", "start"):
            await security_service.set_security_enabled(ctx.guild.id, True)
            return await ctx.send(
                embed=success_embed(
                    f"{Emojis.AN_ENABLED} Anti-Nuke Enabled",
                    "All detection routes are armed.",
                )
            )
        if lowered in ("off", "disable", "stop"):
            view = AntiNukeDisableConfirmView(None, ctx.author.id)  # type: ignore
            return await ctx.send(
                embed=warning_embed(
                    "⚠️ Confirmation Required: Disable Anti-Nuke?",
                    "This leaves the server unprotected. Confirm below to disable.",
                ),
                view=view,
            )

        embed = await self.generate_control_panel_embed(ctx.guild)
        view = AntiNukeControlPanelView(self, ctx.guild, ctx.author.id)
        await view.init_components()
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg

    @commands.command(name="lockdown", aliases=["serverlock"])
    @commands.has_permissions(administrator=True)
    async def prefix_lockdown(self, ctx: commands.Context, state: str = "enable"):
        """Emergency lockdown prefix shortcut."""
        lock = state.lower() in ("enable", "on", "start", "lock")
        count = await security_service.execute_lockdown(ctx.guild, lock=lock)
        status_text = (
            f"{Emojis.AN_LOCKDOWN} Emergency Lockdown Activated" if lock else "🔓 Lockdown Lifted"
        )
        embed = warning_embed(
            status_text,
            f"Successfully updated **{count}** text channels.\n"
            f"Chatting permissions for `@everyone` have been {'revoked' if lock else 'restored'}.",
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(AntiNuke(bot))
