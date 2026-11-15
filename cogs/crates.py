"""NOVEXA - Crates, Mystery Vaults, Gems & Special Rewards Cog.

Features:
- Transparent drop rates displayed for Common, Rare, Epic, and Legendary crates
- Batch crate opening with aggregate loot summaries
- Dedicated Gem Shop with exclusive mythical artifacts and prestige titles
- Event and promo code claiming system
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
import random
from typing import Optional, List, Dict
from database.database import db
from services.economy_service import (
    economy_service,
    CURRENCY_NAME,
    CURRENCY_SYMBOL,
    GEM_NAME,
    GEM_SYMBOL,
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

logger = logging.getLogger("novexa.crates")

CRATE_INFO = {
    "common_crate": {
        "name": "Oak Mystery Crate",
        "emoji": "📦",
        "cost": "500 Coins",
        "rates": "• 70% Coins (300-800)\n• 20% Gems (1-3)\n• 10% Consumables & Training Gear",
    },
    "rare_crate": {
        "name": "Silver Treasure Crate",
        "emoji": "🧰",
        "cost": "2,200 Coins or 5 Gems",
        "rates": "• 55% Coins (1,500-4,000)\n• 25% Gems (4-10)\n• 20% Rare Weapons & Safari Nets",
    },
    "epic_crate": {
        "name": "Royal Amethyst Crate",
        "emoji": "🔮",
        "cost": "8,000 Coins or 18 Gems",
        "rates": "• 45% Coins (6,000-15,000)\n• 30% Gems (15-30)\n• 25% Epic Dragon Slayer & Master Nets",
    },
    "legendary_crate": {
        "name": "Celestial Novexa Vault",
        "emoji": "👑",
        "cost": "30,000 Coins or 60 Gems",
        "rates": "• 30% Coins (25,000-60,000)\n• 35% Gems (40-100)\n• 35% Mythic Blades, Railguns & Golden Lassos",
    },
}


class Crates(commands.Cog):
    """NOVEXA Mystery Crates & Gem Vaults."""

    crate_group = app_commands.Group(name="crate", description="Inspect and open mystery crates")

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @crate_group.command(name="view", description="Inspect unopened crates in your inventory and view drop probabilities")
    @app_commands.describe(user="Member to inspect")
    async def crate_view(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        if not await check_channel_allowed(interaction, "marketplace"):
            return

        target = user or interaction.user
        crates_inv = await db.fetchall(
            """
            SELECT inv.quantity, it.*
            FROM economy_inventory inv
            JOIN economy_items it ON inv.item_id = it.item_id
            WHERE inv.guild_id = ? AND inv.user_id = ? AND it.category = 'crates'
            """,
            (interaction.guild_id, target.id),
        )

        user_counts = {r["item_id"]: r["quantity"] for r in crates_inv}

        embed = economy_embed(
            title=f"📦 Mystery Crates - {target.display_name}",
            description="Open your crates using `/crate open <type> [amount]`.\nAll drop rates are certified 100% server-side randomized.\n",
            color=COLOR_ECO_GOLD,
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        for cid, info in CRATE_INFO.items():
            qty = user_counts.get(cid, 0)
            embed.add_field(
                name=f"{info['emoji']} {info['name']} — Owned: **{qty}x**",
                value=f"**Cost:** `{info['cost']}`\n**Probabilities:**\n{info['rates']}",
                inline=False,
            )

        embed.set_footer(text="Buy more crates in /shop crates or earn them from daily streaks!")
        await interaction.response.send_message(embed=embed)

    @crate_group.command(name="open", description="Open mystery crates to receive random coins, gems, and rare items")
    @app_commands.choices(crate_type=[
        app_commands.Choice(name="📦 Oak Mystery Crate", value="common_crate"),
        app_commands.Choice(name="🧰 Silver Treasure Crate", value="rare_crate"),
        app_commands.Choice(name="🔮 Royal Amethyst Crate", value="epic_crate"),
        app_commands.Choice(name="👑 Celestial Novexa Vault", value="legendary_crate"),
    ])
    @app_commands.describe(crate_type="Select crate type", amount="Number of crates to unlock at once (1-10)")
    async def open_crate_slash(
        self,
        interaction: discord.Interaction,
        crate_type: app_commands.Choice[str],
        amount: int = 1,
    ):
        if not await check_channel_allowed(interaction, "marketplace"):
            return

        if amount < 1 or amount > 25:
            return await interaction.response.send_message("You can open between 1 and 25 crates at a time.", ephemeral=True)

        success, results, summary = await economy_service.open_crate(
            interaction.guild_id, interaction.user.id, crate_type.value, amount
        )
        if not success:
            return await interaction.response.send_message(embed=economy_embed("❌ Cannot Open", summary, COLOR_ECO_ERROR), ephemeral=True)

        embed = economy_embed(
            title=f"🎉 Unlocked {amount}x {crate_type.name}!",
            description=summary,
            color=COLOR_ECO_GOLD,
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        # Highlight special equipment drops if any
        specials = [r["special"] for r in results if r.get("special")]
        if specials:
            embed.add_field(name="✨ Rare Equipment Pulled!", value=", ".join(f"`{s}`" for s in specials), inline=False)

        await interaction.response.send_message(embed=embed)

    # Prefix Commands for complete backward compatibility
    @commands.command(name="crate")
    async def prefix_crate(self, ctx: commands.Context, user: Optional[discord.Member] = None):
        target = user or ctx.author
        crates_inv = await db.fetchall(
            """
            SELECT inv.quantity, it.*
            FROM economy_inventory inv
            JOIN economy_items it ON inv.item_id = it.item_id
            WHERE inv.guild_id = ? AND inv.user_id = ? AND it.category = 'crates'
            """,
            (ctx.guild.id, target.id),
        )
        user_counts = {r["item_id"]: r["quantity"] for r in crates_inv}
        embed = economy_embed(
            title=f"📦 Mystery Crates - {target.display_name}",
            description=f"Open your crates using `{BOT_PREFIX}open-crate <type> [amount]` or `/crate open`.\n",
            color=COLOR_ECO_GOLD,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        for cid, info in CRATE_INFO.items():
            qty = user_counts.get(cid, 0)
            embed.add_field(
                name=f"{info['emoji']} {info['name']} — Owned: **{qty}x**",
                value=f"**Cost:** `{info['cost']}`\n**Probabilities:**\n{info['rates']}",
                inline=False,
            )
        await ctx.send(embed=embed)

    @commands.command(name="open-crate", aliases=["opencrate"])
    async def prefix_open_crate(self, ctx: commands.Context, crate_type: str = "common_crate", amount: int = 1):
        clean_type = crate_type.lower().strip()
        if "common" in clean_type or "oak" in clean_type:
            c_type = "common_crate"
        elif "silver" in clean_type or "rare" in clean_type:
            c_type = "rare_crate"
        elif "royal" in clean_type or "epic" in clean_type:
            c_type = "epic_crate"
        elif "celestial" in clean_type or "legendary" in clean_type:
            c_type = "legendary_crate"
        else:
            c_type = clean_type

        success, results, summary = await economy_service.open_crate(
            ctx.guild.id, ctx.author.id, c_type, amount
        )
        if not success:
            return await ctx.send(embed=economy_embed("❌ Cannot Open", summary, COLOR_ECO_ERROR))

        embed = economy_embed(
            title=f"🎉 Unlocked {amount}x {c_type}!",
            description=summary,
            color=COLOR_ECO_GOLD,
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @app_commands.command(name="gems", description="Check your current premium Gem balance and how to acquire them")
    @app_commands.describe(user="Member to inspect")
    async def gems(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        if not await check_channel_allowed(interaction, "marketplace"):
            return

        target = user or interaction.user
        data = await economy_service.get_or_create_user(interaction.guild_id, target.id)

        embed = economy_embed(
            title=f"💎 Gems Vault - {target.display_name}",
            description=f"You currently possess **{data['gems']} {GEM_NAME}** ({GEM_SYMBOL})!\n\n"
                        f"### 🌟 How to Earn Gems:\n"
                        f"• Complete **Achievements** (`/achievements`)\n"
                        f"• Maintain consecutive **Daily Streaks** (`/daily`)\n"
                        f"• Claim **Weekly & Monthly** bonuses (`/weekly`, `/monthly`)\n"
                        f"• Open **Treasure Crates** (`/open-crate`)\n"
                        f"• Level up your account (`/work`, `/hunt`)\n\n"
                        f"*Visit the `/gem-shop` to purchase mythical weapons and royal artifacts!*",
            color=COLOR_ECO_INFO,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="gem-shop", description="Browse and purchase exclusive Mythical items and prestige gear using Gems")
    async def gem_shop(self, interaction: discord.Interaction):
        if not await check_channel_allowed(interaction, "marketplace"):
            return

        rows = await db.fetchall("SELECT * FROM economy_items WHERE gem_price > 0 ORDER BY gem_price ASC")
        if not rows:
            return await interaction.response.send_message("No items currently available in the Gem Shop.", ephemeral=True)

        embed = economy_embed(
            title="💎 NOVEXA EXCLUSIVE GEM SHOP",
            description="Spend your premium Gems on game-changing mythical weapons and items!\nUse `/buy <item_id>` or staff commands to redeem.\n",
            color=COLOR_ECO_INFO,
        )
        for it in rows:
            embed.add_field(
                name=f"{it['icon']} {it['name']} (`{it['item_id']}`)",
                value=f"**Price:** **{it['gem_price']} {GEM_SYMBOL}**\n"
                      f"*{it['description']}*\n"
                      f"**Ability:** {it['special_ability'] or 'None'}",
                inline=False,
            )

        embed.set_footer(text="Gems are earned purely in-game via achievements, streaks, and level-ups.")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="claim-reward", description="Redeem promotional server reward codes for coins, gems, and crates")
    @app_commands.describe(code="Secret promo code (e.g. NOVEXA2026, WELCOME, ULTIMATE)")
    async def claim_reward(self, interaction: discord.Interaction, code: str):
        clean_code = code.upper().strip()

        # Built-in promotional codes tracked per user in DB
        promo_codes = {
            "NOVEXA2026": {"coins": 2500, "gems": 15, "crate": "rare_crate"},
            "GULAMALI2026": {"coins": 2500, "gems": 15, "crate": "rare_crate"},
            "ULTIMATE": {"coins": 1000, "gems": 5, "crate": "common_crate"},
            "OWOBOT": {"coins": 1500, "gems": 10, "crate": "common_crate"},
        }

        if clean_code not in promo_codes:
            return await interaction.response.send_message(
                embed=economy_embed("❌ Invalid Code", "That promo code does not exist or has expired.", COLOR_ECO_ERROR),
                ephemeral=True,
            )

        # Check if already redeemed using transactions audit
        redeemed = await db.fetchone(
            "SELECT id FROM economy_transactions WHERE guild_id = ? AND from_user_id = ? AND description = ?",
            (interaction.guild_id, interaction.user.id, f"Promo Code: {clean_code}"),
        )
        if redeemed:
            return await interaction.response.send_message(
                embed=economy_embed("⚠️ Already Claimed", "You have already redeemed this reward code!", COLOR_ECO_INFO),
                ephemeral=True,
            )

        reward = promo_codes[clean_code]
        await economy_service.modify_wallet(interaction.guild_id, interaction.user.id, reward["coins"], tx_type="promo", description=f"Promo Code: {clean_code}")
        await economy_service.modify_gems(interaction.guild_id, interaction.user.id, reward["gems"])
        if reward.get("crate"):
            await economy_service.give_item(interaction.guild_id, interaction.user.id, reward["crate"], 1)

        embed = economy_embed(
            title="🎉 Promo Reward Claimed!",
            description=f"Successfully redeemed **{clean_code}**!\n\n"
                        f"• **+{reward['coins']:,}** {CURRENCY_NAME} ({CURRENCY_SYMBOL})\n"
                        f"• **+{reward['gems']}** {GEM_NAME} ({GEM_SYMBOL})\n"
                        f"• **+1x** `{reward['crate']}`",
            color=COLOR_ECO_SUCCESS,
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Crates(bot))
