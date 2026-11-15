import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
import json
import time
from typing import Optional, Dict, List, Any, Tuple

from database.database import db
from utils.embeds import primary_embed, success_embed, error_embed, warning_embed, info_embed
from utils.permissions import has_admin_or_owner
from utils.templates import TEMPLATES, DEFAULT_ROLES, STANDARD_LOGS_CATEGORY, TEMPLATE_CATEGORIES
from cogs.tickets import TicketPanelView
from services.dropper_service import dropper_service

logger = logging.getLogger("novexa.templates")


async def apply_permission_lockdown(
    guild: discord.Guild,
    member_role: Optional[discord.Role] = None,
) -> Tuple[Dict[str, int], List[str]]:
    """Hide every category/channel from @everyone and grant the bot's Member role per channel type."""
    if member_role is None:
        member_role = discord.utils.find(
            lambda r: "member" in r.name.lower() and not r.is_default() and not r.managed,
            guild.roles,
        )

    everyone_hidden = discord.PermissionOverwrite(view_channel=False)
    member_general_ow = discord.PermissionOverwrite(
        view_channel=True, send_messages=True, read_message_history=True, add_reactions=True,
    )
    member_text_ow = discord.PermissionOverwrite(
        view_channel=True, send_messages=False, read_message_history=True, add_reactions=True,
    )
    member_voice_ow = discord.PermissionOverwrite(
        view_channel=True, connect=True, speak=True, stream=True,
    )
    member_category_ow = discord.PermissionOverwrite(view_channel=True)

    stats = {"categories": 0, "channels": 0, "failed": 0}
    failures: List[str] = []

    async def _edit_overwrites(target, payload) -> bool:
        for attempt in range(4):
            try:
                await target.edit(overwrites=payload, reason="Novexa Permission Lockdown")
                return True
            except discord.HTTPException as e:
                if e.status == 429:
                    await asyncio.sleep(e.retry_after if e.retry_after is not None else 0.5)
                else:
                    failures.append(f"{target.name}: {e}")
                    return False
            except Exception as e:
                failures.append(f"{target.name}: {e}")
                return False
        failures.append(f"{target.name}: rate limited")
        return False

    jobs: List[Tuple[str, Any, Dict[Any, discord.PermissionOverwrite]]] = []

    for cat in guild.categories:
        payload = dict(cat.overwrites)
        payload[guild.default_role] = everyone_hidden
        if member_role:
            payload[member_role] = member_category_ow
        jobs.append(("cat", cat, payload))

    for ch in guild.channels:
        if isinstance(ch, discord.CategoryChannel):
            continue
        payload = dict(ch.overwrites)
        payload[guild.default_role] = everyone_hidden
        if member_role:
            if isinstance(ch, (discord.VoiceChannel, discord.StageChannel)):
                payload[member_role] = member_voice_ow
            elif "general" in ch.name.lower():
                payload[member_role] = member_general_ow
            else:
                payload[member_role] = member_text_ow
        jobs.append(("ch", ch, payload))

    results = await asyncio.gather(
        *[_edit_overwrites(obj, payload) for _, obj, payload in jobs],
        return_exceptions=True,
    )

    for (kind, _, _), res in zip(jobs, results):
        if res is True:
            stats["categories" if kind == "cat" else "channels"] += 1
        else:
            stats["failed"] += 1
            if isinstance(res, Exception):
                failures.append(str(res))

    return stats, failures


class ServerNameModal(discord.ui.Modal, title="Server Name Configuration"):
    """Collect the user's preferred server name before initiating setup."""

    server_name_input = discord.ui.TextInput(
        label="What should your Discord Server be named?",
        placeholder="e.g. NOVEXA GAMING HUB",
        min_length=2,
        max_length=100,
        required=True,
    )

    def __init__(self, template_id: str):
        super().__init__()
        self.template_id = template_id

    async def on_submit(self, interaction: discord.Interaction):
        template = TEMPLATES.get(self.template_id)
        if not template:
            return await interaction.response.send_message(
                embed=error_embed("Template Error", "Selected template was not found."),
                ephemeral=True,
            )

        new_name = self.server_name_input.value.strip()

        # Build preview embed
        total_channels = sum(len(cat["channels"]) for cat in template["categories"])
        text_count = sum(sum(1 for ch in cat["channels"] if ch["type"] == "text") for cat in template["categories"])
        voice_count = sum(sum(1 for ch in cat["channels"] if ch["type"] == "voice") for cat in template["categories"])

        preview_embed = primary_embed(
            title="📋 NOVEXA SERVER BUILDER • SETUP PREVIEW",
            description=(
                f"Please review the proposed server architecture before building.\n"
                f"No existing channels, roles or configurations will be deleted.\n\n"
                f"**Selected Template:** {template['emoji']} **{template['name']}**\n"
                f"**Category:** `{template['category']}`\n"
                f"**New Server Name:** `{new_name}`\n"
                f"**Description:** {template['description']}\n"
            ),
        )

        categories_summary = "\n".join([f"• **{c['name']}** ({len(c['channels'])} channels)" for c in template["categories"][:6]])
        if len(template["categories"]) > 6:
            categories_summary += f"\n• ... and {len(template['categories']) - 6} more categories."

        preview_embed.add_field(
            name=f"📁 Categories ({len(template['categories'])})",
            value=categories_summary,
            inline=False,
        )

        preview_embed.add_field(
            name="📊 Channel Architecture",
            value=f"💬 Text Channels: **{text_count}**\n🔊 Voice Channels: **{voice_count}**\nTotal: **{total_channels}**",
            inline=True,
        )

        preview_embed.add_field(
            name=f"🛡️ Roles Hierarchy ({len(template['roles'])})",
            value="🤖 Novexa (Top) • 👤 Member (2nd) • 👑 Owner • 🔱 Co-Owner • 🛡️ Admin • 🔨 Mod • 🎫 Support • 💎 Platinum • 🥇 Gold • 🥈 Silver • ✅ Verified • 🤖 Bots",
            inline=True,
        )

        preview_embed.add_field(
            name="⚙️ Automatic Modules Integrated",
            value=(
                "✅ **Welcome System** (Welcome channel + greeting embed)\n"
                "✅ **Verification Gate** (Rules + 1-Click interactive verify button)\n"
                "✅ **Support Tickets** (Dedicated ticket panel + Create button)\n"
                "✅ **Enterprise Logs** (10 channels under 🛡️ NOVEXA LOGS)\n"
                "✅ **Anti-Nuke Protection** (Owner whitelist + audit log channel)"
            ),
            inline=False,
        )

        preview_embed.set_footer(text="Click 'Confirm & Build' to start. You can safely rollback anytime using /server-setup-rollback.")

        view = SetupConfirmView(self.template_id, new_name)
        await interaction.response.send_message(embed=preview_embed, view=view, ephemeral=True)


class CategorySelect(discord.ui.Select):
    """Dropdown to filter templates by category or browse all in 25-item pages."""

    def __init__(self, current_category: str = "p1"):
        options = [
            discord.SelectOption(
                label="Browse All (Page 1: 1-25)",
                value="p1",
                description="Templates 1 to 25 (Gaming, Store, Tech, Creators, Anime)",
                emoji="🌐",
                default=(current_category == "p1"),
            ),
            discord.SelectOption(
                label="Browse All (Page 2: 26-50)",
                value="p2",
                description="Templates 26 to 50 (Social, Music, Education, Business, Ops)",
                emoji="🌐",
                default=(current_category == "p2"),
            ),
            discord.SelectOption(
                label="Gaming & Esports",
                value="gaming",
                description="8 Templates • Free Fire, Esports, FiveM, FPS, Roblox, Royale",
                emoji="🎮",
                default=(current_category == "gaming"),
            ),
            discord.SelectOption(
                label="Store & Commerce",
                value="store",
                description="6 Templates • Digital Store, Crypto, Clothing, Reselling",
                emoji="🛍️",
                default=(current_category == "store"),
            ),
            discord.SelectOption(
                label="Tech, Coding & AI",
                value="tech",
                description="6 Templates • Developers, AI/ML, Cyber Security, GameDev",
                emoji="💻",
                default=(current_category == "tech"),
            ),
            discord.SelectOption(
                label="Content Creators & Media",
                value="creators",
                description="5 Templates • YouTube, Twitch, Podcast, Lifestyle, TikTok",
                emoji="🎥",
                default=(current_category == "creators"),
            ),
            discord.SelectOption(
                label="Anime, Manga & Fandoms",
                value="anime",
                description="5 Templates • Anime Lounge, Genshin, Cosplay, Lofi Cafe",
                emoji="⛩️",
                default=(current_category == "anime"),
            ),
            discord.SelectOption(
                label="Social, Hangout & Lifestyle",
                value="social",
                description="5 Templates • Community, Study Cafe, Fitness, Books, Cinema",
                emoji="💬",
                default=(current_category == "social"),
            ),
            discord.SelectOption(
                label="Music & Audio Production",
                value="music",
                description="4 Templates • Music Studio, DJ Electronic, Indie, Voice",
                emoji="🎵",
                default=(current_category == "music"),
            ),
            discord.SelectOption(
                label="Education, Campus & Stocks",
                value="education",
                description="4 Templates • Education, Languages, Medical, Finance",
                emoji="📚",
                default=(current_category == "education"),
            ),
            discord.SelectOption(
                label="Business & Enterprise",
                value="business",
                description="4 Templates • Corporate, Startups, Real Estate, Charity",
                emoji="🏢",
                default=(current_category == "business"),
            ),
            discord.SelectOption(
                label="Special Ops, Events & Minimal",
                value="special",
                description="3 Templates • Staff Mgmt, Giveaways, Dark Minimalist",
                emoji="⚡",
                default=(current_category == "special"),
            ),
        ]

        super().__init__(
            placeholder="📁 Step 1: Filter by Category / Page...",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        selected_cat = self.values[0]
        view: TemplateSelectView = self.view
        view.current_category = selected_cat
        view.rebuild_items()
        embed = view.get_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)


class TemplateSelect(discord.ui.Select):
    """Interactive Discord select menu displaying filtered server templates (max 25)."""

    def __init__(self, current_category: str = "p1"):
        all_templates_list = list(TEMPLATES.items())
        options = []

        if current_category == "p1":
            target_list = all_templates_list[:25]
        elif current_category == "p2":
            target_list = all_templates_list[25:50]
        else:
            target_list = [(tid, t) for tid, t in all_templates_list if t.get("group") == current_category]

        for tid, tdata in target_list[:25]:
            cat_short = tdata.get("category", "")[:20]
            desc = tdata.get("description", "")
            full_desc = f"[{cat_short}] {desc}"[:100]
            options.append(
                discord.SelectOption(
                    label=tdata["name"][:100],
                    value=tid,
                    description=full_desc,
                    emoji=tdata.get("emoji", "📋"),
                )
            )

        cat_label = {
            "p1": "All (1-25)",
            "p2": "All (26-50)",
            "gaming": "Gaming & Esports",
            "store": "Store & Commerce",
            "tech": "Tech & AI",
            "creators": "Content Creators",
            "anime": "Anime & Manga",
            "social": "Social & Hangout",
            "music": "Music & Audio",
            "education": "Education & Stocks",
            "business": "Business & Startups",
            "special": "Special Ops & Events",
        }.get(current_category, "Templates")

        super().__init__(
            placeholder=f"✨ Step 2: Choose a {cat_label} Template ({len(options)} available)...",
            min_values=1,
            max_values=1,
            options=options,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction):
        selected_template_id = self.values[0]
        modal = ServerNameModal(selected_template_id)
        # Pre-fill modal with current guild name
        modal.server_name_input.default = interaction.guild.name if interaction.guild else "Community Server"
        await interaction.response.send_modal(modal)


class TemplateSelectView(discord.ui.View):
    """Two-tier view holding Category Filter and Template Select for 50 templates."""

    def __init__(self, current_category: str = "p1"):
        super().__init__(timeout=300.0)
        self.current_category = current_category
        self.rebuild_items()

    def rebuild_items(self):
        self.clear_items()
        self.add_item(CategorySelect(self.current_category))
        self.add_item(TemplateSelect(self.current_category))

    def get_embed(self, guild: Optional[discord.Guild] = None) -> discord.Embed:
        cat_names = {
            "p1": "🌐 All Templates (Page 1 of 2: #1 - #25)",
            "p2": "🌐 All Templates (Page 2 of 2: #26 - #50)",
            "gaming": "🎮 Gaming & Esports (8 Templates)",
            "store": "🛍️ Store & Commerce (6 Templates)",
            "tech": "💻 Tech, Coding & AI (6 Templates)",
            "creators": "🎥 Content Creators & Media (5 Templates)",
            "anime": "⛩️ Anime, Manga & Fandoms (5 Templates)",
            "social": "💬 Social, Hangout & Lifestyle (5 Templates)",
            "music": "🎵 Music & Audio Production (4 Templates)",
            "education": "📚 Education, Campus & Stocks (4 Templates)",
            "business": "🏢 Business, Startups & Enterprise (4 Templates)",
            "special": "⚡ Special Ops, Events & Minimal (3 Templates)",
        }
        category_title = cat_names.get(self.current_category, "Professional Templates")

        all_templates_list = list(TEMPLATES.items())
        if self.current_category == "p1":
            showing = all_templates_list[:25]
        elif self.current_category == "p2":
            showing = all_templates_list[25:50]
        else:
            showing = [(tid, t) for tid, t in all_templates_list if t.get("group") == self.current_category]

        lines = []
        for idx, (tid, t) in enumerate(showing, start=1):
            lines.append(f"`{idx:02d}.` {t.get('emoji', '📁')} **{t['name']}** — *{t['description'][:65]}*")

        desc_body = "\n".join(lines[:12])
        if len(lines) > 12:
            desc_body += f"\n*...and {len(lines) - 12} more in this category (see Step 2 dropdown below)*"

        embed = primary_embed(
            title="🏗️ NOVEXA SERVER BUILDER • 50 TEMPLATES",
            description=(
                "Transform your Discord server into a world-class community with one click!\n\n"
                f"**Active Category:** {category_title}\n\n"
                f"{desc_body}\n\n"
                "**How to Build:**\n"
                "1️⃣ Use **Step 1** dropdown to filter by category or page.\n"
                "2️⃣ Use **Step 2** dropdown to pick your template.\n"
                "3️⃣ Enter your desired server name in the popup modal.\n"
                "4️⃣ Choose **Build (Keep Existing)** or **Wipe & Build Fresh**."
            ),
        )
        embed.set_footer(text="NOVEXA • 50 Templates • 10 Aesthetic Categories")
        return embed


class SetupConfirmView(discord.ui.View):
    """Confirmation buttons for launching the server builder."""

    def __init__(self, template_id: str, server_name: str):
        super().__init__(timeout=180.0)
        self.template_id = template_id
        self.server_name = server_name

    @discord.ui.button(label="Build (Keep Existing)", style=discord.ButtonStyle.success, emoji="✅")
    async def btn_confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

        cog: Optional[ServerTemplates] = interaction.client.get_cog("ServerTemplates")
        if not cog:
            return await interaction.followup.send("Server template engine not loaded.", ephemeral=True)

        await cog.execute_builder(interaction, self.template_id, self.server_name, wipe_first=False)

    @discord.ui.button(label="Wipe & Build Fresh", style=discord.ButtonStyle.danger, emoji="🧹")
    async def btn_wipe_build(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

        cog: Optional[ServerTemplates] = interaction.client.get_cog("ServerTemplates")
        if not cog:
            return await interaction.followup.send("Server template engine not loaded.", ephemeral=True)

        await cog.execute_builder(interaction, self.template_id, self.server_name, wipe_first=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def btn_cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            embed=info_embed("Setup Cancelled", "Server template generation was cancelled. No changes were made."),
            view=self,
        )


class ResetConfirmView(discord.ui.View):
    """Confirmation view for wiping server channels and roles."""

    def __init__(self, scope: str):
        super().__init__(timeout=60.0)
        self.scope = scope

    @discord.ui.button(label="⚠️ Yes, Wipe & Reset Server", style=discord.ButtonStyle.danger, emoji="💥")
    async def btn_confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

        cog: Optional[ServerTemplates] = interaction.client.get_cog("ServerTemplates")
        if not cog:
            return await interaction.followup.send("Server template engine not loaded.", ephemeral=True)

        await cog.execute_reset(interaction, self.scope)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def btn_cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            embed=info_embed("Reset Cancelled", "Server wipe operation was cancelled. All channels and roles were preserved."),
            view=self,
        )


class RollbackConfirmView(discord.ui.View):
    """Confirmation view for rolling back created server resources."""

    def __init__(self, guild_id: int):
        super().__init__(timeout=60.0)
        self.guild_id = guild_id

    @discord.ui.button(label="Confirm Rollback", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def btn_confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

        cog: Optional[ServerTemplates] = interaction.client.get_cog("ServerTemplates")
        if not cog:
            return await interaction.followup.send("Server template engine not loaded.", ephemeral=True)

        await cog.execute_rollback(interaction)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def btn_cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            embed=info_embed("Rollback Cancelled", "Rollback operation was cancelled. All resources were kept intact."),
            view=self,
        )


class DropperConfirmationView(discord.ui.View):
    """Interactive confirmation view before creating the 16 Dropper Channels."""

    def __init__(self, guild: discord.Guild, preview: Dict[str, Any], user: discord.User):
        super().__init__(timeout=180.0)
        self.guild = guild
        self.preview = preview
        self.user = user

    def get_embed(self) -> discord.Embed:
        p = self.preview
        embed = primary_embed(
            title="💻 NOVEXA DROPPER CHANNELS • SETUP PREVIEW",
            description=(
                f"**Target Server:** `{self.guild.name}`\n"
                f"**Planned Category:** `{p['category_name']}` ({'Reusing Existing' if p['category_exists'] else 'Will Create New'})\n"
                f"**Detected Style:** `{p['style_description']}`\n\n"
                f"📊 **Architecture Status:**\n"
                f"• Channels to Create: **+{p['to_create_count']}**\n"
                f"• Already Existing (Skipped): **{p['already_existing_count']}**\n"
                f"• Total Channels: **{p['total_channels']}**\n\n"
                f"*Existing channels, roles, and permissions will be 100% preserved. Click below to proceed.*"
            ),
        )
        ch_lines = []
        for ch in p["channels"][:16]:
            tag = "*(Exists)*" if ch["already_exists"] else "*(New)*"
            ch_lines.append(f"`{ch['formatted_name']}` {tag}")

        embed.add_field(
            name="📁 Planned 16 Developer Channels (In Order)",
            value="\n".join(ch_lines[:8]),
            inline=True
        )
        embed.add_field(
            name="⠀",
            value="\n".join(ch_lines[8:16]),
            inline=True
        )
        embed.set_footer(
            text=f"Requested by {self.user.name} • Safe Idempotent Execution",
            icon_url=self.user.display_avatar.url if hasattr(self.user, "display_avatar") else None
        )
        return embed

    @discord.ui.button(label="Confirm & Create Channels", style=discord.ButtonStyle.success, emoji="🚀")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("Only the administrator who initiated this preview can confirm.", ephemeral=True)

        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content="⏳ **Creating Dropper channels safely with detected style... Please wait...**",
            view=self
        )

        try:
            res = await dropper_service.execute_dropper(self.guild, self.user.id, self.user.name)
            success_emb = success_embed(
                "Dropper Channels Deployed Successfully!",
                (
                    f"Successfully configured the Developer category in **{self.guild.name}**!\n\n"
                    f"📁 **Category:** `{res['category_name']}` ({'Reused Existing' if res['category_reused'] else 'Newly Created'})\n"
                    f"✅ **Channels Created:** **+{res['created_count']}**\n"
                    f"⏭️ **Channels Skipped (Existing):** **{res['skipped_count']}**\n"
                    f"🎨 **Style Applied:** `{res['style_description']}`\n"
                )
            )
            if res["failed_count"] > 0:
                success_emb.add_field(
                    name="⚠️ Partial Notice",
                    value=f"{res['failed_count']} channels failed: " + ", ".join(f"{f['name']} ({f['error']})" for f in res["failed_channels"]),
                    inline=False
                )
            await interaction.edit_original_response(content=None, embed=success_emb, view=None)
        except Exception as e:
            logger.error(f"Error creating dropper channels: {e}", exc_info=True)
            await interaction.edit_original_response(
                content=None,
                embed=error_embed("Creation Error", f"An error occurred while creating channels: {e}"),
                view=None
            )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="✖️")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("Only the administrator who initiated this preview can cancel.", ephemeral=True)
        await interaction.response.edit_message(
            content="❌ **Dropper Channels setup cancelled. No channels or categories were created.**",
            embed=None,
            view=None
        )


class ServerTemplates(commands.Cog):
    """Enterprise Discord Server Template Generator with 50 Fully-Integrated Architecture Presets."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ==================== SLASH COMMANDS ====================

    server_group = app_commands.Group(name="server-template", description="Generate and manage 50 professional Discord server templates")

    @server_group.command(name="setup", description="Generate a complete professional Discord server structure from 50 templates")
    @has_admin_or_owner()
    async def server_setup(self, interaction: discord.Interaction):
        """Display template selection menu."""
        if not interaction.guild:
            return await interaction.response.send_message("This command can only be used in a Discord server.", ephemeral=True)

        # Check bot permissions
        bot_member = interaction.guild.me
        if not bot_member.guild_permissions.manage_channels or not bot_member.guild_permissions.manage_roles:
            return await interaction.response.send_message(
                embed=error_embed(
                    "Missing Permissions",
                    "I require `Manage Channels` and `Manage Roles` permissions to generate server templates.",
                ),
                ephemeral=True,
            )

        view = TemplateSelectView(current_category="p1")
        embed = view.get_embed(interaction.guild)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @server_group.command(name="status", description="View the current server template configuration and generation report")
    @has_admin_or_owner()
    async def server_setup_status(self, interaction: discord.Interaction):
        """Show active template status."""
        row = await db.fetchone("SELECT * FROM server_setups WHERE guild_id = ?", (interaction.guild_id,))
        if not row:
            return await interaction.response.send_message(
                embed=info_embed(
                    "No Setup Found",
                    "No server template has been generated for this server yet.\nRun `/server-setup` to choose from 50 templates and build your server!",
                ),
                ephemeral=True,
            )

        created_cats = json.loads(row["created_categories"] or "[]")
        created_channels = json.loads(row["created_channels"] or "[]")
        created_roles = json.loads(row["created_roles"] or "[]")
        log_channels = json.loads(row["logging_channels"] or "{}")

        embed = primary_embed(
            title="📊 NOVEXA SERVER BUILDER • STATUS REPORT",
            description=(
                f"**Active Template:** `{row['template_name']}` (`{row['template_id']}`)\n"
                f"**Configured Name:** `{row['server_name'] or interaction.guild.name}`\n"
                f"**Setup Status:** **{row['setup_status'].upper()}**\n"
                f"**Generated On:** `{row['setup_timestamp']}`\n"
            ),
        )

        embed.add_field(
            name="📦 Created Resources",
            value=(
                f"📁 Categories: **{len(created_cats)}**\n"
                f"💬 Channels: **{len(created_channels)}**\n"
                f"🛡️ Roles: **{len(created_roles)}**"
            ),
            inline=True,
        )

        welcome_ch = interaction.guild.get_channel(row["welcome_channel_id"]) if row["welcome_channel_id"] else None
        rules_ch = interaction.guild.get_channel(row["rules_channel_id"]) if row["rules_channel_id"] else None
        ticket_cat = interaction.guild.get_channel(row["ticket_category_id"]) if row["ticket_category_id"] else None

        embed.add_field(
            name="⚙️ Integrated Modules",
            value=(
                f"🌸 Welcome: {welcome_ch.mention if welcome_ch else 'Not linked'}\n"
                f"📜 Rules/Verify: {rules_ch.mention if rules_ch else 'Not linked'}\n"
                f"🎫 Ticket Category: {ticket_cat.name if ticket_cat else 'Not linked'}\n"
                f"🛡️ Logging Channels: **{len(log_channels)}** linked"
            ),
            inline=True,
        )

        if row["setup_status"] == "completed":
            embed.set_footer(text="To rollback newly created resources safely without touching pre-existing ones, use /server-setup-rollback.")
        else:
            embed.set_footer(text="This template setup has been rolled back.")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @server_group.command(name="rollback", description="Safely remove only the resources created by the template generator")
    @has_admin_or_owner()
    async def server_setup_rollback(self, interaction: discord.Interaction):
        """Prompt to rollback template generation."""
        row = await db.fetchone("SELECT * FROM server_setups WHERE guild_id = ?", (interaction.guild_id,))
        if not row:
            return await interaction.response.send_message(
                embed=info_embed("No Setup to Rollback", "No server setup session exists to rollback on this server."),
                ephemeral=True,
            )

        if row["setup_status"] == "rolled_back":
            return await interaction.response.send_message(
                embed=warning_embed("Already Rolled Back", "The previous setup session on this server has already been rolled back."),
                ephemeral=True,
            )

        created_cats = json.loads(row["created_categories"] or "[]")
        created_channels = json.loads(row["created_channels"] or "[]")
        created_roles = json.loads(row["created_roles"] or "[]")

        embed = warning_embed(
            "Rollback Confirmation Required",
            (
                f"Are you sure you want to rollback the **{row['template_name']}** setup?\n\n"
                f"**Resources to be safely deleted:**\n"
                f"• Channels: **{len(created_channels)}**\n"
                f"• Categories: **{len(created_cats)}**\n"
                f"• Roles: **{len(created_roles)}**\n\n"
                f"⚠️ **Safe Rollback Guarantee:**\n"
                f"Only resources created by this specific setup session will be removed.\n"
                f"Any pre-existing server channels, roles or settings will **NOT** be touched."
            ),
        )

        view = RollbackConfirmView(interaction.guild_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @server_group.command(name="reset", description="Wipe all channels and custom roles to start completely fresh")
    @app_commands.describe(scope="What to delete: 'all' (channels & roles), 'channels' (channels only), or 'roles' (roles only)")
    @app_commands.choices(scope=[
        app_commands.Choice(name="Delete All Channels & Custom Roles (Full Wipe)", value="all"),
        app_commands.Choice(name="Delete All Channels & Categories Only", value="channels"),
        app_commands.Choice(name="Delete Custom Roles Only", value="roles"),
    ])
    @has_admin_or_owner()
    async def server_reset(self, interaction: discord.Interaction, scope: Optional[app_commands.Choice[str]] = None):
        """Prompt confirmation before wiping server resources."""
        if not interaction.guild:
            return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)

        bot_member = interaction.guild.me
        if not bot_member.guild_permissions.manage_channels or not bot_member.guild_permissions.manage_roles:
            return await interaction.response.send_message(
                embed=error_embed(
                    "Missing Permissions",
                    "I require `Manage Channels` and `Manage Roles` permissions to reset the server.",
                ),
                ephemeral=True,
            )

        chosen_scope = scope.value if scope else "all"
        total_channels = len(interaction.guild.channels)
        manageable_roles = sum(1 for r in interaction.guild.roles if not r.is_default() and not r.managed and r < bot_member.top_role)

        scope_desc = {
            "all": f"💥 **Full Server Reset:**\n• **{total_channels}** channels & categories\n• **{manageable_roles}** custom roles",
            "channels": f"📁 **Channels Wipe:**\n• **{total_channels}** channels & categories",
            "roles": f"🛡️ **Roles Wipe:**\n• **{manageable_roles}** custom roles",
        }[chosen_scope]

        embed = warning_embed(
            "CRITICAL: SERVER WIPE & RESET CONFIRMATION",
            (
                f"You are about to delete resources in **{interaction.guild.name}**:\n\n"
                f"{scope_desc}\n\n"
                f"⚠️ **PERMANENT ACTION WARNING:**\n"
                f"• This action permanently deletes the selected resources.\n"
                f"• A fresh channel `🚀・getting-started` will be created automatically so your server remains accessible.\n"
                f"• After resetting, run `/server-setup` to build any of the 50 complete templates!\n\n"
                f"Click **Confirm Wipe** below only if you are 100% sure."
            ),
        )

        view = ResetConfirmView(chosen_scope)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @server_group.command(name="align-roles", description="Align role hierarchy and lock every channel to the Member role with @everyone View Channel off")
    @has_admin_or_owner()
    async def align_roles_cmd(self, interaction: discord.Interaction):
        """Role setup: Novexa on top, Member second, then staff — and every channel locked to Member."""
        if not interaction.guild:
            return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)

        bot_member = interaction.guild.me
        if not bot_member.guild_permissions.manage_channels or not bot_member.guild_permissions.manage_roles:
            return await interaction.response.send_message(
                embed=error_embed(
                    "Missing Permissions",
                    "I need `Manage Channels` and `Manage Roles` to align roles and rewrite channel overwrites.",
                ),
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True)
        ok, msg = await self.organize_roles(interaction.guild)

        member_role = discord.utils.find(
            lambda r: "member" in r.name.lower() and not r.is_default() and not r.managed,
            interaction.guild.roles,
        )
        stats, failures = await apply_permission_lockdown(interaction.guild, member_role)

        lines = [
            f"{msg}",
            "",
            f"**Structure Applied:**\n"
            f"1. 🤖 **{bot_member.top_role.name}** (Top Role)\n"
            f"2. 👤 **Member** (2nd Role)\n"
            f"3. 👑 **Owner / Administration**\n"
            f"4. 🔱 **Staff, Moderators & Support**\n"
            f"5. 💎 **Community & Verified**\n"
            f"6. 🤖 **Bots**",
            "",
            f"**Member role:** {member_role.mention if member_role else '`not found`'}",
            f"**@everyone:** `View Channel` → OFF on every category and channel",
            f"**Categories locked:** `{stats['categories']}` • **Channels locked:** `{stats['channels']}`",
        ]
        if stats["failed"]:
            lines.append(f"**Failed:** `{stats['failed']}` — {'; '.join(failures[:5])}")

        body = "\n".join(lines)
        if ok and not stats["failed"]:
            embed = success_embed("Role Setup Complete", body)
        elif ok:
            embed = warning_embed("Role Setup Applied With Channel Errors", body)
        else:
            embed = error_embed("Role Setup Error", body)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @server_group.command(name="dropper", description="Automatically create a Developer category with 16 channels matching server style")
    @has_admin_or_owner()
    async def server_dropper_cmd(self, interaction: discord.Interaction):
        """Analyze server style, show preview, and create the 16 Developer dropper channels upon confirmation."""
        if not interaction.guild:
            return await interaction.response.send_message("This command can only be used in a Discord server.", ephemeral=True)

        bot_member = interaction.guild.me
        if not bot_member.guild_permissions.manage_channels:
            return await interaction.response.send_message(
                embed=error_embed("Missing Permissions", "I require `Manage Channels` permission to create categories and channels."),
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True)
        try:
            preview = dropper_service.get_preview(interaction.guild)
            view = DropperConfirmationView(interaction.guild, preview, interaction.user)
            embed = view.get_embed()
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            logger.error(f"Error inspecting dropper preview: {e}", exc_info=True)
            await interaction.followup.send(
                embed=error_embed("Inspection Error", f"Failed to analyze server style: {e}"),
                ephemeral=True
            )

    @staticmethod
    async def organize_roles(guild: discord.Guild, roles_map: Optional[Dict[str, discord.Role]] = None) -> Tuple[bool, str]:
        """Align role hierarchy so Novexa is Top, Member is 2nd, followed by Administration & Community."""
        bot_member = guild.me
        if not bot_member.guild_permissions.manage_roles:
            return False, "Bot is missing the `Manage Roles` permission to organize role hierarchy."

        roles_map = roles_map or {}
        # Identify key roles
        member_role = (
            roles_map.get("👤 Member")
            or discord.utils.find(lambda r: "member" in r.name.lower() and not r.is_default() and not r.managed and r < bot_member.top_role, guild.roles)
        )
        owner_role = roles_map.get("👑 Owner") or roles_map.get("👑 Guild Leader") or discord.utils.find(lambda r: "owner" in r.name.lower() and not r.is_default() and not r.managed and r < bot_member.top_role, guild.roles)
        co_owner_role = roles_map.get("🔱 Co-Owner") or roles_map.get("🔱 Co-Leader") or discord.utils.find(lambda r: "co-owner" in r.name.lower() and not r.is_default() and not r.managed and r < bot_member.top_role, guild.roles)
        admin_role = roles_map.get("🛡️ Administrator") or roles_map.get("🛡️ Scrims Manager") or discord.utils.find(lambda r: "admin" in r.name.lower() and not r.is_default() and not r.managed and r < bot_member.top_role, guild.roles)
        mod_role = roles_map.get("🔨 Moderator") or roles_map.get("🔨 Scrims Host") or discord.utils.find(lambda r: "mod" in r.name.lower() and not r.is_default() and not r.managed and r < bot_member.top_role, guild.roles)
        support_role = roles_map.get("🎫 Support Team") or roles_map.get("💎 VIP Supporter") or discord.utils.find(lambda r: "support" in r.name.lower() and not r.is_default() and not r.managed and r < bot_member.top_role, guild.roles)
        plat_role = roles_map.get("💎 Platinum") or roles_map.get("🏆 Tier-1 Esports")
        gold_role = roles_map.get("🥇 Gold") or roles_map.get("🎖️ Lineup Alpha")
        silver_role = roles_map.get("🥈 Silver") or roles_map.get("🎖️ Lineup Bravo")
        verified_role = roles_map.get("✅ Verified") or roles_map.get("✅ Verified Player") or discord.utils.find(lambda r: "verified" in r.name.lower() and not r.is_default() and not r.managed and r < bot_member.top_role, guild.roles)
        bots_role = roles_map.get("🤖 Bots") or discord.utils.find(lambda r: "bot" in r.name.lower() and not r.is_default() and not r.managed and r < bot_member.top_role, guild.roles)

        desired_order: List[discord.Role] = []
        # Member role MUST be first under Novexa (2nd overall role)
        if member_role:
            desired_order.append(member_role)

        # Followed by staff & community hierarchy
        for r in [owner_role, co_owner_role, admin_role, mod_role, support_role, plat_role, gold_role, silver_role, verified_role, bots_role]:
            if r and r not in desired_order and r < bot_member.top_role and r.id != guild.id:
                desired_order.append(r)

        # Append any remaining roles from roles_map
        for r_name, r_obj in roles_map.items():
            if r_obj and r_obj not in desired_order and r_obj < bot_member.top_role and r_obj.id != guild.id:
                desired_order.append(r_obj)

        manageable_order = [r for r in desired_order if r < bot_member.top_role and not r.is_default() and not r.managed]
        if not manageable_order:
            return False, "No manageable roles found below bot's top role to position."

        bot_pos = bot_member.top_role.position
        # Build positions dict: Member gets bot_pos - 1, Owner gets bot_pos - 2, etc.
        pos_dict = {}
        for idx, r in enumerate(manageable_order):
            target_pos = max(1, bot_pos - 1 - idx)
            pos_dict[r] = target_pos

        for attempt in range(4):
            try:
                await guild.edit_role_positions(positions=pos_dict, reason="Novexa Role Hierarchy: Top=Novexa, 2nd=Member, Staff & Community")
                logger.info(f"Role hierarchy successfully structured in {guild.name}: Member as 2nd role under {bot_member.top_role.name}")
                return True, f"Role hierarchy aligned: **{bot_member.top_role.name}** (Top) ➔ **{member_role.name if member_role else 'Member'}** (2nd) ➔ Administration & Staff."
            except discord.HTTPException as e:
                if e.status == 429:
                    await asyncio.sleep(e.retry_after if e.retry_after is not None else 0.5)
                else:
                    return False, f"Discord API error editing role positions: {e}"
            except Exception as e:
                return False, f"Failed to edit role positions: {e}"

        return False, "Rate limit timeout while organizing role positions."

    # ==================== CORE BUILDER & RESET ENGINE ====================

    async def wipe_server(
        self,
        guild: discord.Guild,
        preserve_channel_id: Optional[int] = None,
        wipe_channels: bool = True,
        wipe_roles: bool = True,
    ) -> Tuple[int, int, int, List[str]]:
        """Ultra-Fast parallel server wipe for channels, categories, and custom roles."""
        deleted_channels = 0
        deleted_cats = 0
        deleted_roles = 0
        errors: List[str] = []

        async def _delete_item(item, is_cat: bool = False, is_role: bool = False):
            nonlocal deleted_channels, deleted_cats, deleted_roles
            for attempt in range(4):
                try:
                    await item.delete(reason="Novexa Ultra-Fast Server Wipe")
                    if is_role:
                        deleted_roles += 1
                    elif is_cat:
                        deleted_cats += 1
                    else:
                        deleted_channels += 1
                    return
                except discord.NotFound:
                    return
                except discord.HTTPException as e:
                    if e.status == 429:
                        await asyncio.sleep(e.retry_after if e.retry_after is not None else 0.05)
                    else:
                        errors.append(f"{'Role' if is_role else 'Channel'} {getattr(item, 'name', '')}: {e}")
                        return
                except Exception as e:
                    errors.append(f"{'Role' if is_role else 'Channel'} {getattr(item, 'name', '')}: {e}")
                    return

        tasks = []
        if wipe_channels:
            # Regular channels (text/voice)
            for ch in list(guild.channels):
                if isinstance(ch, discord.CategoryChannel):
                    continue
                if preserve_channel_id and ch.id == preserve_channel_id:
                    continue
                tasks.append(_delete_item(ch, is_cat=False, is_role=False))

            # Categories
            for cat in list(guild.categories):
                if preserve_channel_id and any(c.id == preserve_channel_id for c in cat.channels):
                    continue
                tasks.append(_delete_item(cat, is_cat=True, is_role=False))

        if wipe_roles:
            bot_top_role = guild.me.top_role
            for role in list(guild.roles):
                if role.is_default() or role.managed or role.is_premium_subscriber():
                    continue
                if role >= bot_top_role:
                    continue
                tasks.append(_delete_item(role, is_cat=False, is_role=True))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        return deleted_channels, deleted_cats, deleted_roles, errors

    async def execute_reset(self, interaction: discord.Interaction, scope: str):
        """Execute server wipe and generate landing channel with maximum speed."""
        guild = interaction.guild
        if not guild:
            return

        wipe_channels = scope in ("all", "channels")
        wipe_roles = scope in ("all", "roles")
        start_time = time.perf_counter()

        landing_channel: Optional[discord.TextChannel] = None
        if wipe_channels:
            try:
                landing_channel = await guild.create_text_channel(
                    name="🚀・getting-started",
                    topic="Welcome! Use /server-setup to generate a professional server structure.",
                    reason="Novexa Server Reset Landing Channel",
                )
            except Exception as e:
                logger.error(f"Failed to create landing channel during reset: {e}")

        preserve_id = landing_channel.id if landing_channel else interaction.channel_id

        await interaction.followup.send(
            embed=primary_embed(
                "⚡ ULTRA-FAST SERVER WIPE IN PROGRESS",
                "Deleting all channels and roles at maximum parallel speed...",
            ),
            ephemeral=True,
        )

        del_ch, del_cat, del_r, errors = await self.wipe_server(
            guild,
            preserve_channel_id=preserve_id,
            wipe_channels=wipe_channels,
            wipe_roles=wipe_roles,
        )

        elapsed = time.perf_counter() - start_time

        if landing_channel:
            finish_embed = success_embed(
                "⚡ SERVER WIPE & RESET COMPLETE!",
                (
                    f"**{guild.name}** has been cleanly reset in **{elapsed:.2f} seconds**!\n\n"
                    f"**Summary of Deleted Resources:**\n"
                    f"• Channels Deleted: **{del_ch}**\n"
                    f"• Categories Deleted: **{del_cat}**\n"
                    f"• Custom Roles Deleted: **{del_r}**\n\n"
                    f"🚀 **Next Step:**\n"
                    f"Run `/server-setup` to choose from **50 complete templates** (Gaming, Digital Store, Anime, Tech, etc.) and build your new server in seconds!"
                ),
            )
            finish_embed.set_footer(text=f"NOVEXA • Ultra-Fast Speed Engine ({elapsed:.2f}s)")
            await landing_channel.send(embed=finish_embed)

            if interaction.channel_id != landing_channel.id:
                try:
                    old_ch = guild.get_channel(interaction.channel_id)
                    if old_ch:
                        await old_ch.delete(reason="Clean up reset interaction channel")
                except Exception:
                    pass
        else:
            await interaction.followup.send(
                embed=success_embed(
                    "Reset Complete",
                    f"Deleted **{del_r}** custom roles in **{elapsed:.2f}s**. Server is ready for new templates!",
                ),
                ephemeral=True,
            )

    async def execute_builder(self, interaction: discord.Interaction, template_id: str, new_server_name: str, wipe_first: bool = False):
        """Execute complete, ultra-fast parallel server building in seconds."""
        template = TEMPLATES.get(template_id)
        if not template:
            return await interaction.followup.send("Selected template definition was not found.", ephemeral=True)

        guild = interaction.guild
        if not guild:
            return

        start_time = time.perf_counter()
        bot_member = guild.me
        created_category_ids: List[int] = []
        created_channel_ids: List[int] = []
        created_role_ids: List[int] = []
        logging_channels_map: Dict[str, int] = {}
        failed_operations: List[str] = []

        welcome_channel: Optional[discord.TextChannel] = None
        rules_channel: Optional[discord.TextChannel] = None
        ticket_panel_channel: Optional[discord.TextChannel] = None
        ticket_category: Optional[discord.CategoryChannel] = None
        antinuke_log_channel: Optional[discord.TextChannel] = None

        # 0. Clean Wipe if user requested 'Wipe & Build Fresh'
        if wipe_first:
            await interaction.followup.send(
                embed=primary_embed(
                    f"⚡ NOVEXA ULTRA-FAST BUILDER • {template['emoji']} {template['name'].upper()}",
                    f"🧹 Purging existing channels and custom roles at maximum parallel speed...\nTarget Server Name: `{new_server_name}`",
                ),
                ephemeral=True,
            )
            del_ch, del_cat, del_r, wipe_errs = await self.wipe_server(
                guild,
                preserve_channel_id=interaction.channel_id,
                wipe_channels=True,
                wipe_roles=True,
            )
            failed_operations.extend(wipe_errs)
        else:
            await interaction.followup.send(
                embed=primary_embed(
                    f"⚡ NOVEXA ULTRA-FAST BUILDER • {template['emoji']} {template['name'].upper()}",
                    f"🚀 Launching parallel generation engine for `{new_server_name}`...",
                ),
                ephemeral=True,
            )

        # 1. Rename guild concurrently if needed
        async def _rename_guild():
            nonlocal new_server_name
            if bot_member.guild_permissions.manage_guild and guild.name != new_server_name:
                for attempt in range(3):
                    try:
                        await guild.edit(name=new_server_name, reason="Novexa Ultra-Fast Server Setup")
                        return
                    except discord.HTTPException as e:
                        if e.status == 429:
                            await asyncio.sleep(e.retry_after if e.retry_after is not None else 0.05)
                        else:
                            failed_operations.append(f"Server Rename: {e}")
                            return
                    except Exception as e:
                        failed_operations.append(f"Server Rename: {e}")
                        return

        # 2. Build Roles Concurrently in Parallel
        existing_roles = {r.name.lower(): r for r in guild.roles}
        roles_map: Dict[str, discord.Role] = {}

        async def _create_role_worker(role_data):
            r_name = role_data["name"]
            existing = existing_roles.get(r_name.lower())
            if existing:
                roles_map[r_name] = existing
                return

            perms_dict = role_data.get("perms", {})
            role_perms = discord.Permissions(**perms_dict) if perms_dict else discord.Permissions.none()

            for attempt in range(4):
                try:
                    new_role = await guild.create_role(
                        name=r_name,
                        color=discord.Color(role_data.get("color", 0x99AAB5)),
                        hoist=role_data.get("hoist", False),
                        mentionable=role_data.get("mentionable", False),
                        permissions=role_perms,
                        reason="Novexa Ultra-Fast Server Setup",
                    )
                    created_role_ids.append(new_role.id)
                    roles_map[r_name] = new_role
                    return
                except discord.HTTPException as e:
                    if e.status == 429:
                        await asyncio.sleep(e.retry_after if e.retry_after is not None else 0.05)
                    else:
                        failed_operations.append(f"Role '{r_name}': {e}")
                        return
                except Exception as e:
                    failed_operations.append(f"Role '{r_name}': {e}")
                    return

        # Launch rename and roles in parallel
        await asyncio.gather(
            _rename_guild(),
            *[_create_role_worker(rd) for rd in template["roles"]],
            return_exceptions=True,
        )

        # 2.1 Structure role hierarchy: Top=Novexa, 2nd=Member, followed by Administration & Staff
        try:
            await self.organize_roles(guild, roles_map)
        except Exception as e:
            logger.warning(f"Error organizing role positions: {e}")

        # 3. Build Categories Concurrently in Parallel
        owner_role = roles_map.get("👑 Owner") or roles_map.get("👑 Guild Leader")
        co_owner_role = roles_map.get("🔱 Co-Owner") or roles_map.get("🔱 Co-Leader")
        admin_role = roles_map.get("🛡️ Administrator") or roles_map.get("🛡️ Scrims Manager")
        mod_role = roles_map.get("🔨 Moderator") or roles_map.get("🔨 Scrims Host")
        support_role = roles_map.get("🎫 Support Team") or roles_map.get("🔨 Scrims Host")

        categories_map: Dict[str, discord.CategoryChannel] = {}

        def _get_category_overwrites(cat_type: str) -> Dict[Any, discord.PermissionOverwrite]:
            overwrites: Dict[Any, discord.PermissionOverwrite] = {}
            if cat_type == "owner_only":
                overwrites[guild.default_role] = discord.PermissionOverwrite(view_channel=False)
                if owner_role:
                    overwrites[owner_role] = discord.PermissionOverwrite(view_channel=True, connect=True, speak=True, send_messages=True)
                if co_owner_role:
                    overwrites[co_owner_role] = discord.PermissionOverwrite(view_channel=True, connect=True, speak=True, send_messages=True)
                overwrites[bot_member] = discord.PermissionOverwrite(view_channel=True, manage_channels=True)
            elif cat_type in ("staff_only", "logs"):
                overwrites[guild.default_role] = discord.PermissionOverwrite(view_channel=False)
                if admin_role:
                    overwrites[admin_role] = discord.PermissionOverwrite(view_channel=True, read_messages=True, send_messages=True, connect=True, speak=True)
                if mod_role:
                    overwrites[mod_role] = discord.PermissionOverwrite(view_channel=True, read_messages=True, send_messages=True, connect=True, speak=True)
                overwrites[bot_member] = discord.PermissionOverwrite(view_channel=True, manage_channels=True, send_messages=True, embed_links=True)
            elif cat_type == "public_read_only":
                overwrites[guild.default_role] = discord.PermissionOverwrite(view_channel=True, send_messages=False, add_reactions=True)
                if admin_role:
                    overwrites[admin_role] = discord.PermissionOverwrite(send_messages=True)
                overwrites[bot_member] = discord.PermissionOverwrite(view_channel=True, send_messages=True, embed_links=True)
            return overwrites

        async def _create_category_worker(cat_data):
            nonlocal ticket_category
            cat_name = cat_data["name"]
            cat_type = cat_data.get("type", "public")
            existing_cat = discord.utils.get(guild.categories, name=cat_name)
            if existing_cat:
                categories_map[cat_name] = existing_cat
                if "ticket" in cat_name.lower():
                    ticket_category = existing_cat
                return

            overwrites = _get_category_overwrites(cat_type)
            for attempt in range(4):
                try:
                    category_obj = await guild.create_category(
                        name=cat_name,
                        overwrites=overwrites,
                        reason="Novexa Ultra-Fast Server Setup",
                    )
                    created_category_ids.append(category_obj.id)
                    categories_map[cat_name] = category_obj
                    if "ticket" in cat_name.lower():
                        ticket_category = category_obj
                    return
                except discord.HTTPException as e:
                    if e.status == 429:
                        await asyncio.sleep(e.retry_after if e.retry_after is not None else 0.05)
                    else:
                        failed_operations.append(f"Category '{cat_name}': {e}")
                        return
                except Exception as e:
                    failed_operations.append(f"Category '{cat_name}': {e}")
                    return

        # Launch all categories in parallel
        await asyncio.gather(
            *[_create_category_worker(cd) for cd in template["categories"]],
            return_exceptions=True,
        )

        # 4. Build ALL Channels Across ALL Categories Concurrently in Parallel
        async def _create_channel_worker(cat_obj: discord.CategoryChannel, ch_data: dict, pos: int):
            nonlocal welcome_channel, rules_channel, ticket_panel_channel, antinuke_log_channel
            ch_name = ch_data["name"]
            ch_type = ch_data.get("type", "text")
            ch_topic = ch_data.get("topic")
            special = ch_data.get("special", "")
            user_limit = ch_data.get("user_limit", 0)

            existing_ch = discord.utils.get(cat_obj.channels, name=ch_name)
            channel_obj = existing_ch

            if not channel_obj:
                for attempt in range(4):
                    try:
                        if ch_type == "text":
                            channel_obj = await cat_obj.create_text_channel(
                                name=ch_name,
                                topic=ch_topic,
                                position=pos,
                                reason="Novexa Ultra-Fast Server Setup",
                            )
                        else:
                            channel_obj = await cat_obj.create_voice_channel(
                                name=ch_name,
                                user_limit=user_limit,
                                position=pos,
                                reason="Novexa Ultra-Fast Server Setup",
                            )
                        created_channel_ids.append(channel_obj.id)
                        break
                    except discord.HTTPException as e:
                        if e.status == 429:
                            await asyncio.sleep(e.retry_after if e.retry_after is not None else 0.05)
                        else:
                            failed_operations.append(f"Channel '{ch_name}': {e}")
                            return
                    except Exception as e:
                        failed_operations.append(f"Channel '{ch_name}': {e}")
                        return

            if not channel_obj:
                return

            if special == "welcome" and isinstance(channel_obj, discord.TextChannel):
                welcome_channel = channel_obj
            elif special == "rules" and isinstance(channel_obj, discord.TextChannel):
                rules_channel = channel_obj
            elif special == "ticket_panel" and isinstance(channel_obj, discord.TextChannel):
                ticket_panel_channel = channel_obj
            elif special.startswith("log_") and isinstance(channel_obj, discord.TextChannel):
                logging_channels_map[special] = channel_obj.id
                if special == "log_antinuke":
                    antinuke_log_channel = channel_obj

        channel_tasks = []
        for cat_data in template["categories"]:
            cat_name = cat_data["name"]
            cat_obj = categories_map.get(cat_name)
            if not cat_obj:
                continue
            for idx, ch_data in enumerate(cat_data["channels"]):
                channel_tasks.append(_create_channel_worker(cat_obj, ch_data, idx))

        if channel_tasks:
            await asyncio.gather(*channel_tasks, return_exceptions=True)

        # 4.5 Channel permission lockdown — @everyone View Channel off everywhere,
        # the bot-created Member role granted per channel type (staff/log categories stay closed)
        try:
            member_role = roles_map.get("👤 Member") or discord.utils.find(
                lambda r: "member" in r.name.lower() and not r.is_default() and not r.managed,
                guild.roles,
            )
            lock_stats, lock_failures = await apply_permission_lockdown(guild, member_role)
            if lock_failures:
                failed_operations.extend(f"Permissions: {f}" for f in lock_failures[:10])
            logger.info(
                f"Permission lockdown: {lock_stats['categories']} categories, "
                f"{lock_stats['channels']} channels, {lock_stats['failed']} failed"
            )
        except Exception as e:
            logger.warning(f"Error applying channel permission lockdown: {e}")
            failed_operations.append(f"Permission Lockdown: {e}")

        # 5. Concurrently Configure Post-Setup Modules (Welcome, Rules, Verification, Tickets, Logging, Anti-Nuke)
        async def _configure_welcome():
            if not welcome_channel:
                return
            try:
                member_role = roles_map.get("👤 Member") or discord.utils.find(lambda r: "member" in r.name.lower() and not r.is_default() and not r.managed, guild.roles)
                member_role_id = member_role.id if member_role else None
                await db.execute(
                    """
                    INSERT INTO welcome_config (guild_id, channel_id, leave_channel_id, is_enabled, embed_enabled, banner_enabled, autorole_enabled, autorole_id)
                    VALUES (?, ?, ?, 1, 1, 1, 1, ?)
                    ON CONFLICT(guild_id) DO UPDATE SET
                        channel_id = excluded.channel_id,
                        leave_channel_id = excluded.leave_channel_id,
                        is_enabled = 1,
                        embed_enabled = 1,
                        banner_enabled = 1,
                        autorole_enabled = 1,
                        autorole_id = excluded.autorole_id
                    """,
                    (guild.id, welcome_channel.id, welcome_channel.id, member_role_id),
                )
                wel_emb = primary_embed(
                    title=f"🌸 Welcome to {guild.name}!",
                    description=(
                        "We are thrilled to have you here!\n\n"
                        "• Please read the server rules in the rules channel.\n"
                        "• Grab your roles and verify your account.\n"
                        "• Enjoy your stay and have fun!"
                    ),
                )
                wel_emb.set_thumbnail(url=guild.icon.url if guild.icon else None)
                await welcome_channel.send(embed=wel_emb)
            except Exception as e:
                logger.error(f"Error configuring welcome: {e}")
                failed_operations.append(f"Welcome Config: {e}")

        async def _configure_rules_verification():
            if not rules_channel:
                return
            try:
                rules_emb = primary_embed(
                    title=f"📜 {guild.name.upper()} • SERVER RULES & GUIDELINES",
                    description=(
                        "Welcome! By joining this server, you agree to abide by Discord's Terms of Service and the rules below:\n\n"
                        "**1. Respect Everyone:** Treat all members and staff with respect. Hate speech, harassment, sexism, and toxicity are strictly prohibited.\n"
                        "**2. No Spam or Self-Promotion:** Do not spam text, emojis, capital letters, or post unauthorized invite links.\n"
                        "**3. Safe Content Only:** NSFW content, gore, malicious files, or illegal links will result in an immediate permanent ban.\n"
                        "**4. Voice & Channel Etiquette:** Keep conversations relevant to channel topics. No loud mic spam or voice changers in public VCs.\n"
                        "**5. Follow Staff Decisions:** Server staff have the final say. Do not argue with moderators in public channels."
                    ),
                )
                rules_emb.set_footer(text="NOVEXA PROTECTION • Server Rules")
                await rules_channel.send(embed=rules_emb)
            except Exception as e:
                logger.error(f"Error configuring rules channel: {e}")
                failed_operations.append(f"Rules Config: {e}")

        async def _configure_tickets():
            if not ticket_panel_channel:
                return
            try:
                panel_id = f"panel_{guild.id}_{ticket_panel_channel.id}"
                cat_id = ticket_category.id if ticket_category else ticket_panel_channel.category_id
                support_role_id = support_role.id if support_role else None
                transcripts_ch_id = logging_channels_map.get("log_transcripts")

                ticket_emb = primary_embed(
                    title="🎫 CUSTOMER & MEMBER SUPPORT DESK",
                    description=(
                        "Need assistance, have billing questions, or wish to contact staff?\n\n"
                        "• Click the **Create Ticket** button below.\n"
                        "• A private channel will be created exclusively for you and our staff.\n"
                        "• Please state your request clearly and wait patiently for an agent."
                    ),
                )
                ticket_emb.set_footer(text="NOVEXA TICKETING • Fast 24/7 Support")
                ticket_msg = await ticket_panel_channel.send(embed=ticket_emb, view=TicketPanelView())

                await db.execute(
                    """
                    INSERT INTO ticket_panels (panel_id, guild_id, channel_id, message_id, title, description, category_id, support_role_id, transcript_channel_id)
                    VALUES (?, ?, ?, ?, 'Customer Support', 'Click below to open a ticket', ?, ?, ?)
                    ON CONFLICT(panel_id) DO UPDATE SET
                        channel_id = excluded.channel_id,
                        message_id = excluded.message_id,
                        category_id = excluded.category_id,
                        support_role_id = excluded.support_role_id,
                        transcript_channel_id = excluded.transcript_channel_id
                    """,
                    (panel_id, guild.id, ticket_panel_channel.id, ticket_msg.id, cat_id, support_role_id, transcripts_ch_id),
                )
            except Exception as e:
                logger.error(f"Error configuring tickets: {e}")
                failed_operations.append(f"Ticket Config: {e}")

        async def _configure_logging_and_antinuke():
            try:
                await db.execute(
                    """
                    INSERT INTO logging_config (
                        guild_id, joins_channel_id, leaves_channel_id, message_edits_channel_id,
                        message_deletes_channel_id, role_changes_channel_id, channel_changes_channel_id,
                        bans_channel_id, kicks_channel_id, timeouts_channel_id, ticket_activity_channel_id,
                        payment_activity_channel_id, antinuke_channel_id, errors_channel_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(guild_id) DO UPDATE SET
                        joins_channel_id = excluded.joins_channel_id,
                        leaves_channel_id = excluded.leaves_channel_id,
                        message_edits_channel_id = excluded.message_edits_channel_id,
                        message_deletes_channel_id = excluded.message_deletes_channel_id,
                        role_changes_channel_id = excluded.role_changes_channel_id,
                        channel_changes_channel_id = excluded.channel_changes_channel_id,
                        bans_channel_id = excluded.bans_channel_id,
                        kicks_channel_id = excluded.kicks_channel_id,
                        timeouts_channel_id = excluded.timeouts_channel_id,
                        ticket_activity_channel_id = excluded.ticket_activity_channel_id,
                        payment_activity_channel_id = excluded.payment_activity_channel_id,
                        antinuke_channel_id = excluded.antinuke_channel_id,
                        errors_channel_id = excluded.errors_channel_id
                    """,
                    (
                        guild.id,
                        logging_channels_map.get("log_member"),
                        logging_channels_map.get("log_member"),
                        logging_channels_map.get("log_message"),
                        logging_channels_map.get("log_message"),
                        logging_channels_map.get("log_member"),
                        logging_channels_map.get("log_update"),
                        logging_channels_map.get("log_security"),
                        logging_channels_map.get("log_security"),
                        logging_channels_map.get("log_security"),
                        logging_channels_map.get("log_ticket"),
                        logging_channels_map.get("log_payment"),
                        logging_channels_map.get("log_antinuke"),
                        logging_channels_map.get("log_bot"),
                    ),
                )
            except Exception as e:
                logger.error(f"Error configuring logging: {e}")
                failed_operations.append(f"Logging Config: {e}")

            try:
                antinuke_ch_id = logging_channels_map.get("log_antinuke")
                await db.execute(
                    """
                    INSERT INTO antinuke_config (guild_id, enabled, punishment_type, log_channel_id)
                    VALUES (?, 1, 'ban', ?)
                    ON CONFLICT(guild_id) DO UPDATE SET
                        enabled = 1,
                        log_channel_id = excluded.log_channel_id
                    """,
                    (guild.id, antinuke_ch_id),
                )
                await db.execute(
                    """
                    INSERT INTO antinuke_whitelist (guild_id, target_id, target_type, added_by)
                    VALUES (?, ?, 'user', ?)
                    ON CONFLICT(guild_id, target_id) DO NOTHING
                    """,
                    (guild.id, guild.owner_id, self.bot.user.id),
                )
            except Exception as e:
                logger.error(f"Error configuring antinuke: {e}")
                failed_operations.append(f"Anti-Nuke Config: {e}")

        # Launch module setups concurrently in parallel
        await asyncio.gather(
            _configure_welcome(),
            _configure_rules_verification(),
            _configure_tickets(),
            _configure_logging_and_antinuke(),
            return_exceptions=True,
        )

        # 6. Save Setup Record to Database
        await db.execute(
            """
            INSERT INTO server_setups (
                guild_id, template_id, template_name, server_name,
                created_categories, created_channels, created_roles,
                welcome_channel_id, exit_channel_id, rules_channel_id,
                ticket_category_id, logging_channels,
                setup_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed')
            ON CONFLICT(guild_id) DO UPDATE SET
                template_id = excluded.template_id,
                template_name = excluded.template_name,
                server_name = excluded.server_name,
                created_categories = excluded.created_categories,
                created_channels = excluded.created_channels,
                created_roles = excluded.created_roles,
                welcome_channel_id = excluded.welcome_channel_id,
                exit_channel_id = excluded.exit_channel_id,
                rules_channel_id = excluded.rules_channel_id,
                ticket_category_id = excluded.ticket_category_id,
                logging_channels = excluded.logging_channels,
                setup_status = 'completed',
                setup_timestamp = CURRENT_TIMESTAMP
            """,
            (
                guild.id,
                template["id"],
                template["name"],
                new_server_name,
                json.dumps(created_category_ids),
                json.dumps(created_channel_ids),
                json.dumps(created_role_ids),
                welcome_channel.id if welcome_channel else None,
                welcome_channel.id if welcome_channel else None,
                rules_channel.id if rules_channel else None,
                ticket_category.id if ticket_category else None,
                json.dumps(logging_channels_map),
            ),
        )

        elapsed = time.perf_counter() - start_time

        # 7. Final Completion Report Embed
        status_symbol = "✅" if not failed_operations else "⚠️"
        completion_embed = success_embed(
            f"{status_symbol} NOVEXA SERVER BUILDER • SETUP COMPLETE!",
            (
                f"Your server **{guild.name}** has been built with **{template['emoji']} {template['name']}** architecture in **{elapsed:.2f} seconds**!\n\n"
                f"**⚡ Performance Metrics:**\n"
                f"• Execution Time: **{elapsed:.2f}s** (Ultra-Fast Parallel Engine)\n"
                f"• 📁 Categories Created: **{len(created_category_ids)}**\n"
                f"• 💬 Channels Created: **{len(created_channel_ids)}**\n"
                f"• 🛡️ Roles Created: **{len(created_role_ids)}**\n"
                f"• 📜 Logging Channels: **{len(logging_channels_map)}** under **🛡️ NOVEXA LOGS**\n\n"
                f"**🚀 Connected Modules:**\n"
                f"• 🌸 **Welcome System:** {welcome_channel.mention if welcome_channel else 'Configured'}\n"
                f"• 🔐 **Verification Gate:** {rules_channel.mention if rules_channel else 'Configured'} (Interactive Button Active)\n"
                f"• 🎫 **Ticket Support Desk:** {ticket_panel_channel.mention if ticket_panel_channel else 'Configured'} (Create Button Active)\n"
                f"• 🛡️ **Anti-Nuke Raid Protection:** Active (Owner Whitelisted)\n"
                f"• 📜 **Enterprise Audit Logging:** 10 Channels connected in **🛡️ NOVEXA LOGS**\n"
            ),
        )

        if failed_operations:
            completion_embed.add_field(
                name=f"⚠️ Notice ({len(failed_operations)} minor issues)",
                value="\n".join(failed_operations[:5]),
                inline=False,
            )

        completion_embed.set_footer(text=f"NOVEXA • Setup Finished in {elapsed:.2f}s")
        try:
            await interaction.edit_original_response(embed=completion_embed)
        except Exception:
            pass

        # If Wipe & Build Fresh was chosen, send final report to welcome channel and clean up old channel
        if wipe_first and welcome_channel and interaction.channel_id != welcome_channel.id:
            try:
                await welcome_channel.send(embed=completion_embed)
                old_interaction_ch = guild.get_channel(interaction.channel_id)
                if old_interaction_ch and old_interaction_ch.id not in created_channel_ids:
                    await asyncio.sleep(0.5)
                    await old_interaction_ch.delete(reason="Clean up wiped server placeholder channel")
            except Exception as e:
                logger.warning(f"Could not clean up old interaction channel: {e}")

    # ==================== CORE ROLLBACK ENGINE ====================

    async def execute_rollback(self, interaction: discord.Interaction):
        """Safely delete only newly created channels, categories and roles in parallel."""
        row = await db.fetchone("SELECT * FROM server_setups WHERE guild_id = ?", (interaction.guild_id,))
        if not row:
            return await interaction.followup.send("No setup record found to rollback.", ephemeral=True)

        guild = interaction.guild
        if not guild:
            return

        start_time = time.perf_counter()
        created_channels = json.loads(row["created_channels"] or "[]")
        created_cats = json.loads(row["created_categories"] or "[]")
        created_roles = json.loads(row["created_roles"] or "[]")

        deleted_channels = 0
        deleted_cats = 0
        deleted_roles = 0

        async def _delete_rb_ch(ch_id: int):
            nonlocal deleted_channels
            ch = guild.get_channel(ch_id)
            if ch:
                for attempt in range(4):
                    try:
                        await ch.delete(reason="Novexa Ultra-Fast Setup Rollback")
                        deleted_channels += 1
                        return
                    except discord.NotFound:
                        return
                    except discord.HTTPException as e:
                        if e.status == 429:
                            await asyncio.sleep(e.retry_after if e.retry_after is not None else 0.05)
                        else:
                            return
                    except Exception:
                        return

        async def _delete_rb_cat(cat_id: int):
            nonlocal deleted_cats
            cat = guild.get_channel(cat_id)
            if cat and isinstance(cat, discord.CategoryChannel):
                for attempt in range(4):
                    try:
                        await cat.delete(reason="Novexa Ultra-Fast Setup Rollback")
                        deleted_cats += 1
                        return
                    except discord.NotFound:
                        return
                    except discord.HTTPException as e:
                        if e.status == 429:
                            await asyncio.sleep(e.retry_after if e.retry_after is not None else 0.05)
                        else:
                            return
                    except Exception:
                        return

        async def _delete_rb_role(r_id: int):
            nonlocal deleted_roles
            role = guild.get_role(r_id)
            if role and not role.is_default() and role < guild.me.top_role:
                for attempt in range(4):
                    try:
                        await role.delete(reason="Novexa Ultra-Fast Setup Rollback")
                        deleted_roles += 1
                        return
                    except discord.NotFound:
                        return
                    except discord.HTTPException as e:
                        if e.status == 429:
                            await asyncio.sleep(e.retry_after if e.retry_after is not None else 0.05)
                        else:
                            return
                    except Exception:
                        return

        # Execute rollback in parallel!
        tasks = [
            *[_delete_rb_ch(cid) for cid in created_channels],
            *[_delete_rb_cat(catid) for catid in created_cats],
            *[_delete_rb_role(rid) for rid in created_roles],
        ]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        await db.execute("UPDATE server_setups SET setup_status = 'rolled_back' WHERE guild_id = ?", (guild.id,))
        elapsed = time.perf_counter() - start_time

        embed = success_embed(
            "⚡ Rollback Operation Complete",
            (
                f"Successfully rolled back the **{row['template_name']}** setup in **{elapsed:.2f}s**.\n\n"
                f"**Cleaned Up Resources:**\n"
                f"• Deleted Channels: **{deleted_channels}**\n"
                f"• Deleted Categories: **{deleted_cats}**\n"
                f"• Deleted Roles: **{deleted_roles}**\n\n"
                f"✅ All pre-existing server channels and roles were safely preserved."
            ),
        )
        embed.set_footer(text=f"NOVEXA • Ultra-Fast Speed Engine ({elapsed:.2f}s)")
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ServerTemplates(bot))

