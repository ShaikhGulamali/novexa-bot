import discord
from discord.ext import commands
from discord import app_commands
import logging
import datetime
from typing import Optional
from database.database import db
from utils.embeds import primary_embed, success_embed, error_embed, warning_embed, info_embed
from utils.permissions import check_hierarchy
from utils.helpers import parse_time, format_duration, PaginatorView

logger = logging.getLogger("novexa.moderation")


class BanConfirmView(discord.ui.View):
    def __init__(self, target: discord.Member, author: discord.Member, reason: str, delete_days: int):
        super().__init__(timeout=30.0)
        self.target = target
        self.author = author
        self.reason = reason
        self.delete_days = delete_days

    @discord.ui.button(label="Confirm Ban", style=discord.ButtonStyle.danger, emoji="🔨")
    async def btn_confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("Only the command author can confirm this.", ephemeral=True)

        try:
            await self.target.ban(reason=f"Banned by {self.author}: {self.reason}", delete_message_days=self.delete_days)
            await db.execute(
                "INSERT INTO moderation_logs (guild_id, user_id, moderator_id, action, reason) VALUES (?, ?, ?, 'ban', ?)",
                (interaction.guild_id, self.target.id, self.author.id, self.reason),
            )
            await interaction.response.edit_message(
                embed=success_embed("Member Banned", f"Successfully banned {self.target.mention} (`{self.target.id}`).\n**Reason:** {self.reason}"),
                view=None,
            )
        except discord.Forbidden:
            await interaction.response.edit_message(
                embed=error_embed("Ban Failed", "Bot lacks permission to ban this member."),
                view=None,
            )
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def btn_cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("Only the command author can cancel this.", ephemeral=True)
        await interaction.response.edit_message(embed=info_embed("Cancelled", "Ban operation was cancelled."), view=None)
        self.stop()


class Moderation(commands.Cog):
    """Complete Suite of Enterprise Moderation & Server Enforcement Tools."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ban", description="Ban a member from the server with confirmation")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.describe(
        user="Member to ban",
        reason="Reason for ban",
        delete_days="Number of days of messages to delete (0-7)"
    )
    async def ban(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str = "No reason provided.",
        delete_days: int = 0,
    ):
        allowed, err = check_hierarchy(interaction.user, user, interaction.guild.me)
        if not allowed:
            return await interaction.response.send_message(embed=error_embed("Hierarchy Error", err), ephemeral=True)

        delete_days = max(0, min(delete_days, 7))
        view = BanConfirmView(user, interaction.user, reason, delete_days)
        embed = warning_embed(
            "Ban Confirmation",
            f"Are you sure you want to ban **{user.display_name}** (`{user.id}`)?\n\n"
            f"**Reason:** {reason}\n"
            f"**Delete Messages:** {delete_days} days"
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="unban", description="Unban a user by their user ID")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.describe(user_id="The Discord ID of the banned user", reason="Reason for unbanning")
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: str = "No reason provided."):
        if not user_id.isdigit():
            return await interaction.response.send_message(embed=error_embed("Invalid ID", "Please provide a valid user ID."), ephemeral=True)

        uid = int(user_id)
        try:
            user = await self.bot.fetch_user(uid)
            await interaction.guild.unban(user, reason=f"Unbanned by {interaction.user}: {reason}")
            await db.execute(
                "INSERT INTO moderation_logs (guild_id, user_id, moderator_id, action, reason) VALUES (?, ?, ?, 'unban', ?)",
                (interaction.guild_id, uid, interaction.user.id, reason),
            )
            await interaction.response.send_message(
                embed=success_embed("User Unbanned", f"Successfully unbanned {user.mention} (`{user.id}`).")
            )
        except discord.NotFound:
            await interaction.response.send_message(embed=error_embed("Not Found", "This user is not banned in this server."), ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(embed=error_embed("Forbidden", "Bot lacks permission to unban members."), ephemeral=True)

    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.describe(user="Member to kick", reason="Reason for kick")
    async def kick(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided."):
        allowed, err = check_hierarchy(interaction.user, user, interaction.guild.me)
        if not allowed:
            return await interaction.response.send_message(embed=error_embed("Hierarchy Error", err), ephemeral=True)

        try:
            await user.kick(reason=f"Kicked by {interaction.user}: {reason}")
            await db.execute(
                "INSERT INTO moderation_logs (guild_id, user_id, moderator_id, action, reason) VALUES (?, ?, ?, 'kick', ?)",
                (interaction.guild_id, user.id, interaction.user.id, reason),
            )
            await interaction.response.send_message(
                embed=success_embed("Member Kicked", f"Successfully kicked {user.mention}.\n**Reason:** {reason}")
            )
        except discord.Forbidden:
            await interaction.response.send_message(embed=error_embed("Error", "Bot lacks permission to kick this member."), ephemeral=True)

    timeout_group = app_commands.Group(name="timeout", description="Manage member timeouts")

    @timeout_group.command(name="set", description="Timeout (mute) a member for a specified duration")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(
        user="Member to timeout",
        duration="Duration like 10m, 2h, 1d (max 28d)",
        reason="Reason for timeout"
    )
    async def timeout(self, interaction: discord.Interaction, user: discord.Member, duration: str, reason: str = "No reason provided."):
        allowed, err = check_hierarchy(interaction.user, user, interaction.guild.me)
        if not allowed:
            return await interaction.response.send_message(embed=error_embed("Hierarchy Error", err), ephemeral=True)

        seconds = parse_time(duration)
        if not seconds or seconds < 10 or seconds > 2419200:  # 28 days max in Discord
            return await interaction.response.send_message(
                embed=error_embed("Invalid Duration", "Provide a duration between 10s and 28d (e.g. `15m`, `3h`, `2d`)."),
                ephemeral=True,
            )

        until = discord.utils.utcnow() + datetime.timedelta(seconds=seconds)
        try:
            await user.timeout(until, reason=f"Timed out by {interaction.user}: {reason}")
            await db.execute(
                "INSERT INTO moderation_logs (guild_id, user_id, moderator_id, action, reason, duration) VALUES (?, ?, ?, 'timeout', ?, ?)",
                (interaction.guild_id, user.id, interaction.user.id, reason, seconds),
            )
            await interaction.response.send_message(
                embed=success_embed(
                    "Member Timed Out",
                    f"{user.mention} has been timed out for **{format_duration(seconds)}**.\n**Reason:** {reason}"
                )
            )
        except discord.Forbidden:
            await interaction.response.send_message(embed=error_embed("Error", "Bot lacks permission to timeout this member."), ephemeral=True)

    @timeout_group.command(name="remove", description="Remove timeout from a member")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(user="Member to untimeout", reason="Reason for removing timeout")
    async def untimeout(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided."):
        allowed, err = check_hierarchy(interaction.user, user, interaction.guild.me)
        if not allowed:
            return await interaction.response.send_message(embed=error_embed("Hierarchy Error", err), ephemeral=True)

        try:
            await user.timeout(None, reason=f"Timeout removed by {interaction.user}: {reason}")
            await db.execute(
                "INSERT INTO moderation_logs (guild_id, user_id, moderator_id, action, reason) VALUES (?, ?, ?, 'untimeout', ?)",
                (interaction.guild_id, user.id, interaction.user.id, reason),
            )
            await interaction.response.send_message(
                embed=success_embed("Timeout Removed", f"Successfully removed timeout from {user.mention}.")
            )
        except discord.Forbidden:
            await interaction.response.send_message(embed=error_embed("Error", "Bot lacks permission to remove timeout."), ephemeral=True)

    warn_group = app_commands.Group(name="warn", description="Member warnings management")

    @warn_group.command(name="add", description="Issue a formal server warning to a member")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(user="Member to warn", reason="Reason for warning")
    async def warn(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        allowed, err = check_hierarchy(interaction.user, user, interaction.guild.me)
        if not allowed:
            return await interaction.response.send_message(embed=error_embed("Hierarchy Error", err), ephemeral=True)

        await db.execute(
            "INSERT INTO warnings (guild_id, user_id, moderator_id, reason) VALUES (?, ?, ?, ?)",
            (interaction.guild_id, user.id, interaction.user.id, reason),
        )

        count_row = await db.fetchone(
            "SELECT COUNT(*) as total FROM warnings WHERE guild_id = ? AND user_id = ?",
            (interaction.guild_id, user.id),
        )
        total_warns = count_row["total"] if count_row else 1

        embed = warning_embed(
            "Member Warned",
            f"**Target:** {user.mention} (`{user.id}`)\n"
            f"**Moderator:** {interaction.user.mention}\n"
            f"**Reason:** {reason}\n"
            f"**Total Warnings:** {total_warns}"
        )
        await interaction.response.send_message(embed=embed)

        try:
            dm_emb = warning_embed(
                f"Warning from {interaction.guild.name}",
                f"You have received a formal warning in **{interaction.guild.name}**.\n"
                f"**Reason:** {reason}\n"
                f"**Total Warnings:** {total_warns}"
            )
            await user.send(embed=dm_emb)
        except Exception:
            pass

    @warn_group.command(name="list", description="View warnings history for a member")
    @app_commands.describe(user="Member to inspect")
    async def warnings_cmd(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        target = user or interaction.user
        rows = await db.fetchall(
            "SELECT * FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY id DESC",
            (interaction.guild_id, target.id),
        )

        if not rows:
            return await interaction.response.send_message(
                embed=info_embed("No Warnings", f"{target.mention} has a clean record with 0 warnings."),
                ephemeral=True,
            )

        pages = []
        chunk_size = 5
        for i in range(0, len(rows), chunk_size):
            chunk = rows[i : i + chunk_size]
            embed = primary_embed(title=f"⚠️ Warning History - {target.display_name} ({len(rows)} Total)")
            for w in chunk:
                embed.add_field(
                    name=f"Case #{w['id']} • {w['timestamp']}",
                    value=f"**Mod:** <@{w['moderator_id']}>\n**Reason:** {w['reason']}",
                    inline=False,
                )
            pages.append(embed)

        if len(pages) == 1:
            await interaction.response.send_message(embed=pages[0])
        else:
            view = PaginatorView(pages, interaction.user.id)
            await interaction.response.send_message(embed=pages[0], view=view)

    @app_commands.command(name="clear", description="Bulk delete messages in the current channel")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(amount="Number of messages to delete (1-100)", user="Filter deletion to a specific user")
    async def clear(self, interaction: discord.Interaction, amount: int, user: Optional[discord.Member] = None):
        if not (1 <= amount <= 100):
            return await interaction.response.send_message(embed=error_embed("Invalid Amount", "Please choose between 1 and 100."), ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel

        def check_msg(m: discord.Message) -> bool:
            return m.author.id == user.id if user else True

        deleted = await channel.purge(limit=amount, check=check_msg)
        await interaction.followup.send(
            embed=success_embed("Messages Cleared", f"Deleted **{len(deleted)}** messages" + (f" from {user.mention}." if user else ".")),
            ephemeral=True,
        )

    @app_commands.command(name="slowmode", description="Set channel slowmode cooldown in seconds")
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.describe(seconds="Slowmode in seconds (0 to disable, max 21600)")
    async def slowmode(self, interaction: discord.Interaction, seconds: int):
        if not (0 <= seconds <= 21600):
            return await interaction.response.send_message(embed=error_embed("Invalid Range", "Slowmode must be between 0 and 21600s (6 hours)."), ephemeral=True)

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return

        await channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await interaction.response.send_message(embed=success_embed("Slowmode Disabled", "Slowmode has been turned off."))
        else:
            await interaction.response.send_message(embed=success_embed("Slowmode Configured", f"Slowmode set to **{seconds} seconds**."))

    channel_mod = app_commands.Group(name="channel", description="Manage channel access, lockdowns, and privacy")

    @channel_mod.command(name="lock", description="Lock a channel to prevent regular members from chatting")
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.describe(channel="Channel to lock (defaults to current channel)", reason="Reason for locking")
    async def lock(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None, reason: str = "Channel lockdown"):
        target_ch = channel or interaction.channel
        overwrites = target_ch.overwrites_for(interaction.guild.default_role)
        overwrites.send_messages = False
        await target_ch.set_permissions(interaction.guild.default_role, overwrite=overwrites, reason=f"Locked by {interaction.user}: {reason}")
        await interaction.response.send_message(
            embed=warning_embed("Channel Locked", f"{target_ch.mention} has been locked.\n**Reason:** {reason}")
        )

    @channel_mod.command(name="unlock", description="Unlock a previously locked channel")
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.describe(channel="Channel to unlock", reason="Reason for unlocking")
    async def unlock(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None, reason: str = "Channel unlocked"):
        target_ch = channel or interaction.channel
        overwrites = target_ch.overwrites_for(interaction.guild.default_role)
        overwrites.send_messages = None
        await target_ch.set_permissions(interaction.guild.default_role, overwrite=overwrites, reason=f"Unlocked by {interaction.user}: {reason}")
        await interaction.response.send_message(
            embed=success_embed("Channel Unlocked", f"{target_ch.mention} has been unlocked.")
        )

    @channel_mod.command(name="hide", description="Hide a channel from regular members")
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.describe(channel="Channel to hide")
    async def hide(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        target_ch = channel or interaction.channel
        overwrites = target_ch.overwrites_for(interaction.guild.default_role)
        overwrites.view_channel = False
        await target_ch.set_permissions(interaction.guild.default_role, overwrite=overwrites, reason=f"Hidden by {interaction.user}")
        await interaction.response.send_message(
            embed=warning_embed("Channel Hidden", f"{target_ch.mention} is now hidden from `@everyone`."),
            ephemeral=True,
        )

    @channel_mod.command(name="unhide", description="Unhide a channel for regular members")
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.describe(channel="Channel to unhide")
    async def unhide(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        target_ch = channel or interaction.channel
        overwrites = target_ch.overwrites_for(interaction.guild.default_role)
        overwrites.view_channel = None
        await target_ch.set_permissions(interaction.guild.default_role, overwrite=overwrites, reason=f"Unhidden by {interaction.user}")
        await interaction.response.send_message(
            embed=success_embed("Channel Unhidden", f"{target_ch.mention} is now visible to `@everyone`.")
        )

    @app_commands.command(name="nickname", description="Change a member's server nickname")
    @app_commands.checks.has_permissions(manage_nicknames=True)
    @app_commands.describe(user="Member to change nickname for", nickname="New nickname (leave blank to reset)")
    async def nickname(self, interaction: discord.Interaction, user: discord.Member, nickname: Optional[str] = None):
        allowed, err = check_hierarchy(interaction.user, user, interaction.guild.me)
        if not allowed:
            return await interaction.response.send_message(embed=error_embed("Hierarchy Error", err), ephemeral=True)

        try:
            await user.edit(nick=nickname, reason=f"Nickname modified by {interaction.user}")
            action = f"Changed nickname of {user.mention} to **{nickname}**." if nickname else f"Reset nickname for {user.mention}."
            await interaction.response.send_message(embed=success_embed("Nickname Updated", action))
        except discord.Forbidden:
            await interaction.response.send_message(embed=error_embed("Error", "Bot lacks permission to modify this user's nickname."), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))

