"""NOVEXA - Staff Management, Nickname Styling & Channel Permissions Suite.

Features:
- Staff Role Management: Automatically creates and assigns an aesthetic Staff role.
- Aesthetic Nickname Prefix: Applies stylish Unicode Staff prefixes to new staff members
  (e.g. '[ ꜱᴛᴀꜰꜰ ] MemberName', '🛡️ ꜱᴛᴀꜰꜰ ┃ MemberName', '⚡ ꜱᴛᴀꜰꜰ ┃ MemberName')
  and restores their original name upon removal.
- Staff Apply / Permissions Engine:
  - Interactive multi-channel selector dropdown: Select channels or categories where staff should operate.
  - Automatically resolves AppCommandChannel snowflakes to live GuildChannels.
  - Automatically configures channel permission overwrites:
    • View Channel (Read Messages)
    • Read Message History
    • Send Messages & Send in Threads
    • Attach Files & Embed Links
    • Add Reactions
    • Use External Emojis & Stickers
  - Parent category visibility inheritance to prevent hidden channels.
- Full Slash Command Group (/staff) & Prefix Command Suite (n!staff).
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
import json
from typing import Optional, List, Dict, Any, Tuple, Union

from database.database import db
from config import BOT_NAME, BOT_PREFIX
from utils.embeds import primary_embed, success_embed, error_embed, warning_embed, info_embed
from utils.permissions import has_admin_or_owner

logger = logging.getLogger("novexa.staff")

COLOR_STAFF = 0x1ABC9C      # Turquoise / Teal
COLOR_SUCCESS = 0x2ECC71    # Emerald Green
COLOR_WARNING = 0xF1C40F    # Gold
COLOR_DANGER = 0xE74C3C     # Crimson Red

STYLES = {
    "small_caps": ("[ ꜱᴛᴀꜰꜰ ] {name}", "[ ꜱᴛᴀꜰꜰ ]"),
    "shield": ("🛡️ ꜱᴛᴀꜰꜰ ┃ {name}", "🛡️ ꜱᴛᴀꜰꜰ ┃"),
    "lightning": ("⚡ ꜱᴛᴀꜰꜰ ┃ {name}", "⚡ ꜱᴛᴀꜰꜰ ┃"),
    "star": ("⭐ ꜱᴛᴀꜰꜰ ┃ {name}", "⭐ ꜱᴛᴀꜰꜰ ┃"),
    "bracket": ("【STAFF】{name}", "【STAFF】"),
    "diamond": ("💎 ꜱᴛᴀꜰꜰ ┃ {name}", "💎 ꜱᴛᴀꜰꜰ ┃"),
}


def format_staff_nickname(base_name: str, style_key: str = "small_caps") -> str:
    """Format member name with stylish staff prefix while strictly respecting 32-char Discord limit."""
    template, prefix = STYLES.get(style_key, STYLES["small_caps"])
    prefix_len = len(prefix) + 1  # include space
    max_name_len = 32 - prefix_len
    clean_name = base_name[:max_name_len]
    return template.replace("{name}", clean_name).strip()


async def apply_staff_permissions(
    channel_or_category: Union[discord.abc.GuildChannel, discord.CategoryChannel, discord.TextChannel, discord.VoiceChannel],
    staff_role: discord.Role,
    reason: str = "NOVEXA Staff Channel Permissions",
) -> bool:
    """Apply exact Staff permissions to a channel or an entire category."""
    try:
        # 1. If target is a Category
        if isinstance(channel_or_category, discord.CategoryChannel):
            cat_ow = channel_or_category.overwrites_for(staff_role)
            cat_ow.view_channel = True
            cat_ow.read_messages = True
            cat_ow.read_message_history = True
            cat_ow.send_messages = True
            cat_ow.send_messages_in_threads = True
            cat_ow.embed_links = True
            cat_ow.attach_files = True
            cat_ow.add_reactions = True
            cat_ow.use_external_emojis = True
            cat_ow.use_external_stickers = True
            await channel_or_category.set_permissions(staff_role, overwrite=cat_ow, reason=reason)

            # Apply to all child channels in category
            for child in channel_or_category.channels:
                child_ow = child.overwrites_for(staff_role)
                child_ow.view_channel = True
                child_ow.read_messages = True
                child_ow.read_message_history = True
                child_ow.send_messages = True
                child_ow.send_messages_in_threads = True
                child_ow.embed_links = True
                child_ow.attach_files = True
                child_ow.add_reactions = True
                child_ow.use_external_emojis = True
                child_ow.use_external_stickers = True
                if isinstance(child, (discord.VoiceChannel, discord.StageChannel)):
                    child_ow.connect = True
                    child_ow.speak = True
                await child.set_permissions(staff_role, overwrite=child_ow, reason=reason)
            return True

        # 2. If target is a Text / Voice / Forum Channel
        # Ensure parent category allows viewing so category doesn't hide the channel
        if getattr(channel_or_category, "category", None):
            parent_cat = channel_or_category.category
            cat_ow = parent_cat.overwrites_for(staff_role)
            if not cat_ow.view_channel:
                cat_ow.view_channel = True
                await parent_cat.set_permissions(staff_role, overwrite=cat_ow, reason=f"{reason} (Parent Category View)")

        # Set explicit channel overwrite
        overwrites = channel_or_category.overwrites_for(staff_role)
        overwrites.view_channel = True
        overwrites.read_messages = True
        overwrites.read_message_history = True
        overwrites.send_messages = True
        overwrites.send_messages_in_threads = True
        overwrites.embed_links = True
        overwrites.attach_files = True
        overwrites.add_reactions = True
        overwrites.use_external_emojis = True
        overwrites.use_external_stickers = True

        if isinstance(channel_or_category, (discord.VoiceChannel, discord.StageChannel)):
            overwrites.connect = True
            overwrites.speak = True

        await channel_or_category.set_permissions(staff_role, overwrite=overwrites, reason=reason)
        return True
    except Exception as e:
        logger.error(f"Error applying staff permissions to {getattr(channel_or_category, 'name', 'Channel')}: {e}", exc_info=True)
        return False


class StaffChannelSelect(discord.ui.ChannelSelect):
    """Interactive multi-channel selector for Staff permissions configuration."""

    def __init__(self, staff_role: discord.Role, guild: discord.Guild):
        super().__init__(
            placeholder="Select all channels where Staff can send messages & view...",
            min_values=1,
            max_values=25,
            channel_types=[
                discord.ChannelType.text,
                discord.ChannelType.news,
                discord.ChannelType.voice,
                discord.ChannelType.stage_voice,
                discord.ChannelType.forum,
                discord.ChannelType.category,
            ],
        )
        self.staff_role = staff_role
        self.guild = guild

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        selected_channels = self.values
        applied_channels: List[str] = []
        failed_channels: List[str] = []
        channel_ids = []

        for ch in selected_channels:
            channel_ids.append(ch.id)
            # Resolve live GuildChannel from AppCommandChannel
            actual_channel = self.guild.get_channel(ch.id)
            if not actual_channel:
                try:
                    actual_channel = await self.guild.fetch_channel(ch.id)
                except Exception:
                    failed_channels.append(f"`{ch.id}`")
                    continue

            ok = await apply_staff_permissions(
                actual_channel,
                self.staff_role,
                reason=f"NOVEXA Staff Channel Permissions applied by {interaction.user.name}",
            )
            if ok:
                applied_channels.append(actual_channel.mention)
            else:
                failed_channels.append(actual_channel.name)

        # Save to database
        await db.execute(
            "INSERT INTO staff_config (guild_id, role_id, channels_json) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id) DO UPDATE SET role_id = excluded.role_id, channels_json = excluded.channels_json",
            (self.guild.id, self.staff_role.id, json.dumps(channel_ids)),
        )

        embed = discord.Embed(
            title="🛡️ Staff Channel Permissions Configured!",
            description=(
                f"Successfully applied Staff permissions to **{len(applied_channels)} channels** for {self.staff_role.mention}!\n\n"
                f"**Granted Permissions in Selected Channels:**\n"
                f"• ✅ **View Channel & Read Messages**\n"
                f"• ✅ **Read Message History**\n"
                f"• ✅ **Send Messages & Send in Threads**\n"
                f"• ✅ **Attach Files & Upload Media**\n"
                f"• ✅ **Add Reactions**\n"
                f"• ✅ **Use External Emojis & Stickers**\n\n"
                f"**Active Staff Channels:**\n"
                + ", ".join(applied_channels[:15])
                + (f" and {len(applied_channels)-15} more..." if len(applied_channels) > 15 else "")
            ),
            color=COLOR_SUCCESS,
        )
        if failed_channels:
            embed.add_field(name="⚠️ Failed Channels (Missing Permissions)", value=", ".join(failed_channels), inline=False)

        await interaction.followup.send(embed=embed)


class StaffChannelSelectView(discord.ui.View):
    """Interactive view holding channel selector."""

    def __init__(self, staff_role: discord.Role, guild: discord.Guild):
        super().__init__(timeout=120)
        self.add_item(StaffChannelSelect(staff_role, guild))


class Staff(commands.Cog):
    """Staff Management, Role Provisioning & Channel Permissions Suite."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _get_or_create_staff_role(self, guild: discord.Guild) -> discord.Role:
        """Resolve or automatically create the dedicated Staff role with proper base permissions."""
        cfg = await db.fetchone("SELECT role_id FROM staff_config WHERE guild_id = ?", (guild.id,))
        if cfg and cfg["role_id"]:
            role = guild.get_role(cfg["role_id"])
            if role:
                return role

        # Look for existing role
        for r in guild.roles:
            if r.name.lower() in ("🛡️ ꜱᴛᴀꜰꜰ", "staff", "ꜱᴛᴀꜰꜰ", "server staff"):
                await db.execute(
                    "INSERT INTO staff_config (guild_id, role_id) VALUES (?, ?) "
                    "ON CONFLICT(guild_id) DO UPDATE SET role_id = excluded.role_id",
                    (guild.id, r.id),
                )
                return r

        # Base permissions for Staff
        base_permissions = discord.Permissions(
            view_channel=True,
            send_messages=True,
            send_messages_in_threads=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
            add_reactions=True,
            use_external_emojis=True,
            use_external_stickers=True,
            change_nickname=True,
            connect=True,
            speak=True,
        )

        # Automatically create aesthetic Staff role
        role = await guild.create_role(
            name="🛡️ ꜱᴛᴀꜰꜰ",
            color=discord.Color.teal(),
            hoist=True,
            mentionable=False,
            permissions=base_permissions,
            reason="NOVEXA Automated Staff Role Initialization",
        )

        await db.execute(
            "INSERT INTO staff_config (guild_id, role_id) VALUES (?, ?) "
            "ON CONFLICT(guild_id) DO UPDATE SET role_id = excluded.role_id",
            (guild.id, role.id),
        )
        return role

    # ==================== SLASH COMMAND GROUP ====================
    staff_group = app_commands.Group(name="staff", description="Manage server staff members and permissions")

    @staff_group.command(name="add", description="Make a member staff with role and stylish staff nickname")
    @has_admin_or_owner()
    @app_commands.describe(
        user="The member to promote to Staff",
        style="Nickname font and badge style",
    )
    @app_commands.choices(style=[
        app_commands.Choice(name="[ ꜱᴛᴀꜰꜰ ] Name (Small Caps Aesthetic)", value="small_caps"),
        app_commands.Choice(name="🛡️ ꜱᴛᴀꜰꜰ ┃ Name (Shield Badge)", value="shield"),
        app_commands.Choice(name="⚡ ꜱᴛᴀꜰꜰ ┃ Name (Lightning Electric)", value="lightning"),
        app_commands.Choice(name="⭐ ꜱᴛᴀꜰꜰ ┃ Name (Star VIP)", value="star"),
        app_commands.Choice(name="【STAFF】Name (Bracket Bold)", value="bracket"),
        app_commands.Choice(name="💎 ꜱᴛᴀꜰꜰ ┃ Name (Diamond Luxury)", value="diamond"),
    ])
    async def slash_staff_add(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        style: Optional[app_commands.Choice[str]] = None,
    ):
        await interaction.response.defer(ephemeral=False)
        guild = interaction.guild
        style_key = style.value if style else "small_caps"

        # 1. Resolve or create Staff role
        staff_role = await self._get_or_create_staff_role(guild)

        # 2. Assign role
        if staff_role not in user.roles:
            try:
                await user.add_roles(staff_role, reason=f"Promoted to Staff by {interaction.user.name}")
            except discord.Forbidden:
                return await interaction.followup.send(
                    embed=error_embed("Permission Denied", f"Bot cannot assign {staff_role.mention}. Move the bot's role higher in Server Settings > Roles.")
                )

        # 3. Format and update stylish nickname
        orig_nick = user.nick or user.name
        new_nick = format_staff_nickname(user.display_name, style_key)
        nick_changed = False
        nick_error = ""

        try:
            await user.edit(nick=new_nick, reason="NOVEXA Staff Promotion")
            nick_changed = True
        except discord.Forbidden:
            nick_error = "*(Bot could not change nickname due to Discord role hierarchy or target is Server Owner)*"
        except Exception as e:
            nick_error = f"*(Nickname update failed: {e})*"

        # 4. Save to database
        await db.execute(
            "INSERT INTO server_staff (guild_id, user_id, original_nick, added_by) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET original_nick = excluded.original_nick, added_by = excluded.added_by",
            (guild.id, user.id, orig_nick, interaction.user.id),
        )

        embed = discord.Embed(
            title="🎉 New Staff Member Promoted!",
            description=(
                f"{user.mention} is now an official member of the **{guild.name}** Staff Team!\n\n"
                f"• **Assigned Role:** {staff_role.mention}\n"
                f"• **Staff Nickname:** `{new_nick}` {nick_error}\n"
                f"• **Promoted By:** {interaction.user.mention}\n\n"
                f"ℹ️ *To configure which channels Staff can chat in, use `/staff apply`!*"
            ),
            color=COLOR_SUCCESS,
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"{BOT_NAME} Staff Suite • Role Hierarchy Verified")
        await interaction.followup.send(embed=embed)

    @staff_group.command(name="remove", description="Remove a member from staff and restore their nickname")
    @has_admin_or_owner()
    @app_commands.describe(user="The member to remove from Staff")
    async def slash_staff_remove(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=False)
        guild = interaction.guild

        staff_role = await self._get_or_create_staff_role(guild)

        # 1. Remove role
        if staff_role in user.roles:
            try:
                await user.remove_roles(staff_role, reason=f"Removed from Staff by {interaction.user.name}")
            except discord.Forbidden:
                pass

        # 2. Restore nickname
        row = await db.fetchone(
            "SELECT original_nick FROM server_staff WHERE guild_id = ? AND user_id = ?",
            (guild.id, user.id),
        )
        orig_nick = row["original_nick"] if row and row["original_nick"] else user.name

        try:
            if user.nick and any(p in user.nick for p in ["[ ꜱᴛᴀꜰꜰ ]", "ꜱᴛᴀꜰꜰ", "【STAFF】"]):
                await user.edit(nick=orig_nick if orig_nick != user.name else None, reason="NOVEXA Staff Demotion")
        except Exception:
            pass

        # 3. Remove from database
        await db.execute(
            "DELETE FROM server_staff WHERE guild_id = ? AND user_id = ?",
            (guild.id, user.id),
        )

        embed = discord.Embed(
            title="🛡️ Staff Member Removed",
            description=f"{user.mention} has been removed from Staff. Their staff role and nickname prefix have been cleared.",
            color=COLOR_WARNING,
        )
        await interaction.followup.send(embed=embed)

    @staff_group.command(name="list", description="List all staff members in this server")
    async def slash_staff_list(self, interaction: discord.Interaction):
        guild = interaction.guild
        staff_role = await self._get_or_create_staff_role(guild)

        members = staff_role.members
        if not members:
            return await interaction.response.send_message(
                embed=info_embed("No Staff Members", f"No members currently have the {staff_role.mention} role.\nUse `/staff add @user` to promote someone!"),
                ephemeral=True,
            )

        lines = []
        for idx, m in enumerate(members[:30], start=1):
            lines.append(f"**{idx}.** {m.mention} (`{m.display_name}`) • ID: `{m.id}`")

        embed = discord.Embed(
            title=f"🛡️ {guild.name} Official Staff Team ({len(members)})",
            description="\n".join(lines),
            color=COLOR_STAFF,
        )
        embed.set_footer(text=f"Role: @{staff_role.name} • Total: {len(members)} active staff")
        await interaction.response.send_message(embed=embed)

    @staff_group.command(name="apply", description="Select channels where Staff can send messages and view")
    @has_admin_or_owner()
    @app_commands.describe(channel="Specific channel to configure (leave empty for multi-channel selector)")
    async def slash_staff_apply(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
    ):
        guild = interaction.guild
        staff_role = await self._get_or_create_staff_role(guild)

        if channel:
            # Single channel direct application with robust permission resolver
            ok = await apply_staff_permissions(
                channel,
                staff_role,
                reason=f"NOVEXA Staff Channel Permissions applied by {interaction.user.name}",
            )
            if not ok:
                return await interaction.response.send_message(
                    embed=error_embed("Failed", f"Could not apply permissions in {channel.mention}. Check bot role hierarchy.")
                )

            embed = discord.Embed(
                title="🛡️ Staff Permissions Applied!",
                description=(
                    f"Successfully granted Staff permissions in {channel.mention} for {staff_role.mention}!\n\n"
                    f"• ✅ **View Channel & Read Messages**\n"
                    f"• ✅ **Read Message History**\n"
                    f"• ✅ **Send Messages & Send in Threads**\n"
                    f"• ✅ **Attach Files & Upload Media**\n"
                    f"• ✅ **Add Reactions**\n"
                    f"• ✅ **Use External Emojis & Stickers**"
                ),
                color=COLOR_SUCCESS,
            )
            return await interaction.response.send_message(embed=embed)

        # Multi-channel interactive dropdown
        view = StaffChannelSelectView(staff_role, guild)
        embed = discord.Embed(
            title="🛡️ Configure Staff Channel Access",
            description=(
                f"Choose the channels below where **{staff_role.mention}** will have permission to:\n"
                f"• View channel and read message history\n"
                f"• Send messages, stickers & emojis\n"
                f"• Attach files and add reactions\n\n"
                f"👇 *Select channels from the dropdown menu below:*"
            ),
            color=COLOR_STAFF,
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # ==================== PREFIX COMMAND SUITE ====================

    @commands.group(name="staff", invoke_without_command=True)
    async def prefix_staff(self, ctx: commands.Context):
        """Staff Management Command Guide."""
        embed = discord.Embed(
            title="🛡️ NOVEXA Staff Management Suite",
            description=(
                f"**Staff Commands:**\n"
                f"• `{BOT_PREFIX}staff add @user [style]` — Promote a member to staff with stylish nickname\n"
                f"• `{BOT_PREFIX}staff remove @user` — Remove a member from staff and restore name\n"
                f"• `{BOT_PREFIX}staff list` — List all server staff members\n"
                f"• `{BOT_PREFIX}staff apply` — Open interactive channel selector for permissions\n"
                f"• `{BOT_PREFIX}staff apply #channel` — Grant staff permissions in a channel\n\n"
                f"**Available Nickname Styles:**\n"
                f"`small_caps`, `shield`, `lightning`, `star`, `bracket`, `diamond`"
            ),
            color=COLOR_STAFF,
        )
        await ctx.send(embed=embed)

    @prefix_staff.command(name="add")
    @commands.has_permissions(manage_roles=True)
    async def p_staff_add(self, ctx: commands.Context, user: discord.Member, style: Optional[str] = "small_caps"):
        """Promote a member to staff."""
        guild = ctx.guild
        staff_role = await self._get_or_create_staff_role(guild)

        if staff_role not in user.roles:
            try:
                await user.add_roles(staff_role, reason=f"Promoted to Staff by {ctx.author.name}")
            except discord.Forbidden:
                return await ctx.send(f"❌ Cannot assign {staff_role.mention}. Move NOVEXA's role higher in Server Settings.")

        orig_nick = user.nick or user.name
        new_nick = format_staff_nickname(user.display_name, style or "small_caps")

        try:
            await user.edit(nick=new_nick, reason="NOVEXA Staff Promotion")
        except Exception:
            pass

        await db.execute(
            "INSERT INTO server_staff (guild_id, user_id, original_nick, added_by) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET original_nick = excluded.original_nick, added_by = excluded.added_by",
            (guild.id, user.id, orig_nick, ctx.author.id),
        )

        embed = discord.Embed(
            title="🎉 New Staff Member Promoted!",
            description=(
                f"{user.mention} is now an official member of **{guild.name}** Staff!\n\n"
                f"• **Role:** {staff_role.mention}\n"
                f"• **Nickname:** `{new_nick}`\n"
                f"• **Promoted By:** {ctx.author.mention}\n\n"
                f"Type `{BOT_PREFIX}staff apply` to select channels for Staff chat permissions!"
            ),
            color=COLOR_SUCCESS,
        )
        await ctx.send(embed=embed)

    @prefix_staff.command(name="remove", aliases=["del", "demote"])
    @commands.has_permissions(manage_roles=True)
    async def p_staff_remove(self, ctx: commands.Context, user: discord.Member):
        """Demote a staff member."""
        guild = ctx.guild
        staff_role = await self._get_or_create_staff_role(guild)

        if staff_role in user.roles:
            try:
                await user.remove_roles(staff_role, reason=f"Demoted by {ctx.author.name}")
            except Exception:
                pass

        row = await db.fetchone(
            "SELECT original_nick FROM server_staff WHERE guild_id = ? AND user_id = ?",
            (guild.id, user.id),
        )
        orig_nick = row["original_nick"] if row and row["original_nick"] else user.name

        try:
            if user.nick and any(p in user.nick for p in ["[ ꜱᴛᴀꜰꜰ ]", "ꜱᴛᴀꜰꜰ", "【STAFF】"]):
                await user.edit(nick=orig_nick if orig_nick != user.name else None, reason="NOVEXA Staff Demotion")
        except Exception:
            pass

        await db.execute("DELETE FROM server_staff WHERE guild_id = ? AND user_id = ?", (guild.id, user.id))
        await ctx.send(f"✅ Removed {user.mention} from Staff.")

    @prefix_staff.command(name="list")
    async def p_staff_list(self, ctx: commands.Context):
        """List all staff members."""
        guild = ctx.guild
        staff_role = await self._get_or_create_staff_role(guild)
        members = staff_role.members

        if not members:
            return await ctx.send(f"ℹ️ No members currently have the {staff_role.mention} role.")

        lines = [f"**{idx}.** {m.mention} (`{m.display_name}`)" for idx, m in enumerate(members[:25], start=1)]
        embed = discord.Embed(
            title=f"🛡️ {guild.name} Staff Team ({len(members)})",
            description="\n".join(lines),
            color=COLOR_STAFF,
        )
        await ctx.send(embed=embed)

    @prefix_staff.command(name="apply")
    @commands.has_permissions(manage_channels=True)
    async def p_staff_apply(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        """Configure Staff permissions in channels."""
        guild = ctx.guild
        staff_role = await self._get_or_create_staff_role(guild)

        if channel:
            ok = await apply_staff_permissions(
                channel,
                staff_role,
                reason=f"Staff applied by {ctx.author.name}",
            )
            if ok:
                return await ctx.send(f"✅ Staff chat & view permissions configured in {channel.mention}!")
            else:
                return await ctx.send(f"❌ Failed to set permissions in {channel.mention}. Check bot role hierarchy.")

        view = StaffChannelSelectView(staff_role, guild)
        await ctx.send(
            f"👇 **Select all channels where {staff_role.mention} can chat & view:**",
            view=view,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Staff(bot))
