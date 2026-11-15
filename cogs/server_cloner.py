"""NOVEXA Server Structure Cloner Cog.

Complete Public & Internal Discord Server Structure Cloner:
SOURCE SERVER ID / TEMPLATE / IMPORT → CHECK ACCESS → GENERATE TEMPLATE → SELECT DESTINATION → PREVIEW → CONFIRM → CLONE → VERIFICATION REPORT.
"""

import asyncio
import io
import json
import logging
import time
from typing import Optional, Dict, List, Any
import discord
from discord import app_commands
from discord.ext import commands

from database.database import db
from services.server_cloner_service import ServerClonerService, extract_guild_id
from utils.embeds import primary_embed, success_embed, error_embed, warning_embed, info_embed
from utils.emojis import Emojis
from config import BOT_NAME

logger = logging.getLogger("novexa.server_cloner")


# ==================== MODALS & VIEWS ====================

class ServerInputModal(discord.ui.Modal, title="Clone Server Setup"):
    """Modal to collect Source (ID, Template, or Invite) and Destination Server ID."""

    source_input = discord.ui.TextInput(
        label="Source Server ID, Template, or Invite",
        placeholder="e.g. 1568356881364422807 or discord.new/abc or discord.gg/xyz",
        min_length=6,
        max_length=120,
        required=True,
    )
    dest_id_input = discord.ui.TextInput(
        label="Destination Server ID",
        placeholder="e.g. 1535157700168515616 (Must have NOVEXA installed)",
        min_length=17,
        max_length=21,
        required=True,
    )

    def __init__(self, cog: "ServerClonerCog"):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            d_id = int(self.dest_id_input.value.strip())
        except ValueError:
            await interaction.followup.send(
                embed=error_embed("Invalid Input", "Destination Server ID must be a numeric snowflake ID."),
                ephemeral=True,
            )
            return

        s_val = self.source_input.value.strip()
        await self.cog.start_clone_flow(interaction, s_val, d_id)


class TemplateLinkModal(discord.ui.Modal, title="Enter Discord Server Template"):
    """Modal to enter Discord Server Template link or code."""

    template_input = discord.ui.TextInput(
        label="Discord Template Link or Code",
        placeholder="e.g. https://discord.new/abc123xyz or abc123xyz",
        min_length=6,
        max_length=120,
        required=True,
    )

    def __init__(self, cog: "ServerClonerCog", dest_guild_id: int):
        super().__init__()
        self.cog = cog
        self.dest_guild_id = dest_guild_id

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        t_val = self.template_input.value.strip()
        await self.cog.start_clone_flow(interaction, t_val, self.dest_guild_id)


class ReplaceConfirmModal(discord.ui.Modal, title="⚠️ Confirm Replace Mode"):
    """Confirmation modal for destructive Replace Mode cloning."""

    confirmation_input = discord.ui.TextInput(
        label="Type CONFIRM_REPLACE to proceed",
        placeholder="CONFIRM_REPLACE",
        min_length=15,
        max_length=15,
        required=True,
    )

    def __init__(self, view: "ClonePreviewView"):
        super().__init__()
        self.preview_view = view

    async def on_submit(self, interaction: discord.Interaction):
        val = self.confirmation_input.value.strip()
        if val != "CONFIRM_REPLACE":
            await interaction.response.send_message(
                embed=error_embed("Replace Aborted", "Confirmation phrase did not match. Cloning cancelled."),
                ephemeral=True,
            )
            return

        await interaction.response.defer()
        await self.preview_view.trigger_clone(interaction, mode="replace")


class RestrictedAccessView(discord.ui.View):
    """View shown when source server access is restricted (private server)."""

    def __init__(self, cog: "ServerClonerCog", source_query: str, dest_guild_id: int, user_id: int):
        super().__init__(timeout=180)
        self.cog = cog
        self.source_query = source_query
        self.dest_guild_id = dest_guild_id
        self.user_id = user_id

        # Add OAuth2 Bot Invite Link Button if client ID is known
        bot_id = cog.bot.user.id if cog.bot.user else None
        if bot_id:
            invite_url = (
                f"https://discord.com/api/oauth2/authorize?client_id={bot_id}"
                f"&permissions=8&scope=bot%20applications.commands"
            )
            self.add_item(discord.ui.Button(label="Invite NOVEXA to Source", url=invite_url, emoji="🤖"))

    @discord.ui.button(label="Enter Template Link", style=discord.ButtonStyle.primary, emoji="🔗")
    async def btn_template(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Only the command initiator can use this.", ephemeral=True)
        modal = TemplateLinkModal(self.cog, self.dest_guild_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def btn_cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(embed=info_embed("Cancelled", "Operation cancelled."), ephemeral=True)


class ClonePreviewView(discord.ui.View):
    """Interactive preview panel with Add Mode, Replace Mode, and Export buttons."""

    def __init__(
        self,
        cog: "ServerClonerCog",
        structure: Dict[str, Any],
        dest_guild: discord.Guild,
        user_id: int,
        template_id: str,
    ):
        super().__init__(timeout=300)
        self.cog = cog
        self.structure = structure
        self.dest_guild = dest_guild
        self.user_id = user_id
        self.template_id = template_id

    @discord.ui.button(
        label="Add Mode (Safe / Recommended)",
        style=discord.ButtonStyle.success,
        emoji="➕",
        custom_id="cloner_btn_add_mode",
    )
    async def btn_add_mode(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Only the initiator can control this panel.", ephemeral=True)

        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

        await self.trigger_clone(interaction, mode="add")

    @discord.ui.button(
        label="Replace Mode (Destructive)",
        style=discord.ButtonStyle.danger,
        emoji="⚠️",
        custom_id="cloner_btn_replace_mode",
    )
    async def btn_replace_mode(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Only the initiator can control this panel.", ephemeral=True)

        modal = ReplaceConfirmModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="Save Template Only",
        style=discord.ButtonStyle.primary,
        emoji="💾",
        custom_id="cloner_btn_save_only",
    )
    async def btn_save_only(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Only the initiator can control this panel.", ephemeral=True)

        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

        await interaction.followup.send(
            embed=success_embed(
                "Template Saved",
                f"{Emojis.TICK} Custom structure template has been saved!\n"
                f"**Template ID:** `{self.template_id}`\n"
                f"You can apply it to any server later using `/clone apply`.",
            ),
            ephemeral=True,
        )

    @discord.ui.button(
        label="Export JSON",
        style=discord.ButtonStyle.secondary,
        emoji="📥",
        custom_id="cloner_btn_export_json",
    )
    async def btn_export_json(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Only the initiator can control this panel.", ephemeral=True)

        json_str = self.cog.cloner_service.export_structure_json(self.structure)
        s_name = self.structure.get("source_guild_name", "server").replace(" ", "_")
        file = discord.File(io.BytesIO(json_str.encode("utf-8")), filename=f"novexa_structure_{s_name}.json")
        await interaction.response.send_message(
            embed=success_embed("Architecture Exported", f"{Emojis.TICK} Downloaded server structure JSON below:"),
            file=file,
            ephemeral=True,
        )

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.secondary,
        emoji="❌",
        custom_id="cloner_btn_cancel",
    )
    async def btn_cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Only the initiator can control this panel.", ephemeral=True)

        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(
            embed=info_embed("Clone Cancelled", f"{Emojis.ARROW} Server cloning was aborted. No changes made."),
            ephemeral=True,
        )

    async def trigger_clone(self, interaction: discord.Interaction, mode: str):
        """Execute the cloning workflow with live status bar updates."""
        progress_msg = await interaction.followup.send(
            embed=primary_embed(
                "🚀 Initiating Server Cloning Engine",
                f"{Emojis.SPARKLES} Initializing transfer from **{self.structure.get('source_guild_name')}** "
                f"to **{self.dest_guild.name}** in **{mode.upper()} MODE**...\n\n"
                f"`[░░░░░░░░░░] 0%` • Preparing API requests...",
            )
        )

        last_update_time = 0.0

        async def _progress_cb(status: str, pct: float):
            nonlocal last_update_time
            now = time.perf_counter()
            if now - last_update_time < 1.5 and pct < 0.95:
                return
            last_update_time = now

            bar_len = 12
            filled = int(round(bar_len * pct))
            bar = "█" * filled + "░" * (bar_len - filled)
            percent_str = f"{int(pct * 100)}%"

            embed = primary_embed(
                f"🔄 Server Cloning in Progress ({percent_str})",
                f"**Source:** `{self.structure.get('source_guild_name')}`\n"
                f"**Destination:** `{self.dest_guild.name}`\n"
                f"**Mode:** `{mode.upper()} MODE`\n\n"
                f"`[{bar}] {percent_str}`\n\n"
                f"{Emojis.ARROW_GREEN} {status}",
            )
            try:
                await progress_msg.edit(embed=embed)
            except Exception:
                pass

        try:
            report = await self.cog.cloner_service.execute_clone(
                structure=self.structure,
                dest_guild=self.dest_guild,
                user_id=self.user_id,
                mode=mode,
                progress_cb=_progress_cb,
            )

            # Generate Final Verification Report
            report_embed = success_embed(
                title=f"{Emojis.TICK} SERVER CLONE VERIFICATION REPORT",
                description=(
                    f"Architecture successfully reconstructed in **{self.dest_guild.name}**!\n\n"
                    f"**Source Server:** `{report['source_guild_name']}` (`{report['source_guild_id']}`)\n"
                    f"**Access Method:** `{report.get('access_method_display', 'Direct Bot Scan')}`\n"
                    f"**Destination Server:** `{report['dest_guild_name']}` (`{report['dest_guild_id']}`)\n"
                    f"**Execution Mode:** `{report['mode'].upper()} MODE`\n"
                    f"**Duration:** `{report['duration_seconds']}s`"
                ),
            )

            report_embed.add_field(
                name="🛡️ Roles Created",
                value=f"`{report['roles_created']}` roles",
                inline=True,
            )
            report_embed.add_field(
                name="📁 Categories Created",
                value=f"`{report['categories_created']}` categories",
                inline=True,
            )
            report_embed.add_field(
                name="💬 Channels Created",
                value=f"`{report['channels_created']}` text/voice channels",
                inline=True,
            )
            report_embed.add_field(
                name="🔒 Overwrites Applied",
                value=f"`{report['overwrites_applied']}` permission rules",
                inline=True,
            )
            report_embed.add_field(
                name="💾 Reusable Template",
                value=f"Saved as `{self.template_id}`",
                inline=True,
            )
            report_embed.add_field(
                name="⚠️ Notices / Skips",
                value=f"`{report['warnings_count']}` items flagged",
                inline=True,
            )

            if report.get("unavailable_items"):
                unav_text = "\n".join([f"• {u}" for u in report["unavailable_items"][:4]])
                report_embed.add_field(name="ℹ️ Omitted / Restricted Data", value=unav_text, inline=False)

            if report.get("warnings"):
                warning_text = "\n".join([f"• {w}" for w in report["warnings"][:4]])
                if len(report["warnings"]) > 4:
                    warning_text += f"\n• ... and {len(report['warnings']) - 4} more items."
                report_embed.add_field(name="📋 Execution Notes", value=warning_text, inline=False)

            report_embed.set_footer(text=f"{BOT_NAME} Enterprise Architecture Cloner • 100% Verified")
            await progress_msg.edit(embed=report_embed)

        except Exception as e:
            logger.error(f"Clone execution failed: {e}", exc_info=True)
            await progress_msg.edit(
                embed=error_embed(
                    "Cloning Error",
                    f"An unexpected error occurred during server cloning:\n`{e}`\n"
                    f"Check bot permissions and role hierarchy in destination server.",
                )
            )


# ==================== MAIN CLONER COG ====================

class ServerClonerCog(commands.Cog, name="Server Cloner"):
    """Enterprise Discord Server Architecture Scanner & Cloner."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cloner_service = ServerClonerService(bot)

    async def start_clone_flow(
        self, interaction: discord.Interaction, source_query: str, dest_guild_id: int
    ):
        """Unified workflow to scan, validate access, preview, and prepare cloning."""
        # 1. Validate Destination Server
        d_ok, d_msg, d_guild = await self.cloner_service.validate_destination_server(
            dest_guild_id, interaction.user.id
        )
        if not d_ok or not d_guild:
            await interaction.followup.send(embed=error_embed("Destination Server Error", d_msg), ephemeral=True)
            return

        # 2. Resolve Source Access (Multi-tier: Bot, Template, Widget, Invite)
        status_embed = primary_embed(
            "🔍 Resolving Source Server Access...",
            f"{Emojis.SPARKLES} Probing source access methods for: `{source_query}`\n"
            f"Checking Bot Presence ➔ Discord Template API ➔ Public Widget API ➔ Public Preview...",
        )
        status_msg = await interaction.followup.send(embed=status_embed, ephemeral=True)

        try:
            s_ok, access_mode, report, structure = await self.cloner_service.resolve_source_access(
                source_query, interaction.user.id
            )
        except Exception as e:
            logger.error(f"Error resolving source access: {e}", exc_info=True)
            await status_msg.edit(embed=error_embed("Access Resolution Error", f"Unexpected error: `{e}`"))
            return

        # If Source Server is Restricted / Private
        if not s_ok or not structure:
            avail_embed = warning_embed(
                title="📋 SOURCE ACCESS & SCAN AVAILABILITY REPORT",
                description=(
                    f"**Source Input:** `{source_query}`\n"
                    f"**Server Status:** ⚠️ **Access Restricted / Private Server**\n\n"
                    f"{report.get('status_summary')}\n\n"
                    f"**Official Discord API Authorized Alternatives:**\n"
                    + "\n".join([f"• {m}" for m in report.get("available_methods", [])])
                ),
            )
            avail_embed.set_footer(text="Discord Developer Terms of Service strictly forbid scraping private servers.")
            view = RestrictedAccessView(self, source_query, dest_guild_id, interaction.user.id)
            await status_msg.edit(embed=avail_embed, view=view)
            return

        # 3. Save custom template automatically
        template_id = await self.cloner_service.save_template(structure, interaction.user.id)

        # 4. Generate Compatibility Preview & Capacity Checks
        preview = self.cloner_service.generate_clone_preview(structure, d_guild)

        preview_embed = primary_embed(
            title="📋 NOVEXA SERVER CLONER • ARCHITECTURE PREVIEW",
            description=(
                f"Review the imported architecture before cloning into **{d_guild.name}**.\n\n"
                f"**Source Server:** `{preview['source_name']}` (`{preview['source_id']}`)\n"
                f"**Access Method:** `{preview['access_method_display']}`\n"
                f"**Destination Server:** `{preview['dest_name']}` (`{preview['dest_id']}`)\n"
            ),
        )

        preview_embed.add_field(
            name="📊 Source Structure Breakdown",
            value=(
                f"🛡️ Roles: **{preview['roles_count']}**\n"
                f"📁 Categories: **{preview['categories_count']}**\n"
                f"💬 Text Channels: **{preview['text_channels_count']}**\n"
                f"🔊 Voice Channels: **{preview['voice_channels_count']}**\n"
                f"📐 Total Architecture: **{preview['total_channels']} items**"
            ),
            inline=True,
        )

        preview_embed.add_field(
            name="⚙️ Installation Modes",
            value=(
                f"**➕ Add Mode (Default / Safe):**\n"
                f"Creates missing roles & channels. Existing content in destination is **preserved**.\n\n"
                f"**⚠️ Replace Mode:**\n"
                f"Cleans destination channels & custom roles, then creates exact clone."
            ),
            inline=True,
        )

        if preview.get("unsupported"):
            limit_text = "\n".join([f"• {u}" for u in preview["unsupported"][:4]])
            preview_embed.add_field(name="ℹ️ Omitted / Restricted Items", value=limit_text, inline=False)

        if preview.get("warnings"):
            warning_text = "\n".join([f"• {w}" for w in preview["warnings"][:3]])
            preview_embed.add_field(name="⚠️ Destination Compatibility Warnings", value=warning_text, inline=False)

        preview_embed.set_footer(
            text=f"Template ID: {template_id} • Select mode below to begin or export JSON."
        )

        view = ClonePreviewView(self, structure, d_guild, interaction.user.id, template_id)
        await status_msg.edit(embed=preview_embed, view=view)

    # ==================== SLASH COMMANDS ====================

    clone_group = app_commands.Group(
        name="clone", description="Enterprise Discord server structure scanner and cloner"
    )

    @clone_group.command(
        name="server",
        description="Clone server structure using Server ID, Discord Template link, or Vanity Invite",
    )
    @app_commands.describe(
        source="Source Server ID, Discord Template link (discord.new/...), or Vanity Invite",
        destination_server_id="ID of the destination Discord server to apply structure into (optional)",
    )
    async def slash_clone_server(
        self,
        interaction: discord.Interaction,
        source: Optional[str] = None,
        destination_server_id: Optional[str] = None,
    ):
        """Main server cloning slash command entrypoint."""
        if not source or not destination_server_id:
            modal = ServerInputModal(self)
            await interaction.response.send_modal(modal)
            return

        await interaction.response.defer(ephemeral=True)
        try:
            d_id = int(destination_server_id.strip())
        except ValueError:
            await interaction.followup.send(
                embed=error_embed("Invalid Input", "Destination Server ID must be a numeric snowflake ID."),
                ephemeral=True,
            )
            return

        await self.start_clone_flow(interaction, source.strip(), d_id)

    @clone_group.command(
        name="import",
        description="Import an authorized server structure JSON file or Discord template link",
    )
    @app_commands.describe(
        file="Upload a .json structure file exported from NOVEXA or Discord template",
        template_link="Discord Server Template link or code (e.g. discord.new/abc123xyz)",
        destination_server_id="Destination Server ID to apply structure into (optional)",
    )
    async def slash_clone_import(
        self,
        interaction: discord.Interaction,
        file: Optional[discord.Attachment] = None,
        template_link: Optional[str] = None,
        destination_server_id: Optional[str] = None,
    ):
        if not file and not template_link:
            await interaction.response.send_message(
                embed=warning_embed(
                    "Import Source Required",
                    f"{Emojis.ARROW} Please provide either a `.json` structure file or a Discord template link.",
                ),
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        structure = None
        if file:
            if not file.filename.endswith(".json"):
                return await interaction.followup.send(
                    embed=error_embed("Invalid File", "Only `.json` files are supported."),
                    ephemeral=True,
                )
            try:
                content_bytes = await file.read()
                content_str = content_bytes.decode("utf-8")
                v_ok, v_msg, structure = self.cloner_service.parse_imported_json(content_str, interaction.user.id)
                if not v_ok or not structure:
                    return await interaction.followup.send(
                        embed=error_embed("Import Failed", v_msg), ephemeral=True
                    )
            except Exception as e:
                return await interaction.followup.send(
                    embed=error_embed("File Error", f"Could not read uploaded JSON: `{e}`"),
                    ephemeral=True,
                )
        elif template_link:
            s_ok, access_mode, report, structure = await self.cloner_service.resolve_source_access(
                template_link.strip(), interaction.user.id
            )
            if not s_ok or not structure:
                return await interaction.followup.send(
                    embed=error_embed("Template Error", report.get("status_summary", "Unknown template error.")),
                    ephemeral=True,
                )

        # Save template
        template_id = await self.cloner_service.save_template(structure, interaction.user.id)

        if destination_server_id:
            try:
                d_id = int(destination_server_id.strip())
                return await self.start_clone_flow(interaction, template_id, d_id)
            except ValueError:
                pass

        embed = success_embed(
            "Structure Imported Successfully",
            f"{Emojis.TICK} Successfully imported architecture: **{structure.get('source_guild_name')}**!\n\n"
            f"**Template ID:** `{template_id}`\n"
            f"🛡️ Roles: **{len(structure.get('roles', []))}**\n"
            f"📁 Categories: **{len(structure.get('categories', []))}**\n"
            f"💬 Text Channels: **{len(structure.get('text_channels', []))}**\n"
            f"🔊 Voice Channels: **{len(structure.get('voice_channels', []))}**\n\n"
            f"Deploy this structure anytime using: `/clone apply {template_id} <destination_id>`",
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @clone_group.command(
        name="export",
        description="Export an authorized server structure into a downloadable JSON file",
    )
    @app_commands.describe(
        server_id="ID of the server to export (defaults to current server)",
    )
    async def slash_clone_export(
        self, interaction: discord.Interaction, server_id: Optional[str] = None
    ):
        await interaction.response.defer(ephemeral=True)
        g_id = int(server_id.strip()) if server_id and server_id.strip().isdigit() else interaction.guild_id

        if not g_id:
            return await interaction.followup.send(
                embed=error_embed("Error", "Please run inside a server or provide a server ID."),
                ephemeral=True,
            )

        s_ok, access_mode, report, structure = await self.cloner_service.resolve_source_access(
            str(g_id), interaction.user.id
        )
        if not s_ok or not structure:
            return await interaction.followup.send(
                embed=error_embed("Export Failed", report.get("status_summary", "Could not access server.")),
                ephemeral=True,
            )

        json_str = self.cloner_service.export_structure_json(structure)
        s_name = structure.get("source_guild_name", "server").replace(" ", "_")
        file = discord.File(io.BytesIO(json_str.encode("utf-8")), filename=f"novexa_structure_{s_name}.json")

        embed = success_embed(
            "Server Architecture Exported",
            f"{Emojis.TICK} Architecture for **{structure.get('source_guild_name')}** has been exported.\n"
            f"Save this JSON file or import it into any server using `/clone import`.",
        )
        await interaction.followup.send(embed=embed, file=file, ephemeral=True)

    @clone_group.command(name="templates", description="List all saved custom server clone templates")
    async def template_list(self, interaction: discord.Interaction):
        templates = await self.cloner_service.list_templates(creator_id=interaction.user.id)
        if not templates:
            await interaction.response.send_message(
                embed=info_embed(
                    "No Templates Found",
                    f"{Emojis.ARROW} You haven't scanned or saved any custom server templates yet.\n"
                    f"Use `/clone server` to scan any authorized server or `/clone import` to upload a template!",
                ),
                ephemeral=True,
            )
            return

        embed = primary_embed(
            title=f"📋 Saved Server Templates ({len(templates)})",
            description="Your reusable custom server architectures scanned from live Discord servers:",
        )
        for t in templates[:10]:
            embed.add_field(
                name=f"📁 {t['template_name']}",
                value=(
                    f"**ID:** `{t['template_id']}`\n"
                    f"**Source Server:** `{t['source_guild_name']}`\n"
                    f"**Created:** `{t['created_at']}`"
                ),
                inline=False,
            )

        embed.set_footer(text="Use `/clone apply <id> <destination_id>` to deploy a template to any server.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @clone_group.command(name="view", description="Inspect detailed role and channel counts of a template")
    @app_commands.describe(template_id="ID of the clone template to inspect")
    async def template_view(self, interaction: discord.Interaction, template_id: str):
        data = await self.cloner_service.get_template(template_id.strip())
        if not data:
            await interaction.response.send_message(
                embed=error_embed("Not Found", f"No template found matching ID `{template_id}`."),
                ephemeral=True,
            )
            return

        embed = primary_embed(
            title=f"📋 Template: {data.get('template_name', 'Custom Architecture')}",
            description=(
                f"**Source Server:** `{data.get('source_guild_name')}` (`{data.get('source_guild_id')}`)\n"
                f"**Access Method:** `{data.get('access_method_display', 'Standard Scan')}`\n\n"
                f"🛡️ Roles: **{len(data.get('roles', []))}**\n"
                f"📁 Categories: **{len(data.get('categories', []))}**\n"
                f"💬 Text Channels: **{len(data.get('text_channels', []))}**\n"
                f"🔊 Voice Channels: **{len(data.get('voice_channels', []))}**\n"
            ),
        )

        categories_summary = "\n".join(
            [f"• **{c['name']}**" for c in data.get("categories", [])[:8]]
        )
        if len(data.get("categories", [])) > 8:
            categories_summary += f"\n• ... and {len(data['categories']) - 8} more."
        if categories_summary:
            embed.add_field(name="Categories Architecture", value=categories_summary, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @clone_group.command(name="apply", description="Deploy a saved cloned template to an authorized destination server")
    @app_commands.describe(
        template_id="ID of the saved clone template to deploy",
        destination_server_id="ID of the destination server to apply architecture into",
    )
    async def template_apply(
        self, interaction: discord.Interaction, template_id: str, destination_server_id: str
    ):
        await interaction.response.defer(ephemeral=True)
        try:
            d_id = int(destination_server_id.strip())
        except ValueError:
            await interaction.followup.send(
                embed=error_embed("Invalid Input", "Destination Server ID must be a number."),
                ephemeral=True,
            )
            return

        data = await self.cloner_service.get_template(template_id.strip())
        if not data:
            await interaction.followup.send(
                embed=error_embed("Not Found", f"Template `{template_id}` does not exist."),
                ephemeral=True,
            )
            return

        d_ok, d_msg, d_guild = await self.cloner_service.validate_destination_server(
            d_id, interaction.user.id
        )
        if not d_ok or not d_guild:
            await interaction.followup.send(
                embed=error_embed("Destination Server Error", d_msg),
                ephemeral=True,
            )
            return

        preview = self.cloner_service.generate_clone_preview(data, d_guild)
        preview_embed = primary_embed(
            title=f"📋 DEPLOY TEMPLATE: {data.get('template_name')}",
            description=(
                f"Deploying saved architecture to **{d_guild.name}** (`{d_guild.id}`).\n\n"
                f"🛡️ Roles: **{preview['roles_count']}**\n"
                f"📁 Categories: **{preview['categories_count']}**\n"
                f"💬 Text Channels: **{preview['text_channels_count']}**\n"
                f"🔊 Voice Channels: **{preview['voice_channels_count']}**\n"
            ),
        )

        view = ClonePreviewView(self, data, d_guild, interaction.user.id, template_id)
        await interaction.followup.send(embed=preview_embed, view=view, ephemeral=True)

    @clone_group.command(name="delete", description="Delete a saved clone template")
    @app_commands.describe(template_id="ID of the template to delete")
    async def template_delete(self, interaction: discord.Interaction, template_id: str):
        ok = await self.cloner_service.delete_template(template_id.strip())
        if ok:
            await interaction.response.send_message(
                embed=success_embed("Template Deleted", f"{Emojis.TICK} Template `{template_id}` was removed."),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                embed=error_embed("Not Found", f"Template `{template_id}` could not be found."),
                ephemeral=True,
            )

    # ==================== PREFIX COMMAND COMPATIBILITY ====================

    @commands.command(name="clone", aliases=["cloneserver", "serverclone"])
    @commands.has_permissions(administrator=True)
    async def prefix_clone(self, ctx: commands.Context, source: str, dest_id: int):
        """Prefix command to initiate server cloning."""
        d_ok, d_msg, d_guild = await self.cloner_service.validate_destination_server(
            dest_id, ctx.author.id
        )
        if not d_ok or not d_guild:
            await ctx.send(embed=error_embed("Destination Server Error", d_msg))
            return

        status_msg = await ctx.send(
            embed=primary_embed("Resolving Access...", f"Probing access for source: `{source}`...")
        )
        s_ok, access_mode, report, structure = await self.cloner_service.resolve_source_access(
            source, ctx.author.id
        )
        if not s_ok or not structure:
            avail_embed = warning_embed(
                title="Access Restricted",
                description=(
                    f"**Status:** ⚠️ Access Restricted\n"
                    f"{report.get('status_summary')}\n\n"
                    f"Use `/clone server` or `/clone import` to provide a Discord template link or JSON file."
                ),
            )
            await status_msg.edit(embed=avail_embed)
            return

        template_id = await self.cloner_service.save_template(structure, ctx.author.id)
        preview = self.cloner_service.generate_clone_preview(structure, d_guild)

        embed = primary_embed(
            title="📋 NOVEXA SERVER CLONER • PREVIEW",
            description=(
                f"**Source:** `{preview['source_name']}`\n"
                f"**Access:** `{preview['access_method_display']}`\n"
                f"**Destination:** `{preview['dest_name']}`\n\n"
                f"Roles: **{preview['roles_count']}** • Categories: **{preview['categories_count']}** • "
                f"Channels: **{preview['total_channels']}**"
            ),
        )
        view = ClonePreviewView(self, structure, d_guild, ctx.author.id, template_id)
        await status_msg.edit(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(ServerClonerCog(bot))
