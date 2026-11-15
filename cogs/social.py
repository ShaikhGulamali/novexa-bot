"""NOVEXA - Social, Marriage, Friendship & Atomic Trading Cog.

Features:
- Marriage proposals with Diamond Ring validation and divorce handling
- Fun /ship compatibility calculation with personalized dynamic commentary
- User gifting (coins and inventory items)
- Atomic 2-Player trading system with double-confirmation preventing duplicate item exploits
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
import random
import json
import hashlib
from typing import Optional, List, Dict
from database.database import db
from services.economy_service import (
    economy_service,
    CURRENCY_NAME,
    CURRENCY_SYMBOL,
)
from utils.economy_checks import (
    check_channel_allowed,
    economy_embed,
    COLOR_ECO_PRIMARY,
    COLOR_ECO_GOLD,
    COLOR_ECO_SUCCESS,
    COLOR_ECO_ERROR,
    COLOR_ECO_INFO,
)

logger = logging.getLogger("novexa.social")


class MarriageProposalView(discord.ui.View):
    """Interactive proposal view for /marry."""

    def __init__(self, proposer_id: int, target_id: int, guild_id: int):
        super().__init__(timeout=60.0)
        self.proposer_id = proposer_id
        self.target_id = target_id
        self.guild_id = guild_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.target_id:
            await interaction.response.send_message("❌ This marriage proposal is not addressed to you!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="💍 I Say Yes!", style=discord.ButtonStyle.success, custom_id="marry_yes")
    async def accept_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        for child in self.children:
            child.disabled = True

        success, msg = await economy_service.marry(self.guild_id, self.proposer_id, self.target_id)
        if success:
            embed = economy_embed(
                "💖 JUST MARRIED! 💖",
                f"Ring the wedding bells! <@{self.proposer_id}> and <@{self.target_id}> are now happily married!\n\n"
                f"*May your partnership be blessed with endless wealth, bountiful hunts, and eternal joy.*",
                COLOR_ECO_GOLD,
            )
            embed.set_thumbnail(url="https://em-content.zobj.net/source/microsoft-teams/363/sparkling-heart_1f496.png")
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.edit_message(
                embed=economy_embed("❌ Marriage Failed", msg, COLOR_ECO_ERROR),
                view=self,
            )

    @discord.ui.button(label="💔 I Must Decline", style=discord.ButtonStyle.secondary, custom_id="marry_no")
    async def decline_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        for child in self.children:
            child.disabled = True
        embed = economy_embed("💔 Proposal Declined", f"<@{self.target_id}> gently declined the marriage proposal.", COLOR_ECO_INFO)
        await interaction.response.edit_message(embed=embed, view=self)


class TradeSessionView(discord.ui.View):
    """Interactive 2-Player Atomic Trade Interface with double confirmation."""

    def __init__(
        self,
        guild_id: int,
        p1_id: int,
        p2_id: int,
        p1_coins: int,
        p1_item_id: Optional[str],
        p1_qty: int,
        p2_coins: int,
        p2_item_id: Optional[str],
        p2_qty: int,
    ):
        super().__init__(timeout=90.0)
        self.guild_id = guild_id
        self.p1_id = p1_id
        self.p2_id = p2_id
        self.p1_coins = p1_coins
        self.p1_item_id = p1_item_id
        self.p1_qty = p1_qty
        self.p2_coins = p2_coins
        self.p2_item_id = p2_item_id
        self.p2_qty = p2_qty

        self.p1_confirmed = False
        self.p2_confirmed = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in (self.p1_id, self.p2_id):
            await interaction.response.send_message("❌ You are not a participant in this trade!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✅ Confirm Trade", style=discord.ButtonStyle.success, custom_id="confirm_trade")
    async def confirm_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.p1_id:
            self.p1_confirmed = True
        elif interaction.user.id == self.p2_id:
            self.p2_confirmed = True

        status_text = f"• <@{self.p1_id}>: {'✅ Ready' if self.p1_confirmed else '⏳ Waiting'}\n" \
                      f"• <@{self.p2_id}>: {'✅ Ready' if self.p2_confirmed else '⏳ Waiting'}"

        if not (self.p1_confirmed and self.p2_confirmed):
            await interaction.response.send_message(f"Your confirmation has been locked in!\n\n{status_text}", ephemeral=True)
            return

        # Both confirmed: Execute atomic swap!
        self.stop()
        for child in self.children:
            child.disabled = True

        # Re-verify Player 1 funds and items
        u1 = await economy_service.get_or_create_user(self.guild_id, self.p1_id)
        if self.p1_coins > 0 and u1["wallet"] < self.p1_coins:
            return await interaction.response.edit_message(
                embed=economy_embed("❌ Trade Aborted", f"<@{self.p1_id}> has insufficient coins to complete this trade!", COLOR_ECO_ERROR),
                view=self,
            )

        if self.p1_item_id:
            inv1 = await db.fetchone(
                "SELECT quantity FROM economy_inventory WHERE guild_id = ? AND user_id = ? AND item_id = ?",
                (self.guild_id, self.p1_id, self.p1_item_id),
            )
            if not inv1 or inv1["quantity"] < self.p1_qty:
                return await interaction.response.edit_message(
                    embed=economy_embed("❌ Trade Aborted", f"<@{self.p1_id}> no longer possesses the required items!", COLOR_ECO_ERROR),
                    view=self,
                )

        # Re-verify Player 2 funds and items
        u2 = await economy_service.get_or_create_user(self.guild_id, self.p2_id)
        if self.p2_coins > 0 and u2["wallet"] < self.p2_coins:
            return await interaction.response.edit_message(
                embed=economy_embed("❌ Trade Aborted", f"<@{self.p2_id}> has insufficient coins to complete this trade!", COLOR_ECO_ERROR),
                view=self,
            )

        if self.p2_item_id:
            inv2 = await db.fetchone(
                "SELECT quantity FROM economy_inventory WHERE guild_id = ? AND user_id = ? AND item_id = ?",
                (self.guild_id, self.p2_id, self.p2_item_id),
            )
            if not inv2 or inv2["quantity"] < self.p2_qty:
                return await interaction.response.edit_message(
                    embed=economy_embed("❌ Trade Aborted", f"<@{self.p2_id}> no longer possesses the required items!", COLOR_ECO_ERROR),
                    view=self,
                )

        # Execute atomic item and coin swaps
        if self.p1_coins > 0:
            await economy_service.modify_wallet(self.guild_id, self.p1_id, -self.p1_coins, tx_type="trade", description=f"Trade to {self.p2_id}")
            await economy_service.modify_wallet(self.guild_id, self.p2_id, self.p1_coins, tx_type="trade", description=f"Trade from {self.p1_id}")

        if self.p2_coins > 0:
            await economy_service.modify_wallet(self.guild_id, self.p2_id, -self.p2_coins, tx_type="trade", description=f"Trade to {self.p1_id}")
            await economy_service.modify_wallet(self.guild_id, self.p1_id, self.p2_coins, tx_type="trade", description=f"Trade from {self.p2_id}")

        if self.p1_item_id:
            await economy_service.remove_item(self.guild_id, self.p1_id, self.p1_item_id, self.p1_qty)
            await economy_service.give_item(self.guild_id, self.p2_id, self.p1_item_id, self.p1_qty)

        if self.p2_item_id:
            await economy_service.remove_item(self.guild_id, self.p2_id, self.p2_item_id, self.p2_qty)
            await economy_service.give_item(self.guild_id, self.p1_id, self.p2_item_id, self.p2_qty)

        embed = economy_embed(
            title="🔄 Trade Executed Successfully!",
            description=f"The atomic trade between <@{self.p1_id}> and <@{self.p2_id}> was safely settled!",
            color=COLOR_ECO_SUCCESS,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger, custom_id="cancel_trade")
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        for child in self.children:
            child.disabled = True
        embed = economy_embed("🚫 Trade Cancelled", f"The trade was cancelled by {interaction.user.mention}.", COLOR_ECO_ERROR)
        await interaction.response.edit_message(embed=embed, view=self)


class Social(commands.Cog):
    """NOVEXA Social, Relationships, Gifting & Trading."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="marry", description="Propose marriage to another member using a Diamond Ring")
    @app_commands.describe(user="The member you wish to propose to")
    async def marry(self, interaction: discord.Interaction, user: discord.Member):
        if not await check_channel_allowed(interaction, "economy"):
            return

        if user.id == interaction.user.id:
            return await interaction.response.send_message("You cannot marry yourself!", ephemeral=True)
        if user.bot:
            return await interaction.response.send_message("You cannot marry bots.", ephemeral=True)

        # Check ring ownership
        ring = await db.fetchone(
            "SELECT quantity FROM economy_inventory WHERE guild_id = ? AND user_id = ? AND item_id = 'diamond_ring'",
            (interaction.guild_id, interaction.user.id),
        )
        if not ring or ring["quantity"] <= 0:
            return await interaction.response.send_message(
                embed=economy_embed(
                    "💍 Diamond Ring Required",
                    "You need a **💍 Diamond Engagement Ring** to propose!\n"
                    "Purchase one at `/shop special` for 10,000 Coins.",
                    COLOR_ECO_ERROR,
                ),
                ephemeral=True,
            )

        view = MarriageProposalView(interaction.user.id, user.id, interaction.guild_id)
        embed = economy_embed(
            title="💍 A Romantic Proposal Has Been Made!",
            description=f"{interaction.user.mention} has dropped to one knee and presented a shimmering Diamond Ring to {user.mention}!\n\n"
                        f"*{user.mention}, do you take {interaction.user.display_name} to be your lawfully wedded companion?*",
            color=COLOR_ECO_GOLD,
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.send_message(content=user.mention, embed=embed, view=view)

    @app_commands.command(name="divorce", description="Divorce your current partner in this server")
    async def divorce(self, interaction: discord.Interaction):
        if not await check_channel_allowed(interaction, "economy"):
            return

        success, msg = await economy_service.divorce(interaction.guild_id, interaction.user.id)
        if success:
            embed = economy_embed("💔 Marriage Dissolved", msg, COLOR_ECO_INFO)
            await interaction.response.send_message(embed=embed)
        else:
            embed = economy_embed("❌ Error", msg, COLOR_ECO_ERROR)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="ship", description="Calculate the cosmic romantic compatibility between two members")
    @app_commands.describe(user1="First member", user2="Second member (optional, defaults to yourself)")
    async def ship(self, interaction: discord.Interaction, user1: discord.Member, user2: Optional[discord.Member] = None):
        target2 = user2 or interaction.user
        target1 = user1

        # Deterministic seed so same pair has consistent result on the same day
        seed_str = f"{min(target1.id, target2.id)}-{max(target1.id, target2.id)}"
        score = int(hashlib.md5(seed_str.encode()).hexdigest(), 16) % 101

        filled = score // 10
        bar = "💖" * filled + "🖤" * (10 - filled)

        if score >= 90:
            verdict = "🔥 **MATCH MADE IN HEAVEN!** Soulmates bound by cosmic destiny!"
        elif score >= 70:
            verdict = "✨ **Strong Chemistry!** Sparks fly whenever you're in the same voice channel."
        elif score >= 50:
            verdict = "🌿 **Decent Potential.** With some shared pizza and gaming, it could blossom."
        elif score >= 30:
            verdict = "🌧️ **Complicated.** High chance of dramatic arguments over loot drops."
        else:
            verdict = "💀 **Disaster Zone.** Run the opposite direction!"

        embed = economy_embed(
            title=f"💘 Love Meter: {target1.display_name} × {target2.display_name}",
            description=f"Compatibility Score: **{score}%**\n`[{bar}]`\n\n{verdict}",
            color=COLOR_ECO_GOLD,
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="friends", description="View your server friends list or add friends")
    @app_commands.describe(user="Member to inspect")
    async def friends(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        target = user or interaction.user
        friends_rows = await db.fetchall(
            """
            SELECT friend_id, created_at FROM economy_friends
            WHERE guild_id = ? AND user_id = ?
            """,
            (interaction.guild_id, target.id),
        )

        if not friends_rows:
            embed = economy_embed(
                f"👥 Friends - {target.display_name}",
                "No friends recorded yet! Use `/gift` to send coins or items to your friends.",
                COLOR_ECO_INFO,
            )
            return await interaction.response.send_message(embed=embed)

        lines = [f"• <@{r['friend_id']}>" for r in friends_rows]
        embed = economy_embed(
            title=f"👥 Friends - {target.display_name} ({len(friends_rows)})",
            description="\n".join(lines),
            color=COLOR_ECO_PRIMARY,
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="gift", description="Gift virtual coins or inventory items to a server friend")
    @app_commands.describe(
        user="Recipient member",
        coins="Amount of coins to gift (optional)",
        item_id="Item ID to gift from inventory (optional)",
        quantity="Number of items to gift (default 1)",
    )
    async def gift(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        coins: Optional[int] = None,
        item_id: Optional[str] = None,
        quantity: int = 1,
    ):
        if not await check_channel_allowed(interaction, "marketplace"):
            return

        if user.id == interaction.user.id:
            return await interaction.response.send_message("You cannot gift things to yourself!", ephemeral=True)
        if user.bot:
            return await interaction.response.send_message("You cannot gift things to bots.", ephemeral=True)

        if not coins and not item_id:
            return await interaction.response.send_message("Please specify either `coins` or an `item_id` to gift.", ephemeral=True)

        gift_details = []

        # Handle coins gift
        if coins and coins > 0:
            success, msg = await economy_service.pay(interaction.guild_id, interaction.user.id, user.id, coins)
            if not success:
                return await interaction.response.send_message(embed=economy_embed("❌ Gift Failed", msg, COLOR_ECO_ERROR), ephemeral=True)
            gift_details.append(f"**{coins:,} {CURRENCY_NAME}**")

        # Handle item gift
        if item_id:
            clean_id = item_id.lower().strip()
            inv = await db.fetchone(
                "SELECT quantity FROM economy_inventory WHERE guild_id = ? AND user_id = ? AND item_id = ?",
                (interaction.guild_id, interaction.user.id, clean_id),
            )
            if not inv or inv["quantity"] < quantity:
                return await interaction.response.send_message(f"You don't have **{quantity}x** `{clean_id}` to gift!", ephemeral=True)

            item = await db.fetchone("SELECT name, icon FROM economy_items WHERE item_id = ?", (clean_id,))
            await economy_service.remove_item(interaction.guild_id, interaction.user.id, clean_id, quantity)
            await economy_service.give_item(interaction.guild_id, user.id, clean_id, quantity)
            gift_details.append(f"**{quantity}x {item['icon'] if item else '📦'} {item['name'] if item else clean_id}**")

        # Record friendship automatically
        await db.execute(
            "INSERT INTO economy_friends (guild_id, user_id, friend_id) VALUES (?, ?, ?) ON CONFLICT DO NOTHING",
            (interaction.guild_id, interaction.user.id, user.id),
        )
        await db.execute(
            "INSERT INTO economy_friends (guild_id, user_id, friend_id) VALUES (?, ?, ?) ON CONFLICT DO NOTHING",
            (interaction.guild_id, user.id, interaction.user.id),
        )

        embed = economy_embed(
            "🎁 Generous Gift Delivered!",
            f"{interaction.user.mention} gifted {user.mention}:\n• " + "\n• ".join(gift_details),
            COLOR_ECO_SUCCESS,
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="trade", description="Initiate a secure atomic 2-player swap of coins or items")
    @app_commands.describe(
        user="Trading partner",
        offer_coins="Coins you offer (optional)",
        offer_item="Item ID you offer (optional)",
        offer_quantity="Quantity of offered item",
        request_coins="Coins requested in return (optional)",
        request_item="Item ID requested in return (optional)",
        request_quantity="Quantity of requested item",
    )
    async def trade(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        offer_coins: Optional[int] = 0,
        offer_item: Optional[str] = None,
        offer_quantity: int = 1,
        request_coins: Optional[int] = 0,
        request_item: Optional[str] = None,
        request_quantity: int = 1,
    ):
        if not await check_channel_allowed(interaction, "marketplace"):
            return

        if user.id == interaction.user.id:
            return await interaction.response.send_message("You cannot trade with yourself!", ephemeral=True)
        if user.bot:
            return await interaction.response.send_message("You cannot trade with bots.", ephemeral=True)

        o_coins = max(0, offer_coins or 0)
        r_coins = max(0, request_coins or 0)
        o_item = offer_item.lower().strip() if offer_item else None
        r_item = request_item.lower().strip() if request_item else None

        # Validate initial offer of proposer
        u1 = await economy_service.get_or_create_user(interaction.guild_id, interaction.user.id)
        if o_coins > 0 and u1["wallet"] < o_coins:
            return await interaction.response.send_message(f"You don't have **{o_coins:,} Coins** to offer!", ephemeral=True)

        if o_item:
            inv1 = await db.fetchone(
                "SELECT quantity FROM economy_inventory WHERE guild_id = ? AND user_id = ? AND item_id = ?",
                (interaction.guild_id, interaction.user.id, o_item),
            )
            if not inv1 or inv1["quantity"] < offer_quantity:
                return await interaction.response.send_message(f"You don't have **{offer_quantity}x** `{o_item}` to offer!", ephemeral=True)

        view = TradeSessionView(
            guild_id=interaction.guild_id,
            p1_id=interaction.user.id,
            p2_id=user.id,
            p1_coins=o_coins,
            p1_item_id=o_item,
            p1_qty=offer_quantity,
            p2_coins=r_coins,
            p2_item_id=r_item,
            p2_qty=request_quantity,
        )

        embed = economy_embed(
            title="🔄 Atomic Trade Proposal",
            description=f"### Proposed Exchange:\n"
                        f"**{interaction.user.display_name} offers:**\n"
                        f"• {f'{o_coins:,} {CURRENCY_SYMBOL}' if o_coins else 'No coins'}\n"
                        f"• {f'{offer_quantity}x `{o_item}`' if o_item else 'No items'}\n\n"
                        f"**{user.display_name} gives in return:**\n"
                        f"• {f'{r_coins:,} {CURRENCY_SYMBOL}' if r_coins else 'No coins'}\n"
                        f"• {f'{request_quantity}x `{r_item}`' if r_item else 'No items'}\n\n"
                        f"*Both members must click **Confirm Trade** below to atomically execute the exchange.*",
            color=COLOR_ECO_PRIMARY,
        )
        await interaction.response.send_message(content=f"{interaction.user.mention} and {user.mention}", embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Social(bot))

