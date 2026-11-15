"""NOVEXA - Server Backup & Disaster Recovery Suite Cog.

Security configuration lives in the single /antinuke surface.
This cog keeps only the backup vault:

- /backup create
- /backup list
- /backup restore
- /backup delete
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional
from services.backup_service import backup_service
from utils.permissions import has_admin_or_owner
from utils.embeds import primary_embed, success_embed, error_embed, warning_embed

logger = logging.getLogger("novexa.security")


class RestoreConfirmView(discord.ui.View):
    """Interactive confirmation dialog for restoring server architecture from a backup snapshot."""

    def __init__(self, guild: discord.Guild, backup_id: str, author_id: int):
        super().__init__(timeout=60)
        self.guild = guild
        self.backup_id = backup_id
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Only the command invoker can confirm this restoration.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Proceed with Restoration", style=discord.ButtonStyle.danger, emoji="🔄")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        try:
            stats = await backup_service.restore_backup(self.guild, self.backup_id)
            embed = success_embed(
                "🎉 Server Restoration Completed",
                f"Successfully restored elements from backup `{self.backup_id}`:\n\n"
                f"• **Roles Restored:** {stats['roles_created']}\n"
                f"• **Categories Restored:** {stats['categories_created']}\n"
                f"• **Channels Restored:** {stats['channels_created']}\n"
                f"• **Configs Restored:** {stats['configs_restored']}\n\n"
                f"🛡️ *Existing channels and roles were preserved.*",
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(embed=error_embed("Restoration Error", str(e)))

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Restoration cancelled.", embed=None, view=None)


class Security(commands.Cog):
    """Server structure snapshots and disaster recovery."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ==================== /backup COMMAND GROUP ====================

    backup_group = app_commands.Group(name="backup", description="Server structure snapshots and disaster recovery")

    @backup_group.command(name="create", description="Create an instant snapshot backup of roles, channels, and bot settings")
    @has_admin_or_owner()
    @app_commands.describe(name="Optional custom name for this snapshot")
    async def backup_create(self, interaction: discord.Interaction, name: Optional[str] = None):
        await interaction.response.defer(ephemeral=True)
        res = await backup_service.create_backup(interaction.guild, interaction.user.id, name)
        embed = success_embed(
            "Server Snapshot Created",
            f"**Backup ID:** `{res['backup_id']}`\n"
            f"**Name:** {res['name']}\n\n"
            f"• **Roles Backed Up:** {res['roles_count']}\n"
            f"• **Channels Backed Up:** {res['channels_count']}\n"
            f"• **Categories Backed Up:** {res['categories_count']}\n"
            f"• **Webhooks Indexed:** {res['webhooks_count']}\n\n"
            f"To restore this backup at any time, run `/backup restore id:{res['backup_id']}`.",
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @backup_group.command(name="list", description="List all saved backup snapshots for this server")
    @has_admin_or_owner()
    async def backup_list(self, interaction: discord.Interaction):
        backups = await backup_service.list_backups(interaction.guild_id)
        if not backups:
            return await interaction.response.send_message("No backups have been created for this server yet. Create one with `/backup create`.", ephemeral=True)

        lines = []
        for b in backups[:10]:
            size_kb = round(b.get("size_bytes", 0) / 1024, 1)
            lines.append(f"• **`{b['backup_id']}`** — {b['backup_name']} *({b['created_at'][:16]}, {size_kb} KB)*")

        embed = primary_embed(title=f"💾 Saved Server Snapshots — {interaction.guild.name}", description="\n".join(lines))
        embed.set_footer(text=f"Total: {len(backups)} Snapshots • Use /backup restore <id> to apply")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @backup_group.command(name="restore", description="Restore missing channels, roles, and settings from a snapshot")
    @has_admin_or_owner()
    @app_commands.describe(backup_id="Backup ID code to restore (e.g. bk_a1b2c3d4e5)")
    async def backup_restore(self, interaction: discord.Interaction, backup_id: str):
        payload = await backup_service.get_backup(backup_id.strip())
        if not payload:
            return await interaction.response.send_message(
                embed=error_embed("Backup Not Found", f"No snapshot found with ID `{backup_id}`."),
                ephemeral=True,
            )

        roles_len = len(payload.get("roles", []))
        ch_len = len(payload.get("channels", []))
        cat_len = len(payload.get("categories", []))

        embed = warning_embed(
            "Confirm Disaster Recovery",
            f"You are about to restore snapshot **`{backup_id}`** ({payload.get('created_at')[:16]}):\n\n"
            f"• **Roles in Snapshot:** {roles_len}\n"
            f"• **Channels in Snapshot:** {ch_len}\n"
            f"• **Categories in Snapshot:** {cat_len}\n\n"
            f"⚠️ **Safe Recovery Guarantee:** This operation will recreate any missing channels, categories, and roles. "
            f"It will **NOT** delete existing channels or wipe members.",
        )
        view = RestoreConfirmView(interaction.guild, backup_id.strip(), interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @backup_group.command(name="delete", description="Permanently delete a backup snapshot from the vault")
    @has_admin_or_owner()
    @app_commands.describe(backup_id="Backup ID to delete")
    async def backup_delete(self, interaction: discord.Interaction, backup_id: str):
        deleted = await backup_service.delete_backup(backup_id.strip())
        if deleted:
            await interaction.response.send_message(
                embed=success_embed("Backup Deleted", f"Successfully removed backup `{backup_id}` from vault."),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                embed=error_embed("Not Found", f"Could not find backup `{backup_id}`."),
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Security(bot))

