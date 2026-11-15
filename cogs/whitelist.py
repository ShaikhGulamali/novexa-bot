"""NOVEXA - Advanced Whitelist & Bot Approval Suite Cog.

Features:
- Granular per-server whitelist management for trusted staff and moderation roles
- Strict least-privilege enforcement: Whitelist NEVER grants permissions a member does not already have
- Dedicated Approved Bots registry for owner-verified bot applications
- Emergency bulk clear with confirmation dialog
- Bot-addition interception itself lives in cogs/antinuke.py (single listener, panic ban + DM)
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
import datetime
from typing import Optional, List
from database.database import db
from services.security_service import security_service
from utils.permissions import has_admin_or_owner, is_bot_owner
from utils.embeds import primary_embed, success_embed, error_embed, warning_embed

logger = logging.getLogger("novexa.whitelist")


class ClearWhitelistConfirmView(discord.ui.View):
    """Confirmation view for wiping all whitelisted users and roles."""

    def __init__(self, guild_id: int, author_id: int):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Only the command invoker can confirm this action.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirm Reset Whitelist", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await db.execute("DELETE FROM antinuke_whitelist WHERE guild_id = ?", (self.guild_id,))
        await db.execute(
            """
            INSERT INTO whitelist_audit (guild_id, target_id, target_type, action, performed_by)
            VALUES (?, 0, 'ALL', 'CLEAR_ALL', ?)
            """,
            (self.guild_id, interaction.user.id),
        )
        embed = warning_embed("Whitelist Reset", "All whitelisted users and roles for this server have been removed.")
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Whitelist reset cancelled.", embed=None, view=None)


class Whitelist(commands.Cog):
    """Enterprise Whitelist Management & Bot Addition Protection."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ==================== SLASH COMMANDS: /whitelist ====================

    whitelist_group = app_commands.Group(name="whitelist", description="Manage trusted immunity whitelist and bot approval")

    @whitelist_group.command(name="add", description="Add a trusted member or role to the Anti-Nuke immunity whitelist")
    @has_admin_or_owner()
    @app_commands.describe(
        user="Member to whitelist",
        role="Role to whitelist",
        duration_days="Optional expiration in days (leave empty for permanent)",
    )
    async def whitelist_add(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.Member] = None,
        role: Optional[discord.Role] = None,
        duration_days: Optional[int] = None,
    ):
        target = user or role
        if not target:
            return await interaction.response.send_message("Please specify either a user or a role to whitelist.", ephemeral=True)

        if target.id == interaction.user.id:
            return await interaction.response.send_message(
                embed=error_embed("Security Restriction", "You cannot whitelist yourself. Another authorized staff member or the server owner must perform this action."),
                ephemeral=True,
            )

        target_type = "role" if isinstance(target, discord.Role) else "user"
        expires_at = None
        if duration_days and duration_days > 0:
            expires_at = (
                datetime.datetime.utcnow() + datetime.timedelta(days=duration_days)
            ).strftime("%Y-%m-%d %H:%M:%S")

        await security_service.add_whitelist(
            interaction.guild_id,
            target.id,
            target_type,
            added_by=interaction.user.id,
            expires_at=expires_at,
        )

        # Record in audit log
        await db.execute(
            """
            INSERT INTO whitelist_audit (guild_id, target_id, target_type, action, performed_by, expires_at)
            VALUES (?, ?, ?, 'ADD', ?, ?)
            """,
            (interaction.guild_id, target.id, target_type, interaction.user.id, expires_at),
        )

        dur_text = f"for **{duration_days} days**" if duration_days else "**permanently**"
        embed = success_embed(
            "Whitelist Granted",
            f"Successfully added {target.mention} (`{target.id}`) to the immunity whitelist {dur_text}.\n\n"
            f"🛡️ *Note: Whitelist grants immunity from automated anti-nuke threshold strikes. It does NOT grant administrator privileges or permission to add unauthorized bots.*",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @whitelist_group.command(name="remove", description="Remove a member or role from the immunity whitelist")
    @has_admin_or_owner()
    @app_commands.describe(
        user="Member to remove from whitelist",
        role="Role to remove from whitelist",
    )
    async def whitelist_remove(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.Member] = None,
        role: Optional[discord.Role] = None,
    ):
        target = user or role
        if not target:
            return await interaction.response.send_message("Please specify either a user or a role to remove.", ephemeral=True)

        target_type = "role" if isinstance(target, discord.Role) else "user"
        res = await db.execute(
            "DELETE FROM antinuke_whitelist WHERE guild_id = ? AND target_id = ?",
            (interaction.guild_id, target.id),
        )

        await db.execute(
            """
            INSERT INTO whitelist_audit (guild_id, target_id, target_type, action, performed_by)
            VALUES (?, ?, ?, 'REMOVE', ?)
            """,
            (interaction.guild_id, target.id, target_type, interaction.user.id),
        )

        embed = warning_embed("Whitelist Revoked", f"Removed {target.mention} from the immunity whitelist.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @whitelist_group.command(name="list", description="View all currently whitelisted members and roles")
    @has_admin_or_owner()
    async def whitelist_list(self, interaction: discord.Interaction):
        rows = await db.fetchall("SELECT * FROM antinuke_whitelist WHERE guild_id = ?", (interaction.guild_id,))
        if not rows:
            return await interaction.response.send_message("No users or roles are currently whitelisted on this server.", ephemeral=True)

        members_list = []
        roles_list = []
        for r in rows:
            adder = f"<@{r['added_by']}>" if r['added_by'] else "Unknown"
            suffix = ""
            if "expires_at" in r.keys() and r["expires_at"]:
                suffix = f" — expires {r['expires_at'][:10]}"
            if r["target_type"] == "role":
                roles_list.append(f"• <@&{r['target_id']}> — Added by {adder}{suffix}")
            else:
                members_list.append(f"• <@{r['target_id']}> — Added by {adder}{suffix}")

        embed = primary_embed(title=f"🛡️ Whitelist Registry — {interaction.guild.name}")
        embed.description = "Members and roles below are immune from automatic anti-nuke threshold triggers."
        if members_list:
            embed.add_field(name=f"Whitelisted Users ({len(members_list)})", value="\n".join(members_list[:15]), inline=False)
        if roles_list:
            embed.add_field(name=f"Whitelisted Roles ({len(roles_list)})", value="\n".join(roles_list[:15]), inline=False)

        embed.set_footer(text=f"Total: {len(rows)} entries • Server Owner is permanently immune")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @whitelist_group.command(name="check", description="Check if a specific member or role is currently whitelisted")
    @has_admin_or_owner()
    @app_commands.describe(
        user="Member to check",
        role="Role to check",
    )
    async def whitelist_check(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.Member] = None,
        role: Optional[discord.Role] = None,
    ):
        target = user or role or interaction.user
        guild = interaction.guild

        if target.id == guild.owner_id:
            embed = success_embed("Immunity Status: OWNER", f"{target.mention} is the **Server Owner** and has permanent absolute immunity.")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        is_wl = await security_service.is_whitelisted(guild, target)
        if is_wl:
            embed = success_embed("Immunity Status: WHITELISTED", f"{target.mention} is **actively whitelisted** and immune from anti-nuke threshold strikes.")
        else:
            embed = warning_embed("Immunity Status: NOT WHITELISTED", f"{target.mention} is **not whitelisted** and is subject to standard rate-limit enforcement.")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @whitelist_group.command(name="clear", description="Clear all whitelisted members and roles for this server")
    @has_admin_or_owner()
    async def whitelist_clear(self, interaction: discord.Interaction):
        view = ClearWhitelistConfirmView(interaction.guild_id, interaction.user.id)
        embed = warning_embed(
            "Confirm Whitelist Reset",
            "Are you sure you want to delete **ALL** whitelisted users and roles from this server?\n"
            "This action cannot be undone.",
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @whitelist_group.command(name="settings", description="View whitelist governance settings and security guidelines")
    @has_admin_or_owner()
    async def whitelist_settings(self, interaction: discord.Interaction):
        embed = primary_embed(title=f"🛡️ Whitelist Governance & Security — {interaction.guild.name}")
        embed.description = (
            "### 🔒 Security Principles:\n"
            "1. **No Privilege Elevation:** Whitelisting a user does NOT give them Administrator permissions.\n"
            "2. **Bot Addition Isolated:** Whitelisted users CANNOT add unapproved bots.\n"
            "3. **Owner Protected:** The server owner is permanently immune and cannot be removed.\n"
            "4. **Audit Tracked:** Every addition and revocation is logged permanently in the security database.\n\n"
            "### 📋 Management Commands:\n"
            "• `/whitelist add <user/role>` - Add trusted entry\n"
            "• `/whitelist remove <user/role>` - Revoke whitelist\n"
            "• `/whitelist list` - View all whitelisted entities\n"
            "• `/whitelist bot-approve <bot_id>` - Approve a bot application"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ==================== BOT ADDITION APPROVAL COMMANDS ====================

    @whitelist_group.command(name="bot-approve", description="Approve a verified Discord bot application ID for addition")
    @has_admin_or_owner()
    @app_commands.describe(
        bot_id="Discord Client / Application ID of the bot to approve",
        bot_name="Descriptive name of the bot (e.g. Midjourney, Rythm)",
    )
    async def whitelist_bot_approve(
        self,
        interaction: discord.Interaction,
        bot_id: str,
        bot_name: Optional[str] = "Approved Bot",
    ):
        try:
            bot_int_id = int(bot_id.strip())
        except ValueError:
            return await interaction.response.send_message("Invalid Bot ID. Please provide a numeric Discord application ID.", ephemeral=True)

        await db.execute(
            """
            INSERT OR REPLACE INTO security_approved_bots (guild_id, bot_id, bot_name, approved_by)
            VALUES (?, ?, ?, ?)
            """,
            (interaction.guild_id, bot_int_id, bot_name, interaction.user.id),
        )

        embed = success_embed(
            "Bot Application Approved",
            f"Bot **{bot_name}** (`{bot_int_id}`) is now explicitly approved to join **{interaction.guild.name}**.\n\n"
            f"When invited, it will not be automatically kicked by the Bot Protection suite.",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @whitelist_group.command(name="bot-remove", description="Revoke approved status for a bot application ID")
    @has_admin_or_owner()
    @app_commands.describe(bot_id="Discord Client / Application ID to remove")
    async def whitelist_bot_remove(self, interaction: discord.Interaction, bot_id: str):
        try:
            bot_int_id = int(bot_id.strip())
        except ValueError:
            return await interaction.response.send_message("Invalid Bot ID.", ephemeral=True)

        await db.execute(
            "DELETE FROM security_approved_bots WHERE guild_id = ? AND bot_id = ?",
            (interaction.guild_id, bot_int_id),
        )
        embed = warning_embed("Bot Approval Revoked", f"Removed Bot ID `{bot_int_id}` from the approved bots list.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @whitelist_group.command(name="bot-list", description="List all explicitly approved bot applications for this server")
    @has_admin_or_owner()
    async def whitelist_bot_list(self, interaction: discord.Interaction):
        rows = await db.fetchall("SELECT * FROM security_approved_bots WHERE guild_id = ?", (interaction.guild_id,))
        if not rows:
            return await interaction.response.send_message("No bot applications are currently approved. Any bot invited by non-owners will be auto-kicked.", ephemeral=True)

        lines = [f"• **{r['bot_name']}** (`{r['bot_id']}`) — Approved by <@{r['approved_by']}>" for r in rows]
        embed = primary_embed(title=f"🤖 Approved Bot Applications — {interaction.guild.name}", description="\n".join(lines))
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Whitelist(bot))

