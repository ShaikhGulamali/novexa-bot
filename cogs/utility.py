import discord
from discord.ext import commands
from discord import app_commands
import logging
import datetime
import random
import asyncio
from typing import Optional, List
from database.database import db
from utils.embeds import primary_embed, success_embed, error_embed, warning_embed, info_embed
from utils.emojis import Emojis
from utils.permissions import has_admin_or_owner
from utils.helpers import parse_time, format_duration
from config import BOT_NAME, BOT_VERSION, BOT_DESCRIPTION

logger = logging.getLogger("novexa.utility")


class VoiceJoinView(discord.ui.View):
    """Persistent interactive panel to connect/disconnect bot to Voice Channel."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Join Voice",
        style=discord.ButtonStyle.success,
        emoji="🔊",
        custom_id="novexa_voice_join_btn",
    )
    async def btn_join(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        if not isinstance(member, discord.Member) or not member.voice or not member.voice.channel:
            await interaction.response.send_message(
                embed=warning_embed(
                    "Voice Required",
                    f"{Emojis.ARROW} Pehle kisi voice channel me join kijiye, phir button dabayein!",
                ),
                ephemeral=True,
            )
            return

        target_channel = member.voice.channel
        perms = target_channel.permissions_for(interaction.guild.me)
        if not perms.connect:
            await interaction.response.send_message(
                embed=error_embed(
                    "Missing Permissions",
                    f"{Emojis.ARROW} Mere paas {target_channel.mention} me connect hone ki permission nahi hai!",
                ),
                ephemeral=True,
            )
            return

        vc = interaction.guild.voice_client
        try:
            if vc and vc.is_connected():
                if vc.channel.id != target_channel.id:
                    await vc.move_to(target_channel)
                    await interaction.response.send_message(
                        embed=success_embed(
                            "Moved Voice Channel",
                            f"{Emojis.TICK} Successfully moved to {target_channel.mention}!",
                        ),
                        ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        embed=info_embed(
                            "Already Connected",
                            f"{Emojis.SPARKLES} Bot pehle se {target_channel.mention} me connected hai!",
                        ),
                        ephemeral=True,
                    )
            else:
                await target_channel.connect(self_deaf=True)
                await interaction.response.send_message(
                    embed=success_embed(
                        "Voice Connected",
                        f"{Emojis.TICK} Successfully joined {target_channel.mention}!",
                    ),
                    ephemeral=True,
                )
        except Exception as e:
            await interaction.response.send_message(
                embed=error_embed("Connection Error", f"Voice connect karte waqt error aaya: `{e}`"),
                ephemeral=True,
            )

    @discord.ui.button(
        label="Leave Voice",
        style=discord.ButtonStyle.danger,
        emoji="🔌",
        custom_id="novexa_voice_leave_btn",
    )
    async def btn_leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_connected():
            ch_name = vc.channel.mention if vc.channel else "voice channel"
            await vc.disconnect(force=True)
            await interaction.response.send_message(
                embed=info_embed(
                    "Voice Disconnected",
                    f"{Emojis.ARROW} Successfully disconnected from {ch_name}!",
                ),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                embed=warning_embed(
                    "Not Connected",
                    f"{Emojis.ARROW} Bot kisi bhi voice channel me connected nahi hai.",
                ),
                ephemeral=True,
            )


class GiveawayJoinView(discord.ui.View):
    """Interactive button to enter an ongoing server giveaway."""

    def __init__(self, message_id: int):
        super().__init__(timeout=None)
        self.message_id = message_id

    @discord.ui.button(label="Enter Giveaway", style=discord.ButtonStyle.success, emoji="🎉", custom_id="gulamali_giveaway_enter")
    async def btn_enter(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🎉 You have entered the giveaway! Best of luck!", ephemeral=True)


class Utility(commands.Cog):
    """Essential Server Tools, Starboard, Giveaways, Polls & Auto-Responders."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle Auto-Responders and Sticky Messages."""
        if message.author.bot or not message.guild:
            return

        # 1. Auto Responders
        content_lower = message.content.strip().lower()
        responders = await db.fetchall(
            "SELECT trigger, response, match_type FROM auto_responders WHERE guild_id = ?",
            (message.guild.id,),
        )
        for r in responders:
            trigger = r["trigger"].lower()
            matched = (content_lower == trigger) if r["match_type"] == "exact" else (trigger in content_lower)
            if matched:
                try:
                    await message.channel.send(r["response"])
                except Exception:
                    pass
                break

        # 2. Sticky Message check
        sticky = await db.fetchone(
            "SELECT content, last_message_id FROM sticky_messages WHERE channel_id = ? AND guild_id = ?",
            (message.channel.id, message.guild.id),
        )
        if sticky and sticky["content"]:
            # Delete old sticky message if exists
            old_id = sticky["last_message_id"]
            if old_id and old_id != message.id:
                try:
                    old_msg = await message.channel.fetch_message(old_id)
                    await old_msg.delete()
                except Exception:
                    pass

            # Post sticky message at the bottom
            embed = info_embed("📌 Pinned Notice", sticky["content"])
            embed.set_footer(text="NOVEXA • Sticky Notice")
            new_msg = await message.channel.send(embed=embed)
            await db.execute(
                "UPDATE sticky_messages SET last_message_id = ? WHERE channel_id = ?",
                (new_msg.id, message.channel.id),
            )

        # 3. Plain Chat Typing "Send Message" listener
        # Formats:
        # "send message #channel <text>"
        # "sendmessage #channel <text>"
        # "send #channel <text>"
        raw_text = message.content.strip()
        lower_text = raw_text.lower()
        if (
            lower_text.startswith(("send message ", "sendmessage ", "send "))
            and message.channel_mentions
            and isinstance(message.author, discord.Member)
            and (message.author.guild_permissions.manage_messages or message.author.guild_permissions.administrator)
        ):
            target_channel = message.channel_mentions[0]
            parts = raw_text.split(target_channel.mention, 1)
            if len(parts) > 1 and parts[1].strip():
                msg_body = parts[1].strip()
                processed = self._expand_custom_emojis(msg_body)

                file_to_send = None
                if message.attachments:
                    try:
                        import io
                        b = await message.attachments[0].read()
                        file_to_send = discord.File(io.BytesIO(b), filename=message.attachments[0].filename)
                    except Exception:
                        pass

                try:
                    await target_channel.send(content=processed, file=file_to_send)
                    if message.guild.me.guild_permissions.manage_messages:
                        try:
                            await message.delete()
                        except Exception:
                            pass
                    await message.channel.send(
                        embed=success_embed("Send Message", f"Message dispatched to {target_channel.mention}!"),
                        delete_after=5,
                    )
                    return
                except Exception as e:
                    await message.channel.send(embed=error_embed("Send Message Error", str(e)), delete_after=8)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Starboard listener for ⭐ reactions."""
        if str(payload.emoji) != "⭐" or not payload.guild_id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        cfg = await db.fetchone("SELECT * FROM starboard_config WHERE guild_id = ?", (guild.id,))
        if not cfg or not cfg["enabled"] or not cfg["channel_id"]:
            return

        starboard_channel = guild.get_channel(cfg["channel_id"])
        if not starboard_channel or not isinstance(starboard_channel, discord.TextChannel):
            return

        origin_channel = guild.get_channel(payload.channel_id)
        if not origin_channel or not isinstance(origin_channel, discord.TextChannel):
            return

        try:
            origin_message = await origin_channel.fetch_message(payload.message_id)
        except Exception:
            return

        reaction = discord.utils.get(origin_message.reactions, emoji="⭐")
        star_count = reaction.count if reaction else 0

        threshold = cfg["star_count"] or 3
        if star_count < threshold:
            return

        # Check if already posted
        existing = await db.fetchone(
            "SELECT starboard_message_id FROM starboard_messages WHERE original_message_id = ?",
            (origin_message.id,),
        )

        embed = primary_embed(
            title=f"⭐ Starred Message ({star_count} stars)",
            description=origin_message.content or "*Attachment/Embed*",
        )
        embed.set_author(name=origin_message.author.display_name, icon_url=origin_message.author.display_avatar.url)
        embed.add_field(name="Source", value=f"[Jump to Message]({origin_message.jump_url})", inline=False)
        if origin_message.attachments:
            embed.set_image(url=origin_message.attachments[0].url)

        if existing and existing["starboard_message_id"]:
            try:
                sb_msg = await starboard_channel.fetch_message(existing["starboard_message_id"])
                await sb_msg.edit(content=f"⭐ **{star_count}** | {origin_channel.mention}", embed=embed)
            except Exception:
                pass
        else:
            sb_msg = await starboard_channel.send(content=f"⭐ **{star_count}** | {origin_channel.mention}", embed=embed)
            await db.execute(
                "INSERT INTO starboard_messages (original_message_id, starboard_message_id, guild_id, channel_id) VALUES (?, ?, ?, ?)",
                (origin_message.id, sb_msg.id, guild.id, origin_channel.id),
            )

    # ==================== SLASH COMMANDS ====================

    info_group = app_commands.Group(name="info", description="Bot, server, and member lookup information")

    @info_group.command(name="ping", description="Check the bot's WebSocket latency and responsiveness")
    async def ping(self, interaction: discord.Interaction):
        latency_ms = round(self.bot.latency * 1000)
        embed = success_embed("🏓 Pong!", f"**API Latency:** `{latency_ms}ms`\n**Database:** `Operational (SQLite WAL)`")
        await interaction.response.send_message(embed=embed)

    @info_group.command(name="bot", description="View information and specs for NOVEXA")
    async def botinfo(self, interaction: discord.Interaction):
        embed = primary_embed(title=f"🤖 {BOT_NAME} v{BOT_VERSION}", description=BOT_DESCRIPTION)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name="Servers (Guilds)", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="Total Users", value=f"{sum(g.member_count or 0 for g in self.bot.guilds):,}", inline=True)
        embed.add_field(name="Framework", value="discord.py 2.x • Python 3.12+", inline=True)
        embed.add_field(name="Features", value="Anti-Nuke • Music • Tickets • Leveling • Payments • Logging", inline=False)
        await interaction.response.send_message(embed=embed)

    @info_group.command(name="server", description="Display comprehensive information about the current server")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = primary_embed(title=f"🏰 Server Information: {guild.name}")
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        owner = guild.owner or await self.bot.fetch_user(guild.owner_id)
        embed.add_field(name="Owner", value=owner.mention if owner else "Unknown", inline=True)
        embed.add_field(name="Server ID", value=str(guild.id), inline=True)
        embed.add_field(name="Created On", value=guild.created_at.strftime("%b %d, %Y"), inline=True)

        embed.add_field(name="Total Members", value=str(guild.member_count), inline=True)
        embed.add_field(name="Text Channels", value=str(len(guild.text_channels)), inline=True)
        embed.add_field(name="Voice Channels", value=str(len(guild.voice_channels)), inline=True)

        embed.add_field(name="Roles Count", value=str(len(guild.roles)), inline=True)
        embed.add_field(name="Boost Level", value=f"Tier {guild.premium_tier} ({guild.premium_subscription_count} boosts)", inline=True)
        embed.add_field(name="Verification Level", value=str(guild.verification_level).capitalize(), inline=True)

        await interaction.response.send_message(embed=embed)

    @info_group.command(name="user", description="View detailed information about a member")
    @app_commands.describe(user="Member to inspect")
    async def userinfo(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        target = user or interaction.user
        if not isinstance(target, discord.Member):
            return await interaction.response.send_message("User not found.", ephemeral=True)

        embed = primary_embed(title=f"👤 User Info - {target.display_name}")
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="User ID", value=str(target.id), inline=True)
        embed.add_field(name="Joined Server", value=target.joined_at.strftime("%b %d, %Y") if target.joined_at else "Unknown", inline=True)
        embed.add_field(name="Account Created", value=target.created_at.strftime("%b %d, %Y"), inline=True)

        roles_list = [r.mention for r in reversed(target.roles) if not r.is_default()]
        roles_str = ", ".join(roles_list[:12]) if roles_list else "None"
        if len(roles_list) > 12:
            roles_str += f" (+{len(roles_list) - 12} more)"
        embed.add_field(name=f"Roles ({len(roles_list)})", value=roles_str, inline=False)
        embed.add_field(name="Highest Role", value=target.top_role.mention, inline=True)
        embed.add_field(name="Bot Account?", value="Yes" if target.bot else "No", inline=True)

        await interaction.response.send_message(embed=embed)

    @info_group.command(name="avatar", description="Display a user's high-resolution avatar")
    @app_commands.describe(user="User to view avatar for")
    async def avatar(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        target = user or interaction.user
        embed = primary_embed(title=f"🖼️ Avatar: {target.display_name}")
        embed.set_image(url=target.display_avatar.url)
        embed.add_field(name="Download Links", value=f"[PNG]({target.display_avatar.with_format('png').url}) | [JPG]({target.display_avatar.with_format('jpg').url}) | [WebP]({target.display_avatar.with_format('webp').url})")
        await interaction.response.send_message(embed=embed)

    @info_group.command(name="banner", description="Display a user's profile banner if available")
    @app_commands.describe(user="User to inspect banner")
    async def banner(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        target_user = user or interaction.user
        fetched_user = await self.bot.fetch_user(target_user.id)
        if not fetched_user.banner:
            return await interaction.response.send_message(embed=info_embed("No Banner", f"{fetched_user.display_name} has no banner set."), ephemeral=True)

        embed = primary_embed(title=f"🎨 Banner: {fetched_user.display_name}")
        embed.set_image(url=fetched_user.banner.url)
        await interaction.response.send_message(embed=embed)

    @info_group.command(name="members", description="Display the current member count of this server")
    async def membercount(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = primary_embed(title=f"👥 Member Count: {guild.name}")
        embed.add_field(name="Total Members", value=f"**{guild.member_count:,}**", inline=True)
        embed.add_field(name="Humans", value=f"**{sum(1 for m in guild.members if not m.bot):,}**", inline=True)
        embed.add_field(name="Bots", value=f"**{sum(1 for m in guild.members if m.bot):,}**", inline=True)
        await interaction.response.send_message(embed=embed)

    community_group = app_commands.Group(name="community", description="Interactive community polls and server suggestions")

    @community_group.command(name="poll", description="Create an interactive server poll")
    @app_commands.describe(
        question="Poll question",
        option1="Option 1",
        option2="Option 2",
        option3="Optional Option 3",
        option4="Optional Option 4",
    )
    async def poll(
        self,
        interaction: discord.Interaction,
        question: str,
        option1: str,
        option2: str,
        option3: Optional[str] = None,
        option4: Optional[str] = None,
    ):
        options = [option1, option2]
        if option3:
            options.append(option3)
        if option4:
            options.append(option4)

        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
        embed = primary_embed(title=f"📊 Poll: {question}")
        embed.set_footer(text=f"Poll started by {interaction.user.display_name}")

        desc = []
        for i, opt in enumerate(options):
            desc.append(f"{emojis[i]} **{opt}**")
        embed.description = "\n\n".join(desc)

        await interaction.response.send_message("Poll created!", ephemeral=True)
        poll_msg = await interaction.channel.send(embed=embed)
        for i in range(len(options)):
            await poll_msg.add_reaction(emojis[i])

    @community_group.command(name="suggest", description="Submit a suggestion for the server")
    @app_commands.describe(idea="Your suggestion or feedback")
    async def suggest(self, interaction: discord.Interaction, idea: str):
        embed = primary_embed(title="💡 New Server Suggestion", description=idea)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text="Vote using the reactions below!")

        msg = await interaction.channel.send(embed=embed)
        await msg.add_reaction("👍")
        await msg.add_reaction("👎")
        await interaction.response.send_message(embed=success_embed("Suggestion Submitted", "Your suggestion was posted!"), ephemeral=True)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text="Vote using the reactions below!")

        msg = await interaction.channel.send(embed=embed)
        await msg.add_reaction("👍")
        await msg.add_reaction("👎")
        await interaction.response.send_message(embed=success_embed("Suggestion Submitted", "Your suggestion was posted!"), ephemeral=True)

    giveaway = app_commands.Group(name="giveaway", description="Server giveaways")

    @giveaway.command(name="start", description="Launch an automatic server giveaway with timer")
    @has_admin_or_owner()
    @app_commands.describe(
        prize="What is being given away?",
        duration="Duration like 30m, 2h, 1d",
        winners="Number of winners (default: 1)",
    )
    async def giveaway_start(self, interaction: discord.Interaction, prize: str, duration: str, winners: int = 1):
        seconds = parse_time(duration)
        if not seconds or seconds < 10:
            return await interaction.response.send_message(embed=error_embed("Invalid Duration", "Please provide a duration like `10m`, `1h`, or `1d`."), ephemeral=True)

        end_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=seconds)
        end_timestamp = int(end_time.timestamp())

        embed = primary_embed(
            title=f"🎉 GIVEAWAY: {prize}",
            description=f"Click the button below to enter!\n\n"
                        f"**Prize:** {prize}\n"
                        f"**Winners:** {winners}\n"
                        f"**Hosted By:** {interaction.user.mention}\n"
                        f"**Ends:** <t:{end_timestamp}:R> (<t:{end_timestamp}:f>)"
        )
        embed.set_footer(text="NOVEXA • Giveaways")

        await interaction.response.send_message("Launching giveaway...", ephemeral=True)
        gw_msg = await interaction.channel.send(embed=embed)
        view = GiveawayJoinView(gw_msg.id)
        await gw_msg.edit(view=view)

        # Record giveaway
        await db.execute(
            """
            INSERT INTO giveaways (message_id, guild_id, channel_id, prize, winners_count, end_time, host_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (gw_msg.id, interaction.guild_id, interaction.channel_id, prize, winners, end_time.timestamp(), interaction.user.id),
        )

        # Background sleep task to conclude giveaway
        async def end_giveaway():
            await asyncio.sleep(seconds)
            # Pick random reaction or users from guild
            try:
                eligible = [m for m in interaction.guild.members if not m.bot]
                if not eligible:
                    return await interaction.channel.send(f"No valid participants for **{prize}**.")
                chosen = random.sample(eligible, k=min(winners, len(eligible)))
                winners_mention = ", ".join(m.mention for m in chosen)

                win_embed = success_embed(
                    "🎉 Giveaway Concluded!",
                    f"**Prize:** {prize}\n**Winner(s):** {winners_mention}\n**Hosted By:** {interaction.user.mention}"
                )
                await interaction.channel.send(content=f"Congratulations {winners_mention}!", embed=win_embed)
                await db.execute("UPDATE giveaways SET ended = 1 WHERE message_id = ?", (gw_msg.id,))
            except Exception as e:
                logger.error(f"Error concluding giveaway: {e}")

        self.bot.loop.create_task(end_giveaway())

    starboard = app_commands.Group(name="starboard", description="Configure the Starboard showcase channel")

    @starboard.command(name="setup", description="Configure the Starboard showcase channel")
    @has_admin_or_owner()
    @app_commands.describe(channel="Channel where starred messages will be posted", star_count="Number of stars required (default 3)")
    async def starboard_setup(self, interaction: discord.Interaction, channel: discord.TextChannel, star_count: int = 3):
        await db.execute(
            """
            INSERT INTO starboard_config (guild_id, channel_id, star_count, enabled)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(guild_id) DO UPDATE SET
                channel_id = excluded.channel_id,
                star_count = excluded.star_count,
                enabled = 1
            """,
            (interaction.guild_id, channel.id, star_count),
        )
        await interaction.response.send_message(
            embed=success_embed("Starboard Configured", f"Starboard channel set to {channel.mention} (Threshold: ⭐ {star_count})."),
            ephemeral=True,
        )

    sticky = app_commands.Group(name="sticky", description="Stick persistent messages to the bottom of channels")

    @sticky.command(name="set", description="Stick a persistent message to the bottom of this channel")
    @has_admin_or_owner()
    @app_commands.describe(content="Notice text to keep stuck at the bottom")
    async def sticky_set(self, interaction: discord.Interaction, content: str):
        await db.execute(
            """
            INSERT INTO sticky_messages (channel_id, guild_id, content)
            VALUES (?, ?, ?)
            ON CONFLICT(channel_id) DO UPDATE SET content = excluded.content
            """,
            (interaction.channel_id, interaction.guild_id, content),
        )
        await interaction.response.send_message(
            embed=success_embed("Sticky Message Set", "This notice will stick to the bottom of the channel when new messages arrive."),
            ephemeral=True,
        )

    @sticky.command(name="remove", description="Remove sticky message from this channel")
    @has_admin_or_owner()
    async def sticky_remove(self, interaction: discord.Interaction):
        await db.execute("DELETE FROM sticky_messages WHERE channel_id = ?", (interaction.channel_id,))
        await interaction.response.send_message(
            embed=success_embed("Sticky Message Removed", "Sticky notice removed from this channel."),
            ephemeral=True,
        )

    # ==================== BROADCAST / SEND MESSAGE / AUTO-RESPONDER ====================

    broadcast = app_commands.Group(name="broadcast", description="Broadcast messages and automated responders")

    @broadcast.command(name="autoresponder", description="Create an automated auto-responder trigger")
    @has_admin_or_owner()
    @app_commands.choices(match_type=[
        app_commands.Choice(name="Exact Match", value="exact"),
        app_commands.Choice(name="Contains Keyword", value="contains"),
    ])
    @app_commands.describe(trigger="Trigger phrase", response="Reply text", match_type="How to match trigger")
    async def autoresponder(self, interaction: discord.Interaction, trigger: str, response: str, match_type: app_commands.Choice[str]):
        await db.execute(
            "INSERT INTO auto_responders (guild_id, trigger, response, match_type) VALUES (?, ?, ?, ?)",
            (interaction.guild_id, trigger.strip(), response.strip(), match_type.value),
        )
        await interaction.response.send_message(
            embed=success_embed("Auto Responder Created", f"**Trigger:** `{trigger}` ({match_type.name})\n**Response:** {response}"),
            ephemeral=True,
        )

    # ==================== SEND MESSAGE / CHANNEL DISPATCHER ====================

    async def _handle_send_message_flow(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel],
        message: Optional[str],
        attachment: Optional[discord.Attachment],
        reply_to: Optional[str],
    ):
        target_channel = channel or interaction.channel
        if not isinstance(target_channel, discord.TextChannel):
            return await interaction.response.send_message("Please select a valid text channel.", ephemeral=True)

        if not message and not attachment:
            # If no content was typed in the slash arguments, open the multi-line "Send Message" modal!
            modal = SendMessageModal(self, target_channel)
            return await interaction.response.send_modal(modal)

        await interaction.response.defer(ephemeral=True)

        # Expand shorthand :emoji_name: if accessible by bot
        processed_message = self._expand_custom_emojis(message) if message else None

        # Prepare attachment if present
        discord_file = None
        if attachment:
            try:
                file_bytes = await attachment.read()
                import io
                discord_file = discord.File(fp=io.BytesIO(file_bytes), filename=attachment.filename)
            except Exception as e:
                logger.warning(f"Could not forward attachment: {e}")

        # Reference message if replying
        ref_message = None
        if reply_to and reply_to.strip().isdigit():
            try:
                ref_message = await target_channel.fetch_message(int(reply_to.strip()))
            except Exception:
                pass

        try:
            if ref_message:
                await ref_message.reply(content=processed_message, file=discord_file, mention_author=False)
            else:
                await target_channel.send(content=processed_message, file=discord_file)

            await interaction.followup.send(
                embed=success_embed("Send Message", f"Your message was successfully sent to {target_channel.mention}!"),
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.followup.send(
                embed=error_embed("Permission Denied", f"I don't have permission to send messages in {target_channel.mention}."),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.followup.send(
                embed=error_embed("Failed to Send", str(e)),
                ephemeral=True,
            )

    @broadcast.command(name="say", description="Send a custom message to any channel through the bot with Nitro emoji support")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(
        message="Message to send (Supports text, markdown, and Nitro animated/custom emojis)",
        channel="Channel to send the message in (defaults to current channel)",
        attachment="Optional image or file attachment to send",
        reply_to="Optional Message ID to reply to",
    )
    async def say_cmd(
        self,
        interaction: discord.Interaction,
        message: str,
        channel: Optional[discord.TextChannel] = None,
        attachment: Optional[discord.Attachment] = None,
        reply_to: Optional[str] = None,
    ):
        await self._handle_send_message_flow(interaction, channel, message, attachment, reply_to)

    @broadcast.command(name="modal", description="Open a multi-line text editor modal to write and send messages")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(channel="Channel where message will be sent (defaults to current channel)")
    async def say_modal_cmd(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        target_channel = channel or interaction.channel
        if not isinstance(target_channel, discord.TextChannel):
            return await interaction.response.send_message("Please select a valid text channel.", ephemeral=True)

        modal = ChannelMessageModal(self, target_channel)
        await interaction.response.send_modal(modal)

    @broadcast.command(name="embed", description="Broadcast an elegant custom embed to any channel")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(
        description="The main text/content of the embed (supports Markdown & Nitro Emojis)",
        title="Optional title for the embed",
        channel="Channel to send the embed to (defaults to current channel)",
        color_hex="Optional hex color code (e.g. #5865F2, #FF0055, #00FFCC)",
        image="Optional image file attachment to display in the embed",
        footer="Optional footer text",
    )
    async def embed_say_cmd(
        self,
        interaction: discord.Interaction,
        description: str,
        title: Optional[str] = None,
        channel: Optional[discord.TextChannel] = None,
        color_hex: Optional[str] = None,
        image: Optional[discord.Attachment] = None,
        footer: Optional[str] = None,
    ):
        target_channel = channel or interaction.channel
        if not isinstance(target_channel, discord.TextChannel):
            return await interaction.response.send_message("Please select a valid text channel.", ephemeral=True)

        color = discord.Color.blurple()
        if color_hex:
            import re
            clean = color_hex.strip().lstrip("#")
            if re.match(r"^[0-9a-fA-F]{6}$", clean):
                color = discord.Color(int(clean, 16))

        processed_desc = self._expand_custom_emojis(description)
        embed = discord.Embed(
            title=title if title else None,
            description=processed_desc,
            color=color,
            timestamp=discord.utils.utcnow(),
        )

        if footer:
            embed.set_footer(text=footer)

        if image:
            embed.set_image(url=image.url)

        try:
            await target_channel.send(embed=embed)
            await interaction.response.send_message(
                embed=success_embed("Embed Sent", f"Custom embed dispatched to {target_channel.mention}!"),
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("Permission Denied", f"Missing permissions to send embed in {target_channel.mention}."),
                ephemeral=True,
            )

    # ==================== PREFIX VOICE SUMMONING ====================

    @commands.command(name="join")
    async def prefix_join(self, ctx: commands.Context):
        """Prefix command to summon bot to voice with interactive buttons."""
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(embed=warning_embed("Voice Required", f"{Emojis.ARROW} Pehle kisi voice channel me join kijiye!"))
            return
        target = ctx.author.voice.channel
        vc = ctx.guild.voice_client
        try:
            if vc and vc.is_connected():
                if vc.channel.id != target.id:
                    await vc.move_to(target)
            else:
                await target.connect(self_deaf=True)
            embed = success_embed(
                "Voice Channel Connected",
                f"{Emojis.TICK} Connected to {target.mention}!",
            )
            await ctx.send(embed=embed, view=VoiceJoinView())
        except Exception as e:
            await ctx.send(embed=error_embed("Voice Error", str(e)))

    @commands.command(name="leave", aliases=["dc", "disconnect"])
    async def prefix_leave(self, ctx: commands.Context):
        """Prefix command to disconnect bot from voice."""
        vc = ctx.guild.voice_client
        if vc and vc.is_connected():
            ch = vc.channel.mention if vc.channel else "voice"
            await vc.disconnect(force=True)
            await ctx.send(embed=info_embed("Disconnected", f"{Emojis.ARROW} Left {ch}."))
        else:
            await ctx.send(embed=warning_embed("Not In Voice", f"{Emojis.ARROW} Bot kisi bhi voice channel me nahi hai."))

    def _expand_custom_emojis(self, text: str) -> str:
        """Expand :emoji_name: to <a:emoji_name:id> or <:emoji_name:id> if found in bot cache."""
        import re
        pattern = r"(?<!<):([a-zA-Z0-9_]{2,32}):(?![\d>]+)"
        def replacer(match):
            emoji_name = match.group(1)
            found = discord.utils.get(self.bot.emojis, name=emoji_name)
            if found:
                return str(found)
            return match.group(0)
        return re.sub(pattern, replacer, text)


class SendMessageModal(discord.ui.Modal, title="Send Message"):
    message_text = discord.ui.TextInput(
        label="Message Content (Line breaks & emojis supported)",
        style=discord.TextStyle.paragraph,
        placeholder="Type your announcement or message here... Nitro emojis <:name:id> or <a:name:id> work seamlessly!",
        min_length=1,
        max_length=2000,
        required=True,
    )

    def __init__(self, utility_cog: Utility, target_channel: discord.TextChannel):
        super().__init__()
        self.cog = utility_cog
        self.target_channel = target_channel

    async def on_submit(self, interaction: discord.Interaction):
        content = self.message_text.value
        processed_content = self.cog._expand_custom_emojis(content)
        try:
            await self.target_channel.send(content=processed_content)
            await interaction.response.send_message(
                embed=success_embed("Send Message", f"Your message has been posted to {self.target_channel.mention}!"),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(
                embed=error_embed("Error Sending Message", str(e)),
                ephemeral=True,
            )


ChannelMessageModal = SendMessageModal


async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))

