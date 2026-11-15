"""NOVEXA - Mention Reply & React User Auto-Response Engine.

Features:
- Mention Reply: Automatically replies with a custom message/embed when a configured user is mentioned in chat.
  - Supports admin assignment: /mentionreply add @user <message>
  - Supports self assignment: /mentionreply set <message>
  - Supports removal: /mentionreply remove @user, /mentionreply clear
  - Supports listing: /mentionreply list
  - Dynamic placeholders: {user}, {username}, {target}, {target_name}, {server}, {time}
  - Anti-spam cooldown per channel to prevent spam rings.
- React User: Automatically adds a custom reaction emoji when a configured user sends a message.
  - /mentionreply react_add @user <emoji>
  - /mentionreply react_remove @user
  - /mentionreply react_list
  - Prefix shortcuts: n!reactuser / n!ru
- Zero-latency in-memory caching for real-time Discord gateway processing.
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
import time
import datetime
from typing import Optional, Dict, Tuple, Any, List

from database.database import db
from config import BOT_NAME, BOT_PREFIX
from utils.embeds import success_embed, error_embed, info_embed, primary_embed
from utils.emojis import Emojis

logger = logging.getLogger("novexa.mention_reply")

COLOR_MENTION = 0x5865F2  # Blurple
COLOR_SUCCESS = 0x2ECC71  # Green
COLOR_WARNING = 0xF1C40F  # Gold


class MentionReply(commands.Cog):
    """Automated Mention Replies and React User System."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # In-memory caches: (guild_id, user_id) -> data
        self._mention_cache: Dict[Tuple[int, int], Dict[str, Any]] = {}
        self._react_cache: Dict[Tuple[int, int], str] = {}
        # Cooldown cache: (guild_id, channel_id, user_id) -> last_timestamp
        self._cooldowns: Dict[Tuple[int, int, int], float] = {}

    async def cog_load(self):
        """Preload all active mention replies and react users into memory."""
        try:
            m_rows = await db.fetchall(
                "SELECT guild_id, user_id, reply_message, embed_enabled, cooldown_seconds "
                "FROM mention_replies WHERE is_enabled = 1"
            )
            for r in m_rows:
                self._mention_cache[(r["guild_id"], r["user_id"])] = {
                    "message": r["reply_message"],
                    "embed": bool(r["embed_enabled"]),
                    "cooldown": r["cooldown_seconds"] or 5,
                }

            r_rows = await db.fetchall(
                "SELECT guild_id, user_id, emoji FROM react_users WHERE is_enabled = 1"
            )
            for r in r_rows:
                self._react_cache[(r["guild_id"], r["user_id"])] = r["emoji"]

            logger.info(
                f"Loaded {len(self._mention_cache)} mention replies and {len(self._react_cache)} react users into memory cache."
            )
        except Exception as e:
            logger.error(f"Error loading mention reply cache: {e}", exc_info=True)

    # ==================== SLASH COMMAND GROUP ====================
    mention_group = app_commands.Group(
        name="mentionreply",
        description="Automated Mention Replies and React User system",
    )

    @mention_group.command(
        name="add",
        description="Configure an automatic reply when a specific user is mentioned",
    )
    @app_commands.describe(
        user="The user to set a mention reply for",
        message="The message to reply with (supports {user}, {target}, {server})",
        use_embed="Send reply as a rich Discord embed card",
        cooldown="Anti-spam cooldown seconds in that channel (default: 5s)",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def slash_mention_add(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        message: str,
        use_embed: bool = False,
        cooldown: int = 5,
    ):
        clean_msg = message.strip()
        if not clean_msg:
            return await interaction.response.send_message(
                embed=error_embed("Invalid Input", "Reply message cannot be empty."),
                ephemeral=True,
            )

        cd = max(1, min(60, cooldown))
        guild_id = interaction.guild_id

        await db.execute(
            "INSERT INTO mention_replies (guild_id, user_id, reply_message, embed_enabled, is_enabled, cooldown_seconds, created_by) "
            "VALUES (?, ?, ?, ?, 1, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET "
            "reply_message = excluded.reply_message, "
            "embed_enabled = excluded.embed_enabled, "
            "is_enabled = 1, "
            "cooldown_seconds = excluded.cooldown_seconds, "
            "created_by = excluded.created_by",
            (guild_id, user.id, clean_msg, 1 if use_embed else 0, cd, interaction.user.id),
        )

        self._mention_cache[(guild_id, user.id)] = {
            "message": clean_msg,
            "embed": use_embed,
            "cooldown": cd,
        }

        embed = discord.Embed(
            title="✅ Mention Reply Configured",
            description=(
                f"Successfully set an automatic mention reply for {user.mention}!\n\n"
                f"**Reply Message:**\n> {clean_msg}\n\n"
                f"• **Format:** {'Rich Embed' if use_embed else 'Standard Text'}\n"
                f"• **Channel Cooldown:** `{cd}s`"
            ),
            color=COLOR_SUCCESS,
        )
        embed.set_footer(text="Placeholders available: {user}, {target}, {server}, {time}")
        await interaction.response.send_message(embed=embed)

    @mention_group.command(
        name="remove",
        description="Remove an automatic mention reply for a user",
    )
    @app_commands.describe(user="The user whose mention reply you want to delete")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def slash_mention_remove(self, interaction: discord.Interaction, user: discord.Member):
        guild_id = interaction.guild_id
        await db.execute(
            "DELETE FROM mention_replies WHERE guild_id = ? AND user_id = ?",
            (guild_id, user.id),
        )
        self._mention_cache.pop((guild_id, user.id), None)

        embed = discord.Embed(
            title="🗑️ Mention Reply Removed",
            description=f"Automatic mention reply for {user.mention} has been deleted.",
            color=COLOR_WARNING,
        )
        await interaction.response.send_message(embed=embed)

    @mention_group.command(
        name="set",
        description="Set your own personal mention reply / AFK message",
    )
    @app_commands.describe(message="Your personal reply message when anyone mentions you")
    async def slash_mention_set(self, interaction: discord.Interaction, message: str):
        clean_msg = message.strip()
        if not clean_msg:
            return await interaction.response.send_message(
                embed=error_embed("Invalid Input", "Reply message cannot be empty."),
                ephemeral=True,
            )

        guild_id = interaction.guild_id
        user_id = interaction.user.id

        await db.execute(
            "INSERT INTO mention_replies (guild_id, user_id, reply_message, embed_enabled, is_enabled, cooldown_seconds, created_by) "
            "VALUES (?, ?, ?, 0, 1, 5, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET "
            "reply_message = excluded.reply_message, "
            "is_enabled = 1, "
            "created_by = excluded.created_by",
            (guild_id, user_id, clean_msg, user_id),
        )

        self._mention_cache[(guild_id, user_id)] = {
            "message": clean_msg,
            "embed": False,
            "cooldown": 5,
        }

        embed = discord.Embed(
            title="✅ Personal Mention Reply Set",
            description=(
                f"Whenever someone mentions you in this server, NOVEXA will reply with:\n> *{clean_msg}*"
            ),
            color=COLOR_SUCCESS,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @mention_group.command(
        name="clear",
        description="Clear your personal mention reply",
    )
    async def slash_mention_clear(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        user_id = interaction.user.id

        await db.execute(
            "DELETE FROM mention_replies WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        self._mention_cache.pop((guild_id, user_id), None)

        embed = discord.Embed(
            title="🗑️ Personal Mention Reply Cleared",
            description="Your automatic mention reply has been removed.",
            color=COLOR_SUCCESS,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @mention_group.command(
        name="list",
        description="List all active mention replies configured in this server",
    )
    async def slash_mention_list(self, interaction: discord.Interaction):
        rows = await db.fetchall(
            "SELECT user_id, reply_message, embed_enabled, cooldown_seconds FROM mention_replies WHERE guild_id = ? AND is_enabled = 1",
            (interaction.guild_id,),
        )
        if not rows:
            return await interaction.response.send_message(
                embed=info_embed(
                    "No Mention Replies",
                    "There are currently no automatic mention replies configured in this server.\nUse `/mentionreply add @user <message>` to create one!",
                ),
                ephemeral=True,
            )

        lines = []
        for idx, r in enumerate(rows[:15], start=1):
            u = interaction.guild.get_member(r["user_id"])
            u_str = u.mention if u else f"`{r['user_id']}`"
            preview = r["reply_message"][:45] + ("..." if len(r["reply_message"]) > 45 else "")
            lines.append(f"**{idx}.** {u_str} — \"{preview}\" (`{r['cooldown_seconds']}s`)")

        embed = discord.Embed(
            title=f"📋 Active Mention Replies ({len(rows)})",
            description="\n".join(lines),
            color=COLOR_MENTION,
        )
        embed.set_footer(text=f"Total: {len(rows)} configured • NOVEXA Automation")
        await interaction.response.send_message(embed=embed)

    # ---------------- REACT USER SUBCOMMANDS ----------------
    @mention_group.command(
        name="react_add",
        description="Automatically add an emoji reaction whenever a user sends a message",
    )
    @app_commands.describe(
        user="The user to auto-react to",
        emoji="The emoji to react with (e.g. ⭐, 🔥, or custom emoji)",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def slash_react_add(self, interaction: discord.Interaction, user: discord.Member, emoji: str):
        clean_emoji = emoji.strip()
        guild_id = interaction.guild_id

        await db.execute(
            "INSERT INTO react_users (guild_id, user_id, emoji, is_enabled, created_by) "
            "VALUES (?, ?, ?, 1, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET "
            "emoji = excluded.emoji, "
            "is_enabled = 1, "
            "created_by = excluded.created_by",
            (guild_id, user.id, clean_emoji, interaction.user.id),
        )
        self._react_cache[(guild_id, user.id)] = clean_emoji

        embed = discord.Embed(
            title="✅ React User Configured",
            description=f"NOVEXA will now automatically react with {clean_emoji} whenever {user.mention} sends a message!",
            color=COLOR_SUCCESS,
        )
        await interaction.response.send_message(embed=embed)

    @mention_group.command(
        name="react_remove",
        description="Remove auto-reaction for a user",
    )
    @app_commands.describe(user="The user whose auto-react you want to remove")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def slash_react_remove(self, interaction: discord.Interaction, user: discord.Member):
        guild_id = interaction.guild_id
        await db.execute(
            "DELETE FROM react_users WHERE guild_id = ? AND user_id = ?",
            (guild_id, user.id),
        )
        self._react_cache.pop((guild_id, user.id), None)

        embed = discord.Embed(
            title="🗑️ React User Removed",
            description=f"Auto-reaction for {user.mention} has been removed.",
            color=COLOR_WARNING,
        )
        await interaction.response.send_message(embed=embed)

    @mention_group.command(
        name="react_list",
        description="List all active react users in this server",
    )
    async def slash_react_list(self, interaction: discord.Interaction):
        rows = await db.fetchall(
            "SELECT user_id, emoji FROM react_users WHERE guild_id = ? AND is_enabled = 1",
            (interaction.guild_id,),
        )
        if not rows:
            return await interaction.response.send_message(
                embed=info_embed(
                    "No React Users",
                    "There are currently no react users configured in this server.\nUse `/mentionreply react_add @user <emoji>` to create one!",
                ),
                ephemeral=True,
            )

        lines = []
        for idx, r in enumerate(rows[:20], start=1):
            u = interaction.guild.get_member(r["user_id"])
            u_str = u.mention if u else f"`{r['user_id']}`"
            lines.append(f"**{idx}.** {u_str} ➔ {r['emoji']}")

        embed = discord.Embed(
            title=f"⭐ Active React Users ({len(rows)})",
            description="\n".join(lines),
            color=COLOR_MENTION,
        )
        await interaction.response.send_message(embed=embed)

    # ==================== PREFIX COMMANDS ====================
    @commands.group(name="mentionreply", aliases=["mr"], invoke_without_command=True)
    async def prefix_mentionreply(self, ctx: commands.Context):
        """Mention Reply command suite."""
        embed = discord.Embed(
            title="💬 Mention Reply Command Guide",
            description=(
                f"**Usage:**\n"
                f"• `{BOT_PREFIX}mr add @user <message>` — Admin configure mention reply\n"
                f"• `{BOT_PREFIX}mr remove @user` — Admin remove mention reply\n"
                f"• `{BOT_PREFIX}mr set <message>` — Member set their own reply\n"
                f"• `{BOT_PREFIX}mr clear` — Member clear their reply\n"
                f"• `{BOT_PREFIX}mr list` — List all mention replies\n\n"
                f"**React User Commands:**\n"
                f"• `{BOT_PREFIX}reactuser add @user <emoji>` (or `n!ru add`)\n"
                f"• `{BOT_PREFIX}reactuser remove @user`\n"
                f"• `{BOT_PREFIX}reactuser list`"
            ),
            color=COLOR_MENTION,
        )
        await ctx.send(embed=embed)

    @prefix_mentionreply.command(name="add")
    @commands.has_permissions(manage_guild=True)
    async def p_mr_add(self, ctx: commands.Context, user: discord.Member, *, message: str):
        clean_msg = message.strip()
        guild_id = ctx.guild.id

        await db.execute(
            "INSERT INTO mention_replies (guild_id, user_id, reply_message, embed_enabled, is_enabled, cooldown_seconds, created_by) "
            "VALUES (?, ?, ?, 0, 1, 5, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET "
            "reply_message = excluded.reply_message, "
            "is_enabled = 1, "
            "created_by = excluded.created_by",
            (guild_id, user.id, clean_msg, ctx.author.id),
        )
        self._mention_cache[(guild_id, user.id)] = {
            "message": clean_msg,
            "embed": False,
            "cooldown": 5,
        }
        await ctx.send(f"✅ Set mention reply for {user.mention}: \"{clean_msg}\"")

    @prefix_mentionreply.command(name="remove", aliases=["del", "delete"])
    @commands.has_permissions(manage_guild=True)
    async def p_mr_remove(self, ctx: commands.Context, user: discord.Member):
        guild_id = ctx.guild.id
        await db.execute(
            "DELETE FROM mention_replies WHERE guild_id = ? AND user_id = ?",
            (guild_id, user.id),
        )
        self._mention_cache.pop((guild_id, user.id), None)
        await ctx.send(f"🗑️ Removed mention reply for {user.mention}.")

    @prefix_mentionreply.command(name="set")
    async def p_mr_set(self, ctx: commands.Context, *, message: str):
        clean_msg = message.strip()
        guild_id = ctx.guild.id
        user_id = ctx.author.id

        await db.execute(
            "INSERT INTO mention_replies (guild_id, user_id, reply_message, embed_enabled, is_enabled, cooldown_seconds, created_by) "
            "VALUES (?, ?, ?, 0, 1, 5, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET "
            "reply_message = excluded.reply_message, "
            "is_enabled = 1, "
            "created_by = excluded.created_by",
            (guild_id, user_id, clean_msg, user_id),
        )
        self._mention_cache[(guild_id, user_id)] = {
            "message": clean_msg,
            "embed": False,
            "cooldown": 5,
        }
        await ctx.send(f"✅ {ctx.author.mention}, your personal mention reply has been set: \"{clean_msg}\"")

    @prefix_mentionreply.command(name="clear")
    async def p_mr_clear(self, ctx: commands.Context):
        guild_id = ctx.guild.id
        user_id = ctx.author.id
        await db.execute(
            "DELETE FROM mention_replies WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        self._mention_cache.pop((guild_id, user_id), None)
        await ctx.send(f"🗑️ {ctx.author.mention}, your personal mention reply has been cleared.")

    @prefix_mentionreply.command(name="list")
    async def p_mr_list(self, ctx: commands.Context):
        rows = await db.fetchall(
            "SELECT user_id, reply_message FROM mention_replies WHERE guild_id = ? AND is_enabled = 1",
            (ctx.guild.id,),
        )
        if not rows:
            return await ctx.send("ℹ️ No mention replies configured in this server.")

        lines = []
        for idx, r in enumerate(rows[:15], start=1):
            u = ctx.guild.get_member(r["user_id"])
            u_str = u.mention if u else f"`{r['user_id']}`"
            preview = r["reply_message"][:40] + ("..." if len(r["reply_message"]) > 40 else "")
            lines.append(f"**{idx}.** {u_str} ➔ \"{preview}\"")

        embed = discord.Embed(
            title=f"📋 Active Mention Replies ({len(rows)})",
            description="\n".join(lines),
            color=COLOR_MENTION,
        )
        await ctx.send(embed=embed)

    # ---------------- PREFIX REACT USER COMMANDS ----------------
    @commands.group(name="reactuser", aliases=["ru", "autoreact"], invoke_without_command=True)
    async def prefix_reactuser(self, ctx: commands.Context):
        """React User commands."""
        embed = discord.Embed(
            title="⭐ React User System",
            description=(
                f"Automatically add emoji reactions to a user's messages.\n\n"
                f"• `{BOT_PREFIX}reactuser add @user <emoji>` — Add auto-react\n"
                f"• `{BOT_PREFIX}reactuser remove @user` — Remove auto-react\n"
                f"• `{BOT_PREFIX}reactuser list` — List all auto-react users"
            ),
            color=COLOR_MENTION,
        )
        await ctx.send(embed=embed)

    @prefix_reactuser.command(name="add")
    @commands.has_permissions(manage_guild=True)
    async def p_ru_add(self, ctx: commands.Context, user: discord.Member, emoji: str):
        clean_emoji = emoji.strip()
        guild_id = ctx.guild.id

        await db.execute(
            "INSERT INTO react_users (guild_id, user_id, emoji, is_enabled, created_by) "
            "VALUES (?, ?, ?, 1, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET "
            "emoji = excluded.emoji, "
            "is_enabled = 1, "
            "created_by = excluded.created_by",
            (guild_id, user.id, clean_emoji, ctx.author.id),
        )
        self._react_cache[(guild_id, user.id)] = clean_emoji
        await ctx.send(f"✅ Added auto-reaction {clean_emoji} for {user.mention}!")

    @prefix_reactuser.command(name="remove", aliases=["del", "delete"])
    @commands.has_permissions(manage_guild=True)
    async def p_ru_remove(self, ctx: commands.Context, user: discord.Member):
        guild_id = ctx.guild.id
        await db.execute(
            "DELETE FROM react_users WHERE guild_id = ? AND user_id = ?",
            (guild_id, user.id),
        )
        self._react_cache.pop((guild_id, user.id), None)
        await ctx.send(f"🗑️ Removed auto-reaction for {user.mention}.")

    @prefix_reactuser.command(name="list")
    async def p_ru_list(self, ctx: commands.Context):
        rows = await db.fetchall(
            "SELECT user_id, emoji FROM react_users WHERE guild_id = ? AND is_enabled = 1",
            (ctx.guild.id,),
        )
        if not rows:
            return await ctx.send("ℹ️ No react users configured in this server.")

        lines = []
        for idx, r in enumerate(rows[:20], start=1):
            u = ctx.guild.get_member(r["user_id"])
            u_str = u.mention if u else f"`{r['user_id']}`"
            lines.append(f"**{idx}.** {u_str} ➔ {r['emoji']}")

        embed = discord.Embed(
            title=f"⭐ Active React Users ({len(rows)})",
            description="\n".join(lines),
            color=COLOR_MENTION,
        )
        await ctx.send(embed=embed)

    # ==================== GATEWAY EVENT LISTENER ====================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for messages to execute React User and Mention Replies."""
        # 1. Ignore bots and DMs
        if message.author.bot or not message.guild:
            return

        guild_id = message.guild.id
        author_id = message.author.id

        # 2. Check React User (Fast O(1) in-memory check)
        react_emoji = self._react_cache.get((guild_id, author_id))
        if react_emoji:
            try:
                # If custom emoji format <:name:id> or <a:name:id>, extract or parse
                if react_emoji.startswith("<") and react_emoji.endswith(">"):
                    emoji_parts = react_emoji.strip("<>").split(":")
                    if len(emoji_parts) >= 3:
                        e_id = int(emoji_parts[-1])
                        custom_e = self.bot.get_emoji(e_id)
                        if custom_e:
                            await message.add_reaction(custom_e)
                        else:
                            await message.add_reaction(react_emoji)
                    else:
                        await message.add_reaction(react_emoji)
                else:
                    await message.add_reaction(react_emoji)
            except Exception as e:
                logger.debug(f"Failed to add auto-reaction for user {author_id}: {e}")

        # 3. Check Mention Replies (Fast O(1) in-memory check)
        if not message.mentions:
            return

        now = time.time()
        for target in message.mentions:
            # Skip self-mentions or bot mentions
            if target.id == author_id or target.bot:
                continue

            config = self._mention_cache.get((guild_id, target.id))
            if not config:
                continue

            # Anti-spam cooldown check per channel per target
            cd_key = (guild_id, message.channel.id, target.id)
            last_time = self._cooldowns.get(cd_key, 0.0)
            cooldown_period = config.get("cooldown", 5)

            if now - last_time < cooldown_period:
                continue  # Rate limited to prevent spam loops

            self._cooldowns[cd_key] = now

            # Format template variables
            raw_msg = config["message"]
            current_time_str = datetime.datetime.now().strftime("%I:%M %p")
            formatted_msg = (
                raw_msg.replace("{user}", message.author.mention)
                .replace("{username}", message.author.display_name)
                .replace("{target}", target.mention)
                .replace("{target_name}", target.display_name)
                .replace("{server}", message.guild.name)
                .replace("{time}", current_time_str)
            )

            try:
                if config.get("embed"):
                    embed = discord.Embed(
                        description=formatted_msg,
                        color=COLOR_MENTION,
                    )
                    embed.set_author(
                        name=f"Automated Reply for {target.display_name}",
                        icon_url=target.display_avatar.url,
                    )
                    await message.reply(embed=embed, mention_author=False)
                else:
                    await message.reply(formatted_msg, mention_author=False)
            except Exception as e:
                logger.warning(f"Failed to send mention reply in {message.channel.id}: {e}")

            # Reply to the first matched mentioned user to avoid double replies in one message
            break


async def setup(bot: commands.Bot):
    await bot.add_cog(MentionReply(bot))

