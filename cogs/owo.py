"""NOVEXA - OwO Interactive Gaming Suite & Dedicated Channels.

Provides:
- Dedicated OwO gaming channel setup (/owo setup, /owo remove, /owo panel, /owo list, n!owosetup)
- Persistent Interactive OwO Control Panel with 15 persistent action buttons
- Prefix-free chat trigger listener in designated OwO channels:
  Members can type 'b', 'battle', 'h', 'hunt', 'c', 'cash', 'bal', 'check', 'p', 'profile',
  'bio', 'setbio', 'd', 'daily', 'w', 'work', 'crime', 'slut', 'z', 'zoo', 's <amt>',
  'cf <amt>', 'inv', 'crate', 'pets', 'marry @user', 'divorce', 'rep @user', 'pay @user <amt>',
  'dep <amt>', 'with <amt>', 'shop', 'buy <item>', 'equip <item>', 'help', 'owo', 'uwu'
  plus 'g <bet>', 'dice <bet> [1-6]', 'weekly', 'monthly', 'rich', 'sell <animal> [n]',
  'fav <animal>', 'ach', 'adopt <pet>', 'feed <pet>', 'unequip <slot>', 'rob @user'
  without ANY slash commands or command prefix!
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
import random
import time
import asyncio
from typing import Optional, List, Dict, Any, Tuple

from database.database import db
from config import BOT_NAME, BOT_PREFIX
from services.economy_service import (
    economy_service,
    CURRENCY_NAME,
    CURRENCY_SYMBOL,
    GEM_NAME,
    GEM_SYMBOL,
)
from utils.economy_checks import (
    format_remaining,
    economy_embed,
    COLOR_ECO_PRIMARY,
    COLOR_ECO_GOLD,
    COLOR_ECO_SUCCESS,
    COLOR_ECO_ERROR,
    COLOR_ECO_INFO,
)

logger = logging.getLogger("novexa.owo")

# Theme colors
COLOR_OWO_PINK = 0xFF69B4
COLOR_OWO_PURPLE = 0x9B59B6
COLOR_OWO_CYAN = 0x1ABC9C

# Rarity colors for hunting and loot
RARITY_COLORS = {
    "Common": 0x95A5A6,
    "Uncommon": 0x2ECC71,
    "Rare": 0x3498DB,
    "Epic": 0x9B59B6,
    "Legendary": 0xF1C40F,
    "Mythical": 0xE74C3C,
}

# Dungeon Monsters for solo combat
DUNGEON_MONSTERS = [
    {
        "name": "Emerald Forest Slime",
        "emoji": "🟢",
        "min_level": 0,
        "hp": 75,
        "attack": 14,
        "defense": 3,
        "coins_reward": (80, 160),
        "xp_reward": 35,
        "dialogue": "A gelatinous slime bubbles and squishes threateningly!",
    },
    {
        "name": "Bloodfang Wolf Pack",
        "emoji": "🐺",
        "min_level": 2,
        "hp": 115,
        "attack": 22,
        "defense": 6,
        "coins_reward": (140, 280),
        "xp_reward": 60,
        "dialogue": "Feral red eyes emerge from the thick shadows with bared fangs!",
    },
    {
        "name": "Goblin Berserker Chief",
        "emoji": "👺",
        "min_level": 4,
        "hp": 165,
        "attack": 33,
        "defense": 10,
        "coins_reward": (240, 480),
        "xp_reward": 95,
        "dialogue": "A savage goblin war chief roars and swings a heavy spiked mace!",
    },
    {
        "name": "Undead Skeleton Knight",
        "emoji": "💀",
        "min_level": 7,
        "hp": 240,
        "attack": 48,
        "defense": 16,
        "coins_reward": (400, 750),
        "xp_reward": 145,
        "dialogue": "An ancient armored skeleton brandishes a cursed, chilling broadsword!",
    },
    {
        "name": "Infernal Magma Fiend",
        "emoji": "👹",
        "min_level": 10,
        "hp": 340,
        "attack": 66,
        "defense": 24,
        "coins_reward": (700, 1250),
        "xp_reward": 230,
        "dialogue": "Molten lava and brimstone burst into flames around a terrifying demon!",
    },
    {
        "name": "Abyssal Void Dragon Boss",
        "emoji": "🐉",
        "min_level": 15,
        "hp": 500,
        "attack": 92,
        "defense": 35,
        "coins_reward": (1400, 2800),
        "xp_reward": 450,
        "dialogue": "The ground shatters as an Abyssal Dragon swoops down breathing void fire!",
    },
]

# Cute OwO phrases
OWO_CUTE_RESPONSES = [
    "(✿◡‿◡) nyaa~ what's this? OwO",
    "(・`ω´・) rawr! You called for OwO?",
    "UwU *notices you* Hello master!",
    "ฅ^•ﻌ•^ฅ nya! Let's play games together!",
    "(◕‿◕✿) OwO is always happy to see you!",
    "🌸 (ﾉ◕ヮ◕)ﾉ*:･ﾟ✧ Have some OwO sparkles!",
]


async def send_response(
    target: Any,
    embed: Optional[discord.Embed] = None,
    content: Optional[str] = None,
    view: Optional[discord.ui.View] = None,
    ephemeral: bool = False,
):
    """Universal dispatcher for interaction and message replies."""
    try:
        kwargs: Dict[str, Any] = {}
        if content is not None:
            kwargs["content"] = content
        if embed is not None:
            kwargs["embed"] = embed
        if view is not None:
            kwargs["view"] = view

        if isinstance(target, discord.Interaction):
            if ephemeral:
                kwargs["ephemeral"] = True
            if not target.response.is_done():
                await target.response.send_message(**kwargs)
            else:
                await target.followup.send(**kwargs)
        elif isinstance(target, discord.Message):
            kwargs["mention_author"] = False
            await target.reply(**kwargs)
        elif isinstance(target, commands.Context):
            await target.send(**kwargs)
    except Exception as e:
        logger.warning(f"Error sending response: {e}", exc_info=True)


class OwOPanelView(discord.ui.View):
    """Persistent Interactive Control Panel for OwO Gaming Suite."""

    def __init__(self):
        super().__init__(timeout=None)

    # ---------------- ROW 0: COMBAT & HUNTING ----------------
    @discord.ui.button(
        label="⚔️ Battle",
        style=discord.ButtonStyle.danger,
        custom_id="owo_btn_battle",
        row=0,
    )
    async def btn_battle(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("OwO")
        if cog:
            await cog.handle_battle(interaction, interaction.user)
        else:
            await interaction.response.send_message("❌ OwO system is temporarily loading...", ephemeral=True)

    @discord.ui.button(
        label="🏹 Hunt",
        style=discord.ButtonStyle.success,
        custom_id="owo_btn_hunt",
        row=0,
    )
    async def btn_hunt(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("OwO")
        if cog:
            await cog.handle_hunt(interaction, interaction.user)
        else:
            await interaction.response.send_message("❌ OwO system is temporarily loading...", ephemeral=True)

    @discord.ui.button(
        label="🐾 Zoo",
        style=discord.ButtonStyle.secondary,
        custom_id="owo_btn_zoo",
        row=0,
    )
    async def btn_zoo(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("OwO")
        if cog:
            await cog.handle_zoo(interaction, interaction.user)
        else:
            await interaction.response.send_message("❌ OwO system is temporarily loading...", ephemeral=True)

    @discord.ui.button(
        label="🎒 Inventory",
        style=discord.ButtonStyle.secondary,
        custom_id="owo_btn_inv",
        row=0,
    )
    async def btn_inv(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("OwO")
        if cog:
            await cog.handle_inventory(interaction, interaction.user)
        else:
            await interaction.response.send_message("❌ OwO system is temporarily loading...", ephemeral=True)

    @discord.ui.button(
        label="📦 Open Crate",
        style=discord.ButtonStyle.secondary,
        custom_id="owo_btn_crate",
        row=0,
    )
    async def btn_crate(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("OwO")
        if cog:
            await cog.handle_crate(interaction, interaction.user)
        else:
            await interaction.response.send_message("❌ OwO system is temporarily loading...", ephemeral=True)

    # ---------------- ROW 1: ECONOMY & CASINO ----------------
    @discord.ui.button(
        label="💰 Check Cash",
        style=discord.ButtonStyle.success,
        custom_id="owo_btn_cash",
        row=1,
    )
    async def btn_cash(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("OwO")
        if cog:
            await cog.handle_cash(interaction, interaction.user)
        else:
            await interaction.response.send_message("❌ OwO system is temporarily loading...", ephemeral=True)

    @discord.ui.button(
        label="🎁 Claim Daily",
        style=discord.ButtonStyle.primary,
        custom_id="owo_btn_daily",
        row=1,
    )
    async def btn_daily(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("OwO")
        if cog:
            await cog.handle_daily(interaction, interaction.user)
        else:
            await interaction.response.send_message("❌ OwO system is temporarily loading...", ephemeral=True)

    @discord.ui.button(
        label="🛠️ Work",
        style=discord.ButtonStyle.secondary,
        custom_id="owo_btn_work",
        row=1,
    )
    async def btn_work(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("OwO")
        if cog:
            await cog.handle_work(interaction, interaction.user)
        else:
            await interaction.response.send_message("❌ OwO system is temporarily loading...", ephemeral=True)

    @discord.ui.button(
        label="🎰 Slots (50)",
        style=discord.ButtonStyle.secondary,
        custom_id="owo_btn_slots",
        row=1,
    )
    async def btn_slots(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("OwO")
        if cog:
            await cog.handle_slots(interaction, interaction.user, bet=50)
        else:
            await interaction.response.send_message("❌ OwO system is temporarily loading...", ephemeral=True)

    @discord.ui.button(
        label="🪙 Coinflip (50)",
        style=discord.ButtonStyle.secondary,
        custom_id="owo_btn_cf",
        row=1,
    )
    async def btn_cf(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("OwO")
        if cog:
            await cog.handle_coinflip(interaction, interaction.user, choice="heads", bet=50)
        else:
            await interaction.response.send_message("❌ OwO system is temporarily loading...", ephemeral=True)

    # ---------------- ROW 2: PROFILE & SOCIAL ----------------
    @discord.ui.button(
        label="👤 Bio / Profile",
        style=discord.ButtonStyle.primary,
        custom_id="owo_btn_bio",
        row=2,
    )
    async def btn_bio(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("OwO")
        if cog:
            await cog.handle_profile(interaction, interaction.user)
        else:
            await interaction.response.send_message("❌ OwO system is temporarily loading...", ephemeral=True)

    @discord.ui.button(
        label="💍 Marriage",
        style=discord.ButtonStyle.secondary,
        custom_id="owo_btn_marry",
        row=2,
    )
    async def btn_marry(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("OwO")
        if cog:
            await cog.handle_marry_status(interaction, interaction.user)
        else:
            await interaction.response.send_message("❌ OwO system is temporarily loading...", ephemeral=True)

    @discord.ui.button(
        label="🐕 Pets",
        style=discord.ButtonStyle.secondary,
        custom_id="owo_btn_pets",
        row=2,
    )
    async def btn_pets(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("OwO")
        if cog:
            await cog.handle_pets(interaction, interaction.user)
        else:
            await interaction.response.send_message("❌ OwO system is temporarily loading...", ephemeral=True)

    @discord.ui.button(
        label="🛒 Shop",
        style=discord.ButtonStyle.secondary,
        custom_id="owo_btn_shop",
        row=2,
    )
    async def btn_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("OwO")
        if cog:
            await cog.handle_shop(interaction, interaction.user)
        else:
            await interaction.response.send_message("❌ OwO system is temporarily loading...", ephemeral=True)

    @discord.ui.button(
        label="📖 OwO Guide",
        style=discord.ButtonStyle.secondary,
        custom_id="owo_btn_help",
        row=2,
    )
    async def btn_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("OwO")
        if cog:
            await cog.handle_help(interaction)
        else:
            await interaction.response.send_message("❌ OwO system is temporarily loading...", ephemeral=True)

    # ---------------- ROW 3: CASINO & PROGRESSION ----------------
    @discord.ui.button(
        label="🎲 Gamble (100)",
        style=discord.ButtonStyle.secondary,
        custom_id="owo_btn_gamble",
        row=3,
    )
    async def btn_gamble(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("OwO")
        if cog:
            await cog.handle_gamble(interaction, interaction.user, bet=100)
        else:
            await interaction.response.send_message("❌ OwO system is temporarily loading...", ephemeral=True)

    @discord.ui.button(
        label="🎰 Dice (100)",
        style=discord.ButtonStyle.secondary,
        custom_id="owo_btn_dice",
        row=3,
    )
    async def btn_dice(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("OwO")
        if cog:
            await cog.handle_dice(interaction, interaction.user, bet=100)
        else:
            await interaction.response.send_message("❌ OwO system is temporarily loading...", ephemeral=True)

    @discord.ui.button(
        label="🏆 Top 10",
        style=discord.ButtonStyle.primary,
        custom_id="owo_btn_top",
        row=3,
    )
    async def btn_top(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("OwO")
        if cog:
            await cog.handle_leaderboard(interaction, interaction.user)
        else:
            await interaction.response.send_message("❌ OwO system is temporarily loading...", ephemeral=True)

    @discord.ui.button(
        label="🎖️ Achievements",
        style=discord.ButtonStyle.secondary,
        custom_id="owo_btn_ach",
        row=3,
    )
    async def btn_ach(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("OwO")
        if cog:
            await cog.handle_achievements(interaction, interaction.user)
        else:
            await interaction.response.send_message("❌ OwO system is temporarily loading...", ephemeral=True)

    @discord.ui.button(
        label="📅 Weekly",
        style=discord.ButtonStyle.success,
        custom_id="owo_btn_weekly",
        row=3,
    )
    async def btn_weekly(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("OwO")
        if cog:
            await cog.handle_weekly(interaction, interaction.user)
        else:
            await interaction.response.send_message("❌ OwO system is temporarily loading...", ephemeral=True)


class OwO(commands.Cog):
    """OwO Interactive Gaming Suite with Prefix-Free Channel Trigger Support."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._owo_channels: set[int] = set()
        self._trigger_cooldowns: Dict[int, float] = {}

    _TRIGGER_COOLDOWN = 1.0

    def _trigger_allowed(self, user_id: int) -> bool:
        """Per-user throttle so one member cannot flood the channel."""
        now = time.monotonic()
        last = self._trigger_cooldowns.get(user_id)
        if last is not None and now - last < self._TRIGGER_COOLDOWN:
            return False
        self._trigger_cooldowns[user_id] = now
        return True

    async def cog_load(self):
        """Preload all active OwO channels into memory cache for zero-latency lookups."""
        try:
            rows = await db.fetchall("SELECT channel_id FROM owo_channels;")
            self._owo_channels = {row["channel_id"] for row in rows}
            logger.info(f"Loaded {len(self._owo_channels)} OwO gaming channels into memory cache.")
        except Exception as e:
            logger.error(f"Error loading OwO channels cache: {e}")

    # ==================== SLASH COMMAND GROUP ====================
    owo_group = app_commands.Group(
        name="owo",
        description="OwO Gaming Suite & Dedicated Interactive Channels",
    )

    @owo_group.command(
        name="setup",
        description="Designate an OwO interactive gaming channel with control panel",
    )
    @app_commands.describe(channel="Text channel to configure for prefix-free OwO gaming (defaults to current)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def slash_owo_setup(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
    ):
        target_chan = channel or interaction.channel
        if not isinstance(target_chan, discord.TextChannel):
            return await interaction.response.send_message(
                "❌ Please specify a standard text channel.", ephemeral=True
            )

        await interaction.response.defer(ephemeral=False)
        await self._setup_channel(target_chan, interaction.guild_id, interaction)

    @owo_group.command(
        name="remove",
        description="Disable OwO gaming mode for a channel",
    )
    @app_commands.describe(channel="Channel to remove from OwO mode (defaults to current)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def slash_owo_remove(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
    ):
        target_chan = channel or interaction.channel
        await db.execute(
            "DELETE FROM owo_channels WHERE guild_id = ? AND channel_id = ?",
            (interaction.guild_id, target_chan.id),
        )
        self._owo_channels.discard(target_chan.id)

        embed = discord.Embed(
            title="🗑️ OwO Mode Disabled",
            description=f"OwO gaming mode and prefix-free triggers have been removed from {target_chan.mention}.",
            color=COLOR_ECO_ERROR,
        )
        await interaction.response.send_message(embed=embed)

    @owo_group.command(
        name="panel",
        description="Send or refresh the OwO Interactive Button Panel in this channel",
    )
    @app_commands.describe(channel="Channel to send the OwO Panel into (defaults to current)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def slash_owo_panel(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
    ):
        target_chan = channel or interaction.channel
        if not isinstance(target_chan, discord.TextChannel):
            return await interaction.response.send_message("❌ Invalid text channel.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        panel_embed = self._build_panel_embed(interaction.guild.name)
        view = OwOPanelView()
        msg = await target_chan.send(embed=panel_embed, view=view)

        # Update DB message ID
        await db.execute(
            "INSERT INTO owo_channels (guild_id, channel_id, panel_message_id) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, channel_id) DO UPDATE SET panel_message_id = excluded.panel_message_id",
            (interaction.guild_id, target_chan.id, msg.id),
        )
        self._owo_channels.add(target_chan.id)

        await interaction.followup.send(
            f"✅ OwO Interactive Panel has been deployed into {target_chan.mention}!",
            ephemeral=True,
        )

    @owo_group.command(
        name="list",
        description="List all channels configured for OwO gaming in this server",
    )
    async def slash_owo_list(self, interaction: discord.Interaction):
        rows = await db.fetchall(
            "SELECT channel_id, created_at FROM owo_channels WHERE guild_id = ?",
            (interaction.guild_id,),
        )
        if not rows:
            return await interaction.response.send_message(
                "ℹ️ No OwO gaming channels are currently configured in this server. Use `/owo setup` to activate one!",
                ephemeral=True,
            )

        chan_lines = []
        for r in rows:
            ch = interaction.guild.get_channel(r["channel_id"])
            if ch:
                chan_lines.append(f"• {ch.mention} (`{ch.id}`)")
            else:
                chan_lines.append(f"• `#deleted-channel` (`{r['channel_id']}`)")

        embed = discord.Embed(
            title="🌸 Active OwO Gaming Channels",
            description="\n".join(chan_lines),
            color=COLOR_OWO_PINK,
        )
        embed.set_footer(text=f"Total: {len(rows)} channel(s) • Prefix-free chat enabled")
        await interaction.response.send_message(embed=embed)

    # ==================== PREFIX COMMANDS ====================
    @commands.command(name="owosetup", aliases=["owo-setup", "setowo"])
    @commands.has_permissions(manage_guild=True)
    async def prefix_owo_setup(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        """Set up an OwO gaming channel with interactive control panel."""
        target_chan = channel or ctx.channel
        await self._setup_channel(target_chan, ctx.guild.id, ctx)

    @commands.command(name="owopanel")
    @commands.has_permissions(manage_guild=True)
    async def prefix_owo_panel(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        """Send the interactive OwO Control Panel."""
        target_chan = channel or ctx.channel
        panel_embed = self._build_panel_embed(ctx.guild.name)
        view = OwOPanelView()
        msg = await target_chan.send(embed=panel_embed, view=view)

        await db.execute(
            "INSERT INTO owo_channels (guild_id, channel_id, panel_message_id) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, channel_id) DO UPDATE SET panel_message_id = excluded.panel_message_id",
            (ctx.guild.id, target_chan.id, msg.id),
        )
        self._owo_channels.add(target_chan.id)
        await ctx.send(f"✅ OwO Interactive Panel deployed to {target_chan.mention}!")

    @commands.command(name="oworemove")
    @commands.has_permissions(manage_guild=True)
    async def prefix_owo_remove(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        """Remove OwO mode from a channel."""
        target_chan = channel or ctx.channel
        await db.execute(
            "DELETE FROM owo_channels WHERE guild_id = ? AND channel_id = ?",
            (ctx.guild.id, target_chan.id),
        )
        self._owo_channels.discard(target_chan.id)
        await ctx.send(f"🗑️ Removed OwO mode from {target_chan.mention}.")

    async def _setup_channel(self, target_chan: discord.TextChannel, guild_id: int, responder: Any):
        """Core setup logic shared by slash and prefix commands."""
        panel_embed = self._build_panel_embed(target_chan.guild.name)
        view = OwOPanelView()
        msg = await target_chan.send(embed=panel_embed, view=view)

        # Pin message if bot has permission
        try:
            await msg.pin(reason="NOVEXA OwO Interactive Panel")
        except Exception:
            pass

        # Save to database
        await db.execute(
            "INSERT INTO owo_channels (guild_id, channel_id, panel_message_id) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, channel_id) DO UPDATE SET panel_message_id = excluded.panel_message_id",
            (guild_id, target_chan.id, msg.id),
        )
        self._owo_channels.add(target_chan.id)

        success_msg = (
            f"🎉 **OwO Gaming Zone Successfully Configured in {target_chan.mention}!**\n\n"
            f"• **Interactive Button Panel:** Pinned & persistent across bot restarts.\n"
            f"• **Prefix-Free Chat Mode:** All members can now type simple shortcuts like `b`, `h`, `check`, `bio`, `daily`, `zoo`, `work`, `slots`, etc. directly without any `/` or `{BOT_PREFIX}` prefix!"
        )

        if isinstance(responder, discord.Interaction):
            await responder.followup.send(success_msg)
        else:
            await responder.send(success_msg)

    def _build_panel_embed(self, server_name: str) -> discord.Embed:
        """Construct the rich OwO Control Panel embed."""
        embed = discord.Embed(
            title="🌸 NOVEXA OwO GAMING ARENA 🌸",
            description=(
                f"Welcome to the official OwO Interactive Arena for **{server_name}**!\n\n"
                f"✨ In this channel, you can enjoy all games **without any command prefix** (`/` or `n!`).\n"
                f"Simply **click the buttons below**, or type short triggers directly in chat!"
            ),
            color=COLOR_OWO_PINK,
        )

        embed.add_field(
            name="⚔️ Combat, Hunting & Safari",
            value=(
                "• `b` or `battle` — Battle Dungeon Bosses or Duel a friend (`b @user [bet]`)\n"
                "• `h` or `hunt` — Hunt exotic wildlife for your Zoo\n"
                "• `z` or `zoo` — Inspect your animal collection (`z @user`)\n"
                "• `inv` or `inventory` — View combat gear & weapons\n"
                "• `crate` or `opencrate` — Open mystery loot crates"
            ),
            inline=False,
        )

        embed.add_field(
            name="💰 Economy, Daily & Casino",
            value=(
                "• `c` or `cash` or `check` or `bal` — Check wallet, bank & gems\n"
                "• `d` or `daily` — Claim daily coins & streak reward\n"
                "• `w` or `work` — Work an hourly job for coins\n"
                "• `crime` / `slut` — High-risk street hustle\n"
                "• `s <amount>` — Spin the 3-reel slot machine (e.g. `s 100`)\n"
                "• `cf <amount> [h/t]` — Flip a coin to double your bet (e.g. `cf 250 heads`)"
            ),
            inline=False,
        )

        embed.add_field(
            name="👤 Profile, Social & Banking",
            value=(
                "• `p` or `profile` or `bio` — View custom graphic profile card (`p @user`)\n"
                "• `setbio <text>` — Update your custom bio\n"
                "• `rep @user` — Give daily reputation\n"
                "• `marry @user` / `divorce` — Marriage and relationships\n"
                "• `pets` — View and manage pet companions\n"
                "• `pay @user <amt>` — Transfer coins to another member\n"
                "• `dep <amt>` / `with <amt>` — Deposit or withdraw bank funds\n"
                "• `shop` / `buy <item>` / `equip <item>` — Armory weapons & gear\n"
                "• `owo` or `uwu` — Cute OwO expressions!"
            ),
            inline=False,
        )

        embed.set_footer(text=f"{BOT_NAME} • OwO Gaming Suite • Zero Prefix Mode Enabled")
        return embed

    # ==================== PREFIX-FREE CHAT LISTENER ====================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Prefix-free message trigger processor for designated OwO channels."""
        # 1. Ignore bots
        if message.author.bot:
            return

        # 2. Check if message is in an OwO-enabled channel (zero overhead O(1) set lookup)
        if message.channel.id not in self._owo_channels:
            return

        content = message.content.strip()
        if not content:
            return

        # Strip prefix if user typed it anyway (n! or /)
        if content.startswith(BOT_PREFIX):
            content = content[len(BOT_PREFIX):].strip()

        tokens = content.split()
        if not tokens:
            return

        cmd = tokens[0].lower()
        args = tokens[1:]

        if not self._trigger_allowed(message.author.id):
            return

        # ================= ROUTING TRIGGERS =================

        # 1. Battle (b, battle, fight)
        if cmd in ("b", "battle", "fight"):
            target_member = message.mentions[0] if message.mentions else None
            bet = 0
            for a in args:
                if a.isdigit():
                    bet = int(a)
                    break
            await self.handle_battle(message, message.author, target=target_member, bet=bet)
            return

        # 2. Hunt (h, hunt, safari)
        if cmd in ("h", "hunt", "safari"):
            await self.handle_hunt(message, message.author)
            return

        # 3. Cash / Balance / Check (c, cash, bal, balance, check, money)
        if cmd in ("c", "cash", "bal", "balance", "check", "money"):
            target_member = message.mentions[0] if message.mentions else message.author
            await self.handle_cash(message, target_member)
            return

        # 4. Profile / Bio (p, profile, bio)
        if cmd in ("p", "profile", "bio"):
            target_member = message.mentions[0] if message.mentions else message.author
            await self.handle_profile(message, message.author, target=target_member)
            return

        # 5. Set Bio (setbio)
        if cmd == "setbio":
            new_bio = " ".join(args).strip()
            if not new_bio:
                await send_response(message, content="ℹ️ Usage: `setbio <your profile bio text>`")
                return
            await self.handle_setbio(message, message.author, new_bio)
            return

        # 6. Daily (d, daily)
        if cmd in ("d", "daily"):
            await self.handle_daily(message, message.author)
            return

        # 7. Work (w, work)
        if cmd in ("w", "work"):
            await self.handle_work(message, message.author)
            return

        # 8. Crime
        if cmd == "crime":
            await self.handle_crime(message, message.author)
            return

        # 9. Slut
        if cmd == "slut":
            await self.handle_slut(message, message.author)
            return

        # 10. Zoo (z, zoo)
        if cmd in ("z", "zoo"):
            target_member = message.mentions[0] if message.mentions else message.author
            await self.handle_zoo(message, target_member)
            return

        # 11. Slots (s, slot, slots)
        if cmd in ("s", "slot", "slots"):
            bet = 50
            if args and args[0].isdigit():
                bet = int(args[0])
            await self.handle_slots(message, message.author, bet=bet)
            return

        # 12. Coinflip (cf, coinflip)
        if cmd in ("cf", "coinflip"):
            bet = 50
            choice = "heads"
            for a in args:
                if a.isdigit():
                    bet = int(a)
                elif a.lower() in ("h", "head", "heads"):
                    choice = "heads"
                elif a.lower() in ("t", "tail", "tails"):
                    choice = "tails"
            await self.handle_coinflip(message, message.author, choice=choice, bet=bet)
            return

        # 13. Inventory (inv, inventory)
        if cmd in ("inv", "inventory"):
            await self.handle_inventory(message, message.author)
            return

        # 14. Crate (crate, crates, opencrate)
        if cmd in ("crate", "crates", "opencrate"):
            await self.handle_crate(message, message.author)
            return

        # 15. Pets (pet, pets)
        if cmd in ("pet", "pets"):
            await self.handle_pets(message, message.author)
            return

        # 16. Marry (marry)
        if cmd == "marry":
            target_member = message.mentions[0] if message.mentions else None
            if not target_member:
                await send_response(message, content="ℹ️ Usage: `marry @user` to propose to someone!")
                return
            await self.handle_marry_proposal(message, message.author, target_member)
            return

        # 17. Divorce (divorce)
        if cmd == "divorce":
            await self.handle_divorce(message, message.author)
            return

        # 18. Rep (rep)
        if cmd == "rep":
            target_member = message.mentions[0] if message.mentions else None
            if not target_member:
                await send_response(message, content="ℹ️ Usage: `rep @user` to give daily reputation!")
                return
            await self.handle_rep(message, message.author, target_member)
            return

        # 19. Pay / Give (pay, give)
        if cmd in ("pay", "give"):
            target_member = message.mentions[0] if message.mentions else None
            amt = 0
            for a in args:
                if a.isdigit():
                    amt = int(a)
                    break
            if not target_member or amt <= 0:
                await send_response(message, content="ℹ️ Usage: `pay @user <amount>`")
                return
            await self.handle_pay(message, message.author, target_member, amt)
            return

        # 20. Deposit (dep, deposit)
        if cmd in ("dep", "deposit"):
            amt_str = args[0] if args else "all"
            await self.handle_deposit(message, message.author, amt_str)
            return

        # 21. Withdraw (with, withdraw)
        if cmd in ("with", "withdraw"):
            amt_str = args[0] if args else "all"
            await self.handle_withdraw(message, message.author, amt_str)
            return

        # 22. Shop (shop)
        if cmd == "shop":
            await self.handle_shop(message, message.author)
            return

        # 23. Buy (buy)
        if cmd == "buy":
            if not args:
                await send_response(message, content="ℹ️ Usage: `buy <item_id>` (e.g. `buy iron_sword`, `buy common_crate`)")
                return
            item_id = args[0].lower()
            await self.handle_buy(message, message.author, item_id)
            return

        # 24. Equip (equip)
        if cmd == "equip":
            if not args:
                await send_response(message, content="ℹ️ Usage: `equip <item_id>` (e.g. `equip iron_sword`)")
                return
            item_id = args[0].lower()
            await self.handle_equip(message, message.author, item_id)
            return

        # 25. Help (help, owohelp)
        if cmd in ("help", "owohelp"):
            await self.handle_help(message)
            return

        # 26. OwO / UwU reactions
        if cmd in ("owo", "uwu"):
            await self.handle_owo_cute(message, message.author)
            return

        # 27. Gamble roll 1-100 (g, gamble)
        if cmd in ("g", "gamble"):
            bet = 100
            for a in args:
                if a.isdigit():
                    bet = int(a)
                    break
            await self.handle_gamble(message, message.author, bet)
            return

        # 28. Dice (dice, roll)
        if cmd in ("dice", "roll"):
            bet = int(args[0]) if args and args[0].isdigit() else 100
            guess = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
            await self.handle_dice(message, message.author, bet, guess)
            return

        # 29. Weekly & monthly bonuses
        if cmd in ("weekly", "wk"):
            await self.handle_weekly(message, message.author)
            return
        if cmd in ("monthly", "mo"):
            await self.handle_monthly(message, message.author)
            return

        # 30. Server leaderboard (rich, top, lb)
        if cmd in ("rich", "top", "lb", "leaderboard"):
            await self.handle_leaderboard(message, message.author)
            return

        # 31. Sell animals (sell)
        if cmd == "sell":
            if not args:
                await send_response(message, content="ℹ️ Usage: `sell <animal name> [amount|all|duplicates]`")
                return
            animal = args[0]
            count = args[1] if len(args) > 1 else "1"
            await self.handle_sell(message, message.author, animal, count)
            return

        # 32. Favorite animal (fav)
        if cmd in ("fav", "favorite"):
            if not args:
                await send_response(message, content="ℹ️ Usage: `fav <animal name>`")
                return
            await self.handle_favorite(message, message.author, args[0])
            return

        # 33. Achievements (ach, achievements)
        if cmd in ("ach", "achievements"):
            await self.handle_achievements(message, message.author)
            return

        # 34. Pet adoption & feeding
        if cmd in ("adopt", "adoptpet"):
            if not args:
                await send_response(message, content="ℹ️ Usage: `adopt <pet_type> [nickname]` (e.g. `adopt dog Buddy`)")
                return
            nickname = " ".join(args[1:]) if len(args) > 1 else None
            await self.handle_adopt(message, message.author, args[0], nickname)
            return
        if cmd == "feed":
            if not args:
                await send_response(message, content="ℹ️ Usage: `feed <pet_type>` (e.g. `feed dog`)")
                return
            await self.handle_feed(message, message.author, args[0])
            return

        # 35. Unequip gear (unequip)
        if cmd == "unequip":
            if not args:
                await send_response(message, content="ℹ️ Usage: `unequip <slot|item_id>` (e.g. `unequip weapon`)")
                return
            await self.handle_unequip(message, message.author, args[0])
            return

        # 36. Rob a member (rob)
        if cmd == "rob":
            target_member = message.mentions[0] if message.mentions else None
            if not target_member:
                await send_response(message, content="ℹ️ Usage: `rob @user` (1 hour cooldown, 45% success)")
                return
            await self.handle_rob(message, message.author, target_member)
            return

    # ==================== CORE ACTION HANDLERS ====================

    async def handle_battle(
        self,
        responder: Any,
        user: discord.Member,
        target: Optional[discord.Member] = None,
        bet: int = 0,
    ):
        """Simulate Dungeon Monster Combat or initiate PvP duel."""
        guild_id = user.guild.id

        # 1. PvP Duel Mode
        if target:
            if target.id == user.id:
                return await send_response(responder, content=f"❌ {user.mention}, you cannot duel yourself!", ephemeral=True)
            if target.bot:
                return await send_response(responder, content=f"❌ {user.mention}, bots cannot enter the arena!", ephemeral=True)

            if bet > 0:
                u1 = await economy_service.get_or_create_user(guild_id, user.id)
                u2 = await economy_service.get_or_create_user(guild_id, target.id)
                if u1["wallet"] < bet:
                    return await send_response(responder, content=f"❌ {user.mention}, you only have **{u1['wallet']:,}** coins!", ephemeral=True)
                if u2["wallet"] < bet:
                    return await send_response(responder, content=f"❌ {target.mention} does not have enough coins for this **{bet:,}** duel bet!", ephemeral=True)

            # Import challenge view from cogs.battle if available
            try:
                from cogs.battle import BattleChallengeView
                view = BattleChallengeView(user.id, target.id, guild_id, bet=bet)
                embed = discord.Embed(
                    title="⚔️ PvP Duel Challenge!",
                    description=(
                        f"{user.mention} has challenged {target.mention} to a duel!\n"
                        f"💰 **Stakes:** {f'{bet:,} Coins' if bet > 0 else 'Honor & Glory'}\n\n"
                        f"{target.mention}, click **Accept Battle** within 60 seconds to fight!"
                    ),
                    color=COLOR_ECO_GOLD,
                )
                return await send_response(responder, embed=embed, view=view)
            except Exception:
                # Direct resolution fallback
                res = await economy_service.resolve_battle(guild_id, user.id, target.id, bet=bet)
                if not res["success"]:
                    return await send_response(responder, content=f"❌ {res['message']}")
                winner_id = res["winner_id"]
                log_txt = "\n".join(res["log"][:6])
                embed = discord.Embed(
                    title=f"🏆 Duel Victory: <@{winner_id}>!",
                    description=f"{log_txt}\n\n🎉 <@{winner_id}> emerged triumphant!",
                    color=COLOR_ECO_SUCCESS,
                )
                return await send_response(responder, embed=embed)

        # 2. Solo Dungeon Monster Battle
        stats = await economy_service.calculate_battle_stats(guild_id, user.id)
        user_lvl = stats["level"]

        # Select appropriate monster
        eligible = [m for m in DUNGEON_MONSTERS if m["min_level"] <= user_lvl]
        if not eligible:
            eligible = [DUNGEON_MONSTERS[0]]
        monster = random.choice(eligible)

        # Combat simulation
        p_hp = stats["max_hp"]
        p_atk = stats["attack"]
        p_def = stats["defense"]
        m_hp = monster["hp"]
        m_atk = monster["attack"]
        m_def = monster["defense"]

        weapon_name = stats["equipped"].get("weapon", {}).get("name", "Bare Fists")
        pet_name = stats["pet"]["name"] if stats["pet"] else "None"

        turns_log: List[str] = []
        turn = 0
        max_turns = 8

        while p_hp > 0 and m_hp > 0 and turn < max_turns:
            turn += 1
            # Player hits monster
            dmg_p = max(8, int((p_atk * random.uniform(0.85, 1.25)) - (m_def * 0.4)))
            is_crit = random.random() < 0.15
            if is_crit:
                dmg_p = int(dmg_p * 1.5)
                turns_log.append(f"💥 **R{turn}:** {user.display_name} landed a **CRITICAL HIT** for **{dmg_p} DMG**!")
            else:
                turns_log.append(f"⚔️ **R{turn}:** {user.display_name} struck {monster['name']} for **{dmg_p} DMG**.")
            m_hp -= dmg_p

            if m_hp <= 0:
                break

            # Monster hits player
            dmg_m = max(5, int((m_atk * random.uniform(0.85, 1.15)) - (p_def * 0.4)))
            p_hp -= dmg_m
            turns_log.append(f"🩸 {monster['emoji']} {monster['name']} retaliated for **{dmg_m} DMG**! (HP: {max(0, p_hp)})")

        player_won = m_hp <= 0 or (p_hp > 0 and m_hp < p_hp)

        if player_won:
            coins_won = random.randint(*monster["coins_reward"])
            xp_won = monster["xp_reward"]

            await economy_service.modify_wallet(guild_id, user.id, coins_won, "battle_win", f"Defeated {monster['name']}")
            await economy_service.add_xp(guild_id, user.id, xp_won)

            # Update battles_won in DB
            await db.execute(
                "UPDATE economy_users SET battles_won = battles_won + 1 WHERE guild_id = ? AND user_id = ?",
                (guild_id, user.id),
            )

            # 15% chance to drop Oak Mystery Crate
            crate_dropped = random.random() < 0.15
            if crate_dropped:
                await db.execute(
                    "INSERT INTO economy_inventory (guild_id, user_id, item_id, quantity) VALUES (?, ?, 'common_crate', 1) "
                    "ON CONFLICT(guild_id, user_id, item_id) DO UPDATE SET quantity = quantity + 1",
                    (guild_id, user.id),
                )

            embed = discord.Embed(
                title=f"⚔️ Dungeon Victory: {user.display_name}!",
                description=(
                    f"**{monster['emoji']} {monster['name']}** has been defeated!\n\n"
                    + "\n".join(turns_log[:6])
                ),
                color=COLOR_ECO_SUCCESS,
            )
            embed.add_field(
                name="🎁 Battle Spoils",
                value=(
                    f"• {CURRENCY_SYMBOL} **+{coins_won:,} Coins**\n"
                    f"• ✨ **+{xp_won} XP**\n"
                    + (f"• 📦 **Bonus Drop:** Unlocked **1x Oak Mystery Crate**!\n" if crate_dropped else "")
                    + f"• 🗡️ Weapon: `{weapon_name}` | 🐾 Pet: `{pet_name}`"
                ),
                inline=False,
            )
        else:
            await db.execute(
                "UPDATE economy_users SET battles_lost = battles_lost + 1 WHERE guild_id = ? AND user_id = ?",
                (guild_id, user.id),
            )
            embed = discord.Embed(
                title=f"💀 Dungeon Defeat: {user.display_name}",
                description=(
                    f"{user.mention} was overpowered by **{monster['emoji']} {monster['name']}**!\n\n"
                    + "\n".join(turns_log[:5])
                    + "\n\n🏥 You retreated safely back to the town square to recover!"
                ),
                color=COLOR_ECO_ERROR,
            )

        embed.set_footer(text=f"Level {user_lvl} Warrior • Type 'b' to battle again!")
        await send_response(responder, embed=embed)

    async def handle_hunt(self, responder: Any, user: discord.Member):
        """Execute safari hunt and add captured animal to zoo."""
        res = await economy_service.hunt(user.guild.id, user.id)

        if not res["success"]:
            rem = format_remaining(res["remaining_seconds"])
            embed = discord.Embed(
                title="⏳ Safari Cooldown Active",
                description=f"{user.mention}, the safari animals are resting! Please wait **{rem}** before hunting again.",
                color=COLOR_ECO_INFO,
            )
            return await send_response(responder, embed=embed)

        enc = res["encounter"]
        if not res["caught"]:
            embed = discord.Embed(
                title="🐾 Safari Encounter: Escaped!",
                description=f"A wild **{enc['emoji']} {enc['name']}** appeared in the bushes, but swiftly escaped into the wild!",
                color=COLOR_ECO_INFO,
            )
            return await send_response(responder, embed=embed)

        rarity = enc["rarity"]
        color = RARITY_COLORS.get(rarity, COLOR_ECO_PRIMARY)
        is_dupe = res["is_duplicate"]
        count = res["total_caught"]

        embed = discord.Embed(
            title=f"🏹 Safari Capture: {enc['emoji']} {enc['name']}!",
            description=(
                f"{user.mention} ventured into the wilderness and captured a **{rarity}** **{enc['name']}**!\n\n"
                f"• **Species:** {enc['emoji']} `{enc['name']}`\n"
                f"• **Rarity Tier:** **{rarity}**\n"
                f"• **Zoo Collection:** `{count}x` in your zoo"
                + (f" *(Duplicate animal!)*" if is_dupe else " *(✨ NEW DISCOVERY!)*")
            ),
            color=color,
        )
        embed.set_footer(text="Type 'h' to hunt again • Type 'z' to view your Zoo")
        await send_response(responder, embed=embed)

    async def handle_cash(self, responder: Any, user: discord.Member):
        """Display member's wallet, bank, gems, net worth and daily streak."""
        data = await economy_service.get_or_create_user(user.guild.id, user.id)
        wallet = data["wallet"]
        bank = data["bank"]
        net_worth = wallet + bank
        gems = data["gems"]
        streak = data["daily_streak"]
        rep = data["reputation"]
        level = data["level"]
        xp = data["xp"]

        embed = discord.Embed(
            title=f"💰 Wealth & Financial Balance: {user.display_name}",
            color=COLOR_ECO_GOLD,
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(
            name="🪙 Liquid Wallet",
            value=f"{CURRENCY_SYMBOL} **{wallet:,}** Coins",
            inline=True,
        )
        embed.add_field(
            name="🏦 Secure Bank",
            value=f"🏦 **{bank:,}** Coins",
            inline=True,
        )
        embed.add_field(
            name="💎 Net Worth",
            value=f"💰 **{net_worth:,}** Coins",
            inline=True,
        )
        embed.add_field(
            name="✨ Premium Gems",
            value=f"{GEM_SYMBOL} **{gems:,}** Gems",
            inline=True,
        )
        embed.add_field(
            name="🔥 Daily Streak",
            value=f"**{streak}** Consecutive Days",
            inline=True,
        )
        embed.add_field(
            name="⭐ Reputation",
            value=f"**{rep}** REP Points",
            inline=True,
        )
        embed.set_footer(text=f"Rank: Level {level} ({xp} XP) • Type 'd' to claim Daily Coins")
        await send_response(responder, embed=embed)

    async def handle_profile(
        self,
        responder: Any,
        user: discord.Member,
        target: Optional[discord.Member] = None,
    ):
        """Display member's graphic profile card with bio, badges, and RPG stats."""
        member = target or user
        guild_id = member.guild.id

        # Profile bio
        prof = await db.fetchone(
            "SELECT bio, custom_color FROM user_profiles WHERE guild_id = ? AND user_id = ?",
            (guild_id, member.id),
        )
        bio = prof["bio"] if prof and prof["bio"] else "Hello! I am enjoying NOVEXA OwO Gaming."
        custom_color = int(prof["custom_color"].replace("#", "0x"), 16) if prof and prof["custom_color"] else COLOR_OWO_PURPLE

        # Economy stats
        eco = await economy_service.get_or_create_user(guild_id, member.id)
        equipped = await economy_service.get_equipped_items(guild_id, member.id)
        pet = await economy_service.get_equipped_pet(guild_id, member.id)
        rel = await economy_service.get_relationship(guild_id, member.id)
        zoo = await economy_service.get_user_zoo(guild_id, member.id)

        weapon_name = equipped.get("weapon", {}).get("name", "None")
        armor_name = equipped.get("armor", {}).get("name", "None")
        pet_name = f"{pet['emoji']} {pet['name']} (Lv.{pet['level']})" if pet else "None"

        # Marriage partner
        partner_str = "Single"
        if rel and rel.get("is_married"):
            p_id = rel["partner_id"]
            partner_str = f"💍 Married to <@{p_id}>"

        embed = discord.Embed(
            title=f"👤 Profile: {member.display_name}",
            description=f"*{bio}*",
            color=custom_color,
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(
            name="📊 Level & Rank",
            value=f"Level **{eco['level']}**\nXP: **{eco['xp']:,}**",
            inline=True,
        )
        embed.add_field(
            name="🪙 Wealth",
            value=f"Coins: **{eco['wallet']:,}**\nBank: **{eco['bank']:,}**",
            inline=True,
        )
        embed.add_field(
            name="⭐ Social & REP",
            value=f"REP: **{eco['reputation']}**\n{partner_str}",
            inline=True,
        )
        embed.add_field(
            name="⚔️ Combat Gear",
            value=f"🗡️ Weapon: `{weapon_name}`\n🛡️ Armor: `{armor_name}`\n🐾 Companion: `{pet_name}`",
            inline=True,
        )
        embed.add_field(
            name="🐾 Collection & Battles",
            value=f"🦁 Zoo: **{len(zoo)}** species\n⚔️ Won: **{eco['battles_won']}** | Lost: **{eco['battles_lost']}**",
            inline=True,
        )

        embed.set_footer(text="Type 'setbio <text>' to update your bio • Type 'b' to battle")
        await send_response(responder, embed=embed)

    async def handle_setbio(self, responder: Any, user: discord.Member, new_bio: str):
        """Update member's custom profile bio."""
        if len(new_bio) > 200:
            return await send_response(responder, content="❌ Bio cannot exceed 200 characters.", ephemeral=True)

        await db.execute(
            "INSERT INTO user_profiles (guild_id, user_id, bio) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET bio = excluded.bio",
            (user.guild.id, user.id, new_bio),
        )

        embed = discord.Embed(
            title="✅ Bio Updated Successfully",
            description=f"{user.mention}, your new profile bio is:\n> *{new_bio}*",
            color=COLOR_ECO_SUCCESS,
        )
        await send_response(responder, embed=embed)

    async def handle_daily(self, responder: Any, user: discord.Member):
        """Claim daily coins and streak bonuses."""
        res = await economy_service.claim_daily(user.guild.id, user.id)
        if not res["success"]:
            rem = format_remaining(res["remaining_seconds"])
            embed = discord.Embed(
                title="⏳ Daily Already Claimed",
                description=f"{user.mention}, you have already claimed today's daily reward! Come back in **{rem}**.",
                color=COLOR_ECO_INFO,
            )
            return await send_response(responder, embed=embed)

        embed = discord.Embed(
            title="🎁 Daily Reward Claimed!",
            description=(
                f"{user.mention}, here is your daily supply!\n\n"
                f"• {CURRENCY_SYMBOL} Base Coins: **+{res['base_reward']:,}**\n"
                f"• 🔥 Streak Bonus: **+{res['streak_bonus']:,}**\n"
                f"• 💰 Total Claimed: **+{res['reward']:,} Coins**\n"
                f"• 🌟 Current Streak: **{res['streak']} Days** in a row!\n"
                f"• 🪙 New Wallet Balance: **{res['new_wallet']:,} Coins**"
            ),
            color=COLOR_ECO_GOLD,
        )
        await send_response(responder, embed=embed)

    async def handle_work(self, responder: Any, user: discord.Member):
        """Perform an hourly job for coins."""
        res = await economy_service.work(user.guild.id, user.id)
        if not res["success"]:
            rem = format_remaining(res["remaining_seconds"])
            embed = discord.Embed(
                title="⏳ Shift Resting",
                description=f"{user.mention}, you are tired from your last work shift! Rest for **{rem}**.",
                color=COLOR_ECO_INFO,
            )
            return await send_response(responder, embed=embed)

        embed = discord.Embed(
            title="🛠️ Work Shift Finished",
            description=(
                f"{user.mention}, {res['message']}\n\n"
                f"• 💰 Salary Earned: **+{res['earned']:,} Coins**\n"
                f"• 🪙 New Wallet Balance: **{res['new_wallet']:,} Coins**"
            ),
            color=COLOR_ECO_SUCCESS,
        )
        await send_response(responder, embed=embed)

    async def handle_crime(self, responder: Any, user: discord.Member):
        """Attempt high-risk crime."""
        res = await economy_service.crime(user.guild.id, user.id)
        if not res["success"]:
            rem = format_remaining(res["remaining_seconds"])
            return await send_response(
                responder,
                embed=discord.Embed(
                    title="⏳ Crime Cooldown",
                    description=f"The police heat is still high! Wait **{rem}** before attempting another crime.",
                    color=COLOR_ECO_INFO,
                ),
            )

        if res["won"]:
            embed = discord.Embed(
                title="🕵️ Crime Successful!",
                description=f"{user.mention}, {res['message']}\n\n💰 Loot: **+{res['amount']:,} Coins**",
                color=COLOR_ECO_SUCCESS,
            )
        else:
            embed = discord.Embed(
                title="🚨 Caught By Police!",
                description=f"{user.mention}, {res['message']}\n\n💸 Fine Paid: **-{res['amount']:,} Coins**",
                color=COLOR_ECO_ERROR,
            )
        await send_response(responder, embed=embed)

    async def handle_slut(self, responder: Any, user: discord.Member):
        """Attempt street gig."""
        res = await economy_service.slut(user.guild.id, user.id)
        if not res["success"]:
            rem = format_remaining(res["remaining_seconds"])
            return await send_response(
                responder,
                embed=discord.Embed(
                    title="⏳ Street Cooldown",
                    description=f"Wait **{rem}** before another street gig.",
                    color=COLOR_ECO_INFO,
                ),
            )

        if res["won"]:
            embed = discord.Embed(
                title="💋 Street Hustle Success",
                description=f"{user.mention}, {res['message']}\n\n💰 Earned: **+{res['amount']:,} Coins**",
                color=COLOR_OWO_PINK,
            )
        else:
            embed = discord.Embed(
                title="💔 Hustle Failed",
                description=f"{user.mention}, {res['message']}\n\n💸 Lost: **-{res['amount']:,} Coins**",
                color=COLOR_ECO_ERROR,
            )
        await send_response(responder, embed=embed)

    async def handle_zoo(self, responder: Any, user: discord.Member):
        """Display member's animal collection by rarity tiers."""
        zoo = await economy_service.get_user_zoo(user.guild.id, user.id)
        if not zoo:
            embed = discord.Embed(
                title=f"🐾 Zoo: {user.display_name}",
                description=(
                    f"{user.mention}, your Zoo is completely empty!\n\n"
                    f"Use `hunt` or click the **[🏹 Hunt]** button to capture wild safari animals!"
                ),
                color=COLOR_ECO_INFO,
            )
            return await send_response(responder, embed=embed)

        tiers: Dict[str, List[str]] = {
            "Mythical": [],
            "Legendary": [],
            "Epic": [],
            "Rare": [],
            "Uncommon": [],
            "Common": [],
        }

        total_animals = 0
        for a in zoo:
            rarity = a.get("rarity", "Common")
            emoji = a.get("emoji", "🐾")
            name = a.get("name", "Animal")
            count = a.get("count", 1)
            total_animals += count
            if rarity in tiers:
                tiers[rarity].append(f"{emoji} {name} `x{count}`")

        embed = discord.Embed(
            title=f"🦁 Animal Zoo & Wildlife: {user.display_name}",
            description=f"Total Captured Animals: **{total_animals:,}** across **{len(zoo)}** species",
            color=COLOR_ECO_GOLD,
        )

        tier_emojis = {
            "Mythical": "👑",
            "Legendary": "🌟",
            "Epic": "🔮",
            "Rare": "💎",
            "Uncommon": "🌿",
            "Common": "🐾",
        }

        for tier, items in tiers.items():
            if items:
                embed.add_field(
                    name=f"{tier_emojis.get(tier, '🐾')} {tier} ({len(items)})",
                    value=", ".join(items[:8]) + (f" and {len(items)-8} more..." if len(items) > 8 else ""),
                    inline=False,
                )

        embed.set_footer(text="Type 'h' to hunt more animals for your collection!")
        await send_response(responder, embed=embed)

    async def handle_slots(self, responder: Any, user: discord.Member, bet: int = 50):
        """Spin 3-reel slot machine."""
        if bet < 10:
            return await send_response(responder, content="❌ Minimum slots bet is 10 coins.", ephemeral=True)
        if bet > 500000:
            return await send_response(responder, content="❌ Maximum slots bet is 500,000 coins.", ephemeral=True)

        res = await economy_service.slots(user.guild.id, user.id, bet)
        if not res["success"]:
            return await send_response(responder, content=f"❌ {user.mention}, {res['message']}", ephemeral=True)

        reels = res["reels"]
        payout = res["payout"]
        won = res["won"]

        slot_frame = (
            f"╔═════════════════════╗\n"
            f"   {reels[0]}  │  {reels[1]}  │  {reels[2]}  \n"
            f"╚═════════════════════╝"
        )

        if won:
            if res.get("jackpot"):
                embed = discord.Embed(
                    title="🎰 💥 MEGA JACKPOT WIN! 💥 🎰",
                    description=(
                        f"```{slot_frame}```\n\n"
                        f"🎉 **JACKPOT!** {user.mention} hit all 3 matching symbols!\n"
                        f"💰 **Payout:** **+{payout:,} Coins** (x{res.get('multiplier', 5)})\n"
                        f"🪙 New Balance: **{res['new_wallet']:,} Coins**"
                    ),
                    color=COLOR_ECO_GOLD,
                )
            else:
                embed = discord.Embed(
                    title="🎰 Slot Machine Win!",
                    description=(
                        f"```{slot_frame}```\n\n"
                        f"✨ Nice spin {user.mention}! You won **+{payout:,} Coins**!\n"
                        f"🪙 New Balance: **{res['new_wallet']:,} Coins**"
                    ),
                    color=COLOR_ECO_SUCCESS,
                )
        else:
            embed = discord.Embed(
                title="🎰 Slot Machine Loss",
                description=(
                    f"```{slot_frame}```\n\n"
                    f"💀 Better luck next spin {user.mention}! Lost **{bet:,} Coins**.\n"
                    f"🪙 New Balance: **{res['new_wallet']:,} Coins**"
                ),
                color=COLOR_ECO_ERROR,
            )

        await send_response(responder, embed=embed)

    async def handle_coinflip(
        self,
        responder: Any,
        user: discord.Member,
        choice: str = "heads",
        bet: int = 50,
    ):
        """Flip a coin to gamble coins."""
        if bet < 10:
            return await send_response(responder, content="❌ Minimum coinflip bet is 10 coins.", ephemeral=True)
        if bet > 500000:
            return await send_response(responder, content="❌ Maximum coinflip bet is 500,000 coins.", ephemeral=True)

        res = await economy_service.coinflip(user.guild.id, user.id, choice, bet)
        if not res["success"]:
            return await send_response(responder, content=f"❌ {user.mention}, {res['message']}", ephemeral=True)

        outcome = res["outcome"].upper()
        won = res["won"]

        if won:
            embed = discord.Embed(
                title="🪙 Coinflip: Victory!",
                description=(
                    f"The golden coin spun in the air and landed on **{outcome}**!\n\n"
                    f"🎉 {user.mention} won **+{res['payout']:,} Coins**!\n"
                    f"🪙 New Balance: **{res['new_wallet']:,} Coins**"
                ),
                color=COLOR_ECO_SUCCESS,
            )
        else:
            embed = discord.Embed(
                title="🪙 Coinflip: Loss",
                description=(
                    f"The coin landed on **{outcome}** (You chose *{choice.upper()}*).\n\n"
                    f"💀 {user.mention} lost **{bet:,} Coins**.\n"
                    f"🪙 New Balance: **{res['new_wallet']:,} Coins**"
                ),
                color=COLOR_ECO_ERROR,
            )

        await send_response(responder, embed=embed)

    async def handle_inventory(self, responder: Any, user: discord.Member):
        """Display equipped combat gear and inventory bag contents."""
        guild_id = user.guild.id
        inv = await economy_service.get_user_inventory(guild_id, user.id)
        equipped = await economy_service.get_equipped_items(guild_id, user.id)

        embed = discord.Embed(
            title=f"🎒 Adventurer Inventory: {user.display_name}",
            color=COLOR_ECO_PRIMARY,
        )

        # Equipped loadout
        w = equipped.get("weapon", {}).get("name", "Bare Fists")
        a = equipped.get("armor", {}).get("name", "Cloth Tunic")
        s = equipped.get("shield", {}).get("name", "None")

        embed.add_field(
            name="⚔️ Combat Loadout",
            value=f"• 🗡️ **Weapon:** `{w}`\n• 🛡️ **Armor:** `{a}`\n• 🔰 **Shield:** `{s}`",
            inline=False,
        )

        if not inv:
            embed.add_field(
                name="📦 Backpack Items",
                value="*Your backpack is empty! Visit the `shop` or win crates in battle.*",
                inline=False,
            )
        else:
            items_str = []
            for item in inv:
                icon = item.get("icon", "📦")
                name = item.get("name", item["item_id"])
                qty = item["quantity"]
                items_str.append(f"• {icon} **{name}** `x{qty}`")
            embed.add_field(
                name=f"📦 Backpack Items ({len(inv)})",
                value="\n".join(items_str[:12]),
                inline=False,
            )

        embed.set_footer(text="Type 'shop' to view the armory • Type 'crate' to open mystery crates")
        await send_response(responder, embed=embed)

    async def handle_crate(self, responder: Any, user: discord.Member):
        """Open mystery loot crates from user inventory."""
        guild_id = user.guild.id

        # Find best available crate in inventory
        crates_priority = ["legendary_crate", "epic_crate", "rare_crate", "common_crate"]
        target_crate = None

        for cid in crates_priority:
            row = await db.fetchone(
                "SELECT quantity FROM economy_inventory WHERE guild_id = ? AND user_id = ? AND item_id = ?",
                (guild_id, user.id, cid),
            )
            if row and row["quantity"] > 0:
                target_crate = cid
                break

        if not target_crate:
            embed = discord.Embed(
                title="📦 No Crates in Inventory",
                description=(
                    f"{user.mention}, you do not have any mystery crates to open!\n\n"
                    f"**How to get crates:**\n"
                    f"• ⚔️ Battle dungeon monsters (`b`)\n"
                    f"• 🏹 Safari hunts (`h`)\n"
                    f"• 🛒 Buy crates in `shop` or `/crates buy`"
                ),
                color=COLOR_ECO_INFO,
            )
            return await send_response(responder, embed=embed)

        success, drops, msg = await economy_service.open_crate(guild_id, user.id, target_crate, amount=1)
        if not success:
            return await send_response(responder, content=f"❌ {msg}", ephemeral=True)

        crate_names = {
            "common_crate": "📦 Oak Mystery Crate",
            "rare_crate": "🧰 Silver Treasure Crate",
            "epic_crate": "🔮 Royal Amethyst Crate",
            "legendary_crate": "👑 Celestial Novexa Vault",
        }

        c_name = crate_names.get(target_crate, "Mystery Crate")
        drop_lines = []
        for d in drops:
            if d.get("type") == "coins":
                drop_lines.append(f"• {CURRENCY_SYMBOL} **+{d['amount']:,} Coins**")
            elif d.get("type") == "gems":
                drop_lines.append(f"• {GEM_SYMBOL} **+{d['amount']} Gems**")
            elif d.get("type") == "item":
                drop_lines.append(f"• 🗡️ **{d.get('item_name', 'Item')}** (`{d.get('rarity', 'Rare')}`)")

        embed = discord.Embed(
            title=f"📦 Unboxed: {c_name}!",
            description=(
                f"{user.mention} opened **1x {c_name}** and revealed:\n\n"
                + "\n".join(drop_lines)
            ),
            color=COLOR_ECO_GOLD,
        )
        await send_response(responder, embed=embed)

    async def handle_pets(self, responder: Any, user: discord.Member):
        """Display adopted companion pets."""
        guild_id = user.guild.id
        pets = await economy_service.get_user_pets(guild_id, user.id)
        equipped = await economy_service.get_equipped_pet(guild_id, user.id)

        if not pets:
            embed = discord.Embed(
                title=f"🐕 Pets & Companions: {user.display_name}",
                description=(
                    f"{user.mention}, you haven't adopted any pets yet!\n\n"
                    f"Use `/pets adopt` to adopt your first loyal animal companion."
                ),
                color=COLOR_ECO_INFO,
            )
            return await send_response(responder, embed=embed)

        eq_id = equipped["pet_id"] if equipped else None
        pet_lines = []
        for p in pets:
            is_eq = " *(ACTIVE COMPANION)*" if p["pet_id"] == eq_id else ""
            pet_lines.append(
                f"• {p['emoji']} **{p['name']}** (Level {p['level']}) — {p['bonus_type']}: `+{p['bonus_value']}%`{is_eq}"
            )

        embed = discord.Embed(
            title=f"🐾 Pet Companions: {user.display_name}",
            description="\n".join(pet_lines),
            color=COLOR_ECO_PRIMARY,
        )
        await send_response(responder, embed=embed)

    async def handle_marry_status(self, responder: Any, user: discord.Member):
        """Display marriage status for button click."""
        rel = await economy_service.get_relationship(user.guild.id, user.id)
        if rel and rel.get("is_married"):
            p_id = rel["partner_id"]
            embed = discord.Embed(
                title="💍 Marriage Status",
                description=(
                    f"{user.mention} is happily married to <@{p_id}>!\n"
                    f"💖 Love Affection: **{rel.get('affection_level', 100)}%**\n"
                    f"Type `divorce` if you wish to dissolve this bond."
                ),
                color=COLOR_OWO_PINK,
            )
        else:
            embed = discord.Embed(
                title="💍 Marriage Status: Single",
                description=(
                    f"{user.mention}, you are currently single!\n\n"
                    f"Type `marry @user` in this channel to propose to someone special!"
                ),
                color=COLOR_OWO_PINK,
            )
        await send_response(responder, embed=embed)

    async def handle_marry_proposal(self, responder: Any, proposer: discord.Member, target: discord.Member):
        """Handle marriage proposal with confirmation."""
        if target.id == proposer.id:
            return await send_response(responder, content=f"❌ {proposer.mention}, you cannot marry yourself!")
        if target.bot:
            return await send_response(responder, content=f"❌ {proposer.mention}, you cannot marry a bot!")

        try:
            from cogs.social import MarriageProposalView
            view = MarriageProposalView(proposer.id, target.id, proposer.guild.id)
            embed = discord.Embed(
                title="💍 Marriage Proposal!",
                description=(
                    f"{proposer.mention} has gotten down on one knee and proposed to {target.mention}!\n\n"
                    f"{target.mention}, click **Accept Proposal** below to marry!"
                ),
                color=COLOR_OWO_PINK,
            )
            await send_response(responder, embed=embed, view=view)
        except Exception:
            ok, msg = await economy_service.marry(proposer.guild.id, proposer.id, target.id)
            if ok:
                embed = discord.Embed(
                    title="💍 Just Married!",
                    description=f"🎉 {proposer.mention} and {target.mention} are now officially married!",
                    color=COLOR_OWO_PINK,
                )
            else:
                embed = discord.Embed(title="❌ Marriage Failed", description=msg, color=COLOR_ECO_ERROR)
            await send_response(responder, embed=embed)

    async def handle_divorce(self, responder: Any, user: discord.Member):
        """Divorce partner."""
        ok, msg = await economy_service.divorce(user.guild.id, user.id)
        if ok:
            embed = discord.Embed(
                title="💔 Divorce Finalized",
                description=f"{user.mention}, you are now single and your relationship has ended.",
                color=COLOR_ECO_ERROR,
            )
        else:
            embed = discord.Embed(title="❌ Divorce Failed", description=msg, color=COLOR_ECO_ERROR)
        await send_response(responder, embed=embed)

    async def handle_rep(self, responder: Any, sender: discord.Member, receiver: discord.Member):
        """Give reputation point to another member."""
        ok, msg = await economy_service.give_rep(sender.guild.id, sender.id, receiver.id)
        if ok:
            embed = discord.Embed(
                title="⭐ Reputation Given!",
                description=f"{sender.mention} gave +1 REP to {receiver.mention}! 🎉",
                color=COLOR_ECO_GOLD,
            )
        else:
            embed = discord.Embed(title="⏳ Reputation Error", description=msg, color=COLOR_ECO_INFO)
        await send_response(responder, embed=embed)

    async def handle_pay(self, responder: Any, sender: discord.Member, receiver: discord.Member, amount: int):
        """Transfer coins between members."""
        ok, msg = await economy_service.pay(sender.guild.id, sender.id, receiver.id, amount)
        if ok:
            embed = discord.Embed(
                title="💸 Coin Transfer Successful",
                description=f"{sender.mention} sent **{amount:,} Coins** to {receiver.mention}! 🪙",
                color=COLOR_ECO_SUCCESS,
            )
        else:
            embed = discord.Embed(title="❌ Payment Failed", description=msg, color=COLOR_ECO_ERROR)
        await send_response(responder, embed=embed)

    async def handle_deposit(self, responder: Any, user: discord.Member, amount_str: str):
        """Deposit coins into bank."""
        ok, deposited, msg = await economy_service.deposit(user.guild.id, user.id, amount_str)
        if ok:
            embed = discord.Embed(
                title="🏦 Bank Deposit Successful",
                description=f"{user.mention}, deposited **{deposited:,} Coins** into your secure vault!",
                color=COLOR_ECO_SUCCESS,
            )
        else:
            embed = discord.Embed(title="❌ Deposit Failed", description=msg, color=COLOR_ECO_ERROR)
        await send_response(responder, embed=embed)

    async def handle_withdraw(self, responder: Any, user: discord.Member, amount_str: str):
        """Withdraw coins from bank."""
        ok, withdrawn, msg = await economy_service.withdraw(user.guild.id, user.id, amount_str)
        if ok:
            embed = discord.Embed(
                title="🏧 Bank Withdrawal Successful",
                description=f"{user.mention}, withdrew **{withdrawn:,} Coins** to your liquid wallet!",
                color=COLOR_ECO_SUCCESS,
            )
        else:
            embed = discord.Embed(title="❌ Withdrawal Failed", description=msg, color=COLOR_ECO_ERROR)
        await send_response(responder, embed=embed)

    async def handle_shop(self, responder: Any, user: discord.Member):
        """Display weapon armory and crate shop."""
        embed = discord.Embed(
            title="🛒 NOVEXA Armory & Item Shop",
            description=(
                f"Upgrade your warrior gear to deal massive damage in battles and catch rare animals!\n"
                f"Type `buy <item_id>` to purchase any item below:"
            ),
            color=COLOR_ECO_GOLD,
        )

        weapons = [
            ("🗡️ `wooden_sword`", "Wooden Training Sword", "150 Coins (+6 ATK)"),
            ("⚔️ `iron_sword`", "Forged Iron Katana", "600 Coins (+18 ATK, +2 DEF)"),
            ("🗡️ `shadow_blade`", "Shadow Assassin Blade", "2,800 Coins (+42 ATK)"),
            ("🔥 `crimson_slayer`", "Crimson Dragon Slayer", "12,000 Coins (+85 ATK, +15 DEF)"),
            ("📦 `common_crate`", "Oak Mystery Crate", "500 Coins"),
            ("🧰 `rare_crate`", "Silver Treasure Crate", "2,200 Coins"),
        ]

        val_lines = [f"{w[0]} — **{w[1]}**\n• Price: `{w[2]}`" for w in weapons]
        embed.add_field(name="Featured Items", value="\n\n".join(val_lines), inline=False)
        embed.set_footer(text="Example: 'buy iron_sword' • 'equip iron_sword'")
        await send_response(responder, embed=embed)

    async def handle_buy(self, responder: Any, user: discord.Member, item_id: str):
        """Buy item from shop."""
        ok, msg = await economy_service.buy_item(user.guild.id, user.id, item_id, 1)
        if ok:
            embed = discord.Embed(
                title="🛒 Purchase Successful",
                description=f"{user.mention}, you purchased **1x `{item_id}`**! Type `equip {item_id}` to equip it.",
                color=COLOR_ECO_SUCCESS,
            )
        else:
            embed = discord.Embed(title="❌ Purchase Failed", description=msg, color=COLOR_ECO_ERROR)
        await send_response(responder, embed=embed)

    async def handle_equip(self, responder: Any, user: discord.Member, item_id: str):
        """Equip item from inventory."""
        ok, msg = await economy_service.equip_item(user.guild.id, user.id, item_id)
        if ok:
            embed = discord.Embed(
                title="⚔️ Gear Equipped",
                description=f"{user.mention}, {msg}",
                color=COLOR_ECO_SUCCESS,
            )
        else:
            embed = discord.Embed(title="❌ Equip Failed", description=msg, color=COLOR_ECO_ERROR)
        await send_response(responder, embed=embed)

    async def handle_help(self, responder: Any):
        """Display complete OwO guide and command list."""
        embed = discord.Embed(
            title="📖 OwO Gaming Guide & Shortcuts",
            description=(
                "In this channel, you can type any of the following shortcuts **without any prefix**:\n\n"
                "• `b` or `battle` — Battle Dungeon Bosses or Duel a friend (`b @user [bet]`)\n"
                "• `h` or `hunt` — Hunt exotic wildlife for your Zoo\n"
                "• `c` or `cash` or `check` or `bal` — Check wallet, bank & gems\n"
                "• `p` or `profile` or `bio` — View custom card (`p @user`)\n"
                "• `setbio <text>` — Update profile bio\n"
                "• `d` or `daily` — Claim daily coins & keep your streak\n"
                "• `w` or `work` — Work an hourly shift for cash\n"
                "• `crime` / `slut` — High-risk street hustle\n"
                "• `z` or `zoo` — Inspect your animal collection\n"
                "• `s <amount>` — Spin the 3-reel slot machine (e.g. `s 100`)\n"
                "• `cf <amount> [h/t]` — Flip a coin to double your bet (e.g. `cf 250 heads`)\n"
                "• `inv` or `inventory` — View combat gear & weapons\n"
                "• `crate` or `opencrate` — Open mystery loot crates\n"
                "• `pets` — View companion pets\n"
                "• `marry @user` / `divorce` — Marriage and relationships\n"
                "• `rep @user` — Give daily reputation\n"
                "• `pay @user <amt>` — Transfer coins to another member\n"
                "• `dep <amt>` / `with <amt>` — Deposit or withdraw bank funds\n"
                "• `shop` / `buy <item>` / `equip <item>` / `unequip <slot>` — Armory weapons & gear\n"
                "• `g <bet>` — Roll 1-100 casino (51+ = 2x, 91+ = 3x)\n"
                "• `dice <bet> [1-6]` — Roll against the bot, or call an exact face for 6x\n"
                "• `weekly` / `monthly` — Claim weekly & monthly vault rewards\n"
                "• `rich` or `top` — Server wealth leaderboard\n"
                "• `sell <animal> [n|all|duplicates]` — Sell zoo animals for coins\n"
                "• `fav <animal>` — Mark your favorite capture\n"
                "• `ach` — View achievements and auto-rewards\n"
                "• `adopt <pet> [nickname]` / `feed <pet>` — Pets from the shelter\n"
                "• `rob @user` — Pickpocket (45% success, 1h cooldown)\n"
                "• `owo` or `uwu` — Cute expressions!"
            ),
            color=COLOR_OWO_PINK,
        )
        embed.set_footer(text=f"{BOT_NAME} • OwO Gaming Suite")
        await send_response(responder, embed=embed)

    # ==================== EXTENDED CASINO & PROGRESSION ====================

    async def handle_gamble(self, responder: Any, user: discord.Member, bet: int = 100):
        """Roll 1-100: 91+ pays 3x, 51-90 pays 2x, the rest is a loss."""
        if bet < 10:
            return await send_response(responder, content="❌ Minimum gamble bet is 10 coins.", ephemeral=True)
        if bet > 500000:
            return await send_response(responder, content="❌ Maximum gamble bet is 500,000 coins.", ephemeral=True)

        res = await economy_service.gamble(user.guild.id, user.id, bet)
        if not res["success"]:
            return await send_response(responder, content=f"❌ {user.mention}, {res['message']}", ephemeral=True)

        if res["won"]:
            embed = discord.Embed(
                title=f"🎲 Gamble — {res['tier']}!",
                description=(
                    f"{user.mention} rolled **{res['roll']}/100**.\n\n"
                    f"• 💰 Payout: **+{res['payout']:,} Coins**\n"
                    f"• 📈 Profit: **+{res['profit']:,} Coins**"
                ),
                color=COLOR_ECO_GOLD,
            )
        else:
            embed = discord.Embed(
                title="🎲 Gamble — Loss",
                description=(
                    f"{user.mention} rolled **{res['roll']}/100**.\n\n"
                    f"• 💸 Lost: **{res['lost']:,} Coins**\n"
                    f"*Need 51+ to win, 91+ for triple.*"
                ),
                color=COLOR_ECO_ERROR,
            )
        await send_response(responder, embed=embed)

    async def handle_dice(self, responder: Any, user: discord.Member, bet: int = 100, guess: Optional[int] = None):
        """Roll a die against the bot, or bet on an exact face for 6x."""
        if bet < 10:
            return await send_response(responder, content="❌ Minimum dice bet is 10 coins.", ephemeral=True)
        if bet > 500000:
            return await send_response(responder, content="❌ Maximum dice bet is 500,000 coins.", ephemeral=True)
        if guess is not None and not 1 <= guess <= 6:
            return await send_response(responder, content="❌ Guess must be between 1 and 6.", ephemeral=True)

        res = await economy_service.dice(user.guild.id, user.id, bet, guess)
        if not res["success"]:
            return await send_response(responder, content=f"❌ {user.mention}, {res['message']}", ephemeral=True)

        faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]

        if res["mode"] == "exact":
            face = faces[res["roll"] - 1]
            if res["won"]:
                embed = discord.Embed(
                    title="🎲 Exact Dice Hit!",
                    description=(
                        f"```\n  {face}  →  {res['roll']}\n```\n"
                        f"{user.mention} called **{res['guess']}** and rolled **{res['roll']}**!\n"
                        f"💰 Payout: **+{res['payout']:,} Coins** (6x)"
                    ),
                    color=COLOR_ECO_GOLD,
                )
            else:
                embed = discord.Embed(
                    title="🎲 Exact Dice Miss",
                    description=(
                        f"```\n  {face}  →  {res['roll']}\n```\n"
                        f"{user.mention} called **{res['guess']}**, rolled **{res['roll']}**. Lost **{res['lost']:,} Coins**."
                    ),
                    color=COLOR_ECO_ERROR,
                )
        else:
            p_face = faces[res["player_roll"] - 1]
            b_face = faces[res["bot_roll"] - 1]
            if res["won"] is None:
                embed = discord.Embed(
                    title="🎲 Dice Tie — Bet Refunded",
                    description=(
                        f"```\n  You {p_face} {res['player_roll']}   •   Bot {b_face} {res['bot_roll']}\n```\n"
                        f"{user.mention}, **{res['refund']:,} Coins** returned."
                    ),
                    color=COLOR_ECO_INFO,
                )
            elif res["won"]:
                embed = discord.Embed(
                    title="🎲 Dice Win!",
                    description=(
                        f"```\n  You {p_face} {res['player_roll']}   •   Bot {b_face} {res['bot_roll']}\n```\n"
                        f"{user.mention} won **+{res['payout']:,} Coins**!"
                    ),
                    color=COLOR_ECO_SUCCESS,
                )
            else:
                embed = discord.Embed(
                    title="🎲 Dice Loss",
                    description=(
                        f"```\n  You {p_face} {res['player_roll']}   •   Bot {b_face} {res['bot_roll']}\n```\n"
                        f"{user.mention} lost **{res['lost']:,} Coins**."
                    ),
                    color=COLOR_ECO_ERROR,
                )
        await send_response(responder, embed=embed)

    async def handle_weekly(self, responder: Any, user: discord.Member):
        res = await economy_service.claim_weekly(user.guild.id, user.id)
        if not res["success"]:
            rem = format_remaining(res["remaining_seconds"])
            return await send_response(
                responder,
                embed=discord.Embed(
                    title="⏳ Weekly Reward Already Claimed",
                    description=f"{user.mention}, next weekly bonus unlocks in **{rem}**.",
                    color=COLOR_ECO_INFO,
                ),
            )
        embed = discord.Embed(
            title="📅 Weekly Bonus Claimed!",
            description=(
                f"{user.mention} collected the weekly crate:\n\n"
                f"• {CURRENCY_SYMBOL} Coins: **+{res['coins']:,}**\n"
                f"• {GEM_SYMBOL} Gems: **+{res['gems']}**\n"
                f"• 📦 Item: **{res['crate'].replace('_', ' ').title()}**"
            ),
            color=COLOR_ECO_GOLD,
        )
        await send_response(responder, embed=embed)

    async def handle_monthly(self, responder: Any, user: discord.Member):
        res = await economy_service.claim_monthly(user.guild.id, user.id)
        if not res["success"]:
            rem = format_remaining(res["remaining_seconds"])
            return await send_response(
                responder,
                embed=discord.Embed(
                    title="⏳ Monthly Reward Already Claimed",
                    description=f"{user.mention}, next monthly vault unlocks in **{rem}**.",
                    color=COLOR_ECO_INFO,
                ),
            )
        embed = discord.Embed(
            title="🗓️ Monthly Vault Claimed!",
            description=(
                f"{user.mention} opened the monthly vault:\n\n"
                f"• {CURRENCY_SYMBOL} Coins: **+{res['coins']:,}**\n"
                f"• {GEM_SYMBOL} Gems: **+{res['gems']}**\n"
                f"• 📦 Item: **{res['crate'].replace('_', ' ').title()}**"
            ),
            color=COLOR_ECO_GOLD,
        )
        await send_response(responder, embed=embed)

    async def handle_leaderboard(self, responder: Any, user: discord.Member):
        rows = await db.fetchall(
            """
            SELECT user_id, wallet, bank, level, (wallet + bank) AS net
            FROM economy_users
            WHERE guild_id = ?
            ORDER BY net DESC
            LIMIT 10
            """,
            (user.guild.id,),
        )
        if not rows:
            return await send_response(responder, content="📉 No economy data in this server yet.")

        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for idx, row in enumerate(rows):
            prefix = medals[idx] if idx < 3 else f"`#{idx + 1}`"
            lines.append(
                f"{prefix} <@{row['user_id']}> — {CURRENCY_SYMBOL} **{int(row['net']):,}** • Lv.{row['level']}"
            )

        embed = discord.Embed(
            title=f"🏆 Wealth Leaderboard — {user.guild.name}",
            description="\n".join(lines),
            color=COLOR_ECO_GOLD,
        )
        embed.set_footer(text="Type 'c' to check your balance • 'd' for daily coins")
        await send_response(responder, embed=embed)

    async def handle_sell(self, responder: Any, user: discord.Member, animal: str, count: str = "1"):
        ok, sold, coins, msg = await economy_service.sell_animal(user.guild.id, user.id, animal, count)
        if not ok:
            return await send_response(responder, content=f"❌ {msg}", ephemeral=True)
        embed = discord.Embed(
            title="💵 Animal Sold",
            description=f"{user.mention} {msg}\n• 📦 Sold: **{sold}x**\n• 💰 Earned: **{coins:,} Coins**",
            color=COLOR_ECO_SUCCESS,
        )
        await send_response(responder, embed=embed)

    async def handle_favorite(self, responder: Any, user: discord.Member, animal: str):
        ok, msg = await economy_service.favorite_animal(user.guild.id, user.id, animal)
        embed = discord.Embed(
            title="⭐ Favorite Animal" if ok else "❌ Favorite Failed",
            description=msg,
            color=COLOR_ECO_SUCCESS if ok else COLOR_ECO_ERROR,
        )
        await send_response(responder, embed=embed)

    async def handle_achievements(self, responder: Any, user: discord.Member):
        newly = await economy_service.check_achievements(user.guild.id, user.id)
        all_rows = await db.fetchall("SELECT key, name, description, icon, coin_reward, gem_reward FROM economy_achievements ORDER BY coin_reward ASC")
        owned = {
            r["achievement_key"]
            for r in await db.fetchall(
                "SELECT achievement_key FROM economy_user_achievements WHERE guild_id = ? AND user_id = ?",
                (user.guild.id, user.id),
            )
        }

        lines = []
        for row in all_rows:
            mark = "✅" if row["key"] in owned else "🔒"
            lines.append(
                f"{mark} {row['icon']} **{row['name']}** — {row['description']}\n"
                f"   ↳ `+{row['coin_reward']:,} coins` · `+{row['gem_reward']} gems`"
            )

        embed = discord.Embed(
            title=f"🎖️ Achievements: {user.display_name}",
            description="\n".join(lines[:12]) or "No achievements configured.",
            color=COLOR_OWO_PURPLE,
        )
        embed.set_footer(text=f"Unlocked {len(owned)}/{len(all_rows)} • New unlocks are auto-rewarded")
        await send_response(responder, embed=embed)

        if newly:
            names = ", ".join(f"{a['icon']} {a['name']}" for a in newly)
            await send_response(responder, content=f"🎉 {user.mention} unlocked: {names}")

    async def handle_adopt(self, responder: Any, user: discord.Member, pet_type: str, nickname: Optional[str] = None):
        ok, msg = await economy_service.adopt_pet(user.guild.id, user.id, pet_type.lower(), nickname)
        embed = discord.Embed(
            title="🏠 Pet Adopted!" if ok else "❌ Adoption Failed",
            description=msg,
            color=COLOR_ECO_SUCCESS if ok else COLOR_ECO_ERROR,
        )
        await send_response(responder, embed=embed)

    async def handle_feed(self, responder: Any, user: discord.Member, pet_type: str):
        ok, msg = await economy_service.feed_pet(user.guild.id, user.id, pet_type.lower())
        embed = discord.Embed(
            title="🍖 Pet Fed!" if ok else "❌ Feeding Failed",
            description=msg,
            color=COLOR_ECO_SUCCESS if ok else COLOR_ECO_ERROR,
        )
        await send_response(responder, embed=embed)

    async def handle_unequip(self, responder: Any, user: discord.Member, target: str):
        ok, msg = await economy_service.unequip_item(user.guild.id, user.id, target)
        embed = discord.Embed(
            title="🎒 Unequipped" if ok else "❌ Unequip Failed",
            description=msg,
            color=COLOR_ECO_SUCCESS if ok else COLOR_ECO_ERROR,
        )
        await send_response(responder, embed=embed)

    async def handle_rob(self, responder: Any, user: discord.Member, target: discord.Member):
        """Pickpocket another member: 45% success, 1 hour cooldown, half of their wallet capped at 5k."""
        guild_id = user.guild.id
        if target.id == user.id:
            return await send_response(responder, content="❌ You cannot rob yourself.", ephemeral=True)
        if target.bot:
            return await send_response(responder, content="❌ Bots carry no wallets.", ephemeral=True)

        robber = await economy_service.get_or_create_user(guild_id, user.id)
        now = time.time()
        cooldown = 3600
        last_rob = robber.get("last_rob") or 0
        try:
            last_rob = float(last_rob)
        except (TypeError, ValueError):
            last_rob = 0.0
        if now - last_rob < cooldown:
            rem = format_remaining(int(cooldown - (now - last_rob)))
            return await send_response(
                responder,
                embed=discord.Embed(
                    title="🚔 Police Still Searching",
                    description=f"{user.mention}, lay low for **{rem}** before another heist.",
                    color=COLOR_ECO_INFO,
                ),
            )

        victim = await economy_service.get_or_create_user(guild_id, target.id)
        if victim["wallet"] < 100:
            return await send_response(
                responder,
                embed=discord.Embed(
                    title="💸 Nothing To Steal",
                    description=f"{target.mention} carries less than **100 coins**.",
                    color=COLOR_ECO_INFO,
                ),
            )

        await db.execute(
            "UPDATE economy_users SET last_rob = ? WHERE guild_id = ? AND user_id = ?",
            (now, guild_id, user.id),
        )

        if random.random() < 0.45:
            loot = min(victim["wallet"] // 2, random.randint(100, 5000))
            taken = await economy_service.modify_wallet(
                guild_id, target.id, -loot, tx_type="rob_victim", description=f"Robbed by {user.id}"
            )
            if not taken:
                loot = int(victim["wallet"])
                await economy_service.modify_wallet(
                    guild_id, target.id, -loot, tx_type="rob_victim", description=f"Robbed by {user.id}"
                )
            await economy_service.modify_wallet(
                guild_id, user.id, loot, tx_type="rob_success", description=f"Robbed {target.id}"
            )
            embed = discord.Embed(
                title="🕵️ Heist Successful!",
                description=(
                    f"{user.mention} robbed {target.mention} and got away with **{loot:,} Coins**! 🪙\n"
                    f"*1 hour before the next heist.*"
                ),
                color=COLOR_ECO_SUCCESS,
            )
        else:
            fine = min(int(victim["wallet"] * 0.1) + 100, 2500)
            wallet_before = robber["wallet"]
            fine = min(fine, wallet_before)
            if fine > 0:
                await economy_service.modify_wallet(
                    guild_id, user.id, -fine, tx_type="rob_fine", description="Caught robbing"
                )
            embed = discord.Embed(
                title="🚨 Caught Red-Handed!",
                description=(
                    f"{user.mention} tried to rob {target.mention} and got caught.\n"
                    f"💸 Fine paid: **{fine:,} Coins**"
                ),
                color=COLOR_ECO_ERROR,
            )
        await send_response(responder, embed=embed)

    async def handle_owo_cute(self, responder: Any, user: discord.Member):
        """Respond with cute OwO expression."""
        phrase = random.choice(OWO_CUTE_RESPONSES)
        await send_response(responder, content=f"{user.mention} {phrase}")


async def setup(bot: commands.Bot):
    await bot.add_cog(OwO(bot))

