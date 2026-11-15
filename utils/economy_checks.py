"""NOVEXA - Economy Channel Guard & UI Helpers."""

import discord
import time
from typing import Optional, List, Tuple
from database.database import db
from config import BOT_NAME

# Purple & Black Branding
COLOR_ECO_PRIMARY = 0x6C3483     # Royal Purple
COLOR_ECO_DARK = 0x1E1B2E        # Dark Purple Black Canvas
COLOR_ECO_GOLD = 0xF1C40F        # Radiant Gold
COLOR_ECO_SUCCESS = 0x2ECC71     # Emerald Green
COLOR_ECO_ERROR = 0xE74C3C       # Crimson Red
COLOR_ECO_INFO = 0x9B59B6        # Amethyst Purple


def format_remaining(seconds: float) -> str:
    """Format seconds into human-readable duration."""
    total = int(max(0, seconds))
    if total < 60:
        return f"`{total}s`"
    minutes, secs = divmod(total, 60)
    if minutes < 60:
        return f"`{minutes}m {secs}s`"
    hours, mins = divmod(minutes, 60)
    if hours < 24:
        return f"`{hours}h {mins}m`"
    days, hrs = divmod(hours, 24)
    return f"`{days}d {hrs}h`"


def economy_embed(title: str, description: str = "", color: int = COLOR_ECO_PRIMARY) -> discord.Embed:
    """Standardized dark purple and black embed for NOVEXA economy."""
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text=f"{BOT_NAME} • Ultimate Economy & RPG")
    return embed


async def check_channel_allowed(
    interaction: discord.Interaction,
    category: str,
) -> bool:
    """Verify if the current channel is permitted for the given economy command category.

    If channel enforcement is enabled and channels are configured for this category,
    returns False and sends a polite redirect message.
    """
    if not interaction.guild:
        return True

    # Check guild economy enabled
    g_row = await db.fetchone(
        "SELECT is_enabled, channel_enforcement FROM economy_guild_settings WHERE guild_id = ?",
        (interaction.guild_id,),
    )
    if g_row:
        if not g_row["is_enabled"]:
            await interaction.response.send_message(
                embed=economy_embed("⚠️ Economy Disabled", "The economy system is currently disabled on this server by staff.", COLOR_ECO_ERROR),
                ephemeral=True,
            )
            return False
        if not g_row["channel_enforcement"]:
            return True
    else:
        # Default: enforcement off
        return True

    # Check designated channels for this category or 'all'
    channels = await db.fetchall(
        "SELECT channel_id FROM economy_channel_settings WHERE guild_id = ? AND category_type IN (?, 'all')",
        (interaction.guild_id, category),
    )
    if not channels:
        # No restrictions configured for this category
        return True

    allowed_ids = {c["channel_id"] for c in channels}
    if interaction.channel_id in allowed_ids:
        return True

    # Not allowed here: send redirect notice
    mentions = [f"<#{cid}>" for cid in allowed_ids]
    embed = economy_embed(
        "🚫 Wrong Channel",
        f"This command is restricted to designated `{category.upper()}` channels!\n\n"
        f"Please head over to: {', '.join(mentions)}",
        COLOR_ECO_ERROR,
    )
    if interaction.response.is_done():
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=True)
    return False

