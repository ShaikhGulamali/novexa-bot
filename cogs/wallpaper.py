"""NOVEXA - AI Wallpaper Generator.

Designate a channel as a wallpaper studio; every message typed there is treated
as an image prompt and NOVEXA replies with a generated wallpaper.

- /wallpaper setup [channel]   -> register a channel (posts the studio panel)
- /wallpaper remove [channel]  -> unregister a channel
- /wallpaper list              -> show registered channels
- Prefix mirror: n!wallpaper setup|remove|list

Sizing keywords are parsed out of the prompt: 4k, 2k, 1440p, 1080p, phone,
portrait, square, ultrawide, banner. Everything else is passed to the model.
"""

import asyncio
import io
import logging
import random
import re
import time
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import quote

import discord
from discord import app_commands
from discord.ext import commands

from config import POLLINATIONS_TOKEN
from database.database import db
from utils.embeds import primary_embed, success_embed, error_embed, info_embed, warning_embed
from utils.permissions import has_admin_or_owner

logger = logging.getLogger("novexa.wallpaper")

API_ENDPOINT = "https://image.pollinations.ai/prompt/{prompt}"
MODELS = ("flux", "turbo")
STYLE_SUFFIX = ", ultra detailed wallpaper, cinematic lighting, sharp focus, no text, no watermark, no logo"
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_PROMPT_CHARS = 800
CROP_RATIO = 0.08
USER_COOLDOWN_SECONDS = 4.0
FREE_TIER_INTERVAL = 0.0 if POLLINATIONS_TOKEN else 45.0
COMMAND_PREFIXES = ("n!", "!", "?", ".", "/", "&", "$", "-")

PHONE_WORDS = ("phone", "mobile", "portrait", "vertical", "android", "iphone", "tall")
SQUARE_WORDS = ("square", "1:1")
ULTRAWIDE_WORDS = ("ultrawide", "ultra wide", "ultra-wide", "banner")

SIZE_TOKENS = {
    "8k": (3840, 2160),
    "4k": (3840, 2160),
    "2160p": (3840, 2160),
    "2k": (2560, 1440),
    "1440p": (2560, 1440),
    "hd": (1920, 1080),
    "1080p": (1920, 1080),
    "fullhd": (1920, 1080),
}


def parse_size(prompt: str) -> Tuple[int, int, str]:
    """Resolve target dimensions from the prompt. Returns (width, height, label)."""
    lowered = prompt.lower()
    wide, tall = 1920, 1080

    for token, dims in SIZE_TOKENS.items():
        if re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", lowered):
            wide, tall = dims
            break

    if any(w in lowered for w in ULTRAWIDE_WORDS):
        wide, tall = (3840, 1600) if wide >= 3840 else (2560, 1080)
        return wide, tall, "ultrawide"

    if any(w in lowered for w in SQUARE_WORDS):
        side = 2160 if wide >= 3840 else 1440 if wide >= 2560 else 1080
        return side, side, "square"

    if any(w in lowered for w in PHONE_WORDS):
        wide, tall = (2160, 3840) if wide >= 3840 else (1440, 2560) if wide >= 2560 else (1080, 1920)
        return wide, tall, "phone"

    return wide, tall, "desktop"


def slugify(text: str, limit: int = 40) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return (slug or "wallpaper")[:limit]


def _post_process(data: bytes, width: int, height: int) -> bytes:
    """Crop the generator's corner mark, fit to target size, compress under limit."""
    from PIL import Image

    img = Image.open(io.BytesIO(data))
    img = img.convert("RGB")

    w, h = img.size
    extra = h - int(round(w * height / width))
    if extra > 0:
        img = img.crop((0, 0, w, h - extra))

    if img.size != (width, height):
        img = img.resize((width, height), Image.LANCZOS)

    quality = 92
    while True:
        buffer = io.BytesIO()
        img.save(buffer, "JPEG", quality=quality, optimize=True, progressive=True)
        blob = buffer.getvalue()
        if len(blob) <= MAX_FILE_BYTES or quality <= 60:
            break
        quality -= 8

    if len(blob) > MAX_FILE_BYTES:
        w, h = img.size
        img = img.resize((int(w * 0.75), int(h * 0.75)), Image.LANCZOS)
        buffer = io.BytesIO()
        img.save(buffer, "JPEG", quality=85, optimize=True, progressive=True)
        blob = buffer.getvalue()

    return blob


class Wallpaper(commands.Cog):
    """Channel-bound AI wallpaper generation."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._channels: Set[int] = set()
        self._locks: Dict[int, asyncio.Lock] = {}
        self._user_cooldowns: Dict[Tuple[int, int], float] = {}
        self._semaphore = asyncio.Semaphore(3)
        self._pace_lock = asyncio.Lock()
        self._next_request_at = 0.0

    async def cog_load(self):
        try:
            rows = await db.fetchall("SELECT channel_id FROM wallpaper_channels")
            self._channels = {row["channel_id"] for row in rows}
            logger.info(f"Loaded {len(self._channels)} wallpaper studio channel(s).")
        except Exception as exc:
            logger.error(f"Failed to load wallpaper channels: {exc}", exc_info=True)

    async def add_channel(self, guild: discord.Guild, channel: discord.TextChannel, actor) -> Tuple[bool, str]:
        """Register a channel as a wallpaper studio. Returns (success, message)."""
        me = guild.me
        perms = channel.permissions_for(me) if me else None
        if not perms or not (perms.send_messages and perms.attach_files and perms.embed_links):
            return False, f"I need `Send Messages`, `Attach Files` and `Embed Links` in {channel.mention}."

        await db.execute(
            "INSERT INTO wallpaper_channels (guild_id, channel_id, created_by) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, channel_id) DO NOTHING",
            (guild.id, channel.id, actor.id if actor else 0),
        )
        self._channels.add(channel.id)

        panel = primary_embed(
            "🖼️ AI Wallpaper Studio",
            "Type anything below and I will paint it as a wallpaper.\n\n"
            "**Examples**\n"
            "• `natural scenery 4k`\n"
            "• `cyberpunk city rain phone wallpaper`\n"
            "• `minimal dark abstract ultrawide`\n\n"
            "**Size keywords:** `4k` · `2k` · `1080p` · `phone` · `square` · `ultrawide`\n"
            f"Default is desktop `1920×1080`. One image at a time"
            + (f", roughly every {int(FREE_TIER_INTERVAL)}s while on the free tier." if FREE_TIER_INTERVAL else "."),
        )
        panel.set_footer(text="NOVEXA • Wallpaper Studio")
        try:
            await channel.send(embed=panel)
        except discord.HTTPException:
            pass
        return True, f"{channel.mention} is now a wallpaper channel."

    async def remove_channel(self, guild_id: int, channel_id: int) -> str:
        await db.execute(
            "DELETE FROM wallpaper_channels WHERE guild_id = ? AND channel_id = ?",
            (guild_id, channel_id),
        )
        self._channels.discard(channel_id)
        return "Channel released. It will not generate wallpapers anymore."

    # ---------------- generation ----------------
    async def _reserve_slot(self) -> float:
        """Hold the process-wide generator slot; returns how long the caller waited."""
        if FREE_TIER_INTERVAL <= 0:
            return 0.0
        async with self._pace_lock:
            wait = self._next_request_at - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            self._next_request_at = time.monotonic() + FREE_TIER_INTERVAL
            return max(wait, 0.0)

    def _push_slot(self, delay: float) -> None:
        self._next_request_at = max(self._next_request_at, time.monotonic() + delay)

    async def _request_image(self, prompt: str, width: int, height: int) -> Tuple[bytes, str]:
        import aiohttp

        seed = random.randint(1, 2_147_483_646)
        url = API_ENDPOINT.format(prompt=quote(prompt, safe=""))
        params = {
            "width": str(width),
            "height": str(height),
            "nologo": "true",
            "seed": str(seed),
            "enhance": "false",
        }
        if POLLINATIONS_TOKEN:
            params["token"] = POLLINATIONS_TOKEN

        timeout = aiohttp.ClientTimeout(total=180)
        last_error = "unknown error"

        for _ in range(2):
            for model in MODELS:
                await self._reserve_slot()
                try:
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.get(url, params={**params, "model": model}) as resp:
                            if resp.status == 402:
                                body = await resp.text()
                                match = re.search(r"Retry after (\d+)s", body)
                                delay = min(int(match.group(1)) + 3 if match else 25, 70)
                                self._push_slot(delay)
                                last_error = f"generator busy — retry in {delay}s"
                                continue
                            if resp.status != 200:
                                last_error = f"HTTP {resp.status}"
                                continue
                            data = await resp.read()
                    if len(data) < 4096:
                        last_error = "empty image returned"
                        continue
                    return data, model
                except asyncio.TimeoutError:
                    last_error = "generation timed out"
                except Exception as exc:
                    last_error = str(exc)
                    logger.warning(f"Wallpaper model '{model}' failed: {exc}")

        raise RuntimeError(last_error)

    async def generate(self, prompt: str) -> Tuple[bytes, str, int, int]:
        width, height, _ = parse_size(prompt)
        full_prompt = f"{prompt}{STYLE_SUFFIX}"[:MAX_PROMPT_CHARS]
        render_height = int(round(height * (1 + CROP_RATIO)))
        raw, model = await self._request_image(full_prompt, width, render_height)
        async with self._semaphore:
            blob = await asyncio.to_thread(_post_process, raw, width, height)
        return blob, model, width, height

    # ---------------- slash commands ----------------
    wallpaper_group = app_commands.Group(
        name="wallpaper",
        description="AI wallpaper studio — turn a channel into a prompt-to-image generator",
    )

    @wallpaper_group.command(name="setup", description="Turn a channel into an AI wallpaper studio")
    @has_admin_or_owner()
    @app_commands.describe(channel="Channel to convert (defaults to the current channel)")
    async def slash_setup(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            return await interaction.response.send_message(
                embed=error_embed("Invalid Channel", "Pick a text channel."), ephemeral=True
            )

        ok, message = await self.add_channel(interaction.guild, target, interaction.user)
        if not ok:
            return await interaction.response.send_message(
                embed=error_embed("Missing Permissions", message), ephemeral=True
            )

        await interaction.response.send_message(
            embed=success_embed(
                "Wallpaper Studio Ready",
                f"{target.mention} is now a wallpaper channel. Every message there becomes a prompt.",
            ),
            ephemeral=True,
        )

    @wallpaper_group.command(name="remove", description="Stop a channel from generating wallpapers")
    @has_admin_or_owner()
    @app_commands.describe(channel="Channel to release (defaults to the current channel)")
    async def slash_remove(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            return await interaction.response.send_message(
                embed=error_embed("Invalid Channel", "Pick a text channel."), ephemeral=True
            )

        await db.execute(
            "DELETE FROM wallpaper_channels WHERE guild_id = ? AND channel_id = ?",
            (interaction.guild_id, target.id),
        )
        self._channels.discard(target.id)

        await interaction.response.send_message(
            embed=warning_embed("Wallpaper Studio Disabled", f"{target.mention} is a normal channel again."),
            ephemeral=True,
        )

    @wallpaper_group.command(name="list", description="List every wallpaper channel in this server")
    @has_admin_or_owner()
    async def slash_list(self, interaction: discord.Interaction):
        rows = await db.fetchall(
            "SELECT channel_id, created_at FROM wallpaper_channels WHERE guild_id = ?",
            (interaction.guild_id,),
        )
        if not rows:
            return await interaction.response.send_message(
                embed=info_embed("No Studios", "No wallpaper channels yet. Run `/wallpaper setup` in a channel."),
                ephemeral=True,
            )

        lines: List[str] = []
        for row in rows:
            channel = interaction.guild.get_channel(row["channel_id"])
            name = channel.mention if channel else f"`deleted {row['channel_id']}`"
            lines.append(f"• {name}")

        embed = primary_embed(f"🖼️ Wallpaper Channels ({len(rows)})", "\n".join(lines))
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ---------------- prefix mirror ----------------
    @commands.group(name="wallpaper", aliases=["wp"], invoke_without_command=True)
    async def prefix_wallpaper(self, ctx: commands.Context):
        await ctx.send(
            embed=info_embed(
                "Wallpaper Studio",
                "• `n!wallpaper setup [channel]` — convert a channel\n"
                "• `n!wallpaper remove [channel]` — release a channel\n"
                "• `n!wallpaper list` — show active studios",
            )
        )

    @prefix_wallpaper.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def prefix_setup(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        target = channel or ctx.channel
        ok, message = await self.add_channel(ctx.guild, target, ctx.author)
        await ctx.send(f"🖼️ {message}" if ok else f"❌ {message}")

    @prefix_wallpaper.command(name="remove", aliases=["off"])
    @commands.has_permissions(administrator=True)
    async def prefix_remove(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        target = channel or ctx.channel
        await db.execute(
            "DELETE FROM wallpaper_channels WHERE guild_id = ? AND channel_id = ?",
            (ctx.guild.id, target.id),
        )
        self._channels.discard(target.id)
        await ctx.send(f"🖼️ {target.mention} released. It will not generate wallpapers anymore.")

    @prefix_wallpaper.command(name="list")
    async def prefix_list(self, ctx: commands.Context):
        rows = await db.fetchall(
            "SELECT channel_id FROM wallpaper_channels WHERE guild_id = ?", (ctx.guild.id,)
        )
        if not rows:
            return await ctx.send("🖼️ No wallpaper channels configured.")
        names = []
        for row in rows:
            channel = ctx.guild.get_channel(row["channel_id"])
            names.append(channel.mention if channel else f"`{row['channel_id']}`")
        await ctx.send("🖼️ **Wallpaper channels:**\n" + "\n".join(names))

    # ---------------- listener ----------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        if message.channel.id not in self._channels:
            return

        prompt = message.content.strip()
        if not prompt:
            return
        if prompt.startswith(COMMAND_PREFIXES):
            return
        if not message.channel.permissions_for(message.guild.me).attach_files:
            return

        now = time.monotonic()
        key = (message.channel.id, message.author.id)
        if now - self._user_cooldowns.get(key, 0.0) < USER_COOLDOWN_SECONDS:
            return
        self._user_cooldowns[key] = now

        lock = self._locks.setdefault(message.channel.id, asyncio.Lock())
        if lock.locked():
            return await message.reply(
                "⏳ Still painting the last one here — one at a time.", mention_author=False
            )

        async with lock:
            prompt = prompt[:MAX_PROMPT_CHARS]
            try:
                await message.add_reaction("🖼️")
            except discord.HTTPException:
                pass

            if FREE_TIER_INTERVAL > 0:
                pending = self._next_request_at - time.monotonic()
                if pending > 3:
                    await message.reply(
                        f"⏳ Generator is cooling down — your wallpaper starts in ~{int(pending)}s.",
                        mention_author=False,
                    )

            try:
                async with message.channel.typing():
                    blob, model, width, height = await self.generate(prompt)
            except Exception as exc:
                logger.error(f"Wallpaper generation failed for '{prompt}': {exc}")
                return await message.reply(
                    embed=error_embed(
                        "Generation Failed",
                        f"Could not paint that one: `{exc}`\nTry a shorter prompt or a different subject.",
                    ),
                    mention_author=False,
                )

            embed = primary_embed(
                f"🖼️ {width}×{height}",
                f"**Prompt:** {prompt[:300]}",
            )
            embed.set_image(url=f"attachment://wallpaper-{slugify(prompt)}.jpg")
            embed.set_footer(text=f"NOVEXA • {model} • requested by {message.author.display_name}")

            file = discord.File(
                fp=io.BytesIO(blob),
                filename=f"wallpaper-{slugify(prompt)}.jpg",
                description=f"Wallpaper generated from: {prompt[:100]}",
            )
            try:
                await message.reply(embed=embed, file=file, mention_author=False)
            except discord.HTTPException as exc:
                logger.warning(f"Wallpaper delivery failed: {exc}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Wallpaper(bot))
