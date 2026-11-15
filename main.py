import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import asyncio
import discord
from discord.ext import commands
from discord import app_commands

from config import (
    BOT_NAME,
    BOT_VERSION,
    BOT_PREFIX,
    DISCORD_TOKEN,
    BASE_DIR,
    DASHBOARD_PORT,
    DASHBOARD_HOST,
)
from database.database import db
from utils.embeds import error_embed

# Import persistent views for registration
from cogs.tickets import TicketPanelView, TicketControlView, TicketClosedView
from cogs.roles import DynamicRolePanelView
from cogs.utility import VoiceJoinView
from cogs.owo import OwOPanelView
from cogs.voice_system import VoiceControlPanelView, AdminVoicePanelView
from services.web_dashboard import WebDashboard

# ==================== LOGGING CONFIGURATION ====================
log_dir = BASE_DIR / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "bot.log"

log_format = logging.Formatter(
    fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

file_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
file_handler.setFormatter(log_format)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_format)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

logger = logging.getLogger("novexa.main")


class NovexaBot(commands.Bot):
    """Production Multi-Guild Discord Bot Engine."""

    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True          # Privileged Intent
        intents.message_content = True  # Privileged Intent
        intents.guilds = True
        intents.voice_states = True
        intents.reactions = True

        super().__init__(
            command_prefix=commands.when_mentioned_or(BOT_PREFIX, "!", "?", "n!"),
            intents=intents,
            help_command=None,
        )
        self.dashboard = WebDashboard(self, port=DASHBOARD_PORT, host=DASHBOARD_HOST)

    async def setup_hook(self):
        """Asynchronous initialization: DB connect, schema init, persistent views, and cog loading."""
        logger.info(f"Initializing {BOT_NAME} v{BOT_VERSION}...")

        # 1. Initialize SQLite Database
        await db.connect()
        await db.init_schema()

        # Load Opus audio library for Discord Voice Streaming (Linux & Windows)
        if not discord.opus.is_loaded():
            try:
                discord.opus._load_default()
            except Exception:
                pass
            if not discord.opus.is_loaded():
                for p in [os.path.abspath("opus.dll"), os.path.abspath("libopus-0.dll"), str(BASE_DIR / "opus.dll"), "libopus.so.0", "libopus.so"]:
                    if os.path.exists(p) or not p.endswith(".dll"):
                        try:
                            discord.opus.load_opus(p)
                            logger.info(f"Loaded Discord Opus codec library from {p}")
                            break
                        except Exception as e:
                            logger.warning(f"Error loading opus from {p}: {e}")

        # 2. Register Persistent Views (Buttons and Panels across restarts)
        self.add_view(TicketPanelView())
        self.add_view(TicketControlView())
        self.add_view(TicketClosedView())
        self.add_view(DynamicRolePanelView())
        self.add_view(VoiceJoinView())
        self.add_view(OwOPanelView())
        self.add_view(VoiceControlPanelView())
        self.add_view(AdminVoicePanelView())
        logger.info("Persistent views registered.")

        # 3. Load all feature Cogs
        cog_modules = [
            "cogs.welcome",
            "cogs.tickets",
            "cogs.antinuke",
            "cogs.antispam",
            "cogs.whitelist",
            "cogs.security",
            "cogs.profile",
            "cogs.payments",
            "cogs.roles",
            "cogs.moderation",
            "cogs.leveling",
            "cogs.utility",
            "cogs.logging",
            "cogs.admin",
            "cogs.server_templates",
            "cogs.economy",
            "cogs.hunt",
            "cogs.battle",
            "cogs.inventory",
            "cogs.pets",
            "cogs.crates",
            "cogs.social",
            "cogs.economy_admin",
            "cogs.server_cloner",
            "cogs.owo",
            "cogs.mention_reply",
            "cogs.staff",
            "cogs.dropper",
            "cogs.wallpaper",
            "cogs.voice_system",
            "cogs.music",
            "cogs.ai_chat",
        ]

        for cog in cog_modules:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded extension: {cog}")
            except Exception as e:
                logger.error(f"Failed to load extension {cog}: {e}", exc_info=True)

        # 4. Start Connected Localhost Web Dashboard
        try:
            await self.dashboard.start()
        except Exception as e:
            logger.warning(f"Failed to start localhost dashboard: {e}")

        # 5. Register slash commands on every guild (instant client visibility)
        asyncio.create_task(self._sync_guild_commands())

    async def sync_slash_commands(self) -> int:
        """Register the command tree on each guild. Guild-scoped registrations
        show up in client pickers immediately; global ones can lag up to an hour."""
        total = 0
        for guild in self.guilds:
            try:
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                total = len(synced)
                logger.info(f"Synced {len(synced)} slash commands to {guild.name} ({guild.id}).")
            except Exception as e:
                logger.warning(f"Guild slash sync failed for {guild.name} ({guild.id}): {e}")
        return total

    async def _sync_guild_commands(self):
        """Guild-scoped commands are the only copy; empty the global list so the
        client never renders two entries for the same command."""
        await self.wait_until_ready()
        try:
            await self.http.bulk_upsert_global_commands(self.application_id, [])
            logger.info("Cleared global command list.")
        except Exception as e:
            logger.warning(f"Global command purge failed: {e}")
        await self.sync_slash_commands()

    async def on_guild_join(self, guild: discord.Guild):
        try:
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            logger.info(f"Synced {len(synced)} slash commands to new guild {guild.name} ({guild.id}).")
        except Exception as e:
            logger.warning(f"Slash sync failed for new guild {guild.name} ({guild.id}): {e}")

    async def on_ready(self):
        logger.info("=" * 60)
        logger.info(f"Logged in as: {self.user.name}#{self.user.discriminator} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds with {sum(g.member_count or 0 for g in self.guilds):,} members.")
        logger.info(f"{BOT_NAME} is fully online and ready.")
        logger.info("=" * 60)

        # Set rich activity
        activity = discord.Activity(
            type=discord.ActivityType.listening,
            name=f"/help • Protecting {len(self.guilds)} servers",
        )
        await self.change_presence(status=discord.Status.online, activity=activity)

        # 5. Start Localhost Live Web Dashboard
        try:
            await self.dashboard.start()
        except Exception as e:
            logger.warning(f"Failed to start localhost dashboard: {e}")

    async def close(self):
        """Graceful shutdown hook."""
        logger.info("Shutting down bot and closing connections...")
        # Disconnect all voice clients
        for vc in self.voice_clients:
            try:
                await vc.disconnect(force=True)
            except Exception:
                pass
        if hasattr(self, "dashboard"):
            try:
                await self.dashboard.stop()
            except Exception:
                pass
        await db.close()
        await super().close()


# ==================== GLOBAL ERROR HANDLER ====================
GulamaliBot = NovexaBot  # Backward compatibility alias
bot = NovexaBot()


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Centralized, user-friendly slash command error handler."""
    if isinstance(error, app_commands.CommandOnCooldown):
        msg = f"⏳ This command is on cooldown. Try again in `{round(error.retry_after, 1)}s`."
        embed = error_embed("Cooldown", msg)
    elif isinstance(error, app_commands.MissingPermissions):
        missing = ", ".join(f"`{p.replace('_', ' ').title()}`" for p in error.missing_permissions)
        msg = f"You lack the required permission(s): {missing}"
        embed = error_embed("Permission Denied", msg)
    elif isinstance(error, app_commands.BotMissingPermissions):
        missing = ", ".join(f"`{p.replace('_', ' ').title()}`" for p in error.missing_permissions)
        msg = f"I lack the required server permission(s): {missing}"
        embed = error_embed("Bot Missing Permissions", msg)
    elif isinstance(error, (app_commands.CheckFailure, app_commands.AppCommandError)):
        msg = str(error) or "You do not have permission to execute this command."
        embed = error_embed("Permission Denied", msg)
    else:
        logger.error(f"Unhandled command error in '{interaction.command.name if interaction.command else 'Unknown'}': {error}", exc_info=True)
        embed = error_embed(
            "An Error Occurred",
            "An unexpected error occurred while executing this command. Staff has been notified."
        )

    try:
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception:
        pass


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    """Keep unknown prefix input quiet and surface real failures once."""
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.CommandOnCooldown):
        try:
            await ctx.reply(f"⏳ On cooldown. Try again in `{round(error.retry_after, 1)}s`.", mention_author=False)
        except Exception:
            pass
        return
    if isinstance(error, (commands.CheckFailure, commands.MissingPermissions, commands.BotMissingPermissions)):
        try:
            await ctx.reply("🔒 You do not have permission to run this command.", mention_author=False)
        except Exception:
            pass
        return
    if isinstance(error, commands.UserInputError):
        try:
            await ctx.reply(f"❌ Invalid input: `{error}`", mention_author=False)
        except Exception:
            pass
        return
    logger.error(f"Prefix command error in '{ctx.command}': {error}", exc_info=error)


# ==================== SINGLE INSTANCE MUTEX LOCK ====================
_instance_socket = None

def _acquire_instance_lock():
    global _instance_socket
    if os.getenv("DISABLE_INSTANCE_LOCK", "").lower() in ("1", "true", "yes"):
        return True
    import socket
    _instance_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # No SO_REUSEADDR: on Windows it lets a second process bind the same port,
        # which silently defeated this guard and produced duplicate bot instances.
        _instance_socket.bind(("127.0.0.1", 49288))
        # listen() puts the socket in LISTENING so the keep-alive engine's netstat probe sees it
        _instance_socket.listen(1)
        return True
    except OSError:
        logger.warning("Another instance of NOVEXA is already running on this machine! Exiting to prevent duplicate replies.")
        print("\n" + "=" * 60)
        print("⚠️  DUPLICATE INSTANCE PREVENTED:")
        print("Another instance of NOVEXA is ALREADY running on your PC.")
        print("This duplicate instance was stopped to prevent 2x double replies.")
        print("=" * 60 + "\n")
        return False


# ==================== ENTRYPOINT ====================
def main():
    if not _acquire_instance_lock():
        sys.exit(0)

    if not DISCORD_TOKEN or DISCORD_TOKEN == "your_bot_token_here":
        logger.critical(
            "DISCORD_TOKEN is missing or invalid! "
            "Please configure your token in .env before running the bot."
        )
        print("\n" + "=" * 60)
        print("CRITICAL CONFIGURATION ERROR:")
        print("Please set your DISCORD_TOKEN in the .env file.")
        print("Copy .env.example to .env and insert your bot token from the Discord Developer Portal.")
        print("=" * 60 + "\n")
        sys.exit(1)

    try:
        bot.run(DISCORD_TOKEN)
    except discord.LoginFailure:
        logger.critical("Failed to log in: The provided Discord token is invalid.")
    except Exception as e:
        logger.critical(f"Fatal error during bot runtime: {e}", exc_info=True)


if __name__ == "__main__":
    main()

