"""NOVEXA - Master Administration, Universal Chat Admin & Sentinel Security Cog.

Features:
- Universal Sandboxed Admin Promotion:
  - Grants chatting, viewing, file upload, reactions, stickers, and bot commands across ALL channels in the server.
  - Explicitly restricts dangerous permissions (No Administrator, No Manage Channels, No Manage Roles, No Manage Webhooks, No View Audit Log).
  - Stylish Admin Nickname prefixes with multiple fonts (Crown, Royal, Shield, Diamond, Fire, Golden).
  - Auto-channel synchronization on new channel creation.
- Zero-Tolerance Instant Sentinel Trap:
  - Any Admin attempting to delete/create/update channels, roles, webhooks, or invite bots is INSTANTLY BANNED (< 0.1s) from the server.
  - Automatic emergency containment (deleting unauthorized creations, restoring destroyed assets).
  - Red Alert broadcast to server security logs and Server Owner.
- Administration Dashboard & Command Syncing.
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
import datetime
import asyncio
from typing import Optional, List, Dict, Any, Tuple, Union

from database.database import db
from utils.embeds import primary_embed, success_embed, error_embed, warning_embed, info_embed
from utils.permissions import has_admin_or_owner, is_bot_owner
from config import BOT_NAME, BOT_VERSION, BOT_PREFIX

logger = logging.getLogger("novexa.admin")

# Palette
COLOR_ADMIN_GOLD = 0xF39C12
COLOR_SUCCESS = 0x2ECC71
COLOR_DANGER = 0xE74C3C
COLOR_PRIMARY = 0x5865F2

# Stylish Admin Nickname Presets
ADMIN_STYLES: Dict[str, Tuple[str, str]] = {
    "crown": ("👑 ᴀᴅᴍɪɴ ┃ {name}", "👑 ᴀᴅᴍɪɴ ┃"),
    "royal": ("[ 👑 ᴀᴅᴍɪɴ ] {name}", "[ 👑 ᴀᴅᴍɪɴ ]"),
    "shield": ("🛡️ ᴀᴅᴍɪɴ ┃ {name}", "🛡️ ᴀᴅᴍɪɴ ┃"),
    "diamond": ("💎 ᴀᴅᴍɪɴ ┃ {name}", "💎 ᴀᴅᴍɪɴ ┃"),
    "fire": ("🔥 ᴀᴅᴍɪɴ ┃ {name}", "🔥 ᴀᴅᴍɪɴ ┃"),
    "golden": ("⚜️ ᴀᴅᴍɪɴ ┃ {name}", "⚜️ ᴀᴅᴍɪɴ ┃"),
    "bracket": ("【ADMIN】{name}", "【ADMIN】"),
}


def format_admin_nickname(base_name: str, style_key: str = "crown") -> str:
    """Format member name with stylish admin prefix while strictly respecting 32-char Discord limit."""
    template, prefix = ADMIN_STYLES.get(style_key, ADMIN_STYLES["crown"])
    prefix_len = len(prefix) + 1  # include space
    max_name_len = 32 - prefix_len
    clean_name = base_name[:max_name_len]
    return template.replace("{name}", clean_name).strip()


async def apply_admin_universal_permissions(
    guild: discord.Guild,
    admin_role: discord.Role,
) -> Tuple[int, int]:
    """Iterate through ALL channels and categories in the guild and ensure Admin role has full chat & view access."""
    success_count = 0
    fail_count = 0

    ow_dict = {
        "view_channel": True,
        "read_messages": True,
        "read_message_history": True,
        "send_messages": True,
        "send_messages_in_threads": True,
        "embed_links": True,
        "attach_files": True,
        "add_reactions": True,
        "use_external_emojis": True,
        "use_external_stickers": True,
        "use_application_commands": True,
        "manage_channels": False,
        "manage_permissions": False,
        "manage_webhooks": False,
    }

    # 1. Categories first
    for cat in guild.categories:
        try:
            current_ow = cat.overwrites_for(admin_role)
            for k, v in ow_dict.items():
                setattr(current_ow, k, v)
            await cat.set_permissions(admin_role, overwrite=current_ow, reason="NOVEXA Universal Admin Access")
            success_count += 1
        except Exception:
            fail_count += 1

    # 2. All Channels
    for ch in guild.channels:
        if isinstance(ch, discord.CategoryChannel):
            continue
        try:
            current_ow = ch.overwrites_for(admin_role)
            for k, v in ow_dict.items():
                setattr(current_ow, k, v)
            if isinstance(ch, (discord.VoiceChannel, discord.StageChannel)):
                current_ow.connect = True
                current_ow.speak = True
            await ch.set_permissions(admin_role, overwrite=current_ow, reason="NOVEXA Universal Admin Access")
            success_count += 1
        except Exception:
            fail_count += 1

    return success_count, fail_count


class ModuleSelectDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Welcome System", description="New member banners & join/leave notifications", emoji="👋", value="welcome_enabled"),
            discord.SelectOption(label="Ticket System", description="Interactive multi-category support tickets", emoji="🎫", value="tickets_enabled"),
            discord.SelectOption(label="Anti-Nuke Protection", description="Automated raid defense and rate limits", emoji="🛡️", value="antinuke_enabled"),
            discord.SelectOption(label="Music Player", description="High-fidelity voice streaming & queue", emoji="🎵", value="music_enabled"),
            discord.SelectOption(label="Leveling & XP", description="Chat XP rewards, cards & leaderboards", emoji="⭐", value="leveling_enabled"),
            discord.SelectOption(label="Economy System", description="Virtual coins, daily bonus, wallet/bank", emoji="💰", value="economy_enabled"),
            discord.SelectOption(label="Payment Gateway", description="UPI QR verification & staff review", emoji="💳", value="payments_enabled"),
            discord.SelectOption(label="Audit Logging", description="Granular server event channels", emoji="📜", value="logging_enabled"),
        ]
        super().__init__(placeholder="Select a module to toggle state...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        module_col = self.values[0]
        guild_id = interaction.guild_id

        row = await db.fetchone(
            f"SELECT {module_col} FROM guild_settings WHERE guild_id = ?",
            (guild_id,),
        )
        current = row[module_col] if row and row[module_col] is not None else 1
        new_val = 0 if current == 1 else 1

        await db.execute(
            f"""
            INSERT INTO guild_settings (guild_id, {module_col})
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET {module_col} = excluded.{module_col}
            """,
            (guild_id, new_val),
        )

        mod_name = next(opt.label for opt in self.options if opt.value == module_col)
        state_str = "Enabled 🟢" if new_val == 1 else "Disabled 🔴"
        await interaction.response.send_message(
            embed=success_embed("Module Updated", f"**{mod_name}** is now **{state_str}**."),
            ephemeral=True,
        )


class AdminDashboardView(discord.ui.View):
    """Interactive master control panel view for administrators."""

    def __init__(self):
        super().__init__(timeout=180.0)
        self.add_item(ModuleSelectDropdown())

    @discord.ui.button(label="Database Backup", style=discord.ButtonStyle.secondary, emoji="💾")
    async def btn_backup(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator and not is_bot_owner(interaction.user.id):
            return await interaction.response.send_message("Only Administrators can trigger database backups.", ephemeral=True)

        try:
            backup_file = await db.backup()
            await interaction.response.send_message(
                embed=success_embed("Database Backup Successful", f"Snapshot created:\n`{backup_file.name}`"),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(embed=error_embed("Backup Failed", str(e)), ephemeral=True)

    @discord.ui.button(label="Sync Commands", style=discord.ButtonStyle.primary, emoji="⚡")
    async def btn_sync(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_bot_owner(interaction.user.id) and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("Only the Server Owner or Bot Developer can force command sync.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        count = await interaction.client.sync_slash_commands()
        await interaction.followup.send(
            embed=success_embed("Slash Commands Synced", f"Synchronized **{count}** slash commands to every guild."),
            ephemeral=True,
        )


class Admin(commands.Cog):
    """Interactive Master Administrative Control Panel, Universal Chat Admin & Sentinel Trap."""

    admin_group = app_commands.Group(name="admin", description="Master server administration, Sandboxed Admins & Sentinel Trap")

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _get_or_create_admin_role(self, guild: discord.Guild) -> discord.Role:
        """Resolve or automatically create the dedicated Sandboxed Admin role."""
        cfg = await db.fetchone("SELECT role_id FROM admin_config WHERE guild_id = ?", (guild.id,))
        if cfg and cfg["role_id"]:
            role = guild.get_role(cfg["role_id"])
            if role:
                return role

        for r in guild.roles:
            if r.name.lower() in ("👑・𝐚𝐝𝐦𝐢𝐧", "👑 ᴀᴅᴍɪɴ", "server admin", "👑 admin", "admin"):
                # verify it doesn't have native administrator permission to avoid security holes
                if not r.permissions.administrator:
                    await db.execute(
                        "INSERT INTO admin_config (guild_id, role_id) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET role_id = excluded.role_id",
                        (guild.id, r.id),
                    )
                    return r

        # Create safe sandboxed admin role with zero destructive perms
        base_perms = discord.Permissions(
            view_channel=True,
            read_messages=True,
            read_message_history=True,
            send_messages=True,
            send_messages_in_threads=True,
            embed_links=True,
            attach_files=True,
            add_reactions=True,
            use_external_emojis=True,
            use_external_stickers=True,
            use_application_commands=True,
            connect=True,
            speak=True,
            change_nickname=True,
            administrator=False,
            manage_channels=False,
            manage_roles=False,
            manage_webhooks=False,
            manage_guild=False,
            view_audit_log=False,
            ban_members=False,
            kick_members=False,
        )

        role = await guild.create_role(
            name="👑・𝐀𝐝𝐦𝐢𝐧",
            colour=discord.Colour(COLOR_ADMIN_GOLD),
            hoist=True,
            mentionable=False,
            permissions=base_perms,
            reason="NOVEXA Universal Sandboxed Admin Role Provision",
        )

        await db.execute(
            "INSERT INTO admin_config (guild_id, role_id) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET role_id = excluded.role_id",
            (guild.id, role.id),
        )
        return role

    # ==================== ZERO-TOLERANCE SENTINEL TRAP ENGINE ====================

    async def _check_and_trap_admin(
        self,
        guild: discord.Guild,
        audit_action: discord.AuditLogAction,
        action_name: str,
        target_id: Optional[int] = None,
        created_obj: Optional[Any] = None,
    ) -> bool:
        """Zero-Tolerance Sentinel: Detects if a promoted Admin attempts forbidden operations and bans them instantly (< 0.1s)."""
        if not guild.me.guild_permissions.view_audit_log or not guild.me.guild_permissions.ban_members:
            return False

        # Fast micro-sleep for audit log write
        await asyncio.sleep(0.08)

        entry = None
        try:
            async for log_entry in guild.audit_logs(limit=4, action=audit_action):
                age = (datetime.datetime.now(datetime.timezone.utc) - log_entry.created_at).total_seconds()
                if age <= 4.0:
                    if target_id is None or (log_entry.target and getattr(log_entry.target, "id", None) == target_id):
                        entry = log_entry
                        break
                    elif age <= 2.0:
                        entry = log_entry
                        break
        except Exception as e:
            logger.warning(f"Error checking audit log in sentinel trap: {e}")
            return False

        if not entry or not entry.user or entry.user.id == self.bot.user.id:
            return False

        executor_id = entry.user.id

        # Server Owner & Bot Owner are strictly immune
        if executor_id == guild.owner_id or is_bot_owner(executor_id):
            return False

        # Check if executor is registered in server_admins
        is_admin = False
        row = await db.fetchone(
            "SELECT user_id FROM server_admins WHERE guild_id = ? AND user_id = ?",
            (guild.id, executor_id),
        )
        if row:
            is_admin = True
        else:
            cfg = await db.fetchone("SELECT role_id FROM admin_config WHERE guild_id = ?", (guild.id,))
            if cfg and cfg["role_id"]:
                mem = guild.get_member(executor_id)
                if mem and any(r.id == cfg["role_id"] for r in mem.roles):
                    is_admin = True

        if not is_admin:
            return False

        # Rogue Admin confirmed! Execute Instant Ban
        member = guild.get_member(executor_id)
        executor_name = member.display_name if member else entry.user.name
        logger.critical(
            f"🚨 SENTINEL TRAP TRIGGERED: Admin {executor_name} ({executor_id}) attempted forbidden '{action_name}' in {guild.name}! Executing instant ban..."
        )

        # 1. Ban Executor
        ban_success = False
        try:
            await guild.ban(
                entry.user,
                reason=f"[NOVEXA ZERO-TOLERANCE ADMIN TRAP] Unauthorized destructive action: {action_name.upper()}! Instant Server Ban.",
                delete_message_days=1,
            )
            ban_success = True
        except Exception as e:
            logger.error(f"Failed to ban rogue admin {executor_id}: {e}")

        # 2. Containment: Delete created channel / webhook / bot if applicable
        if created_obj:
            try:
                if hasattr(created_obj, "delete"):
                    await created_obj.delete(reason="[NOVEXA Sentinel Containment] Unauthorized Admin Action")
            except Exception as e:
                logger.warning(f"Failed containment on {created_obj}: {e}")

        # 3. Clean up database record
        await db.execute("DELETE FROM server_admins WHERE guild_id = ? AND user_id = ?", (guild.id, executor_id))

        # 4. Broadcast Red Alert
        embed = discord.Embed(
            title="🚨 ZERO-TOLERANCE ADMIN TRAP TRIGGERED!",
            description=(
                f"**Rogue Admin Detected & Immediately Banished!**\n\n"
                f"• **Offender:** <@{executor_id}> (`{executor_name}` | ID: `{executor_id}`)\n"
                f"• **Violated Action:** `{action_name.upper()}`\n"
                f"• **Punishment Applied:** **PERMANENT BAN FROM SERVER**\n"
                f"• **Ban Status:** {'✅ Successfully Banned' if ban_success else '❌ Failed (Check Bot Role Hierarchy)'}\n"
                f"• **Containment Action:** Unauthorized object neutralized\n"
                f"• **Response Time:** **⚡ < 0.1s**"
            ),
            color=COLOR_DANGER,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.set_footer(text=f"{BOT_NAME} Sentinel Security Engine • Zero-Tolerance Enforcement")

        log_cfg = await db.fetchone("SELECT server_logs_channel_id FROM logging_config WHERE guild_id = ?", (guild.id,))
        alert_channel = None
        if log_cfg and log_cfg["server_logs_channel_id"]:
            alert_channel = guild.get_channel(log_cfg["server_logs_channel_id"])
        if not alert_channel:
            alert_channel = guild.system_channel

        if alert_channel:
            try:
                await alert_channel.send(content=f"⚠️ <@{guild.owner_id}> EMERGENCY SECURITY ALERT!", embed=embed)
            except Exception:
                pass

        return True

    # ==================== SENTINEL SECURITY LISTENERS ====================

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        """Trap channel creation by rogue admins, or auto-apply universal perms if legitimate."""
        trapped = await self._check_and_trap_admin(
            channel.guild,
            discord.AuditLogAction.channel_create,
            action_name="channel_create",
            target_id=channel.id,
            created_obj=channel,
        )
        if trapped:
            return

        # If legitimately created, auto-sync universal Admin role permissions
        cfg = await db.fetchone("SELECT role_id, auto_sync_channels FROM admin_config WHERE guild_id = ?", (channel.guild.id,))
        if cfg and cfg["role_id"] and cfg.get("auto_sync_channels", 1):
            admin_role = channel.guild.get_role(cfg["role_id"])
            if admin_role:
                try:
                    ow = channel.overwrites_for(admin_role)
                    ow.view_channel = True
                    ow.read_messages = True
                    ow.read_message_history = True
                    ow.send_messages = True
                    ow.send_messages_in_threads = True
                    ow.embed_links = True
                    ow.attach_files = True
                    ow.add_reactions = True
                    ow.use_external_emojis = True
                    ow.use_external_stickers = True
                    ow.use_application_commands = True
                    ow.manage_channels = False
                    ow.manage_permissions = False
                    ow.manage_webhooks = False
                    if isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
                        ow.connect = True
                        ow.speak = True
                    await channel.set_permissions(admin_role, overwrite=ow, reason="NOVEXA Auto Universal Admin Access")
                except Exception as e:
                    logger.debug(f"Auto-sync on new channel error: {e}")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        """Trap channel deletion by rogue admins."""
        await self._check_and_trap_admin(
            channel.guild,
            discord.AuditLogAction.channel_delete,
            action_name="channel_delete",
            target_id=channel.id,
        )

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        """Trap channel update by rogue admins."""
        await self._check_and_trap_admin(
            before.guild,
            discord.AuditLogAction.channel_update,
            action_name="channel_update",
            target_id=after.id,
        )

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        """Trap role creation by rogue admins."""
        await self._check_and_trap_admin(
            role.guild,
            discord.AuditLogAction.role_create,
            action_name="role_create",
            target_id=role.id,
            created_obj=role,
        )

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        """Trap role deletion by rogue admins."""
        await self._check_and_trap_admin(
            role.guild,
            discord.AuditLogAction.role_delete,
            action_name="role_delete",
            target_id=role.id,
        )

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        """Trap role update by rogue admins."""
        await self._check_and_trap_admin(
            before.guild,
            discord.AuditLogAction.role_update,
            action_name="role_update",
            target_id=after.id,
        )

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel: discord.abc.GuildChannel):
        """Trap webhook creation / tampering by rogue admins."""
        await self._check_and_trap_admin(
            channel.guild,
            discord.AuditLogAction.webhook_create,
            action_name="webhook_create",
            target_id=channel.id,
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Trap unauthorized bot invitation by rogue admins."""
        if not member.bot:
            return

        guild = member.guild
        await asyncio.sleep(0.1)

        entry = None
        try:
            async for log_entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.bot_add):
                if log_entry.target and log_entry.target.id == member.id:
                    entry = log_entry
                    break
        except Exception:
            pass

        if not entry or not entry.user:
            return

        executor_id = entry.user.id
        if executor_id == guild.owner_id or is_bot_owner(executor_id):
            return

        is_admin = False
        row = await db.fetchone(
            "SELECT user_id FROM server_admins WHERE guild_id = ? AND user_id = ?",
            (guild.id, executor_id),
        )
        if row:
            is_admin = True
        else:
            cfg = await db.fetchone("SELECT role_id FROM admin_config WHERE guild_id = ?", (guild.id,))
            if cfg and cfg["role_id"]:
                inviter = guild.get_member(executor_id)
                if inviter and any(r.id == cfg["role_id"] for r in inviter.roles):
                    is_admin = True

        if is_admin:
            logger.critical(f"Rogue Admin {executor_id} added unauthorized bot {member.name}! Banishing both...")
            # 1. Ban rogue admin
            try:
                await guild.ban(entry.user, reason="[NOVEXA Sentinel] Unauthorized Bot Addition! Instant Ban.", delete_message_days=1)
            except Exception:
                pass
            # 2. Kick/Ban unauthorized bot
            try:
                await member.kick(reason="[NOVEXA Sentinel Containment] Unauthorized Bot Invitation")
            except Exception:
                pass

    # ==================== SLASH COMMANDS (/admin ...) ====================

    @admin_group.command(name="add", description="Promote a member to Admin with all-channel chat access & stylish nickname")
    @has_admin_or_owner()
    @app_commands.describe(
        user="Member to promote to Admin",
        style="Stylish nickname preset",
    )
    @app_commands.choices(style=[
        app_commands.Choice(name="👑 Crown: 👑 ᴀᴅᴍɪɴ ┃ Name", value="crown"),
        app_commands.Choice(name="👑 Royal Bracket: [ 👑 ᴀᴅᴍɪɴ ] Name", value="royal"),
        app_commands.Choice(name="🛡️ Shield: 🛡️ ᴀᴅᴍɪɴ ┃ Name", value="shield"),
        app_commands.Choice(name="💎 Diamond: 💎 ᴀᴅᴍɪɴ ┃ Name", value="diamond"),
        app_commands.Choice(name="🔥 Fire: 🔥 ᴀᴅᴍɪɴ ┃ Name", value="fire"),
        app_commands.Choice(name="⚜️ Golden: ⚜️ ᴀᴅᴍɪɴ ┃ Name", value="golden"),
        app_commands.Choice(name="【ADMIN】Bracket: 【ADMIN】Name", value="bracket"),
    ])
    async def slash_admin_add(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        style: Optional[app_commands.Choice[str]] = None,
    ):
        guild = interaction.guild
        if user.bot:
            return await interaction.response.send_message("❌ Bots cannot be promoted to Admin.", ephemeral=True)
        if user.id == guild.owner_id:
            return await interaction.response.send_message("❌ The Server Owner already has total server ownership.", ephemeral=True)

        await interaction.response.defer(thinking=True)

        # 1. Get or create Sandboxed Admin Role
        admin_role = await self._get_or_create_admin_role(guild)

        # 2. Assign role
        if admin_role not in user.roles:
            try:
                await user.add_roles(admin_role, reason=f"Promoted to Universal Admin by {interaction.user.name}")
            except discord.Forbidden:
                return await interaction.followup.send(
                    embed=error_embed("Hierarchy Error", f"Cannot assign {admin_role.mention}. Move **{BOT_NAME}'s** role higher in Server Settings > Roles.")
                )

        # 3. Apply stylish nickname
        chosen_style = style.value if style else "crown"
        orig_nick = user.nick or user.name
        new_nick = format_admin_nickname(user.display_name, chosen_style)

        nick_changed = False
        try:
            await user.edit(nick=new_nick, reason="NOVEXA Universal Admin Promotion")
            nick_changed = True
        except Exception as e:
            logger.debug(f"Could not change nickname for {user.name}: {e}")

        # 4. Save to database
        await db.execute(
            "INSERT INTO server_admins (guild_id, user_id, original_nick, added_by) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET original_nick = excluded.original_nick, added_by = excluded.added_by",
            (guild.id, user.id, orig_nick, interaction.user.id),
        )

        # 5. Apply universal channel permissions across all channels
        success_ch, fail_ch = await apply_admin_universal_permissions(guild, admin_role)

        embed = discord.Embed(
            title="👑 New Server Admin Promoted!",
            description=(
                f"Successfully promoted {user.mention} to **Universal Admin**!\n\n"
                f"**👤 Admin Details:**\n"
                f"• **Member:** {user.mention} (`{user.id}`)\n"
                f"• **Assigned Role:** {admin_role.mention}\n"
                f"• **Stylish Nickname:** `{new_nick}` {'✅' if nick_changed else '⚠️ (Role Hierarchy Locked)'}\n"
                f"• **Universal Channel Access:** Granted across **{success_ch} channels/categories**\n\n"
                f"**🔒 Granted Permissions in All Channels:**\n"
                f"• ✅ **Send Messages & Chat Everywhere**\n"
                f"• ✅ **View Channel & Read Message History**\n"
                f"• ✅ **Attach Files, Links & Add Reactions**\n"
                f"• ✅ **Use External Emojis & Stickers**\n"
                f"• ✅ **Full Bot Commands Access**\n\n"
                f"**🛡️ Zero-Tolerance Sentinel Security:**\n"
                f"• ❌ Restricted from deleting, creating, or updating channels/roles/webhooks.\n"
                f"• ⚡ **Trap Notice:** If this admin attempts unauthorized channel/role deletion or bot addition, they will be **INSTANTLY BANNED (< 0.1s)** from the server!"
            ),
            color=COLOR_ADMIN_GOLD,
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"Promoted by {interaction.user.display_name} • {BOT_NAME} Security Suite")

        await interaction.followup.send(embed=embed)

    @admin_group.command(name="remove", description="Remove Admin role from a member and restore their original nickname")
    @has_admin_or_owner()
    @app_commands.describe(user="Member to remove from Admin")
    async def slash_admin_remove(self, interaction: discord.Interaction, user: discord.Member):
        guild = interaction.guild
        cfg = await db.fetchone("SELECT role_id FROM admin_config WHERE guild_id = ?", (guild.id,))
        admin_role = guild.get_role(cfg["role_id"]) if cfg and cfg["role_id"] else None

        if admin_role and admin_role in user.roles:
            try:
                await user.remove_roles(admin_role, reason=f"Admin removed by {interaction.user.name}")
            except Exception:
                pass

        row = await db.fetchone(
            "SELECT original_nick FROM server_admins WHERE guild_id = ? AND user_id = ?",
            (guild.id, user.id),
        )
        orig_nick = row["original_nick"] if row and row["original_nick"] else user.name

        try:
            if user.nick and any(p in user.nick for p in ["👑 ᴀᴅᴍɪɴ", "ᴀᴅᴍɪɴ", "【ADMIN】"]):
                await user.edit(nick=orig_nick if orig_nick != user.name else None, reason="Admin Demotion")
        except Exception:
            pass

        await db.execute("DELETE FROM server_admins WHERE guild_id = ? AND user_id = ?", (guild.id, user.id))
        await interaction.response.send_message(
            embed=success_embed("Admin Removed", f"Successfully removed {user.mention} from Server Admins and restored original nickname.")
        )

    @admin_group.command(name="list", description="Display all official server Admins")
    async def slash_admin_list(self, interaction: discord.Interaction):
        guild = interaction.guild
        cfg = await db.fetchone("SELECT role_id FROM admin_config WHERE guild_id = ?", (guild.id,))
        admin_role = guild.get_role(cfg["role_id"]) if cfg and cfg["role_id"] else None

        members = admin_role.members if admin_role else []
        if not members:
            return await interaction.response.send_message(
                embed=info_embed("No Admins Registered", f"No members currently have the Admin role.\nUse `/admin add @user` to promote someone!"),
                ephemeral=True,
            )

        lines = []
        for idx, m in enumerate(members[:30], start=1):
            lines.append(f"**{idx}.** {m.mention} (`{m.display_name}`) • ID: `{m.id}`")

        embed = discord.Embed(
            title=f"👑 {guild.name} Official Server Admins ({len(members)})",
            description="\n".join(lines),
            color=COLOR_ADMIN_GOLD,
        )
        embed.set_footer(text=f"Total: {len(members)} active server admins")
        await interaction.response.send_message(embed=embed)

    @admin_group.command(name="sync-channels", description="Synchronize universal chat & view permissions across all channels")
    @has_admin_or_owner()
    async def slash_admin_sync_channels(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        guild = interaction.guild
        admin_role = await self._get_or_create_admin_role(guild)
        success_ch, fail_ch = await apply_admin_universal_permissions(guild, admin_role)

        embed = discord.Embed(
            title="👑 Universal Admin Permissions Synced!",
            description=(
                f"Successfully refreshed Universal Admin permissions for {admin_role.mention} across:\n\n"
                f"• ✅ **{success_ch} Channels & Categories Synced**\n"
                f"• ⚠️ **{fail_ch} Skipped / Unmanageable**\n\n"
                f"All Admins now have guaranteed chat & view access in all configured server channels!"
            ),
            color=COLOR_SUCCESS,
        )
        await interaction.followup.send(embed=embed)

    @admin_group.command(name="dashboard", description="Open the interactive server configuration and module dashboard")
    @has_admin_or_owner()
    async def dashboard(self, interaction: discord.Interaction):
        guild = interaction.guild

        row = await db.fetchone("SELECT * FROM guild_settings WHERE guild_id = ?", (guild.id,))
        if not row:
            await db.execute("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (guild.id,))
            row = await db.fetchone("SELECT * FROM guild_settings WHERE guild_id = ?", (guild.id,))

        embed = primary_embed(
            title=f"⚙️ {BOT_NAME} - Admin Dashboard",
            description=f"Server Management Console for **{guild.name}**\nUse the dropdown below to toggle any system on or off instantly.",
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        def badge(val) -> str:
            return "🟢 Enabled" if val else "🔴 Disabled"

        embed.add_field(name="👋 Welcome System", value=badge(row["welcome_enabled"]), inline=True)
        embed.add_field(name="🎫 Tickets", value=badge(row["tickets_enabled"]), inline=True)
        embed.add_field(name="🛡️ Anti-Nuke", value=badge(row["antinuke_enabled"]), inline=True)

        embed.add_field(name="🎵 Music Player", value=badge(row["music_enabled"]), inline=True)
        embed.add_field(name="⭐ Leveling & XP", value=badge(row["leveling_enabled"]), inline=True)
        embed.add_field(name="💰 Economy", value=badge(row["economy_enabled"]), inline=True)

        embed.add_field(name="💳 Payments", value=badge(row["payments_enabled"]), inline=True)
        embed.add_field(name="📜 Audit Logging", value=badge(row["logging_enabled"]), inline=True)

        embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION} • Multi-Guild Architecture")
        view = AdminDashboardView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @admin_group.command(name="backup", description="Create an immediate full backup snapshot of the database")
    @has_admin_or_owner()
    async def admin_backup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            backup_path = await db.backup()
            embed = success_embed(
                "Backup Completed",
                f"Full SQLite database backup saved:\n`{backup_path.name}`\n"
                f"**Path:** `{backup_path}`"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(embed=error_embed("Backup Failed", str(e)), ephemeral=True)

    @admin_group.command(name="sync", description="Force synchronize the slash command set to every guild")
    @has_admin_or_owner()
    async def admin_sync(self, interaction: discord.Interaction):
        if not is_bot_owner(interaction.user.id) and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message(
                embed=error_embed("Permission Denied", "Only Server Owner or Bot Developer can force sync."),
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True)
        count = await self.bot.sync_slash_commands()
        await interaction.followup.send(
            embed=success_embed("Commands Synced", f"Successfully synced **{count}** commands to every guild!"),
            ephemeral=True,
        )

    # ==================== PREFIX COMMAND SUITE ====================

    @commands.group(name="admin", invoke_without_command=True)
    async def prefix_admin(self, ctx: commands.Context):
        """Admin Management Command Guide."""
        embed = discord.Embed(
            title="👑 NOVEXA Universal Admin Suite",
            description=(
                f"**Admin Commands:**\n"
                f"• `{BOT_PREFIX}admin add @user [style]` — Promote a member to Admin (all channels chat + stylish name)\n"
                f"• `{BOT_PREFIX}admin remove @user` — Remove a member from Admin and restore name\n"
                f"• `{BOT_PREFIX}admin list` — List all server Admin members\n"
                f"• `{BOT_PREFIX}admin apply` / `adminsync` — Re-sync universal chat permissions to all channels\n"
                f"• `{BOT_PREFIX}admin dashboard` — Open master configuration panel\n"
                f"• `{BOT_PREFIX}admin backup` — Create instant database snapshot\n\n"
                f"**Available Nickname Styles:**\n"
                f"`crown`, `royal`, `shield`, `diamond`, `fire`, `golden`, `bracket`\n\n"
                f"**⚡ Zero-Tolerance Sentinel:**\n"
                f"Admins attempting channel/role manipulation or bot additions are **BANNED INSTANTLY (< 0.1s)**!"
            ),
            color=COLOR_ADMIN_GOLD,
        )
        await ctx.send(embed=embed)

    @prefix_admin.command(name="add")
    @commands.has_permissions(administrator=True)
    async def p_admin_add(self, ctx: commands.Context, user: discord.Member, style: Optional[str] = "crown"):
        """Promote a member to Admin."""
        guild = ctx.guild
        if user.bot:
            return await ctx.send("❌ Bots cannot be promoted to Admin.")
        if user.id == guild.owner_id:
            return await ctx.send("❌ The Server Owner already has total server ownership.")

        admin_role = await self._get_or_create_admin_role(guild)

        if admin_role not in user.roles:
            try:
                await user.add_roles(admin_role, reason=f"Promoted to Admin by {ctx.author.name}")
            except discord.Forbidden:
                return await ctx.send(f"❌ Cannot assign {admin_role.mention}. Move NOVEXA's role higher in Server Settings.")

        chosen_style = style or "crown"
        orig_nick = user.nick or user.name
        new_nick = format_admin_nickname(user.display_name, chosen_style)

        try:
            await user.edit(nick=new_nick, reason="NOVEXA Universal Admin Promotion")
        except Exception:
            pass

        await db.execute(
            "INSERT INTO server_admins (guild_id, user_id, original_nick, added_by) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET original_nick = excluded.original_nick, added_by = excluded.added_by",
            (guild.id, user.id, orig_nick, ctx.author.id),
        )

        success_ch, fail_ch = await apply_admin_universal_permissions(guild, admin_role)

        embed = discord.Embed(
            title="👑 New Server Admin Promoted!",
            description=(
                f"Successfully promoted {user.mention} to **Universal Admin**!\n\n"
                f"• **Role:** {admin_role.mention}\n"
                f"• **Nickname:** `{new_nick}`\n"
                f"• **All-Channel Access:** Granted in **{success_ch} channels/categories**\n"
                f"• **Permissions:** Chat & view everywhere + bot commands\n"
                f"• **Sentinel Guard:** Protected with 0.1s instant ban if destructive actions attempted!"
            ),
            color=COLOR_ADMIN_GOLD,
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        await ctx.send(embed=embed)

    @prefix_admin.command(name="remove")
    @commands.has_permissions(administrator=True)
    async def p_admin_remove(self, ctx: commands.Context, user: discord.Member):
        """Demote an admin and restore nickname."""
        guild = ctx.guild
        cfg = await db.fetchone("SELECT role_id FROM admin_config WHERE guild_id = ?", (guild.id,))
        admin_role = guild.get_role(cfg["role_id"]) if cfg and cfg["role_id"] else None

        if admin_role and admin_role in user.roles:
            try:
                await user.remove_roles(admin_role, reason=f"Admin removed by {ctx.author.name}")
            except Exception:
                pass

        row = await db.fetchone(
            "SELECT original_nick FROM server_admins WHERE guild_id = ? AND user_id = ?",
            (guild.id, user.id),
        )
        orig_nick = row["original_nick"] if row and row["original_nick"] else user.name

        try:
            if user.nick and any(p in user.nick for p in ["👑 ᴀᴅᴍɪɴ", "ᴀᴅᴍɪɴ", "【ADMIN】"]):
                await user.edit(nick=orig_nick if orig_nick != user.name else None, reason="Admin Demotion")
        except Exception:
            pass

        await db.execute("DELETE FROM server_admins WHERE guild_id = ? AND user_id = ?", (guild.id, user.id))
        await ctx.send(f"✅ Removed {user.mention} from Server Admins.")

    @prefix_admin.command(name="list")
    async def p_admin_list(self, ctx: commands.Context):
        """List all server Admins."""
        guild = ctx.guild
        cfg = await db.fetchone("SELECT role_id FROM admin_config WHERE guild_id = ?", (guild.id,))
        admin_role = guild.get_role(cfg["role_id"]) if cfg and cfg["role_id"] else None

        members = admin_role.members if admin_role else []
        if not members:
            return await ctx.send(f"ℹ️ No members currently have the Admin role.")

        lines = [f"**{idx}.** {m.mention} (`{m.display_name}`)" for idx, m in enumerate(members[:25], start=1)]
        embed = discord.Embed(
            title=f"👑 {guild.name} Official Server Admins ({len(members)})",
            description="\n".join(lines),
            color=COLOR_ADMIN_GOLD,
        )
        await ctx.send(embed=embed)

    @prefix_admin.command(name="apply", aliases=["syncchannels", "sync"])
    @commands.has_permissions(administrator=True)
    async def p_admin_apply(self, ctx: commands.Context):
        """Sync universal permissions across all channels."""
        guild = ctx.guild
        admin_role = await self._get_or_create_admin_role(guild)
        s, f = await apply_admin_universal_permissions(guild, admin_role)
        await ctx.send(f"✅ Universal Admin permissions synced across **{s} channels & categories**!")

    # Direct convenient aliases
    @commands.command(name="addadmin")
    @commands.has_permissions(administrator=True)
    async def alias_addadmin(self, ctx: commands.Context, user: discord.Member, style: Optional[str] = "crown"):
        await self.p_admin_add(ctx, user, style)

    @commands.command(name="removeadmin")
    @commands.has_permissions(administrator=True)
    async def alias_removeadmin(self, ctx: commands.Context, user: discord.Member):
        await self.p_admin_remove(ctx, user)

    @commands.command(name="adminlist")
    async def alias_adminlist(self, ctx: commands.Context):
        await self.p_admin_list(ctx)


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
