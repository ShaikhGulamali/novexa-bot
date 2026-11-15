import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
import io
from typing import Optional
from database.database import db
from utils.embeds import primary_embed, success_embed, error_embed, warning_embed, info_embed
from utils.helpers import generate_html_transcript
from utils.permissions import has_admin_or_owner
from utils.emojis import Emojis

logger = logging.getLogger("novexa.tickets")


class AddMemberModal(discord.ui.Modal, title="Add Member to Ticket"):
    user_input = discord.ui.TextInput(
        label="User ID or Mention",
        placeholder="e.g. 123456789012345678 or @User",
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        text = self.user_input.value.strip().replace("<@", "").replace(">", "").replace("!", "")
        if not text.isdigit():
            return await interaction.response.send_message("Invalid user ID provided.", ephemeral=True)

        user_id = int(text)
        member = interaction.guild.get_member(user_id)
        if not member:
            return await interaction.response.send_message("Member not found in this server.", ephemeral=True)

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return

        await channel.set_permissions(member, read_messages=True, send_messages=True, attach_files=True, embed_links=True)
        await interaction.response.send_message(
            embed=success_embed("Member Added", f"Added {member.mention} to this ticket."),
            ephemeral=False,
        )


class RemoveMemberModal(discord.ui.Modal, title="Remove Member from Ticket"):
    user_input = discord.ui.TextInput(
        label="User ID or Mention",
        placeholder="e.g. 123456789012345678",
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        text = self.user_input.value.strip().replace("<@", "").replace(">", "").replace("!", "")
        if not text.isdigit():
            return await interaction.response.send_message("Invalid user ID provided.", ephemeral=True)

        user_id = int(text)
        member = interaction.guild.get_member(user_id)
        if not member:
            return await interaction.response.send_message("Member not found in this server.", ephemeral=True)

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return

        await channel.set_permissions(member, overwrite=None)
        await interaction.response.send_message(
            embed=warning_embed("Member Removed", f"Removed {member.mention} from this ticket."),
            ephemeral=False,
        )


class RenameTicketModal(discord.ui.Modal, title="Rename Ticket"):
    new_name = discord.ui.TextInput(
        label="New Ticket Name",
        placeholder="e.g. billing-issue",
        min_length=2,
        max_length=40,
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return
        clean_name = self.new_name.value.strip().lower().replace(" ", "-")
        await channel.edit(name=clean_name)
        await interaction.response.send_message(
            embed=success_embed("Ticket Renamed", f"Channel renamed to **#{clean_name}**"),
            ephemeral=False,
        )


class TicketCloseConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60.0)

    @discord.ui.button(label="Confirm Close", style=discord.ButtonStyle.danger, emoji="🔒")
    async def confirm_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return

        await interaction.response.defer()

        # Update database
        ticket_row = await db.fetchone(
            "SELECT * FROM tickets WHERE channel_id = ?",
            (channel.id,)
        )
        if ticket_row:
            await db.execute(
                "UPDATE tickets SET status = 'closed', closed_at = CURRENT_TIMESTAMP WHERE channel_id = ?",
                (channel.id,)
            )

        # Lock channel permissions for ticket author
        if ticket_row and ticket_row["author_id"]:
            author = interaction.guild.get_member(ticket_row["author_id"])
            if author:
                await channel.set_permissions(author, read_messages=True, send_messages=False)

        close_embed = warning_embed(
            "Ticket Closed",
            f"This ticket was closed by {interaction.user.mention}.\n"
            f"Support staff can reopen, generate transcripts, or delete this channel using the buttons below."
        )
        await channel.send(embed=close_embed, view=TicketClosedView())
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Ticket closure cancelled.", ephemeral=True)
        self.stop()


class TicketClosedView(discord.ui.View):
    """Persistent view for closed tickets."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Reopen Ticket", style=discord.ButtonStyle.success, emoji="🔓", custom_id="gulamali_ticket_reopen")
    async def reopen_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return

        ticket_row = await db.fetchone("SELECT * FROM tickets WHERE channel_id = ?", (channel.id,))
        if not ticket_row:
            return await interaction.response.send_message("Ticket record not found.", ephemeral=True)

        await db.execute("UPDATE tickets SET status = 'open', closed_at = NULL WHERE channel_id = ?", (channel.id,))

        if ticket_row["author_id"]:
            author = interaction.guild.get_member(ticket_row["author_id"])
            if author:
                await channel.set_permissions(author, read_messages=True, send_messages=True, attach_files=True, embed_links=True)

        await interaction.response.send_message(
            embed=success_embed("Ticket Reopened", f"Ticket reopened by {interaction.user.mention}.")
        )

    @discord.ui.button(label="Save Transcript", style=discord.ButtonStyle.primary, emoji="📑", custom_id="gulamali_ticket_closed_transcript")
    async def save_transcript(self, interaction: discord.Interaction, button: discord.ui.Button):
        await handle_generate_transcript(interaction)

    @discord.ui.button(label="Delete Ticket", style=discord.ButtonStyle.danger, emoji="🗑️", custom_id="gulamali_ticket_delete")
    async def delete_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return

        await interaction.response.send_message(
            embed=warning_embed("Ticket Deletion", "Ticket will be permanently deleted in **5 seconds**...")
        )
        await asyncio.sleep(5)
        await db.execute("UPDATE tickets SET status = 'deleted' WHERE channel_id = ?", (channel.id,))
        await channel.delete(reason=f"Ticket deleted by {interaction.user}")


async def handle_generate_transcript(interaction: discord.Interaction):
    """Helper to generate HTML transcript for a ticket channel."""
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        return await interaction.response.send_message("Transcripts can only be generated in text channels.", ephemeral=True)

    await interaction.response.defer()

    messages = []
    async for msg in channel.history(limit=1000, oldest_first=True):
        messages.append(msg)

    ticket_row = await db.fetchone("SELECT * FROM tickets WHERE channel_id = ?", (channel.id,))
    author_obj = None
    if ticket_row and ticket_row["author_id"]:
        author_obj = interaction.guild.get_member(ticket_row["author_id"]) or await interaction.client.fetch_user(ticket_row["author_id"])

    html_content = generate_html_transcript(interaction.guild, channel, messages, author_obj)
    buffer = io.BytesIO(html_content.encode("utf-8"))
    file_obj = discord.File(fp=buffer, filename=f"transcript-{channel.name}.html")

    embed = success_embed(
        "Transcript Generated",
        f"**Channel:** #{channel.name}\n"
        f"**Messages Archived:** {len(messages)}\n"
        f"Click the attachment below to view or download the full HTML transcript."
    )
    await interaction.followup.send(embed=embed, file=file_obj)

    # Check if a dedicated transcript channel is configured
    if ticket_row:
        panel_row = await db.fetchone(
            "SELECT transcript_channel_id FROM ticket_panels WHERE guild_id = ? LIMIT 1",
            (interaction.guild_id,)
        )
        if panel_row and panel_row["transcript_channel_id"]:
            log_channel = interaction.guild.get_channel(panel_row["transcript_channel_id"])
            if log_channel and isinstance(log_channel, discord.TextChannel) and log_channel.id != channel.id:
                buffer.seek(0)
                copy_file = discord.File(fp=buffer, filename=f"transcript-{channel.name}.html")
                await log_channel.send(embed=embed, file=copy_file)


class TicketControlView(discord.ui.View):
    """Persistent controls placed inside open ticket channels."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji=Emojis.PARTIAL_BANNED, custom_id="gulamali_ticket_close")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        confirm_view = TicketCloseConfirmView()
        await interaction.response.send_message(
            embed=warning_embed("Close Confirmation", "Are you sure you want to close this ticket?"),
            view=confirm_view,
            ephemeral=True,
        )

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.success, emoji=Emojis.PARTIAL_CROWN, custom_id="gulamali_ticket_claim")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return

        ticket_row = await db.fetchone("SELECT * FROM tickets WHERE channel_id = ?", (channel.id,))
        if not ticket_row:
            return await interaction.response.send_message("Ticket record not found.", ephemeral=True)

        if ticket_row["claimed_by"]:
            claimed_user = interaction.guild.get_member(ticket_row["claimed_by"])
            claimed_name = claimed_user.mention if claimed_user else f"ID {ticket_row['claimed_by']}"
            return await interaction.response.send_message(
                f"This ticket is already claimed by {claimed_name}.", ephemeral=True
            )

        await db.execute(
            "UPDATE tickets SET claimed_by = ? WHERE channel_id = ?",
            (interaction.user.id, channel.id),
        )

        embed = success_embed(
            "Ticket Claimed",
            f"This ticket has been claimed by {interaction.user.mention}.\nThey will assist you shortly!"
        )
        await channel.send(embed=embed)
        await interaction.response.send_message("You have successfully claimed this ticket.", ephemeral=True)

    @discord.ui.button(label="Add Member", style=discord.ButtonStyle.secondary, emoji="➕", custom_id="gulamali_ticket_add")
    async def add_member(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddMemberModal())

    @discord.ui.button(label="Remove Member", style=discord.ButtonStyle.secondary, emoji="➖", custom_id="gulamali_ticket_remove")
    async def remove_member(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RemoveMemberModal())

    @discord.ui.button(label="Rename", style=discord.ButtonStyle.secondary, emoji=Emojis.PARTIAL_GEAR, custom_id="gulamali_ticket_rename")
    async def rename_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RenameTicketModal())

    @discord.ui.button(label="Transcript", style=discord.ButtonStyle.primary, emoji=Emojis.PARTIAL_DIAMOND, custom_id="gulamali_ticket_transcript")
    async def transcript_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await handle_generate_transcript(interaction)


class TicketPanelView(discord.ui.View):
    """Persistent panel view containing the 'Create Ticket' button."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary, emoji=Emojis.PARTIAL_TICKET, custom_id="gulamali_ticket_create")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        # Anti-spam: check if user already has an active open ticket
        existing = await db.fetchone(
            "SELECT channel_id FROM tickets WHERE guild_id = ? AND author_id = ? AND status = 'open'",
            (guild.id, user.id),
        )
        if existing:
            ch = guild.get_channel(existing["channel_id"])
            if ch:
                return await interaction.response.send_message(
                    f"⚠️ You already have an open ticket in {ch.mention}!", ephemeral=True
                )

        await interaction.response.defer(ephemeral=True)

        # Retrieve ticket settings for guild
        panel = await db.fetchone(
            "SELECT * FROM ticket_panels WHERE guild_id = ? ORDER BY panel_id DESC LIMIT 1",
            (guild.id,)
        )
        category_id = panel["category_id"] if panel else None
        support_role_id = panel["support_role_id"] if panel else None

        category = guild.get_channel(category_id) if category_id else None
        if category and not isinstance(category, discord.CategoryChannel):
            category = None

        # Determine next ticket number
        count_row = await db.fetchone(
            "SELECT COUNT(*) as total FROM tickets WHERE guild_id = ?",
            (guild.id,)
        )
        ticket_number = (count_row["total"] if count_row else 0) + 1
        ticket_channel_name = f"ticket-{ticket_number:04d}"

        # Setup channel overwrites
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True, manage_messages=True),
        }

        if support_role_id:
            support_role = guild.get_role(support_role_id)
            if support_role:
                overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True)

        try:
            ticket_channel = await guild.create_text_channel(
                name=ticket_channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Ticket #{ticket_number:04d} | Creator: {user.name} ({user.id})",
            )
        except discord.Forbidden:
            return await interaction.followup.send("Failed to create ticket channel. I lack the `Manage Channels` permission.", ephemeral=True)

        # Record in database
        await db.execute(
            """
            INSERT INTO tickets (guild_id, channel_id, ticket_number, author_id, status)
            VALUES (?, ?, ?, ?, 'open')
            """,
            (guild.id, ticket_channel.id, ticket_number, user.id),
        )

        # Send welcome control embed inside ticket channel
        welcome_embed = primary_embed(
            title=f"Support Ticket #{ticket_number:04d}",
            description=(
                f"{Emojis.TICKET} **Welcome to your private ticket**, {user.mention}!\n\n"
                f"{Emojis.ARROW} Support staff has been notified and will assist you shortly.\n"
                f"{Emojis.ARROW} Please state your inquiry or issue in detail below.\n\n"
                f"{Emojis.GEAR} **Ticket Controls:** Use the buttons below to manage this channel."
            ),
        )
        welcome_embed.add_field(name=f"{Emojis.ARROW} Creator", value=user.mention, inline=True)
        welcome_embed.add_field(name=f"{Emojis.STAR_BLUE} Status", value=f"{Emojis.TICK} Open", inline=True)
        if support_role_id:
            welcome_embed.add_field(name=f"{Emojis.CROWN} Assigned Staff Role", value=f"<@&{support_role_id}>", inline=True)

        await ticket_channel.send(
            content=f"{user.mention}" + (f" <@&{support_role_id}>" if support_role_id else ""),
            embed=welcome_embed,
            view=TicketControlView(),
        )

        await interaction.followup.send(
            f"{Emojis.TICK} Your ticket has been created: {ticket_channel.mention}", ephemeral=True
        )


class Tickets(commands.Cog):
    """Enterprise-grade Multi-Category Ticket System."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    ticket_group = app_commands.Group(name="ticket", description="Manage tickets and create ticket panels")

    @ticket_group.command(name="panel", description="Post a professional ticket creation panel in the channel")
    @has_admin_or_owner()
    @app_commands.describe(
        title="Panel Embed Title",
        description="Panel Embed Description",
        category="Category to create new ticket channels in",
        support_role="Role granted permission to view and claim tickets",
        transcript_channel="Channel where saved transcripts will be logged",
    )
    async def ticket_panel(
        self,
        interaction: discord.Interaction,
        title: str = "🎫 Official Support Center",
        description: str = "",
        category: Optional[discord.CategoryChannel] = None,
        support_role: Optional[discord.Role] = None,
        transcript_channel: Optional[discord.TextChannel] = None,
    ):
        if not description:
            description = (
                f"{Emojis.TICKET} **Official Support & Inquiries**\n\n"
                f"Need assistance, have questions, or want to report an issue?\n"
                f"{Emojis.ARROW} Click the **Create Ticket** button below to open a private channel.\n"
                f"{Emojis.ARROW} Our staff team will be notified immediately to assist you.\n\n"
                f"{Emojis.SPARKLES} *Response time is typically under a few minutes.*"
            )
        panel_embed = primary_embed(title=title, description=description)
        panel_embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        panel_embed.set_footer(text="NOVEXA • Secure Ticket System")

        panel_view = TicketPanelView()
        panel_msg = await interaction.channel.send(embed=panel_embed, view=panel_view)

        panel_id = f"{interaction.guild_id}_{interaction.channel_id}_{panel_msg.id}"
        await db.execute(
            """
            INSERT INTO ticket_panels (panel_id, guild_id, channel_id, message_id, title, description, category_id, support_role_id, transcript_channel_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(panel_id) DO UPDATE SET
                title = excluded.title,
                description = excluded.description,
                category_id = excluded.category_id,
                support_role_id = excluded.support_role_id,
                transcript_channel_id = excluded.transcript_channel_id
            """,
            (
                panel_id,
                interaction.guild_id,
                interaction.channel_id,
                panel_msg.id,
                title,
                description,
                category.id if category else None,
                support_role.id if support_role else None,
                transcript_channel.id if transcript_channel else None,
            ),
        )

        await interaction.response.send_message(
            embed=success_embed("Ticket Panel Deployed", f"Ticket panel created successfully in {interaction.channel.mention}!"),
            ephemeral=True,
        )

    @ticket_group.command(name="stats", description="View server ticket statistics")
    @has_admin_or_owner()
    async def ticket_stats(self, interaction: discord.Interaction):
        total_row = await db.fetchone("SELECT COUNT(*) as count FROM tickets WHERE guild_id = ?", (interaction.guild_id,))
        open_row = await db.fetchone("SELECT COUNT(*) as count FROM tickets WHERE guild_id = ? AND status = 'open'", (interaction.guild_id,))
        closed_row = await db.fetchone("SELECT COUNT(*) as count FROM tickets WHERE guild_id = ? AND status = 'closed'", (interaction.guild_id,))
        claimed_row = await db.fetchone("SELECT COUNT(*) as count FROM tickets WHERE guild_id = ? AND claimed_by IS NOT NULL", (interaction.guild_id,))

        embed = primary_embed(title="📊 Server Ticket Statistics")
        embed.add_field(name="Total Tickets", value=str(total_row["count"] if total_row else 0), inline=True)
        embed.add_field(name="Open Tickets", value=str(open_row["count"] if open_row else 0), inline=True)
        embed.add_field(name="Closed Tickets", value=str(closed_row["count"] if closed_row else 0), inline=True)
        embed.add_field(name="Claimed Tickets", value=str(claimed_row["count"] if claimed_row else 0), inline=True)

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))

