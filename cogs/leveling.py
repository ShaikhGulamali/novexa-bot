import discord
from discord.ext import commands
from discord import app_commands
import logging
import random
import time
from typing import Optional
from database.database import db
from utils.embeds import primary_embed, success_embed, error_embed, info_embed
from utils.permissions import has_admin_or_owner
from utils.helpers import PaginatorView

logger = logging.getLogger("novexa.leveling")


def calculate_xp_for_level(level: int) -> int:
    """Calculate total XP required to reach the given level."""
    return int(100 * (level ** 1.5))


class Leveling(commands.Cog):
    """Competitive XP Progression, Level Milestones, and Virtual Economy."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Grant XP for chat messages with anti-spam cooldown."""
        if message.author.bot or not message.guild:
            return

        guild_id = message.guild.id
        user_id = message.author.id
        now = time.time()

        # Check if leveling is enabled
        g_row = await db.fetchone("SELECT leveling_enabled FROM guild_settings WHERE guild_id = ?", (guild_id,))
        if g_row and not g_row["leveling_enabled"]:
            return

        row = await db.fetchone(
            "SELECT xp, level, last_xp_time FROM leveling WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )

        last_xp = row["last_xp_time"] if row else 0.0
        # 60s anti-spam cooldown
        if now - last_xp < 60.0:
            return

        current_xp = row["xp"] if row else 0
        current_lvl = row["level"] if row else 0
        xp_gain = random.randint(15, 25)
        new_xp = current_xp + xp_gain

        # Check for level up
        xp_needed = calculate_xp_for_level(current_lvl + 1)
        new_lvl = current_lvl
        leveled_up = False

        if new_xp >= xp_needed:
            new_lvl += 1
            leveled_up = True

        await db.execute(
            """
            INSERT INTO leveling (guild_id, user_id, xp, level, last_xp_time)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET
                xp = excluded.xp,
                level = excluded.level,
                last_xp_time = excluded.last_xp_time
            """,
            (guild_id, user_id, new_xp, new_lvl, now),
        )

        if leveled_up:
            # Award 50 bonus coins for leveling up
            await db.execute(
                """
                INSERT INTO economy_users (guild_id, user_id, wallet, xp, level)
                VALUES (?, ?, 550, ?, ?)
                ON CONFLICT(guild_id, user_id) DO UPDATE SET wallet = wallet + 50, xp = excluded.xp, level = excluded.level
                """,
                (guild_id, user_id, new_xp, new_lvl),
            )
            await db.execute(
                """
                INSERT INTO economy (guild_id, user_id, wallet)
                VALUES (?, ?, 150)
                ON CONFLICT(guild_id, user_id) DO UPDATE SET wallet = wallet + 50
                """,
                (guild_id, user_id),
            )
            try:
                lvl_embed = success_embed(
                    "🎉 Level Up!",
                    f"Congratulations {message.author.mention}! You've reached **Level {new_lvl}**!\n"
                    f"Bonus: **+50 Novexa Coins** awarded to your wallet."
                )
                lvl_embed.set_thumbnail(url=message.author.display_avatar.url)
                await message.channel.send(embed=lvl_embed)
            except Exception:
                pass

    @app_commands.command(name="rank", description="Check your current level, rank, and XP progress")
    @app_commands.describe(user="Member to check rank for")
    async def rank(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        target = user or interaction.user
        guild_id = interaction.guild_id

        row = await db.fetchone(
            "SELECT xp, level FROM leveling WHERE guild_id = ? AND user_id = ?",
            (guild_id, target.id),
        )
        current_xp = row["xp"] if row else 0
        level = row["level"] if row else 0
        next_xp = calculate_xp_for_level(level + 1)

        rank_row = await db.fetchone(
            "SELECT COUNT(*) as rank FROM leveling WHERE guild_id = ? AND xp > ?",
            (guild_id, current_xp),
        )
        rank_num = (rank_row["rank"] if rank_row else 0) + 1

        embed = primary_embed(title=f"📊 Rank Card - {target.display_name}")
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="Server Rank", value=f"#{rank_num}", inline=True)
        embed.add_field(name="Level", value=str(level), inline=True)
        embed.add_field(name="Total XP", value=f"{current_xp:,} / {next_xp:,}", inline=True)

        ratio = min(max(current_xp / max(next_xp, 1), 0.0), 1.0)
        filled = int(ratio * 15)
        bar = "█" * filled + "░" * (15 - filled)
        embed.add_field(name="Progress", value=f"`[{bar}]` {int(ratio * 100)}%", inline=False)

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Leveling(bot))


