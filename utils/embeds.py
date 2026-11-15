import discord
import datetime
from typing import Optional, Any
from config import (
    BOT_NAME,
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_ERROR,
    COLOR_WARNING,
    COLOR_INFO,
    COLOR_PREMIUM,
)
from utils.emojis import Emojis


class NovexaEmbed(discord.Embed):
    """Standardized professional Discord embed for NOVEXA."""

    def __init__(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        color: int = COLOR_PRIMARY,
        timestamp: Optional[datetime.datetime] = None,
        **kwargs: Any,
    ):
        super().__init__(
            title=title,
            description=description,
            color=color,
            timestamp=timestamp or datetime.datetime.now(datetime.timezone.utc),
            **kwargs,
        )
        self.set_footer(text=f"{BOT_NAME} • Premium Edition")


# Alias for backward compatibility
GulamaliEmbed = NovexaEmbed


def primary_embed(title: str, description: str = "") -> NovexaEmbed:
    return NovexaEmbed(title=title, description=description, color=COLOR_PRIMARY)


def success_embed(title: str, description: str = "") -> NovexaEmbed:
    desc = f"{Emojis.TICK} {description}" if description else f"{Emojis.TICK} Success!"
    return NovexaEmbed(title=f"✅ {title}", description=desc, color=COLOR_SUCCESS)


def error_embed(title: str, description: str = "") -> NovexaEmbed:
    desc = f"{Emojis.BANNED} {description}" if description else f"{Emojis.BANNED} Error!"
    return NovexaEmbed(title=f"❌ {title}", description=desc, color=COLOR_ERROR)


def warning_embed(title: str, description: str = "") -> NovexaEmbed:
    desc = f"{Emojis.BOMB} {description}" if description else f"{Emojis.BOMB} Warning!"
    return NovexaEmbed(title=f"⚠️ {title}", description=desc, color=COLOR_WARNING)


def info_embed(title: str, description: str = "") -> NovexaEmbed:
    desc = f"{Emojis.DIAMOND} {description}" if description else f"{Emojis.DIAMOND} Information"
    return NovexaEmbed(title=f"ℹ️ {title}", description=desc, color=COLOR_INFO)


def premium_embed(title: str, description: str = "") -> NovexaEmbed:
    desc = f"{Emojis.CROWN} {description}" if description else f"{Emojis.CROWN} Premium VIP"
    return NovexaEmbed(title=f"👑 {title}", description=desc, color=COLOR_PREMIUM)
