"""NOVEXA - Advanced Anti-Spam & Phishing Defense System Cog.

Features:
- Real-time sliding window message rate limiting
- Duplicate and repetitive message detection (hash caching)
- Mass mention filtering & @everyone/@here protection
- Excessive custom/unicode emoji spam detection
- Discord invite link filtering
- Scam & Phishing heuristics (Nitro scams, steam gift scams, crypto airdrops)
- Configurable exemptions for trusted roles and channels
- Automatic message deletion, user warnings, temporary timeouts, and security audit logging
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
import re
import time
import hashlib
import datetime
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Union, Any
from database.database import db
from services.security_service import security_service
from utils.permissions import has_admin_or_owner
from utils.embeds import primary_embed, success_embed, error_embed, warning_embed

logger = logging.getLogger("novexa.antispam")

# Common phishing & scam patterns
SCAM_PATTERNS = [
    re.compile(r"(discord|disocrd|dlscord|disbord)\s*[\.\-_\/]\s*(gift|nitro|airdrop|claim|free|boost)", re.IGNORECASE),
    re.compile(r"(steamcommunity|steamcommnunity|steancommunity)\s*[\.\-_\/]\s*(trade|gift|promo)", re.IGNORECASE),
    re.compile(r"free\s+(nitro|robux|v-bucks|crypto|airdrop)\b", re.IGNORECASE),
    re.compile(r"@everyone\s+.*(nitro|gift|steam|free)", re.IGNORECASE),
]

DISCORD_INVITE_PATTERN = re.compile(r"(discord\.gg|discord\.com\/invite|discordapp\.com\/invite)\/[a-zA-Z0-9]+", re.IGNORECASE)
LINK_PATTERN = re.compile(r"https?:\/\/[^\s]+", re.IGNORECASE)
EMOJI_PATTERN = re.compile(r"<a?:[a-zA-Z0-9_]+:[0-9]+>|[\U00010000-\U0010ffff]", re.UNICODE)


class AntiSpam(commands.Cog):
    """Enterprise Anti-Spam, Invite Filter & Phishing Shield Suite."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # (guild_id, user_id) -> list of timestamp floats
        self._msg_tracker: Dict[Tuple[int, int], List[float]] = defaultdict(list)
        # (guild_id, user_id) -> list of (timestamp, message_hash)
        self._hash_tracker: Dict[Tuple[int, int], List[Tuple[float, str]]] = defaultdict(list)

    async def is_exempt(self, message: discord.Message) -> bool:
        """Check if message author or channel is exempt from anti-spam rules."""
        if not message.guild or not isinstance(message.author, discord.Member):
            return True

        member = message.author
        guild = message.guild

        # Bot owner, server owner, and administrators are exempt
        if member.id == guild.owner_id or member.guild_permissions.administrator:
            return True

        # Check general security whitelist
        if await security_service.is_whitelisted(guild, member):
            return True

        # Check channel and role exemptions in database
        ex = await db.fetchone(
            """
            SELECT id FROM antispam_exemptions
            WHERE guild_id = ? AND (target_id = ? OR target_id IN (%s))
            """ % (",".join(str(r.id) for r in member.roles) if member.roles else "0"),
            (guild.id, message.channel.id),
        )
        return ex is not None

    async def get_config(self, guild_id: int) -> Dict[str, Any]:
        """Fetch anti-spam configuration with defaults."""
        row = await db.fetchone("SELECT * FROM antispam_config WHERE guild_id = ?", (guild_id,))
        if not row:
            await db.execute("INSERT OR IGNORE INTO antispam_config (guild_id) VALUES (?)", (guild_id,))
            row = await db.fetchone("SELECT * FROM antispam_config WHERE guild_id = ?", (guild_id,))
        return dict(row) if row else {}

    # ==================== EVENT LISTENERS ====================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Analyze message content for spam, rapid messages, mass mentions, and phishing."""
        if message.author.bot or not message.guild:
            return

        cfg = await self.get_config(message.guild.id)
        if not cfg.get("enabled", 1):
            return

        if await self.is_exempt(message):
            return

        member = message.author
        guild = message.guild
        content = message.content or ""
        now = time.time()
        key = (guild.id, member.id)

        violation_reason = None
        severity = "MEDIUM"

        # 1. Phishing & Scam Filter
        if cfg.get("scam_filter", 1):
            for pat in SCAM_PATTERNS:
                if pat.search(content):
                    violation_reason = "Malicious Phishing / Free Nitro Scam pattern detected."
                    severity = "HIGH"
                    break

        # 2. Discord Invite Links Filter
        if not violation_reason and cfg.get("invite_filter", 1):
            if DISCORD_INVITE_PATTERN.search(content):
                violation_reason = "Unauthorized Discord invite link posted."

        # 3. Mass Mentions Filter (@everyone / @here / member pings)
        if not violation_reason:
            max_mentions = cfg.get("max_mentions", 5)
            total_mentions = len(message.mentions) + len(message.role_mentions)
            if message.mention_everyone:
                total_mentions += 10
            if total_mentions >= max_mentions:
                violation_reason = f"Excessive mentions detected ({total_mentions} mentions >= limit of {max_mentions})."

        # 4. Emoji Spam Filter
        if not violation_reason:
            max_emojis = cfg.get("max_emojis", 10)
            emojis_found = len(EMOJI_PATTERN.findall(content))
            if emojis_found >= max_emojis:
                violation_reason = f"Emoji spam detected ({emojis_found} emojis >= limit of {max_emojis})."

        # 5. Rapid Messaging Rate Limiter
        if not violation_reason:
            time_window = cfg.get("time_window", 5)
            max_msgs = cfg.get("max_messages_per_window", 5)
            recent_msgs = [t for t in self._msg_tracker[key] if now - t <= time_window]
            recent_msgs.append(now)
            self._msg_tracker[key] = recent_msgs

            if len(recent_msgs) >= max_msgs:
                violation_reason = f"Rapid message spam ({len(recent_msgs)} messages within {time_window}s)."

        # 6. Duplicate Message Filter
        if not violation_reason and cfg.get("duplicate_filter", 1) and len(content) > 6:
            msg_hash = hashlib.md5(content.strip().lower().encode("utf-8")).hexdigest()
            recent_hashes = [(t, h) for t, h in self._hash_tracker[key] if now - t <= 20]
            recent_hashes.append((now, msg_hash))
            self._hash_tracker[key] = recent_hashes

            identical_count = sum(1 for _, h in recent_hashes if h == msg_hash)
            if identical_count >= 3:
                violation_reason = "Repeated identical messages detected (duplicate spam)."

        # Execute punishment if violation occurred
        if violation_reason:
            # 1. Delete message immediately
            try:
                await message.delete()
            except Exception:
                pass

            # 2. Timeout user if configured
            punishment_applied = "DELETED_ONLY"
            punishment = cfg.get("punishment", "timeout").lower()
            duration_secs = cfg.get("action_duration", 300)

            if punishment == "timeout" and member.top_role < guild.me.top_role:
                try:
                    await member.timeout(datetime.timedelta(seconds=duration_secs), reason=f"[NOVEXA Anti-Spam] {violation_reason}")
                    punishment_applied = f"TIMEOUT_{duration_secs}s"
                except Exception:
                    pass
            elif punishment == "kick" and member.top_role < guild.me.top_role:
                try:
                    await member.kick(reason=f"[NOVEXA Anti-Spam] {violation_reason}")
                    punishment_applied = "KICKED"
                except Exception:
                    pass

            # 3. Notify user in channel with temporary self-deleting warning
            try:
                warn_msg = await message.channel.send(
                    f"⚠️ {member.mention}, your message was removed by **NOVEXA Anti-Spam**.\n"
                    f"*Reason:* {violation_reason}",
                    delete_after=8,
                )
            except Exception:
                pass

            # 4. Log incident to security log channel
            await security_service.log_incident(
                guild=guild,
                executor=member,
                action_type="anti_spam_violation",
                details=f"{violation_reason}\n*Snippet:* `{content[:80]}`",
                target_name=f"#{message.channel.name}",
                target_id=message.channel.id,
                severity=severity,
                punishment_applied=punishment_applied,
            )

    # ==================== SLASH COMMANDS ====================

    antispam_group = app_commands.Group(name="antispam", description="Configure server anti-spam, link filters and phishing protection")

    @antispam_group.command(name="settings", description="View current Anti-Spam protection settings and active thresholds")
    @has_admin_or_owner()
    async def antispam_settings(self, interaction: discord.Interaction):
        cfg = await self.get_config(interaction.guild_id)
        embed = primary_embed(title=f"🛡️ Anti-Spam Protection — {interaction.guild.name}")
        status = "🟢 Enabled" if cfg.get("enabled", 1) else "🔴 Disabled"
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Punishment", value=str(cfg.get("punishment", "timeout")).upper(), inline=True)
        embed.add_field(name="Timeout Duration", value=f"{cfg.get('action_duration', 300)}s", inline=True)

        embed.add_field(name="Mention Limit", value=str(cfg.get("max_mentions", 5)), inline=True)
        embed.add_field(name="Emoji Limit", value=str(cfg.get("max_emojis", 10)), inline=True)
        embed.add_field(name="Rapid Rate Limit", value=f"{cfg.get('max_messages_per_window', 5)} msgs / {cfg.get('time_window', 5)}s", inline=True)

        embed.add_field(name="Duplicate Filter", value="Active" if cfg.get("duplicate_filter", 1) else "Off", inline=True)
        embed.add_field(name="Invite Link Filter", value="Active" if cfg.get("invite_filter", 1) else "Off", inline=True)
        embed.add_field(name="Scam & Phishing Shield", value="Active" if cfg.get("scam_filter", 1) else "Off", inline=True)

        await interaction.response.send_message(embed=embed)

    @antispam_group.command(name="toggle", description="Enable or disable the Anti-Spam protection suite")
    @has_admin_or_owner()
    @app_commands.describe(enabled="Turn anti-spam on or off")
    async def antispam_toggle(self, interaction: discord.Interaction, enabled: bool):
        await db.execute(
            """
            INSERT INTO antispam_config (guild_id, enabled) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET enabled = excluded.enabled
            """,
            (interaction.guild_id, 1 if enabled else 0),
        )
        status_text = "Enabled" if enabled else "Disabled"
        await interaction.response.send_message(
            embed=success_embed(f"Anti-Spam {status_text}", f"Anti-Spam protection is now **{status_text.lower()}**."),
            ephemeral=True,
        )

    @antispam_group.command(name="configure", description="Configure specific Anti-Spam limits and action behavior")
    @has_admin_or_owner()
    @app_commands.describe(
        mentions="Max mentions before strike (e.g. 5)",
        emojis="Max emojis before strike (e.g. 10)",
        rate_limit="Max messages allowed within window (e.g. 5)",
        filter_invites="Block unauthorized Discord invites",
        filter_duplicates="Block identical repeated messages",
        filter_scams="Block phishing and scam links",
    )
    async def antispam_configure(
        self,
        interaction: discord.Interaction,
        mentions: Optional[int] = None,
        emojis: Optional[int] = None,
        rate_limit: Optional[int] = None,
        filter_invites: Optional[bool] = None,
        filter_duplicates: Optional[bool] = None,
        filter_scams: Optional[bool] = None,
    ):
        updates = []
        params = []
        if mentions is not None:
            updates.append("max_mentions = ?")
            params.append(mentions)
        if emojis is not None:
            updates.append("max_emojis = ?")
            params.append(emojis)
        if rate_limit is not None:
            updates.append("max_messages_per_window = ?")
            params.append(rate_limit)
        if filter_invites is not None:
            updates.append("invite_filter = ?")
            params.append(1 if filter_invites else 0)
        if filter_duplicates is not None:
            updates.append("duplicate_filter = ?")
            params.append(1 if filter_duplicates else 0)
        if filter_scams is not None:
            updates.append("scam_filter = ?")
            params.append(1 if filter_scams else 0)

        if not updates:
            return await interaction.response.send_message("Please provide at least one parameter to configure.", ephemeral=True)

        params.append(interaction.guild_id)
        await db.execute(
            f"""
            INSERT INTO antispam_config (guild_id) VALUES (?)
            ON CONFLICT(guild_id) DO UPDATE SET {", ".join(updates)}
            """,
            (interaction.guild_id, *params[:-1]) if len(params) > 1 else params,
        )
        await interaction.response.send_message(
            embed=success_embed("Anti-Spam Configuration Updated", "Your anti-spam rules have been updated successfully."),
            ephemeral=True,
        )

    @antispam_group.command(name="exempt", description="Add or remove channel or role exemption from Anti-Spam")
    @has_admin_or_owner()
    @app_commands.choices(action=[
        app_commands.Choice(name="Add Exemption", value="add"),
        app_commands.Choice(name="Remove Exemption", value="remove"),
        app_commands.Choice(name="List Exemptions", value="list"),
    ])
    async def antispam_exempt_cmd(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        channel: Optional[discord.TextChannel] = None,
        role: Optional[discord.Role] = None,
    ):
        guild = interaction.guild
        if action.value == "list":
            rows = await db.fetchall("SELECT * FROM antispam_exemptions WHERE guild_id = ?", (guild.id,))
            if not rows:
                return await interaction.response.send_message("No channel or role exemptions configured.", ephemeral=True)

            lines = []
            for r in rows:
                target = f"<#{r['target_id']}> (Channel)" if r["target_type"] == "channel" else f"<@&{r['target_id']}> (Role)"
                lines.append(f"• {target}")

            embed = primary_embed(title="🛡️ Anti-Spam Exemptions", description="\n".join(lines))
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        target = channel or role
        if not target:
            return await interaction.response.send_message("Please specify either a channel or a role.", ephemeral=True)

        target_type = "channel" if isinstance(target, discord.TextChannel) else "role"

        if action.value == "add":
            await db.execute(
                """
                INSERT OR IGNORE INTO antispam_exemptions (guild_id, target_id, target_type)
                VALUES (?, ?, ?)
                """,
                (guild.id, target.id, target_type),
            )
            await interaction.response.send_message(
                embed=success_embed("Exemption Added", f"Successfully exempted {target.mention} from Anti-Spam filters."),
                ephemeral=True,
            )
        else:
            await db.execute(
                "DELETE FROM antispam_exemptions WHERE guild_id = ? AND target_id = ?",
                (guild.id, target.id),
            )
            await interaction.response.send_message(
                embed=warning_embed("Exemption Removed", f"Removed exemption for {target.mention}."),
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(AntiSpam(bot))

