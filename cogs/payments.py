import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional
from database.database import db
from utils.embeds import primary_embed, success_embed, error_embed, warning_embed, info_embed
from utils.permissions import has_admin_or_owner

logger = logging.getLogger("novexa.payments")


class RejectPaymentModal(discord.ui.Modal, title="Reject Payment"):
    reason_input = discord.ui.TextInput(
        label="Reason for Rejection",
        style=discord.TextStyle.paragraph,
        placeholder="e.g. Transaction ID not found in bank statement, amount mismatch...",
        required=True,
    )

    def __init__(self, record_id: int):
        super().__init__()
        self.record_id = record_id

    async def on_submit(self, interaction: discord.Interaction):
        reason = self.reason_input.value.strip()

        # Update database
        await db.execute(
            """
            UPDATE payment_records
            SET status = 'rejected', notes = ?, reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (reason, interaction.user.id, self.record_id),
        )

        record = await db.fetchone("SELECT * FROM payment_records WHERE id = ?", (self.record_id,))

        # Update staff review embed
        if interaction.message:
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.red().value
            embed.set_field_at(
                index=3,
                name="Status",
                value=f"❌ **Rejected** by {interaction.user.mention}\n**Reason:** {reason}",
                inline=False,
            )
            await interaction.message.edit(embed=embed, view=None)

        await interaction.response.send_message(
            embed=warning_embed("Payment Rejected", f"Transaction #{self.record_id} marked as rejected."),
            ephemeral=True,
        )

        # Notify user if possible
        if record:
            user = interaction.guild.get_member(record["user_id"])
            if user:
                try:
                    dm_embed = error_embed(
                        "Payment Verification Rejected",
                        f"Your payment submission in **{interaction.guild.name}** was rejected.\n"
                        f"**Amount:** {record['amount']}\n"
                        f"**Reference ID:** `{record['reference_id']}`\n"
                        f"**Reason:** {reason}\n\n"
                        f"If you believe this is an error, please open a support ticket."
                    )
                    await user.send(embed=dm_embed)
                except Exception:
                    pass


class PaymentReviewView(discord.ui.View):
    """Staff action buttons for manually verifying user payments."""

    def __init__(self, record_id: int):
        super().__init__(timeout=None)
        self.record_id = record_id

    @discord.ui.button(label="Approve Payment", style=discord.ButtonStyle.success, emoji="✅")
    async def btn_approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Validate staff permissions
        cfg = await db.fetchone("SELECT staff_role_id FROM payments_config WHERE guild_id = ?", (interaction.guild_id,))
        staff_role_id = cfg["staff_role_id"] if cfg else None
        is_staff = (
            interaction.user.guild_permissions.administrator
            or (staff_role_id and any(r.id == staff_role_id for r in interaction.user.roles))
        )
        if not is_staff:
            return await interaction.response.send_message("You do not have permission to review payments.", ephemeral=True)

        await db.execute(
            """
            UPDATE payment_records
            SET status = 'approved', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (interaction.user.id, self.record_id),
        )

        record = await db.fetchone("SELECT * FROM payment_records WHERE id = ?", (self.record_id,))

        if interaction.message:
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.green().value
            embed.set_field_at(
                index=3,
                name="Status",
                value=f"✅ **Approved** by {interaction.user.mention}",
                inline=False,
            )
            await interaction.message.edit(embed=embed, view=None)

        await interaction.response.send_message(
            embed=success_embed("Payment Approved", f"Payment #{self.record_id} successfully verified."),
            ephemeral=True,
        )

        # Notify user
        if record:
            user = interaction.guild.get_member(record["user_id"])
            if user:
                try:
                    dm_embed = success_embed(
                        "Payment Verified & Approved!",
                        f"Your payment in **{interaction.guild.name}** has been confirmed!\n"
                        f"**Amount:** {record['amount']}\n"
                        f"**Reference ID:** `{record['reference_id']}`\n"
                        f"**Verified By:** {interaction.user.mention}\n\n"
                        f"Thank you for your payment!"
                    )
                    await user.send(embed=dm_embed)
                except Exception:
                    pass

    @discord.ui.button(label="Reject Payment", style=discord.ButtonStyle.danger, emoji="❌")
    async def btn_reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = await db.fetchone("SELECT staff_role_id FROM payments_config WHERE guild_id = ?", (interaction.guild_id,))
        staff_role_id = cfg["staff_role_id"] if cfg else None
        is_staff = (
            interaction.user.guild_permissions.administrator
            or (staff_role_id and any(r.id == staff_role_id for r in interaction.user.roles))
        )
        if not is_staff:
            return await interaction.response.send_message("You do not have permission to review payments.", ephemeral=True)

        await interaction.response.send_modal(RejectPaymentModal(self.record_id))


class Payments(commands.Cog):
    """Secure Multi-Currency / UPI Payment Management & Staff Verification."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    payment_group = app_commands.Group(name="payment", description="Configure and manage server payment verifications")

    @payment_group.command(name="setup", description="Configure UPI, Payment QR code, and verification channels")
    @has_admin_or_owner()
    @app_commands.describe(
        upi_id="Your UPI ID (e.g. merchant@upi)",
        qr_image="Upload image of your payment QR code",
        instructions="Payment instructions for buyers",
        staff_role="Staff role allowed to approve/reject payments",
        log_channel="Channel where payment submission reviews will be sent",
    )
    async def payment_setup(
        self,
        interaction: discord.Interaction,
        upi_id: str,
        qr_image: Optional[discord.Attachment] = None,
        instructions: str = "Scan QR or send UPI, then submit your reference ID & screenshot.",
        staff_role: Optional[discord.Role] = None,
        log_channel: Optional[discord.TextChannel] = None,
    ):
        qr_url = qr_image.url if qr_image else ""

        await db.execute(
            """
            INSERT INTO payments_config (guild_id, upi_id, qr_image_url, instructions, staff_role_id, log_channel_id)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                upi_id = excluded.upi_id,
                qr_image_url = CASE WHEN excluded.qr_image_url != '' THEN excluded.qr_image_url ELSE qr_image_url END,
                instructions = excluded.instructions,
                staff_role_id = excluded.staff_role_id,
                log_channel_id = excluded.log_channel_id
            """,
            (
                interaction.guild_id,
                upi_id,
                qr_url,
                instructions,
                staff_role.id if staff_role else None,
                log_channel.id if log_channel else None,
            ),
        )

        embed = success_embed(
            "Payment System Configured",
            f"**UPI ID:** `{upi_id}`\n"
            f"**Review Channel:** {log_channel.mention if log_channel else 'Not set'}\n"
            f"**Staff Role:** {staff_role.mention if staff_role else 'Administrators only'}\n"
            f"**Instructions:** {instructions}\n"
            f"**QR Attached:** {'Yes' if qr_url else 'None'}"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @payment_group.command(name="info", description="Display server payment details and QR code")
    async def pay_cmd(self, interaction: discord.Interaction):
        cfg = await db.fetchone("SELECT * FROM payments_config WHERE guild_id = ?", (interaction.guild_id,))
        if not cfg or not cfg["upi_id"]:
            return await interaction.response.send_message(
                embed=error_embed("Payment Not Configured", "This server has not configured payment information yet."),
                ephemeral=True,
            )

        embed = primary_embed(
            title=f"💳 Payment Gateway - {interaction.guild.name}",
            description=cfg["instructions"],
        )
        embed.add_field(name="UPI ID (Copyable)", value=f"```{cfg['upi_id']}```", inline=False)
        embed.add_field(
            name="Next Step",
            value="After completing the payment, run `/payment submit` to upload your screenshot and transaction reference ID for verification.",
            inline=False,
        )

        if cfg["qr_image_url"]:
            embed.set_image(url=cfg["qr_image_url"])

        await interaction.response.send_message(embed=embed)

    @payment_group.command(name="submit", description="Submit your payment proof and reference ID for manual verification")
    @app_commands.describe(
        amount="Amount paid (e.g. ₹500 or $10)",
        reference_id="Bank/UPI Transaction ID / UTR / Reference number",
        screenshot="Clear screenshot of successful payment confirmation",
    )
    async def payment_submit(
        self,
        interaction: discord.Interaction,
        amount: str,
        reference_id: str,
        screenshot: discord.Attachment,
    ):
        cfg = await db.fetchone("SELECT * FROM payments_config WHERE guild_id = ?", (interaction.guild_id,))
        if not cfg or not cfg["log_channel_id"]:
            return await interaction.response.send_message(
                embed=error_embed("System Unconfigured", "Staff payment review channel is not configured on this server."),
                ephemeral=True,
            )

        log_channel = interaction.guild.get_channel(cfg["log_channel_id"])
        if not log_channel or not isinstance(log_channel, discord.TextChannel):
            return await interaction.response.send_message(
                embed=error_embed("Review Channel Unavailable", "Payment log channel was deleted or is inaccessible."),
                ephemeral=True,
            )

        # Check for duplicate reference ID
        dup = await db.fetchone(
            "SELECT id FROM payment_records WHERE guild_id = ? AND reference_id = ?",
            (interaction.guild_id, reference_id.strip()),
        )
        if dup:
            return await interaction.response.send_message(
                embed=error_embed("Duplicate Reference ID", "This reference ID has already been submitted."),
                ephemeral=True,
            )

        # Record payment
        cursor = await db.execute(
            """
            INSERT INTO payment_records (guild_id, user_id, amount, reference_id, screenshot_url, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
            """,
            (interaction.guild_id, interaction.user.id, amount, reference_id.strip(), screenshot.url),
        )
        record_id = cursor.lastrowid

        # Send review embed to staff log channel
        review_embed = primary_embed(
            title=f"📥 New Payment Submission #{record_id}",
            description=f"Submitted by {interaction.user.mention} (`{interaction.user.id}`)",
        )
        review_embed.add_field(name="Amount", value=amount, inline=True)
        review_embed.add_field(name="Reference ID", value=f"`{reference_id}`", inline=True)
        review_embed.add_field(name="User Tag", value=f"@{interaction.user.name}", inline=True)
        review_embed.add_field(name="Status", value="⏳ **Pending Manual Verification**", inline=False)
        review_embed.set_image(url=screenshot.url)

        view = PaymentReviewView(record_id)
        staff_role_id = cfg["staff_role_id"]
        mention_text = f"<@&{staff_role_id}>" if staff_role_id else ""
        await log_channel.send(content=mention_text, embed=review_embed, view=view)

        # Confirmation to user
        user_embed = success_embed(
            "Payment Submitted Successfully",
            f"Your payment submission (ID: `#{record_id}`) has been sent to staff for manual verification.\n"
            f"**Amount:** {amount}\n"
            f"**Reference ID:** `{reference_id}`\n\n"
            f"You will be notified once reviewed!"
        )
        await interaction.response.send_message(embed=user_embed, ephemeral=True)

    @payment_group.command(name="history", description="View recent payment transactions")
    @app_commands.describe(user="Filter by user (Staff only)")
    async def payment_history(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        is_staff = interaction.user.guild_permissions.manage_guild
        target = user if (is_staff and user) else interaction.user

        rows = await db.fetchall(
            """
            SELECT * FROM payment_records
            WHERE guild_id = ? AND user_id = ?
            ORDER BY id DESC LIMIT 10
            """,
            (interaction.guild_id, target.id),
        )

        if not rows:
            return await interaction.response.send_message(
                embed=info_embed("No Records", f"No payment history found for {target.mention}."),
                ephemeral=True,
            )

        embed = primary_embed(title=f"📜 Payment History - {target.display_name}")
        for r in rows:
            status_emoji = "✅" if r["status"] == "approved" else ("❌" if r["status"] == "rejected" else "⏳")
            embed.add_field(
                name=f"{status_emoji} ID #{r['id']} - {r['amount']} ({r['status'].capitalize()})",
                value=f"Ref: `{r['reference_id']}` | Date: {r['created_at']}" + (f"\nNote: {r['notes']}" if r['notes'] else ""),
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Payments(bot))

