"""NOVEXA - Core Virtual Economy Cog.

Implements all core currency, wallet, bank, jobs, games of chance,
streaks, leaderboards, reputation, and achievements commands.
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional, List
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
    format_remaining,
    economy_embed,
    COLOR_ECO_PRIMARY,
    COLOR_ECO_GOLD,
    COLOR_ECO_SUCCESS,
    COLOR_ECO_ERROR,
    COLOR_ECO_INFO,
)
from utils.helpers import PaginatorView

logger = logging.getLogger("novexa.economy")


class Economy(commands.Cog):
    """NOVEXA Virtual Economy & Mini-Games."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ==================== BALANCE & BANKING ====================

    @app_commands.command(name="balance", description="Check your or another member's virtual coin balance")
    @app_commands.describe(user="Member to inspect")
    async def balance(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        if not await check_channel_allowed(interaction, "economy"):
            return

        target = user or interaction.user
        data = await economy_service.get_or_create_user(interaction.guild_id, target.id)

        wallet = data["wallet"]
        bank = data["bank"]
        gems = data["gems"]
        total_wealth = wallet + bank

        embed = economy_embed(
            title=f"💰 Balance - {target.display_name}",
            color=COLOR_ECO_GOLD,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="👛 Wallet", value=f"**{wallet:,}** {CURRENCY_SYMBOL}", inline=True)
        embed.add_field(name="🏦 Bank", value=f"**{bank:,}** {CURRENCY_SYMBOL}", inline=True)
        embed.add_field(name="💎 Gems", value=f"**{gems:,}** {GEM_SYMBOL}", inline=True)
        embed.add_field(name="👑 Total Wealth", value=f"**{total_wealth:,}** {CURRENCY_NAME}", inline=False)
        embed.add_field(name="🔥 Daily Streak", value=f"**{data['daily_streak']} Days**", inline=True)
        embed.add_field(name="⭐ Level", value=f"**Lvl {data['level']}** (`{data['xp']:,} XP`)", inline=True)

        await interaction.response.send_message(embed=embed)

    @commands.command(name="wallet")
    async def prefix_wallet(self, ctx: commands.Context, user: Optional[discord.Member] = None):
        target = user or ctx.author
        data = await economy_service.get_or_create_user(ctx.guild.id, target.id)
        embed = economy_embed(
            title=f"👛 Wallet - {target.display_name}",
            description=f"**{data['wallet']:,}** {CURRENCY_NAME} ({CURRENCY_SYMBOL})",
            color=COLOR_ECO_PRIMARY,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.set_footer(text="Use deposit to safely store your coins in the bank.")
        await ctx.send(embed=embed)

    @commands.command(name="bank")
    async def prefix_bank(self, ctx: commands.Context, user: Optional[discord.Member] = None):
        target = user or ctx.author
        data = await economy_service.get_or_create_user(ctx.guild.id, target.id)
        embed = economy_embed(
            title=f"🏦 Vault & Bank - {target.display_name}",
            description=f"**{data['bank']:,}** {CURRENCY_NAME} ({CURRENCY_SYMBOL})",
            color=COLOR_ECO_PRIMARY,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.set_footer(text="Use withdraw to take coins out for shop purchases and games.")
        await ctx.send(embed=embed)

    @app_commands.command(name="deposit", description="Deposit virtual coins from your wallet into your bank")
    @app_commands.describe(amount="Amount of coins or 'all'")
    async def deposit(self, interaction: discord.Interaction, amount: str):
        if not await check_channel_allowed(interaction, "economy"):
            return

        success, dep_amount, msg = await economy_service.deposit(interaction.guild_id, interaction.user.id, amount)
        if success:
            embed = economy_embed("🏦 Deposit Successful", msg, COLOR_ECO_SUCCESS)
            await interaction.response.send_message(embed=embed)
        else:
            embed = economy_embed("❌ Deposit Failed", msg, COLOR_ECO_ERROR)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="withdraw", description="Withdraw virtual coins from your bank into your wallet")
    @app_commands.describe(amount="Amount of coins or 'all'")
    async def withdraw(self, interaction: discord.Interaction, amount: str):
        if not await check_channel_allowed(interaction, "economy"):
            return

        success, with_amount, msg = await economy_service.withdraw(interaction.guild_id, interaction.user.id, amount)
        if success:
            embed = economy_embed("👛 Withdrawal Successful", msg, COLOR_ECO_SUCCESS)
            await interaction.response.send_message(embed=embed)
        else:
            embed = economy_embed("❌ Withdrawal Failed", msg, COLOR_ECO_ERROR)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="pay", description="Safely transfer virtual Novexa Coins to another server member")
    @app_commands.describe(user="The member receiving the coins", amount="Amount of coins to send")
    async def pay(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        if not await check_channel_allowed(interaction, "economy"):
            return

        if user.bot:
            return await interaction.response.send_message("Bots do not have economy accounts.", ephemeral=True)

        success, msg = await economy_service.pay(interaction.guild_id, interaction.user.id, user.id, amount)
        if success:
            embed = economy_embed(
                "💸 Coins Transferred",
                f"{interaction.user.mention} sent **{amount:,} {CURRENCY_NAME}** to {user.mention}!",
                COLOR_ECO_SUCCESS,
            )
            await interaction.response.send_message(embed=embed)
        else:
            embed = economy_embed("❌ Payment Failed", msg, COLOR_ECO_ERROR)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    # ==================== REWARD CLAIMS & STREAKS ====================

    @app_commands.command(name="daily", description="Claim your daily bonus coins and advance your daily streak")
    async def daily(self, interaction: discord.Interaction):
        if not await check_channel_allowed(interaction, "economy"):
            return

        res = await economy_service.claim_daily(interaction.guild_id, interaction.user.id)
        if not res["success"]:
            rem = format_remaining(res["remaining_seconds"])
            embed = economy_embed("⏳ Daily Cooldown", f"You've already claimed your daily bonus!\nReturn in **{rem}**.", COLOR_ECO_INFO)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = economy_embed("🎁 Daily Reward Claimed!", color=COLOR_ECO_GOLD)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="Base Reward", value=f"+{res['base_coins']:,} {CURRENCY_SYMBOL}", inline=True)
        embed.add_field(name="Streak Bonus", value=f"+{res['streak_bonus']:,} {CURRENCY_SYMBOL}", inline=True)
        embed.add_field(name="Gems Received", value=f"+{res['gems']} {GEM_SYMBOL}", inline=True)
        embed.add_field(name="🔥 Consecutive Streak", value=f"**{res['streak']} Days**", inline=False)
        if res.get("crate"):
            embed.add_field(name="🎉 Milestone Bonus", value=f"Awarded **1x {res['crate']}**!", inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="weekly", description="Claim your massive weekly bonus reward (Every 7 Days)")
    async def weekly(self, interaction: discord.Interaction):
        if not await check_channel_allowed(interaction, "economy"):
            return

        res = await economy_service.claim_weekly(interaction.guild_id, interaction.user.id)
        if not res["success"]:
            rem = format_remaining(res["remaining_seconds"])
            embed = economy_embed("⏳ Weekly Cooldown", f"Weekly reward not ready yet!\nReturn in **{rem}**.", COLOR_ECO_INFO)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = economy_embed("📅 Weekly Grand Reward Claimed!", color=COLOR_ECO_SUCCESS)
        embed.add_field(name="Coins", value=f"+{res['coins']:,} {CURRENCY_SYMBOL}", inline=True)
        embed.add_field(name="Gems", value=f"+{res['gems']} {GEM_SYMBOL}", inline=True)
        embed.add_field(name="Bonus Crate", value=f"+1x `{res['crate']}`", inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="monthly", description="Claim your monthly VIP reward (Every 30 Days)")
    async def monthly(self, interaction: discord.Interaction):
        if not await check_channel_allowed(interaction, "economy"):
            return

        res = await economy_service.claim_monthly(interaction.guild_id, interaction.user.id)
        if not res["success"]:
            rem = format_remaining(res["remaining_seconds"])
            embed = economy_embed("⏳ Monthly Cooldown", f"Monthly reward not ready yet!\nReturn in **{rem}**.", COLOR_ECO_INFO)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = economy_embed("👑 Monthly VIP Bounty Claimed!", color=COLOR_ECO_GOLD)
        embed.add_field(name="Coins", value=f"+{res['coins']:,} {CURRENCY_SYMBOL}", inline=True)
        embed.add_field(name="Gems", value=f"+{res['gems']} {GEM_SYMBOL}", inline=True)
        embed.add_field(name="Bonus Crate", value=f"+1x `{res['crate']}`", inline=True)
        await interaction.response.send_message(embed=embed)

    # ==================== WORK, CRIME & SLUT ====================

    @app_commands.command(name="work", description="Perform virtual jobs to earn honest Novexa Coins (5-min cooldown)")
    async def work(self, interaction: discord.Interaction):
        if not await check_channel_allowed(interaction, "economy"):
            return

        res = await economy_service.work(interaction.guild_id, interaction.user.id)
        if not res["success"]:
            rem = format_remaining(res["remaining_seconds"])
            embed = economy_embed("☕ Resting from Work", f"You are resting between shifts. Back to work in **{rem}**.", COLOR_ECO_INFO)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = economy_embed(f"💼 Work Complete: {res['job']}", res["scenario"], COLOR_ECO_SUCCESS)
        embed.add_field(name="Paycheck", value=f"**+{res['earned']:,}** {CURRENCY_SYMBOL}", inline=True)
        embed.add_field(name="Experience", value=f"**+{res['xp']}** XP", inline=True)
        if res["leveled_up"]:
            embed.add_field(name="🎉 Level Up!", value=f"You reached **Level {res['new_level']}**!", inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="crime", description="Commit high-stakes virtual heists with a chance of police fines (10-min cooldown)")
    async def crime(self, interaction: discord.Interaction):
        if not await check_channel_allowed(interaction, "economy"):
            return

        res = await economy_service.crime(interaction.guild_id, interaction.user.id)
        if not res["success"]:
            rem = format_remaining(res["remaining_seconds"])
            embed = economy_embed("🚨 Laying Low", f"The police are patrolling! Lay low for **{rem}**.", COLOR_ECO_INFO)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if res["won"]:
            embed = economy_embed("🥷 Crime Successful!", res["scenario"], COLOR_ECO_SUCCESS)
            embed.add_field(name="Loot Stolen", value=f"**+{res['amount']:,}** {CURRENCY_SYMBOL}", inline=True)
            embed.add_field(name="Experience", value=f"**+{res['xp']}** XP", inline=True)
            if res["leveled_up"]:
                embed.add_field(name="🎉 Level Up!", value=f"You reached **Level {res['new_level']}**!", inline=False)
        else:
            embed = economy_embed("👮 Busted by Police!", res["scenario"], COLOR_ECO_ERROR)
            embed.add_field(name="Fine Paid", value=f"**-{res['fine']:,}** {CURRENCY_SYMBOL}", inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="slut", description="Classic OwO-style high-risk flirtatious nightlife encounters (15-min cooldown)")
    async def slut(self, interaction: discord.Interaction):
        if not await check_channel_allowed(interaction, "economy"):
            return

        res = await economy_service.slut(interaction.guild_id, interaction.user.id)
        if not res["success"]:
            rem = format_remaining(res["remaining_seconds"])
            embed = economy_embed("💅 Powdering Your Nose", f"You need to catch your breath! Try again in **{rem}**.", COLOR_ECO_INFO)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if res["won"]:
            embed = economy_embed("💋 Nightlife Success!", res["scenario"], COLOR_ECO_SUCCESS)
            embed.add_field(name="Coins Showered", value=f"**+{res['amount']:,}** {CURRENCY_SYMBOL}", inline=True)
            embed.add_field(name="Experience", value=f"**+{res['xp']}** XP", inline=True)
            if res["leveled_up"]:
                embed.add_field(name="🎉 Level Up!", value=f"You reached **Level {res['new_level']}**!", inline=False)
        else:
            embed = economy_embed("💔 Embarrassing Fail!", res["scenario"], COLOR_ECO_ERROR)
            embed.add_field(name="Lost Coins", value=f"**-{res['fine']:,}** {CURRENCY_SYMBOL}", inline=True)

        await interaction.response.send_message(embed=embed)

    # ==================== GAMES OF CHANCE (VIRTUAL ONLY) ====================

    @app_commands.command(name="coinflip", description="Bet virtual coins on Heads or Tails (2x Payout)")
    @app_commands.choices(choice=[
        app_commands.Choice(name="Heads", value="heads"),
        app_commands.Choice(name="Tails", value="tails"),
    ])
    @app_commands.describe(choice="Heads or Tails", amount="Virtual coin bet")
    async def coinflip(self, interaction: discord.Interaction, choice: app_commands.Choice[str], amount: int):
        if not await check_channel_allowed(interaction, "games"):
            return

        res = await economy_service.coinflip(interaction.guild_id, interaction.user.id, choice.value, amount)
        if not res["success"]:
            return await interaction.response.send_message(embed=economy_embed("❌ Coinflip Error", res["message"], COLOR_ECO_ERROR), ephemeral=True)

        coin_emoji = "🪙" if res["result"] == "heads" else "🥈"
        if res["won"]:
            embed = economy_embed("🎉 Coinflip Winner!", f"The coin landed on **{res['result'].upper()}** {coin_emoji}!\nYou won **+{res['payout']:,} {CURRENCY_SYMBOL}** (+{res['profit']:,} profit)!", COLOR_ECO_SUCCESS)
        else:
            embed = economy_embed("💀 Coinflip Loss", f"The coin landed on **{res['result'].upper()}** {coin_emoji}.\nYou lost your bet of **{res['lost']:,} {CURRENCY_SYMBOL}**.", COLOR_ECO_ERROR)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="dice", description="Roll a 6-sided die. Exact guess = 6x payout, or roll vs Bot")
    @app_commands.describe(amount="Virtual coin bet", guess="Optional exact number guess (1-6)")
    async def dice(self, interaction: discord.Interaction, amount: int, guess: Optional[int] = None):
        if not await check_channel_allowed(interaction, "games"):
            return

        res = await economy_service.dice(interaction.guild_id, interaction.user.id, amount, guess)
        if not res["success"]:
            return await interaction.response.send_message(embed=economy_embed("❌ Dice Error", res["message"], COLOR_ECO_ERROR), ephemeral=True)

        if res["mode"] == "exact":
            if res["won"]:
                embed = economy_embed("🎲 EXACT GUESS WINNER!", f"You predicted **{res['guess']}** and the die rolled **{res['roll']}** 🎲!\n6x Payout: **+{res['payout']:,} {CURRENCY_SYMBOL}**!", COLOR_ECO_GOLD)
            else:
                embed = economy_embed("🎲 Dice Loss", f"You guessed **{res['guess']}**, but the die rolled **{res['roll']}**.\nLost: **{res['lost']:,} {CURRENCY_SYMBOL}**.", COLOR_ECO_ERROR)
        else:
            if res["won"] is True:
                embed = economy_embed("🎲 Dice Victory!", f"Your Roll: **{res['player_roll']}** 🎲 | Bot Roll: **{res['bot_roll']}** 🤖\nYou win **+{res['payout']:,} {CURRENCY_SYMBOL}**!", COLOR_ECO_SUCCESS)
            elif res["won"] is None:
                embed = economy_embed("🎲 Dice Tie!", f"Both rolled **{res['player_roll']}**! Bet of **{res['refund']:,} {CURRENCY_SYMBOL}** returned.", COLOR_ECO_INFO)
            else:
                embed = economy_embed("🎲 Dice Defeat", f"Your Roll: **{res['player_roll']}** 🎲 | Bot Roll: **{res['bot_roll']}** 🤖\nYou lost **{res['lost']:,} {CURRENCY_SYMBOL}**.", COLOR_ECO_ERROR)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="slots", description="Spin the 3-reel slot machine for up to 50x jackpot")
    @app_commands.describe(amount="Virtual coin bet")
    async def slots(self, interaction: discord.Interaction, amount: int):
        if not await check_channel_allowed(interaction, "games"):
            return

        res = await economy_service.slots(interaction.guild_id, interaction.user.id, amount)
        if not res["success"]:
            return await interaction.response.send_message(embed=economy_embed("❌ Slots Error", res["message"], COLOR_ECO_ERROR), ephemeral=True)

        reels_str = " | ".join(res["reels"])
        display = f"```\n╔═══════════════╗\n║  {reels_str}  ║\n╚═══════════════╝\n```"

        if res["won"]:
            embed = economy_embed("🎰 JACKPOT WINNER!", f"{display}\nMultiplier: **{res['multiplier']}x**\nPayout: **+{res['payout']:,} {CURRENCY_SYMBOL}** (+{res['profit']:,} profit)!", COLOR_ECO_GOLD)
        else:
            embed = economy_embed("🎰 Better Luck Next Spin", f"{display}\nNo winning combination. Lost **{res['lost']:,} {CURRENCY_SYMBOL}**.", COLOR_ECO_ERROR)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="gamble", description="Roll 1-100: >50 wins 2x, >90 wins 3x")
    @app_commands.describe(amount="Virtual coin bet")
    async def gamble(self, interaction: discord.Interaction, amount: int):
        if not await check_channel_allowed(interaction, "games"):
            return

        res = await economy_service.gamble(interaction.guild_id, interaction.user.id, amount)
        if not res["success"]:
            return await interaction.response.send_message(embed=economy_embed("❌ Gamble Error", res["message"], COLOR_ECO_ERROR), ephemeral=True)

        if res["won"]:
            embed = economy_embed("🎲 High Roll Winner!", f"You rolled a **{res['roll']} / 100**!\nTier: **{res['tier']}**\nPayout: **+{res['payout']:,} {CURRENCY_SYMBOL}** (+{res['profit']:,} profit)!", COLOR_ECO_SUCCESS)
        else:
            embed = economy_embed("🎲 Gamble Defeat", f"You rolled a **{res['roll']} / 100**.\nRequired > 50 to win. Lost **{res['lost']:,} {CURRENCY_SYMBOL}**.", COLOR_ECO_ERROR)

        await interaction.response.send_message(embed=embed)

    # ==================== LEADERBOARDS & SOCIAL ====================

    @app_commands.command(name="leaderboard", description="View the multi-category server economy leaderboards")
    @app_commands.choices(category=[
        app_commands.Choice(name="Wealth (Wallet + Bank)", value="wealth"),
        app_commands.Choice(name="Highest Level", value="level"),
        app_commands.Choice(name="Animals Collected", value="animals"),
        app_commands.Choice(name="Battles Won", value="battles"),
        app_commands.Choice(name="Reputation", value="rep"),
        app_commands.Choice(name="Daily Streaks", value="streak"),
    ])
    @app_commands.describe(category="Leaderboard sorting category")
    async def leaderboard(self, interaction: discord.Interaction, category: Optional[app_commands.Choice[str]] = None):
        if not await check_channel_allowed(interaction, "games"):
            return

        cat_val = category.value if category else "wealth"

        if cat_val == "wealth":
            rows = await db.fetchall(
                "SELECT user_id, (wallet + bank) as metric FROM economy_users WHERE guild_id = ? ORDER BY metric DESC LIMIT 50",
                (interaction.guild_id,),
            )
            title = "💰 Wealth Leaderboard"
            format_fn = lambda val: f"**{val:,}** {CURRENCY_NAME}"
        elif cat_val == "level":
            rows = await db.fetchall(
                "SELECT user_id, level, xp as metric FROM economy_users WHERE guild_id = ? ORDER BY level DESC, xp DESC LIMIT 50",
                (interaction.guild_id,),
            )
            title = "⭐ Level & XP Leaderboard"
            format_fn = lambda val, r: f"**Lvl {r['level']}** (`{val:,} XP`)"
        elif cat_val == "animals":
            rows = await db.fetchall(
                """
                SELECT ua.user_id, SUM(ua.count) as metric
                FROM economy_user_animals ua
                WHERE ua.guild_id = ?
                GROUP BY ua.user_id
                ORDER BY metric DESC LIMIT 50
                """,
                (interaction.guild_id,),
            )
            title = "🐾 Imperial Zoo Collection Leaderboard"
            format_fn = lambda val: f"**{val:,}** Animals"
        elif cat_val == "battles":
            rows = await db.fetchall(
                "SELECT user_id, battles_won as metric FROM economy_users WHERE guild_id = ? AND battles_won > 0 ORDER BY battles_won DESC LIMIT 50",
                (interaction.guild_id,),
            )
            title = "⚔️ Arena Gladiator Leaderboard"
            format_fn = lambda val: f"**{val:,}** Victories"
        elif cat_val == "rep":
            rows = await db.fetchall(
                "SELECT user_id, reputation as metric FROM economy_users WHERE guild_id = ? AND reputation > 0 ORDER BY reputation DESC LIMIT 50",
                (interaction.guild_id,),
            )
            title = "🌟 Server Reputation Leaderboard"
            format_fn = lambda val: f"**+{val:,}** Rep"
        else:  # streak
            rows = await db.fetchall(
                "SELECT user_id, daily_streak as metric FROM economy_users WHERE guild_id = ? AND daily_streak > 0 ORDER BY daily_streak DESC LIMIT 50",
                (interaction.guild_id,),
            )
            title = "🔥 Daily Streak Masters"
            format_fn = lambda val: f"**{val:,}** Days"

        if not rows:
            return await interaction.response.send_message(
                embed=economy_embed(title, "No records found on this server yet for this category.", COLOR_ECO_INFO),
                ephemeral=True,
            )

        pages: List[discord.Embed] = []
        chunk_size = 10
        for i in range(0, len(rows), chunk_size):
            chunk = rows[i : i + chunk_size]
            embed = economy_embed(title=f"{title} - {interaction.guild.name}", color=COLOR_ECO_GOLD)
            lines = []
            for rank_idx, r in enumerate(chunk, start=i + 1):
                medal = "🥇" if rank_idx == 1 else ("🥈" if rank_idx == 2 else ("🥉" if rank_idx == 3 else f"`#{rank_idx}`"))
                val_str = format_fn(r["metric"], r) if cat_val == "level" else format_fn(r["metric"])
                lines.append(f"{medal} <@{r['user_id']}> — {val_str}")
            embed.description = "\n".join(lines)
            embed.set_footer(text=f"Page {len(pages) + 1} of {((len(rows) - 1) // chunk_size) + 1}")
            pages.append(embed)

        if len(pages) == 1:
            await interaction.response.send_message(embed=pages[0])
        else:
            view = PaginatorView(pages, interaction.user.id)
            await interaction.response.send_message(embed=pages[0], view=view)

    @app_commands.command(name="rep", description="Award a reputation point to another member (24-hour cooldown)")
    @app_commands.describe(user="The member to award reputation to")
    async def rep(self, interaction: discord.Interaction, user: discord.Member):
        if not await check_channel_allowed(interaction, "economy"):
            return

        if user.bot:
            return await interaction.response.send_message("You cannot give reputation to bots.", ephemeral=True)

        success, msg = await economy_service.give_rep(interaction.guild_id, interaction.user.id, user.id)
        if success:
            embed = economy_embed("🌟 Reputation Awarded", msg, COLOR_ECO_GOLD)
            await interaction.response.send_message(embed=embed)
        else:
            embed = economy_embed("⏳ Reputation Cooldown", msg, COLOR_ECO_INFO)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="achievements", description="View all unlocked and locked server achievements")
    @app_commands.describe(user="Member to view achievements for")
    async def achievements(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        if not await check_channel_allowed(interaction, "economy"):
            return

        target = user or interaction.user
        all_achs = await db.fetchall("SELECT * FROM economy_achievements ORDER BY gem_reward")
        user_unlocked = await db.fetchall(
            "SELECT achievement_key, unlocked_at FROM economy_user_achievements WHERE guild_id = ? AND user_id = ?",
            (interaction.guild_id, target.id),
        )
        unlocked_map = {r["achievement_key"]: r["unlocked_at"] for r in user_unlocked}

        lines: List[str] = []
        for ach in all_achs:
            key = ach["key"]
            if key in unlocked_map:
                lines.append(f"✅ **{ach['icon']} {ach['name']}**\n*{ach['description']}* (+{ach['gem_reward']} 💎, +{ach['coin_reward']:,} 🪙)")
            else:
                lines.append(f"🔒 **{ach['icon']} {ach['name']}**\n*{ach['description']}* (Reward: {ach['gem_reward']} 💎, {ach['coin_reward']:,} 🪙)")

        embed = economy_embed(
            title=f"🏆 Achievements - {target.display_name} ({len(unlocked_map)}/{len(all_achs)})",
            description="\n\n".join(lines),
            color=COLOR_ECO_GOLD,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Economy(bot))

