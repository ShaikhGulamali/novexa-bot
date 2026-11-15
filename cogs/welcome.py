"""NOVEXA - Advanced Welcome & Goodbye System Cog.

Features:
- 20 Professionally designed welcome templates with live graphic banner rendering
- Interactive template selection via Discord UI select menus
- Full customization of channels, titles, messages, background URLs, footers and colors
- Direct Message (DM) welcome greetings
- Auto-Role assignment for new members
- Complete variable substitution ({user}, {username}, {user_id}, {server}, {server_id}, {member_count}, {avatar}, {server_icon}, {created_at}, {joined_at})
- Live test simulations for both welcome and goodbye events
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional, List
from database.database import db
from utils.embeds import primary_embed, success_embed, error_embed, info_embed, warning_embed
from utils.helpers import format_template
from utils.emojis import Emojis
from utils.image_generator import generate_welcome_banner
from utils.permissions import has_admin_or_owner
from utils.welcome_templates import WELCOME_TEMPLATES, get_template, list_templates

logger = logging.getLogger("novexa.welcome")


class TemplateSelect(discord.ui.Select):
    """Interactive Discord select menu for browsing and selecting all 20 welcome templates."""

    def __init__(self, current_template: str = "novexa_exclusive", is_goodbye: bool = False):
        self.is_goodbye = is_goodbye
        options = []
        for tid, tinfo in WELCOME_TEMPLATES.items():
            options.append(
                discord.SelectOption(
                    label=tinfo["name"],
                    value=tid,
                    description=tinfo["description"][:100],
                    emoji=tinfo["emoji"],
                    default=(tid == current_template),
                )
            )
        super().__init__(
            placeholder="Select a welcome template style (1 of 20)...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        selected_tid = self.values[0]
        tmpl = get_template(selected_tid)
        col = "goodbye_template_id" if self.is_goodbye else "template_id"

        await db.execute(
            f"""
            INSERT INTO welcome_config (guild_id, {col}, is_enabled)
            VALUES (?, ?, 1)
            ON CONFLICT(guild_id) DO UPDATE SET {col} = excluded.{col}
            """,
            (interaction.guild_id, selected_tid),
        )

        embed = success_embed(
            f"Template Updated: {tmpl['emoji']} {tmpl['name']}",
            f"**Description:** {tmpl['description']}\n"
            f"**Tagline:** `{tmpl['tagline']}`\n"
            f"**Primary Accent:** `{tmpl['primary_hex']}`\n\n"
            f"Use `/{ 'goodbye' if self.is_goodbye else 'welcome' } preview` to inspect your live banner card!",
        )
        embed.color = tmpl["embed_color"]
        await interaction.response.edit_message(embed=embed, view=None)


class TemplateSelectView(discord.ui.View):
    def __init__(self, current_template: str = "novexa_exclusive", is_goodbye: bool = False):
        super().__init__(timeout=120)
        self.add_item(TemplateSelect(current_template, is_goodbye))


class Welcome(commands.Cog):
    """Advanced Welcome & Goodbye Suite with 20 Graphic Templates."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ==================== EVENT LISTENERS ====================

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Handle new member join: welcome banner, embed and DM greeting."""
        if member.bot:
            return

        row = await db.fetchone(
            "SELECT * FROM welcome_config WHERE guild_id = ?",
            (member.guild.id,)
        )
        if not row or not row["is_enabled"]:
            return

        # 2. Direct Message (DM) Welcome Greeting
        if row["dm_enabled"] and row["dm_template"]:
            try:
                dm_text = format_template(row["dm_template"], member)
                dm_embed = primary_embed(
                    title=f"Welcome to {member.guild.name}!",
                    description=dm_text,
                )
                if member.guild.icon:
                    dm_embed.set_thumbnail(url=member.guild.icon.url)
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                pass  # Member has DMs closed
            except Exception as e:
                logger.debug(f"Could not send DM to {member}: {e}")

        # 3. Public Channel Welcome Announcement
        if not row["channel_id"]:
            return

        channel = member.guild.get_channel(row["channel_id"])
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        perms = channel.permissions_for(member.guild.me)
        if not perms.send_messages:
            return

        template_id = row["template_id"] or "novexa_exclusive"
        tmpl = get_template(template_id)
        msg_template = row["message_template"] or "Welcome {user} to **{server}**! You are member #{member_count}."
        formatted_text = format_template(msg_template, member)

        # Generate banner if enabled
        banner_file: Optional[discord.File] = None
        if row["banner_enabled"]:
            try:
                custom_title = row["title"] if row["title"] else None
                if custom_title:
                    custom_title = format_template(custom_title, member)
                custom_footer = row["footer_text"] if row["footer_text"] else None
                if custom_footer:
                    custom_footer = format_template(custom_footer, member)

                banner_file = await generate_welcome_banner(
                    member=member,
                    background_url=row["background_url"] or "",
                    template_id=template_id,
                    custom_title=custom_title,
                    custom_footer=custom_footer,
                )
            except Exception as e:
                logger.error(f"Failed to generate welcome banner for {member}: {e}")

        # Deliver message / embed
        if row["embed_enabled"] and perms.embed_links:
            title_text = row["title"] or f"👋 Welcome to {member.guild.name}!"
            title_text = format_template(title_text, member)

            embed = discord.Embed(
                title=title_text,
                description=formatted_text if row["message_enabled"] else None,
                color=tmpl["embed_color"],
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name=f"{Emojis.ARROW} Member", value=member.mention, inline=True)
            embed.add_field(name=f"{Emojis.STAR_BLUE} Total Members", value=f"#{member.guild.member_count}", inline=True)
            embed.add_field(name=f"{Emojis.SPARKLES} Account Created", value=member.created_at.strftime('%b %d, %Y'), inline=True)

            footer_text = row["footer_text"] or f"Member #{member.guild.member_count} • NOVEXA"
            embed.set_footer(text=format_template(footer_text, member), icon_url=member.guild.icon.url if member.guild.icon else None)

            if banner_file:
                embed.set_image(url=f"attachment://{banner_file.filename}")
                await channel.send(content=member.mention if not row["message_enabled"] else None, embed=embed, file=banner_file)
            else:
                await channel.send(content=member.mention if not row["message_enabled"] else None, embed=embed)
        else:
            if banner_file:
                await channel.send(content=formatted_text, file=banner_file)
            else:
                await channel.send(content=formatted_text)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Handle member leave / goodbye announcement."""
        if member.bot:
            return

        row = await db.fetchone(
            "SELECT * FROM welcome_config WHERE guild_id = ?",
            (member.guild.id,)
        )
        if not row or not row["is_enabled"] or not row["goodbye_enabled"] or not row["leave_channel_id"]:
            return

        channel = member.guild.get_channel(row["leave_channel_id"])
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        perms = channel.permissions_for(member.guild.me)
        if not perms.send_messages:
            return

        leave_template = row["leave_template"] or "{username} has left **{server}**. We are now down to {member_count} members."
        formatted_text = format_template(leave_template, member)

        if row["goodbye_embed_enabled"] and perms.embed_links:
            tmpl = get_template(row["goodbye_template_id"] or "minimal_dark")
            embed = discord.Embed(
                title=f"👋 Goodbye from {member.guild.name}",
                description=formatted_text,
                color=tmpl["embed_color"],
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name=f"{Emojis.STAR_BLUE} Remaining Members", value=str(member.guild.member_count), inline=True)
            await channel.send(embed=embed)
        else:
            await channel.send(content=formatted_text)

    # ==================== SLASH COMMANDS: /welcome ====================

    welcome_group = app_commands.Group(name="welcome", description="Configure server welcome templates, channels & automation")

    @welcome_group.command(name="setup", description="Master welcome setup wizard: channel, template, banner, and embed")
    @has_admin_or_owner()
    @app_commands.describe(
        welcome_channel="Channel where welcome cards and messages are sent",
        goodbye_channel="Optional channel where member leave messages are sent",
        use_banner="Whether to generate and display graphic banner cards",
        use_embed="Whether to format greetings inside rich embeds",
        use_dm="Whether to send a private welcome message to the member",
    )
    async def welcome_setup(
        self,
        interaction: discord.Interaction,
        welcome_channel: discord.TextChannel,
        goodbye_channel: Optional[discord.TextChannel] = None,
        use_banner: bool = True,
        use_embed: bool = True,
        use_dm: bool = False,
    ):
        await db.execute(
            """
            INSERT INTO welcome_config (
                guild_id, channel_id, leave_channel_id, banner_enabled, embed_enabled, dm_enabled, is_enabled
            )
            VALUES (?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(guild_id) DO UPDATE SET
                channel_id = excluded.channel_id,
                leave_channel_id = COALESCE(excluded.leave_channel_id, welcome_config.leave_channel_id),
                banner_enabled = excluded.banner_enabled,
                embed_enabled = excluded.embed_enabled,
                dm_enabled = excluded.dm_enabled,
                is_enabled = 1
            """,
            (
                interaction.guild_id,
                welcome_channel.id,
                goodbye_channel.id if goodbye_channel else None,
                1 if use_banner else 0,
                1 if use_embed else 0,
                1 if use_dm else 0,
            ),
        )

        embed = success_embed(
            "🎉 Welcome System Configured",
            f"**Welcome Channel:** {welcome_channel.mention}\n"
            f"**Goodbye Channel:** {goodbye_channel.mention if goodbye_channel else '*(Disabled)*'}\n"
            f"**Graphic Banners:** `{'Enabled' if use_banner else 'Disabled'}`\n"
            f"**Embed Formatting:** `{'Enabled' if use_embed else 'Disabled'}`\n"
            f"**Direct Message (DM):** `{'Enabled' if use_dm else 'Disabled'}`\n\n"
            f"👉 Use `/welcome template` to pick one of the **20 professional templates**!\n"
            f"👉 Use `/welcome preview` to inspect your live banner card.",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @welcome_group.command(name="channel", description="Quickly assign or change the welcome announcements channel")
    @has_admin_or_owner()
    @app_commands.describe(channel="Text channel for welcome notifications")
    async def welcome_channel_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await db.execute(
            """
            INSERT INTO welcome_config (guild_id, channel_id, is_enabled)
            VALUES (?, ?, 1)
            ON CONFLICT(guild_id) DO UPDATE SET channel_id = excluded.channel_id, is_enabled = 1
            """,
            (interaction.guild_id, channel.id),
        )
        await interaction.response.send_message(
            embed=success_embed("Welcome Channel Set", f"Welcome greetings will now be posted in {channel.mention}."),
            ephemeral=True,
        )

    @welcome_group.command(name="template", description="Choose from 20 professionally designed graphic welcome templates")
    @has_admin_or_owner()
    async def welcome_template_cmd(self, interaction: discord.Interaction):
        row = await db.fetchone("SELECT template_id FROM welcome_config WHERE guild_id = ?", (interaction.guild_id,))
        current = row["template_id"] if row and row["template_id"] else "novexa_exclusive"
        tmpl = get_template(current)

        embed = primary_embed(
            title="🎨 Select Welcome Template (20 Styles Available)",
            description=f"Current Template: **{tmpl['emoji']} {tmpl['name']}**\n\n"
                        f"Choose any of our 20 studio-crafted graphic styles from the menu below to update your server's welcome card immediately.",
        )
        view = TemplateSelectView(current_template=current, is_goodbye=False)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @welcome_group.command(name="preview", description="Generate a real-time live preview of your welcome banner and message")
    @has_admin_or_owner()
    async def welcome_preview_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        row = await db.fetchone("SELECT * FROM welcome_config WHERE guild_id = ?", (interaction.guild_id,))
        tid = row["template_id"] if row and row["template_id"] else "novexa_exclusive"
        tmpl = get_template(tid)

        template_text = (row["message_template"] if row and row["message_template"]
                         else "Welcome {user} to **{server}**! You are member #{member_count}.")
        bg_url = row["background_url"] if row and row["background_url"] else ""

        if not isinstance(interaction.user, discord.Member):
            return await interaction.followup.send("Could not retrieve member profile for preview.")

        formatted_text = format_template(template_text, interaction.user)
        banner_file = await generate_welcome_banner(
            member=interaction.user,
            background_url=bg_url,
            template_id=tid,
            custom_title=row["title"] if row and row["title"] else None,
            custom_footer=row["footer_text"] if row and row["footer_text"] else None,
        )

        title_text = row["title"] if row and row["title"] else f"👋 Welcome to {interaction.guild.name}!"
        title_text = format_template(title_text, interaction.user)

        embed = discord.Embed(
            title=f"{title_text} (LIVE PREVIEW)",
            description=formatted_text,
            color=tmpl["embed_color"],
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_image(url=f"attachment://{banner_file.filename}")
        embed.add_field(name="Active Template", value=f"{tmpl['emoji']} **{tmpl['name']}**", inline=True)
        embed.add_field(name="Member Count", value=f"#{interaction.guild.member_count}", inline=True)
        embed.add_field(name="Primary Accent", value=f"`{tmpl['primary_hex']}`", inline=True)
        embed.set_footer(text=f"Template ID: {tid} • NOVEXA Preview Engine")

        await interaction.followup.send(embed=embed, file=banner_file, ephemeral=True)

    @welcome_group.command(name="customize", description="Customize welcome message, card title, footer, and background URL")
    @has_admin_or_owner()
    @app_commands.describe(
        message="Custom message. Supported variables: {user}, {username}, {user_id}, {server}, {member_count}",
        card_title="Header text displayed on graphic banner",
        footer_text="Footer text on card and embed",
        background_url="Direct image URL (16:9 JPG/PNG) to use as banner background",
    )
    async def welcome_customize_cmd(
        self,
        interaction: discord.Interaction,
        message: Optional[str] = None,
        card_title: Optional[str] = None,
        footer_text: Optional[str] = None,
        background_url: Optional[str] = None,
    ):
        if not any([message, card_title, footer_text, background_url]):
            return await interaction.response.send_message("Please provide at least one field to customize.", ephemeral=True)

        updates = []
        params = []
        if message:
            updates.append("message_template = ?")
            params.append(message)
        if card_title:
            updates.append("title = ?")
            params.append(card_title)
        if footer_text:
            updates.append("footer_text = ?")
            params.append(footer_text)
        if background_url:
            if not (background_url.startswith("http://") or background_url.startswith("https://")):
                return await interaction.response.send_message("Background URL must be a valid HTTP/HTTPS link.", ephemeral=True)
            updates.append("background_url = ?")
            params.append(background_url)

        params.append(interaction.guild_id)
        await db.execute(
            f"""
            INSERT INTO welcome_config (guild_id, is_enabled) VALUES (?, 1)
            ON CONFLICT(guild_id) DO UPDATE SET {", ".join(updates)}
            """,
            params if len(params) == 1 else (interaction.guild_id, *params[:-1]),
        )

        embed = success_embed(
            "Welcome Customization Saved",
            "Your welcome customizations have been updated!\nUse `/welcome preview` to check the updated look."
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @welcome_group.command(name="test", description="Simulate a real new member join event to test your welcome channel setup")
    @has_admin_or_owner()
    async def welcome_test_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not isinstance(interaction.user, discord.Member):
            return await interaction.followup.send("Could not retrieve member profile.")

        row = await db.fetchone("SELECT channel_id FROM welcome_config WHERE guild_id = ?", (interaction.guild_id,))
        if not row or not row["channel_id"]:
            return await interaction.followup.send(
                embed=error_embed("No Channel Set", "Please configure a welcome channel first using `/welcome channel` or `/welcome setup`."),
                ephemeral=True,
            )

        channel = interaction.guild.get_channel(row["channel_id"])
        if not channel:
            return await interaction.followup.send(
                embed=error_embed("Channel Missing", f"The configured channel ID `{row['channel_id']}` no longer exists."),
                ephemeral=True,
            )

        # Trigger simulated on_member_join
        await self.on_member_join(interaction.user)
        await interaction.followup.send(
            embed=success_embed("Test Welcome Dispatched", f"A test welcome event has been sent to {channel.mention}!"),
            ephemeral=True,
        )

    @welcome_group.command(name="disable", description="Turn off the welcome announcements system")
    @has_admin_or_owner()
    async def welcome_disable_cmd(self, interaction: discord.Interaction):
        await db.execute(
            "UPDATE welcome_config SET is_enabled = 0 WHERE guild_id = ?",
            (interaction.guild_id,)
        )
        await interaction.response.send_message(
            embed=warning_embed("Welcome System Disabled", "The welcome system has been turned off."),
            ephemeral=True,
        )

    # ==================== SLASH COMMANDS: /goodbye ====================

    goodbye_group = app_commands.Group(name="goodbye", description="Configure member leave / goodbye messages and templates")

    @goodbye_group.command(name="setup", description="Configure goodbye announcements channel and options")
    @has_admin_or_owner()
    @app_commands.describe(
        channel="Channel where goodbye messages will be posted",
        use_embed="Whether to format goodbye notices inside embeds",
    )
    async def goodbye_setup(self, interaction: discord.Interaction, channel: discord.TextChannel, use_embed: bool = True):
        await db.execute(
            """
            INSERT INTO welcome_config (guild_id, leave_channel_id, goodbye_embed_enabled, goodbye_enabled, is_enabled)
            VALUES (?, ?, ?, 1, 1)
            ON CONFLICT(guild_id) DO UPDATE SET
                leave_channel_id = excluded.leave_channel_id,
                goodbye_embed_enabled = excluded.goodbye_embed_enabled,
                goodbye_enabled = 1
            """,
            (interaction.guild_id, channel.id, 1 if use_embed else 0),
        )
        embed = success_embed(
            "Goodbye System Configured",
            f"**Goodbye Channel:** {channel.mention}\n"
            f"**Embed Styling:** `{'Enabled' if use_embed else 'Disabled'}`\n\n"
            f"Use `/goodbye template` to select a theme, or `/goodbye test` to preview.",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @goodbye_group.command(name="template", description="Choose template style for goodbye notices")
    @has_admin_or_owner()
    async def goodbye_template_cmd(self, interaction: discord.Interaction):
        row = await db.fetchone("SELECT goodbye_template_id FROM welcome_config WHERE guild_id = ?", (interaction.guild_id,))
        current = row["goodbye_template_id"] if row and row["goodbye_template_id"] else "minimal_dark"
        tmpl = get_template(current)

        embed = primary_embed(
            title="🎨 Select Goodbye Notice Theme",
            description=f"Current Style: **{tmpl['emoji']} {tmpl['name']}**\nSelect a theme from the dropdown below:",
        )
        view = TemplateSelectView(current_template=current, is_goodbye=True)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @goodbye_group.command(name="customize", description="Set custom goodbye message template")
    @has_admin_or_owner()
    @app_commands.describe(
        template="Variables: {username}, {user_id}, {server}, {member_count}"
    )
    async def goodbye_customize_cmd(self, interaction: discord.Interaction, template: str):
        await db.execute(
            """
            INSERT INTO welcome_config (guild_id, leave_template, is_enabled)
            VALUES (?, ?, 1)
            ON CONFLICT(guild_id) DO UPDATE SET leave_template = excluded.leave_template
            """,
            (interaction.guild_id, template),
        )
        embed = success_embed("Goodbye Message Updated", f"New Template:\n```{template}```")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @goodbye_group.command(name="test", description="Simulate a member leave event to test your goodbye setup")
    @has_admin_or_owner()
    async def goodbye_test_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not isinstance(interaction.user, discord.Member):
            return await interaction.followup.send("Could not retrieve member profile.")

        row = await db.fetchone("SELECT leave_channel_id FROM welcome_config WHERE guild_id = ?", (interaction.guild_id,))
        if not row or not row["leave_channel_id"]:
            return await interaction.followup.send(
                embed=error_embed("No Goodbye Channel", "Please configure a goodbye channel first using `/goodbye setup`."),
                ephemeral=True,
            )

        channel = interaction.guild.get_channel(row["leave_channel_id"])
        if not channel:
            return await interaction.followup.send(
                embed=error_embed("Channel Missing", f"Configured channel ID `{row['leave_channel_id']}` was not found."),
                ephemeral=True,
            )

        await self.on_member_remove(interaction.user)
        await interaction.followup.send(
            embed=success_embed("Test Goodbye Dispatched", f"A test goodbye event has been posted to {channel.mention}!"),
            ephemeral=True,
        )

    @goodbye_group.command(name="disable", description="Turn off goodbye leave announcements")
    @has_admin_or_owner()
    async def goodbye_disable_cmd(self, interaction: discord.Interaction):
        await db.execute(
            "UPDATE welcome_config SET goodbye_enabled = 0 WHERE guild_id = ?",
            (interaction.guild_id,)
        )
        await interaction.response.send_message(
            embed=warning_embed("Goodbye System Disabled", "Member leave notices have been turned off."),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
