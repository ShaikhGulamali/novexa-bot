"""NOVEXA - Turn-Based Player-vs-Player Combat Engine.

Features:
- Interactive duel challenges with Accept/Decline buttons and timeout
- Weapon, shield, armor, and active pet combat bonuses
- Turn-by-turn battle logs with critical hits and armor mitigation
- XP & virtual coin prize rewards with anti-farming safeguards
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
import time
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

logger = logging.getLogger("novexa.battle")

# Pending challenge registry: target_id -> challenge_dict
active_challenges: Dict[int, Dict] = {}


class BattleChallengeView(discord.ui.View):
    """Interactive Challenge View with Accept and Decline buttons."""

    def __init__(self, challenger_id: int, opponent_id: int, guild_id: int, bet: int = 0):
        super().__init__(timeout=60.0)
        self.challenger_id = challenger_id
        self.opponent_id = opponent_id
        self.guild_id = guild_id
        self.bet = bet

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.opponent_id:
            await interaction.response.send_message(
                "❌ Only the challenged warrior can accept or decline this battle!",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="⚔️ Accept Battle", style=discord.ButtonStyle.danger, custom_id="accept_battle")
    async def accept_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        active_challenges.pop(self.opponent_id, None)

        # Disable buttons
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            embed=economy_embed("⚔️ Battle Accepted!", "The duel has begun! Generating combat simulation...", COLOR_ECO_GOLD),
            view=self,
        )

        res = await economy_service.resolve_battle(self.guild_id, self.challenger_id, self.opponent_id, self.bet)
        if not res["success"]:
            return await interaction.followup.send(embed=economy_embed("❌ Battle Cancelled", res["message"], COLOR_ECO_ERROR))

        winner_id = res["winner_id"]
        loser_id = res["loser_id"]
        log_text = "\n".join(res["log"][:12])  # display top 12 rounds

        embed = economy_embed(
            title=f"🏆 Arena Duel Victory: <@{winner_id}>!",
            color=COLOR_ECO_GOLD,
        )
        embed.description = f"### 📜 Battle Log:\n{log_text}\n\n"
        embed.add_field(name="Victor", value=f"👑 <@{winner_id}>", inline=True)
        embed.add_field(name="Runner-Up", value=f"💀 <@{loser_id}>", inline=True)
        embed.add_field(name="Rounds Fought", value=f"**{res['rounds']}** Rounds", inline=True)
        embed.add_field(name="Prize Won", value=f"**+{res['coin_prize']:,}** {CURRENCY_SYMBOL}", inline=True)
        embed.add_field(name="XP Awarded", value=f"**+{res['xp_reward']}** XP", inline=True)

        await interaction.followup.send(embed=embed)

    @discord.ui.button(label="🏳️ Decline", style=discord.ButtonStyle.secondary, custom_id="decline_battle")
    async def decline_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        active_challenges.pop(self.opponent_id, None)
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            embed=economy_embed("🏳️ Battle Declined", f"<@{self.opponent_id}> declined the duel challenge.", COLOR_ECO_INFO),
            view=self,
        )


class Battle(commands.Cog):
    """NOVEXA Player-vs-Player Combat & Duels."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="battle", description="Challenge another server member to a turn-based arena battle")
    @app_commands.describe(user="The member to challenge")
    async def battle(self, interaction: discord.Interaction, user: discord.Member):
        if not await check_channel_allowed(interaction, "hunting"):
            return

        if user.id == interaction.user.id:
            return await interaction.response.send_message("You cannot challenge yourself to a battle!", ephemeral=True)
        if user.bot:
            return await interaction.response.send_message("You cannot battle bot accounts.", ephemeral=True)

        # Anti-farming / cooldown check against same opponent
        last_fight = await db.fetchone(
            """
            SELECT created_at FROM economy_battles
            WHERE guild_id = ? AND ((challenger_id = ? AND opponent_id = ?) OR (challenger_id = ? AND opponent_id = ?))
            ORDER BY id DESC LIMIT 1
            """,
            (interaction.guild_id, interaction.user.id, user.id, user.id, interaction.user.id),
        )
        if last_fight:
            # 60s anti-farming cooldown between same pairs
            # (handled by service/log timestamp)
            pass

        # Calculate combat stats preview
        p1_stats = await economy_service.calculate_battle_stats(interaction.guild_id, interaction.user.id)
        p2_stats = await economy_service.calculate_battle_stats(interaction.guild_id, user.id)

        view = BattleChallengeView(interaction.user.id, user.id, interaction.guild_id, bet=0)
        active_challenges[user.id] = {
            "challenger_id": interaction.user.id,
            "guild_id": interaction.guild_id,
            "bet": 0,
            "view": view,
        }

        embed = economy_embed(
            title="⚔️ PvP Battle Challenge Issued!",
            description=f"{interaction.user.mention} has challenged {user.mention} to a duel in the arena!\n\n"
                        f"**{interaction.user.display_name}:** Level {p1_stats['level']} | {p1_stats['hp']} HP | {p1_stats['attack']} ATK | {p1_stats['defense']} DEF\n"
                        f"**{user.display_name}:** Level {p2_stats['level']} | {p2_stats['hp']} HP | {p2_stats['attack']} ATK | {p2_stats['defense']} DEF\n\n"
                        f"*{user.mention}, click Accept below within 60 seconds to enter combat!*",
            color=COLOR_ECO_PRIMARY,
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.send_message(content=user.mention, embed=embed, view=view)

    @app_commands.command(name="duel", description="Challenge a member to a high-stakes duel with virtual coin bets")
    @app_commands.describe(user="The member to challenge", bet="Amount of virtual coins to wager")
    async def duel(self, interaction: discord.Interaction, user: discord.Member, bet: int):
        if not await check_channel_allowed(interaction, "hunting"):
            return

        if user.id == interaction.user.id:
            return await interaction.response.send_message("You cannot duel yourself!", ephemeral=True)
        if user.bot:
            return await interaction.response.send_message("You cannot duel bots.", ephemeral=True)
        if bet <= 0:
            return await interaction.response.send_message("Bet must be greater than 0.", ephemeral=True)

        u1 = await economy_service.get_or_create_user(interaction.guild_id, interaction.user.id)
        u2 = await economy_service.get_or_create_user(interaction.guild_id, user.id)

        if u1["wallet"] < bet:
            return await interaction.response.send_message(f"You don't have enough coins! Wallet: **{u1['wallet']:,}** {CURRENCY_SYMBOL}.", ephemeral=True)
        if u2["wallet"] < bet:
            return await interaction.response.send_message(f"{user.display_name} doesn't have enough coins to cover this bet!", ephemeral=True)

        view = BattleChallengeView(interaction.user.id, user.id, interaction.guild_id, bet=bet)
        active_challenges[user.id] = {
            "challenger_id": interaction.user.id,
            "guild_id": interaction.guild_id,
            "bet": bet,
            "view": view,
        }

        embed = economy_embed(
            title=f"⚔️ HIGH STAKES DUEL: {bet:,} {CURRENCY_NAME} WAGER!",
            description=f"{interaction.user.mention} wagered **{bet:,} {CURRENCY_SYMBOL}** against {user.mention}!\n"
                        f"Winner takes **{bet * 2:,} {CURRENCY_SYMBOL}**!\n\n"
                        f"*{user.mention}, accept the duel below within 60 seconds!*",
            color=COLOR_ECO_GOLD,
        )
        await interaction.response.send_message(content=user.mention, embed=embed, view=view)

    @app_commands.command(name="accept-battle", description="Accept an active pending battle challenge issued to you")
    async def accept_battle(self, interaction: discord.Interaction):
        chal = active_challenges.pop(interaction.user.id, None)
        if not chal or chal["guild_id"] != interaction.guild_id:
            return await interaction.response.send_message(
                embed=economy_embed("❌ No Challenge", "You do not have any pending battle challenges.", COLOR_ECO_ERROR),
                ephemeral=True,
            )

        challenger_id = chal["challenger_id"]
        bet = chal["bet"]
        chal["view"].stop()

        await interaction.response.send_message(embed=economy_embed("⚔️ Battle Commencing!", "Resolving duel...", COLOR_ECO_GOLD))

        res = await economy_service.resolve_battle(interaction.guild_id, challenger_id, interaction.user.id, bet)
        if not res["success"]:
            return await interaction.followup.send(embed=economy_embed("❌ Battle Cancelled", res["message"], COLOR_ECO_ERROR))

        winner_id = res["winner_id"]
        loser_id = res["loser_id"]
        log_text = "\n".join(res["log"][:12])

        embed = economy_embed(
            title=f"🏆 Arena Duel Victory: <@{winner_id}>!",
            color=COLOR_ECO_GOLD,
        )
        embed.description = f"### 📜 Battle Log:\n{log_text}\n\n"
        embed.add_field(name="Victor", value=f"👑 <@{winner_id}>", inline=True)
        embed.add_field(name="Runner-Up", value=f"💀 <@{loser_id}>", inline=True)
        embed.add_field(name="Prize Won", value=f"**+{res['coin_prize']:,}** {CURRENCY_SYMBOL}", inline=True)
        embed.add_field(name="XP Awarded", value=f"**+{res['xp_reward']}** XP", inline=True)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="decline-battle", description="Decline an active pending battle challenge")
    async def decline_battle(self, interaction: discord.Interaction):
        chal = active_challenges.pop(interaction.user.id, None)
        if not chal or chal["guild_id"] != interaction.guild_id:
            return await interaction.response.send_message("You have no pending battle challenges to decline.", ephemeral=True)

        chal["view"].stop()
        embed = economy_embed("🏳️ Battle Declined", f"You declined the battle challenge from <@{chal['challenger_id']}>.", COLOR_ECO_INFO)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="battle-stats", description="Inspect your or another warrior's battle attributes and win rate")
    @app_commands.describe(user="Member to inspect")
    async def battle_stats(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        if not await check_channel_allowed(interaction, "hunting"):
            return

        target = user or interaction.user
        stats = await economy_service.calculate_battle_stats(interaction.guild_id, target.id)
        data = await economy_service.get_or_create_user(interaction.guild_id, target.id)

        won = data["battles_won"]
        lost = data["battles_lost"]
        total = won + lost
        win_rate = round((won / total) * 100, 1) if total > 0 else 0.0

        embed = economy_embed(
            title=f"⚔️ Combat Attributes - {target.display_name}",
            color=COLOR_ECO_PRIMARY,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="Health Points (HP)", value=f"❤️ **{stats['max_hp']}** HP", inline=True)
        embed.add_field(name="Attack Power (ATK)", value=f"🗡️ **{stats['attack']}** ATK", inline=True)
        embed.add_field(name="Defense Shields (DEF)", value=f"🛡️ **{stats['defense']}** DEF", inline=True)
        embed.add_field(name="Arena Battles Won", value=f"🏆 **{won:,}** Wins", inline=True)
        embed.add_field(name="Arena Battles Lost", value=f"💀 **{lost:,}** Losses", inline=True)
        embed.add_field(name="Win Rate", value=f"📊 **{win_rate}%**", inline=True)

        equipped_summary = []
        for slot, item in stats["equipped"].items():
            equipped_summary.append(f"• `{slot.upper()}`: {item['icon']} **{item['name']}** (+{item['attack_bonus']} ATK, +{item['defense_bonus']} DEF)")

        embed.add_field(
            name="Equipped Gear",
            value="\n".join(equipped_summary) if equipped_summary else "*No combat equipment equipped. Visit `/shop`!*",
            inline=False,
        )
        if stats["pet"]:
            p = stats["pet"]
            embed.add_field(
                name="Combat Pet Buff",
                value=f"{p['emoji']} **{p['nickname']}** (Lvl {p['level']}): +{p['bonus_value'] * p['level']}% {p['bonus_type'].replace('_', ' ').title()}",
                inline=False,
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="battle-history", description="View recent PvP match records in this server")
    @app_commands.describe(user="Filter by specific warrior")
    async def battle_history(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        if not await check_channel_allowed(interaction, "hunting"):
            return

        target = user or interaction.user
        rows = await db.fetchall(
            """
            SELECT * FROM economy_battles
            WHERE guild_id = ? AND (challenger_id = ? OR opponent_id = ?)
            ORDER BY id DESC LIMIT 10
            """,
            (interaction.guild_id, target.id, target.id),
        )

        if not rows:
            return await interaction.response.send_message(
                embed=economy_embed("⚔️ Battle History", f"No recent battle records found for {target.display_name}.", COLOR_ECO_INFO),
                ephemeral=True,
            )

        lines: List[str] = []
        for r in rows:
            is_win = (r["winner_id"] == target.id)
            status_icon = "🏆 WIN" if is_win else "💀 LOSS"
            opp_id = r["opponent_id"] if r["challenger_id"] == target.id else r["challenger_id"]
            bet_str = f" | Wager: {r['bet_amount']:,} 🪙" if r["bet_amount"] > 0 else ""
            lines.append(f"`{status_icon}` vs <@{opp_id}> — **{r['xp_awarded']} XP**{bet_str} (<t:{int(time.time())}:R>)")

        embed = economy_embed(
            title=f"📜 Battle History - {target.display_name}",
            description="\n\n".join(lines),
            color=COLOR_ECO_GOLD,
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Battle(bot))

