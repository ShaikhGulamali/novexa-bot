"""NOVEXA - Advanced Join to Create Voice Channel & Personal VC Suite.

Implements a production-grade Join to Create system on top of the existing
NOVEXA database, embeds, permission helpers and dashboard config service.

Highlights:
- Generator voice channel spawns a private room, moves the creator in and posts
  a persistent control panel.
- Owner controls: rename, user limit, voice status, bitrate, lock/unlock,
  hide/unhide, allow, reject, kick, transfer ownership, delete.
- Admin suite: /voice setup | enable | disable | config | panel | stats | reset,
  plus an admin panel with defaults editor and active room listing.
- Safety: per-user creation locks, rejoin reuse, empty-room debounce, minimum
  room age, pending-delete guard, restart reconciliation, generator deletion
  handling, permission validation before every write.
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import discord
from discord import app_commands
from discord.ext import commands

from config import BOT_NAME
from database.database import db
from services.config_service import config_service
from utils.embeds import (
    error_embed,
    info_embed,
    primary_embed,
    success_embed,
    warning_embed,
)
from utils.permissions import has_admin_or_owner

logger = logging.getLogger("novexa.voice")

DEFAULT_NAME_FORMAT = "🔊・{username}"
GENERATOR_NAME_HINTS = ("join to create", "join-to-create", "jointocreate", "join_to_create", "j2c")
MAX_CHANNEL_NAME = 100
MIN_BITRATE = 8000
MAX_USER_LIMIT = 99
EMPTY_GRACE_SECONDS = 2.5
OWNER_DEPARTURE_GRACE_SECONDS = 1.5
MIN_ROOM_AGE_SECONDS = 6.0
SELECT_TIMEOUT = 120
PANEL_COLOR = 0x5865F2


# ==================== PURE HELPERS ====================

def is_admin(member: discord.Member) -> bool:
    """Server owner or Administrator permission."""
    if member.id == member.guild.owner_id:
        return True
    return bool(member.guild_permissions.administrator)


def sanitize_name(raw: str) -> str:
    """Strip control characters, collapse whitespace, clamp to Discord's limit."""
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", raw or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip().strip("-")
    return cleaned[:MAX_CHANNEL_NAME].strip() or "Voice Room"


def render_channel_name(fmt: Optional[str], member: discord.Member) -> str:
    """Resolve a name format for a member and sanitize the result."""
    template = fmt or DEFAULT_NAME_FORMAT
    text = (
        template.replace("{username}", member.display_name)
        .replace("{display_name}", member.display_name)
        .replace("{name}", member.name)
        .replace("{server}", member.guild.name)
        .replace("{count}", str(member.guild.member_count or 0))
    )
    return sanitize_name(text)


def validate_name_format(fmt: str) -> Optional[str]:
    """Return an error string when the format is unusable, else None."""
    if not fmt or not fmt.strip():
        return "Name format cannot be empty."
    probe = fmt.replace("{username}", "Example User").replace("{name}", "example")
    probe = probe.replace("{display_name}", "Example User").replace("{server}", "Server")
    probe = probe.replace("{count}", "123")
    if not sanitize_name(probe):
        return "Name format produces an empty channel name."
    return None


def clamp_bitrate(value: Any, guild: discord.Guild) -> int:
    """Clamp a bitrate in bits-per-second to the guild tier limits."""
    try:
        bitrate = int(value)
    except (TypeError, ValueError):
        bitrate = 64000
    ceiling = int(guild.bitrate_limit)
    return max(MIN_BITRATE, min(bitrate, ceiling))


def clamp_user_limit(value: Any) -> int:
    try:
        limit = int(value)
    except (TypeError, ValueError):
        limit = 0
    return max(0, min(limit, MAX_USER_LIMIT))


def parse_created_at(raw: Any) -> Optional[datetime]:
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    if not isinstance(raw, str) or not raw:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(raw)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def room_age_seconds(created_at: Any) -> float:
    parsed = parse_created_at(created_at)
    if not parsed:
        return 0.0
    return max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds())


def bot_can_manage(guild: discord.Guild) -> Tuple[bool, str]:
    me = guild.me
    if me is None:
        return False, "Bot member is not available in this server."
    perms = me.guild_permissions
    missing = []
    if not perms.manage_channels:
        missing.append("Manage Channels")
    if not perms.move_members:
        missing.append("Move Members")
    if missing:
        return False, "Missing permissions: " + ", ".join(missing)
    return True, ""


async def fetch_temp_row(channel_id: int) -> Optional[Any]:
    return await db.fetchone(
        "SELECT * FROM active_temp_channels WHERE channel_id = ?",
        (channel_id,),
    )


async def ensure_owner(interaction: discord.Interaction, channel: discord.VoiceChannel) -> Optional[Dict[str, Any]]:
    """Re-validate that the caller owns (or administers) this temp channel.

    Sends the error response itself and returns None when access is denied.
    """
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message(
            embed=error_embed("Guild Only", "This control panel only works inside a server."),
            ephemeral=True,
        )
        return None

    row = await fetch_temp_row(channel.id)
    if not row:
        await interaction.response.send_message(
            embed=error_embed("Not a Temp Channel", "This voice channel is not managed by Join to Create."),
            ephemeral=True,
        )
        return None

    data = dict(row)
    if data["owner_id"] != interaction.user.id and not is_admin(interaction.user):
        await interaction.response.send_message(
            embed=error_embed(
                "Permission Denied",
                f"Only the channel owner (<@{data['owner_id']}>) or an Administrator can manage this room.",
            ),
            ephemeral=True,
        )
        return None

    return {"channel": channel, "row": data}


# ==================== MODALS ====================

class RenameChannelModal(discord.ui.Modal, title="Rename Voice Channel"):
    channel_name = discord.ui.TextInput(
        label="New Channel Name",
        placeholder="e.g. 🔊・Chill Lounge, Gaming with Friends",
        min_length=1,
        max_length=MAX_CHANNEL_NAME,
        required=True,
    )

    def __init__(self, channel: discord.VoiceChannel):
        super().__init__()
        self.channel = channel
        self.channel_name.default = channel.name

    async def on_submit(self, interaction: discord.Interaction):
        if not await ensure_owner(interaction, self.channel):
            return
        new_name = sanitize_name(self.channel_name.value)
        try:
            await self.channel.edit(name=new_name, reason=f"Renamed by {interaction.user}")
            await interaction.response.send_message(
                embed=success_embed("Channel Renamed", f"Channel renamed to **{new_name}**."),
                ephemeral=True,
            )
        except discord.HTTPException as exc:
            if exc.status == 429:
                return await interaction.response.send_message(
                    embed=warning_embed(
                        "Rate Limited",
                        "Discord limits voice channel renames to 2 per 10 minutes. Try again shortly.",
                    ),
                    ephemeral=True,
                )
            logger.warning("Rename failed for %s: %s", self.channel.id, exc)
            await interaction.response.send_message(
                embed=error_embed("Rename Failed", f"Could not rename the channel: `{exc}`"),
                ephemeral=True,
            )
        except Exception as exc:
            logger.exception("Rename error for %s", self.channel.id)
            await interaction.response.send_message(
                embed=error_embed("Rename Failed", f"Could not rename the channel: `{exc}`"),
                ephemeral=True,
            )


class UserLimitModal(discord.ui.Modal, title="Set User Limit"):
    limit_input = discord.ui.TextInput(
        label="User Limit (0 = Unlimited, 1-99)",
        placeholder="Enter a number between 0 and 99",
        min_length=1,
        max_length=2,
        required=True,
    )

    def __init__(self, channel: discord.VoiceChannel):
        super().__init__()
        self.channel = channel
        self.limit_input.default = str(channel.user_limit)

    async def on_submit(self, interaction: discord.Interaction):
        if not await ensure_owner(interaction, self.channel):
            return
        raw = self.limit_input.value.strip()
        if not raw.isdigit():
            return await interaction.response.send_message(
                embed=error_embed("Invalid Input", "Enter a whole number from 0 (unlimited) to 99."),
                ephemeral=True,
            )
        limit = clamp_user_limit(raw)
        try:
            await self.channel.edit(user_limit=limit, reason=f"User limit set by {interaction.user}")
            shown = "Unlimited" if limit == 0 else f"{limit} users"
            await interaction.response.send_message(
                embed=success_embed("User Limit Updated", f"Channel user limit set to **{shown}**."),
                ephemeral=True,
            )
        except Exception as exc:
            logger.warning("User limit edit failed for %s: %s", self.channel.id, exc)
            await interaction.response.send_message(
                embed=error_embed("Edit Failed", f"Could not update the user limit: `{exc}`"),
                ephemeral=True,
            )


class ChannelStatusModal(discord.ui.Modal, title="Set Voice Channel Status"):
    status_text = discord.ui.TextInput(
        label="Voice Status Text",
        placeholder="e.g. Grinding Valorant | Do Not Disturb",
        max_length=100,
        required=False,
    )

    def __init__(self, channel: discord.VoiceChannel, current: Optional[str] = None):
        super().__init__()
        self.channel = channel
        self.status_text.default = current or ""

    async def on_submit(self, interaction: discord.Interaction):
        if not await ensure_owner(interaction, self.channel):
            return
        status_value = self.status_text.value.strip()[:100]
        updated = False
        try:
            # Voice channel status is not exposed by discord.py 2.7's VoiceChannel.edit,
            # so PATCH it through the raw HTTP client.
            await interaction.client.http.edit_channel(
                self.channel.id,
                status=status_value,
                reason=f"Voice status set by {interaction.user}",
            )
            updated = True
        except Exception as exc:
            logger.warning("Voice status PATCH failed for %s: %s", self.channel.id, exc)

        await db.execute(
            "UPDATE active_temp_channels SET custom_status = ? WHERE channel_id = ?",
            (status_value, self.channel.id),
        )
        shown = status_value or "Cleared"
        if updated:
            embed = success_embed("Status Updated", f"Voice status set to: **{shown}**.")
        else:
            embed = warning_embed(
                "Status Saved Locally",
                f"Saved as **{shown}** in NOVEXA, but Discord rejected the live status update.",
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class BitrateModal(discord.ui.Modal, title="Set Voice Channel Bitrate"):
    bitrate_input = discord.ui.TextInput(
        label="Bitrate in kbps (8 - server max)",
        placeholder="e.g. 64, 96, 128, 256, 384",
        min_length=1,
        max_length=4,
        required=True,
    )

    def __init__(self, channel: discord.VoiceChannel):
        super().__init__()
        self.channel = channel
        self.bitrate_input.default = str(int(channel.bitrate / 1000))

    async def on_submit(self, interaction: discord.Interaction):
        if not await ensure_owner(interaction, self.channel):
            return
        raw = self.bitrate_input.value.strip()
        if not raw.isdigit():
            return await interaction.response.send_message(
                embed=error_embed("Invalid Input", "Enter the bitrate as a whole number of kbps (e.g. 64, 96, 128)."),
                ephemeral=True,
            )
        requested_bps = int(raw) * 1000
        ceiling = int(interaction.guild.bitrate_limit)
        if requested_bps < MIN_BITRATE or requested_bps > ceiling:
            return await interaction.response.send_message(
                embed=error_embed(
                    "Invalid Bitrate",
                    f"Use a value between 8 and {ceiling // 1000} kbps for this server tier.",
                ),
                ephemeral=True,
            )
        try:
            await self.channel.edit(bitrate=requested_bps, reason=f"Bitrate set by {interaction.user}")
            await interaction.response.send_message(
                embed=success_embed("Bitrate Updated", f"Audio bitrate set to **{requested_bps // 1000} kbps**."),
                ephemeral=True,
            )
        except Exception as exc:
            logger.warning("Bitrate edit failed for %s: %s", self.channel.id, exc)
            await interaction.response.send_message(
                embed=error_embed("Bitrate Failed", f"Could not set the bitrate: `{exc}`"),
                ephemeral=True,
            )


class ServerVoiceConfigModal(discord.ui.Modal, title="Voice System Defaults"):
    name_format = discord.ui.TextInput(
        label="Channel Name Format",
        placeholder="🔊・{username}",
        max_length=MAX_CHANNEL_NAME,
        required=True,
    )
    user_limit = discord.ui.TextInput(
        label="Default User Limit (0-99)",
        placeholder="0 = unlimited",
        max_length=2,
        required=True,
    )
    bitrate = discord.ui.TextInput(
        label="Default Bitrate in kbps",
        placeholder="64",
        max_length=4,
        required=True,
    )
    delete_when_empty = discord.ui.TextInput(
        label="Delete When Empty? (yes/no)",
        placeholder="yes",
        max_length=3,
        required=True,
    )

    def __init__(self, cfg: Dict[str, Any], guild: discord.Guild):
        super().__init__()
        self.guild = guild
        self.name_format.default = cfg.get("channel_name_format") or DEFAULT_NAME_FORMAT
        self.user_limit.default = str(cfg.get("default_user_limit") or 0)
        self.bitrate.default = str(int((cfg.get("default_bitrate") or 64000) / 1000))
        self.delete_when_empty.default = "yes" if cfg.get("delete_when_empty", True) else "no"

    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            return await interaction.response.send_message(
                embed=error_embed("Permission Denied", "Administrator permission required."),
                ephemeral=True,
            )
        fmt = self.name_format.value.strip()
        error = validate_name_format(fmt)
        if error:
            return await interaction.response.send_message(
                embed=error_embed("Invalid Format", error),
                ephemeral=True,
            )
        raw_limit = self.user_limit.value.strip()
        raw_bitrate = self.bitrate.value.strip()
        if not raw_limit.isdigit() or not raw_bitrate.isdigit():
            return await interaction.response.send_message(
                embed=error_embed("Invalid Input", "User limit and bitrate must be whole numbers."),
                ephemeral=True,
            )
        delete_flag = self.delete_when_empty.value.strip().lower() in ("yes", "y", "true", "1", "on")
        limit = clamp_user_limit(raw_limit)
        bitrate_bps = clamp_bitrate(int(raw_bitrate) * 1000, self.guild)
        await config_service.update_voice_j2c_config(
            interaction.guild_id,
            {
                "channel_name_format": fmt,
                "default_user_limit": limit,
                "default_bitrate": bitrate_bps,
                "delete_when_empty": delete_flag,
            },
            actor_id=interaction.user.id,
            actor_tag=str(interaction.user),
            source="DISCORD",
        )
        await interaction.response.send_message(
            embed=success_embed(
                "Defaults Saved",
                f"Format: `{fmt}`\nUser limit: `{limit}`\n"
                f"Bitrate: `{bitrate_bps // 1000} kbps`\n"
                f"Auto-delete: `{'yes' if delete_flag else 'no'}`",
            ),
            ephemeral=True,
        )


# ==================== SELECT MENUS ====================

class _OwnerSelect(discord.ui.UserSelect):
    """UserSelect base that re-validates ownership on every selection."""

    def __init__(self, channel: discord.VoiceChannel, *, placeholder: str,
                 min_values: int = 1, max_values: int = 5, custom_id: Optional[str] = None):
        super().__init__(
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            custom_id=custom_id,
        )
        self.channel = channel

    async def _guard(self, interaction: discord.Interaction) -> bool:
        return await ensure_owner(interaction, self.channel) is not None


class AllowUserSelect(_OwnerSelect):
    def __init__(self, channel: discord.VoiceChannel):
        super().__init__(
            channel,
            placeholder="Select member(s) to allow into this room...",
            max_values=5,
            custom_id="vc_select_allow",
        )

    async def callback(self, interaction: discord.Interaction):
        if not await self._guard(interaction):
            return
        allowed = []
        for user in self.values:
            if not isinstance(user, discord.Member):
                continue
            overwrite = self.channel.overwrites_for(user)
            overwrite.view_channel = True
            overwrite.connect = True
            await self.channel.set_permissions(
                user, overwrite=overwrite, reason=f"Allowed by {interaction.user}"
            )
            allowed.append(user.mention)
        if not allowed:
            return await interaction.response.send_message(
                embed=error_embed("No Changes", "No valid server members were selected."),
                ephemeral=True,
            )
        await interaction.response.send_message(
            embed=success_embed("Members Allowed", f"Granted access to {', '.join(allowed)}."),
            ephemeral=True,
        )


class RejectUserSelect(_OwnerSelect):
    def __init__(self, channel: discord.VoiceChannel):
        super().__init__(
            channel,
            placeholder="Select member(s) to deny access...",
            max_values=5,
            custom_id="vc_select_reject",
        )

    async def callback(self, interaction: discord.Interaction):
        if not await self._guard(interaction):
            return
        denied = []
        for user in self.values:
            if not isinstance(user, discord.Member):
                continue
            overwrite = self.channel.overwrites_for(user)
            overwrite.connect = False
            await self.channel.set_permissions(
                user, overwrite=overwrite, reason=f"Denied by {interaction.user}"
            )
            denied.append(user.mention)
        if not denied:
            return await interaction.response.send_message(
                embed=error_embed("No Changes", "No valid server members were selected."),
                ephemeral=True,
            )
        await interaction.response.send_message(
            embed=success_embed("Members Rejected", f"Denied access to {', '.join(denied)}."),
            ephemeral=True,
        )


class KickUserSelect(_OwnerSelect):
    def __init__(self, channel: discord.VoiceChannel):
        super().__init__(
            channel,
            placeholder="Select member(s) to kick from this room...",
            max_values=5,
            custom_id="vc_select_kick",
        )

    async def callback(self, interaction: discord.Interaction):
        if not await self._guard(interaction):
            return
        kicked = []
        for user in self.values:
            if not isinstance(user, discord.Member):
                continue
            if user.id == interaction.user.id:
                continue
            overwrite = self.channel.overwrites_for(user)
            overwrite.connect = False
            await self.channel.set_permissions(
                user, overwrite=overwrite, reason=f"Kicked by {interaction.user}"
            )
            if user.voice and user.voice.channel and user.voice.channel.id == self.channel.id:
                try:
                    await user.move_to(None, reason="Kicked from temporary voice channel")
                except Exception as exc:
                    logger.debug("Kick move failed for %s: %s", user.id, exc)
            kicked.append(user.mention)
        if not kicked:
            return await interaction.response.send_message(
                embed=error_embed("No Changes", "No valid server members were selected."),
                ephemeral=True,
            )
        await interaction.response.send_message(
            embed=success_embed("Members Kicked", f"Removed {', '.join(kicked)} from the room."),
            ephemeral=True,
        )


class TransferOwnerSelect(_OwnerSelect):
    def __init__(self, channel: discord.VoiceChannel):
        super().__init__(
            channel,
            placeholder="Select the new owner for this room...",
            min_values=1,
            max_values=1,
            custom_id="vc_select_transfer",
        )

    async def callback(self, interaction: discord.Interaction):
        if not await self._guard(interaction):
            return
        new_owner = self.values[0]
        if not isinstance(new_owner, discord.Member):
            return await interaction.response.send_message(
                embed=error_embed("Invalid Target", "The new owner must be a member of this server."),
                ephemeral=True,
            )
        if new_owner.bot:
            return await interaction.response.send_message(
                embed=error_embed("Invalid Target", "Bots cannot own a voice room."),
                ephemeral=True,
            )
        if new_owner.id == interaction.user.id:
            return await interaction.response.send_message(
                embed=warning_embed("Already Owner", "You already own this room."),
                ephemeral=True,
            )
        try:
            await db.execute(
                "UPDATE active_temp_channels SET owner_id = ? WHERE channel_id = ?",
                (new_owner.id, self.channel.id),
            )
            old_overwrite = self.channel.overwrites_for(interaction.user)
            old_overwrite.manage_channels = False
            await self.channel.set_permissions(
                interaction.user, overwrite=old_overwrite, reason="Ownership transferred"
            )
            new_overwrite = self.channel.overwrites_for(new_owner)
            new_overwrite.view_channel = True
            new_overwrite.connect = True
            new_overwrite.speak = True
            new_overwrite.manage_channels = True
            await self.channel.set_permissions(
                new_owner,
                overwrite=new_overwrite,
                reason=f"Ownership transferred from {interaction.user}",
            )
        except Exception as exc:
            logger.exception("Ownership transfer failed for %s", self.channel.id)
            return await interaction.response.send_message(
                embed=error_embed("Transfer Failed", f"Could not transfer ownership: `{exc}`"),
                ephemeral=True,
            )
        await interaction.response.send_message(
            embed=success_embed(
                "Ownership Transferred",
                f"👑 {new_owner.mention} now owns {self.channel.mention}.",
            ),
        )


# ==================== PERSONAL CONTROL PANEL ====================

def build_control_panel_embed(owner: discord.Member, channel: discord.VoiceChannel,
                              cfg: Optional[Dict[str, Any]] = None) -> discord.Embed:
    limit = channel.user_limit
    limit_text = "Unlimited" if limit == 0 else f"{limit}"
    locked = "🔒 Locked" if (cfg or {}).get("is_locked") else "🔓 Open"
    hidden = "🕶️ Hidden" if (cfg or {}).get("is_hidden") else "👁️ Visible"
    embed = discord.Embed(
        title=f"🎙️ {owner.display_name}'s Voice Room",
        description=(
            f"Welcome {owner.mention} — this is your private space.\n\n"
            "**Room**\n"
            f"• Name: **{channel.name}**\n"
            f"• Capacity: **{limit_text}**\n"
            f"• Access: **{locked}** · **{hidden}**\n\n"
            "**Controls**\n"
            "✏️ Rename · 👥 Limit · 💬 Status · 📶 Bitrate\n"
            "🔒 Lock · 🔓 Unlock · 🕶️ Hide · 👁️ Unhide\n"
            "➕ Allow · 🚫 Reject · 👢 Kick · 👑 Transfer · 🗑️ Delete\n\n"
            "*The room is removed automatically once everyone leaves.*"
        ),
        color=PANEL_COLOR,
    )
    embed.set_footer(text=f"{BOT_NAME} Voice System • Instant Personal Voice")
    return embed


class VoiceControlPanelView(discord.ui.View):
    """Persistent owner control panel. Registered in main.py with no arguments."""

    def __init__(self):
        super().__init__(timeout=None)

    async def _resolve(self, interaction: discord.Interaction) -> Optional[discord.VoiceChannel]:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                embed=error_embed("Guild Only", "This panel only works inside a server."),
                ephemeral=True,
            )
            return None

        channel = interaction.channel if isinstance(interaction.channel, discord.VoiceChannel) else None
        if channel is None and interaction.user.voice:
            candidate = interaction.user.voice.channel
            if isinstance(candidate, discord.VoiceChannel):
                channel = candidate
        if channel is None:
            await interaction.response.send_message(
                embed=warning_embed(
                    "Voice Room Required",
                    "Open this panel from inside your temporary voice room.",
                ),
                ephemeral=True,
            )
            return None

        row = await fetch_temp_row(channel.id)
        if not row:
            await interaction.response.send_message(
                embed=error_embed("Not a Temp Room", "This channel is not managed by Join to Create."),
                ephemeral=True,
            )
            return None
        data = dict(row)
        if data["owner_id"] != interaction.user.id and not is_admin(interaction.user):
            await interaction.response.send_message(
                embed=error_embed(
                    "Permission Denied",
                    f"Only the room owner (<@{data['owner_id']}>) or an Administrator can use these controls.",
                ),
                ephemeral=True,
            )
            return None
        return channel

    # ---------------- ROW 0: CUSTOMISATION ----------------
    @discord.ui.button(label="Rename", style=discord.ButtonStyle.primary, emoji="✏️", custom_id="vc_btn_rename", row=0)
    async def btn_rename(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = await self._resolve(interaction)
        if channel:
            await interaction.response.send_modal(RenameChannelModal(channel))

    @discord.ui.button(label="Limit", style=discord.ButtonStyle.primary, emoji="👥", custom_id="vc_btn_limit", row=0)
    async def btn_limit(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = await self._resolve(interaction)
        if channel:
            await interaction.response.send_modal(UserLimitModal(channel))

    @discord.ui.button(label="Status", style=discord.ButtonStyle.secondary, emoji="💬", custom_id="vc_btn_status", row=0)
    async def btn_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = await self._resolve(interaction)
        if not channel:
            return
        row = await fetch_temp_row(channel.id)
        current = dict(row).get("custom_status") if row else None
        await interaction.response.send_modal(ChannelStatusModal(channel, current))

    @discord.ui.button(label="Bitrate", style=discord.ButtonStyle.secondary, emoji="📶", custom_id="vc_btn_bitrate", row=0)
    async def btn_bitrate(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = await self._resolve(interaction)
        if channel:
            await interaction.response.send_modal(BitrateModal(channel))

    # ---------------- ROW 1: ACCESS ----------------
    @discord.ui.button(label="Lock", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="vc_btn_lock", row=1)
    async def btn_lock(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = await self._resolve(interaction)
        if not channel:
            return
        try:
            overwrite = channel.overwrites_for(interaction.guild.default_role)
            overwrite.connect = False
            await channel.set_permissions(
                interaction.guild.default_role, overwrite=overwrite, reason=f"Locked by {interaction.user}"
            )
            await db.execute("UPDATE active_temp_channels SET is_locked = 1 WHERE channel_id = ?", (channel.id,))
        except Exception as exc:
            return await interaction.response.send_message(
                embed=error_embed("Lock Failed", f"`{exc}`"), ephemeral=True
            )
        await interaction.response.send_message(
            embed=success_embed("Room Locked", "New members cannot connect until you allow them."),
            ephemeral=True,
        )

    @discord.ui.button(label="Unlock", style=discord.ButtonStyle.success, emoji="🔓", custom_id="vc_btn_unlock", row=1)
    async def btn_unlock(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = await self._resolve(interaction)
        if not channel:
            return
        try:
            overwrite = channel.overwrites_for(interaction.guild.default_role)
            overwrite.connect = True
            await channel.set_permissions(
                interaction.guild.default_role, overwrite=overwrite, reason=f"Unlocked by {interaction.user}"
            )
            await db.execute("UPDATE active_temp_channels SET is_locked = 0 WHERE channel_id = ?", (channel.id,))
        except Exception as exc:
            return await interaction.response.send_message(
                embed=error_embed("Unlock Failed", f"`{exc}`"), ephemeral=True
            )
        await interaction.response.send_message(
            embed=success_embed("Room Unlocked", "Anyone can join this room now."),
            ephemeral=True,
        )

    @discord.ui.button(label="Hide", style=discord.ButtonStyle.secondary, emoji="🕶️", custom_id="vc_btn_hide", row=1)
    async def btn_hide(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = await self._resolve(interaction)
        if not channel:
            return
        try:
            overwrite = channel.overwrites_for(interaction.guild.default_role)
            overwrite.view_channel = False
            await channel.set_permissions(
                interaction.guild.default_role, overwrite=overwrite, reason=f"Hidden by {interaction.user}"
            )
            await db.execute("UPDATE active_temp_channels SET is_hidden = 1 WHERE channel_id = ?", (channel.id,))
        except Exception as exc:
            return await interaction.response.send_message(
                embed=error_embed("Hide Failed", f"`{exc}`"), ephemeral=True
            )
        await interaction.response.send_message(
            embed=success_embed("Room Hidden", "The room is now hidden from @everyone."),
            ephemeral=True,
        )

    @discord.ui.button(label="Unhide", style=discord.ButtonStyle.secondary, emoji="👁️", custom_id="vc_btn_unhide", row=1)
    async def btn_unhide(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = await self._resolve(interaction)
        if not channel:
            return
        try:
            overwrite = channel.overwrites_for(interaction.guild.default_role)
            overwrite.view_channel = True
            await channel.set_permissions(
                interaction.guild.default_role, overwrite=overwrite, reason=f"Unhidden by {interaction.user}"
            )
            await db.execute("UPDATE active_temp_channels SET is_hidden = 0 WHERE channel_id = ?", (channel.id,))
        except Exception as exc:
            return await interaction.response.send_message(
                embed=error_embed("Unhide Failed", f"`{exc}`"), ephemeral=True
            )
        await interaction.response.send_message(
            embed=success_embed("Room Visible", "The room is visible to @everyone again."),
            ephemeral=True,
        )

    # ---------------- ROW 2: MEMBERS & DESTRUCTION ----------------
    @discord.ui.button(label="Allow", style=discord.ButtonStyle.success, emoji="➕", custom_id="vc_btn_allow", row=2)
    async def btn_allow(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = await self._resolve(interaction)
        if not channel:
            return
        view = discord.ui.View(timeout=SELECT_TIMEOUT)
        view.add_item(AllowUserSelect(channel))
        await interaction.response.send_message(
            "Select members to allow into this room:", view=view, ephemeral=True
        )

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger, emoji="🚫", custom_id="vc_btn_reject", row=2)
    async def btn_reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = await self._resolve(interaction)
        if not channel:
            return
        view = discord.ui.View(timeout=SELECT_TIMEOUT)
        view.add_item(RejectUserSelect(channel))
        await interaction.response.send_message(
            "Select members to deny access:", view=view, ephemeral=True
        )

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.danger, emoji="👢", custom_id="vc_btn_remove", row=2)
    async def btn_kick(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = await self._resolve(interaction)
        if not channel:
            return
        view = discord.ui.View(timeout=SELECT_TIMEOUT)
        view.add_item(KickUserSelect(channel))
        await interaction.response.send_message(
            "Select members to kick from this room:", view=view, ephemeral=True
        )

    @discord.ui.button(label="Transfer", style=discord.ButtonStyle.primary, emoji="👑", custom_id="vc_btn_transfer", row=2)
    async def btn_transfer(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = await self._resolve(interaction)
        if not channel:
            return
        view = discord.ui.View(timeout=SELECT_TIMEOUT)
        view.add_item(TransferOwnerSelect(channel))
        await interaction.response.send_message(
            "Select the new owner of this room:", view=view, ephemeral=True
        )

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger, emoji="🗑️", custom_id="vc_btn_delete", row=2)
    async def btn_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = await self._resolve(interaction)
        if not channel:
            return
        cog = interaction.client.get_cog("VoiceSystem")
        await interaction.response.send_message(
            embed=info_embed("Deleting Room", "This voice room is being deleted..."),
            ephemeral=True,
        )
        if isinstance(cog, VoiceSystem):
            await cog.delete_room(channel, reason=f"Deleted by {interaction.user}")
        else:
            try:
                await db.execute("DELETE FROM active_temp_channels WHERE channel_id = ?", (channel.id,))
                await channel.delete(reason="Temporary voice room deleted")
            except Exception as exc:
                logger.warning("Fallback room delete failed for %s: %s", channel.id, exc)


# ==================== ADMIN PANEL ====================

class AdminResetConfirmView(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=60)
        self.guild_id = guild_id

    @discord.ui.button(label="Confirm Reset", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            return await interaction.response.send_message(
                embed=error_embed("Permission Denied", "Administrator permission required."),
                ephemeral=True,
            )
        await config_service.update_voice_j2c_config(
            self.guild_id,
            {"generator_channel_id": None, "category_id": None, "is_enabled": False},
            actor_id=interaction.user.id,
            actor_tag=str(interaction.user),
            source="DISCORD",
        )
        await interaction.response.edit_message(
            embed=success_embed(
                "Configuration Reset",
                "Join to Create settings were cleared. Existing temporary rooms stay until they empty.",
            ),
            view=None,
        )
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            embed=info_embed("Cancelled", "No changes were made."), view=None
        )
        self.stop()


class AdminVoicePanelView(discord.ui.View):
    """Persistent admin panel. Registered in main.py with no arguments."""

    def __init__(self):
        super().__init__(timeout=None)

    async def _admin_guard(self, interaction: discord.Interaction) -> bool:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                embed=error_embed("Guild Only", "This panel only works inside a server."),
                ephemeral=True,
            )
            return False
        if not is_admin(interaction.user):
            await interaction.response.send_message(
                embed=error_embed("Permission Denied", "Administrator permission required."),
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="Setup Join to Create", style=discord.ButtonStyle.success, emoji="🔊", custom_id="adm_vc_btn_setup", row=0)
    async def btn_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._admin_guard(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        cog = interaction.client.get_cog("VoiceSystem")
        if not isinstance(cog, VoiceSystem):
            return await interaction.followup.send("❌ Voice system cog is not loaded.", ephemeral=True)
        embed = await cog.auto_setup_guild(interaction.guild)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="Enable / Disable", style=discord.ButtonStyle.primary, emoji="⚡", custom_id="adm_vc_btn_toggle", row=0)
    async def btn_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._admin_guard(interaction):
            return
        cfg = await config_service.get_voice_j2c_config(interaction.guild_id)
        if not cfg.get("generator_channel_id"):
            return await interaction.response.send_message(
                embed=warning_embed(
                    "Not Configured",
                    "Set a generator channel first with **Setup Join to Create** or `/voice setup`.",
                ),
                ephemeral=True,
            )
        new_state = not bool(cfg.get("is_enabled"))
        await config_service.update_voice_j2c_config(
            interaction.guild_id,
            {"is_enabled": new_state},
            actor_id=interaction.user.id,
            actor_tag=str(interaction.user),
            source="DISCORD",
        )
        await interaction.response.send_message(
            embed=success_embed(
                "System Status Updated",
                f"Join to Create is now **{'Enabled 🟢' if new_state else 'Disabled 🔴'}**.",
            ),
            ephemeral=True,
        )

    @discord.ui.button(label="Active Rooms", style=discord.ButtonStyle.secondary, emoji="📊", custom_id="adm_vc_btn_active", row=0)
    async def btn_active(self, interaction: discord.Interaction, button: discord.ui.Button):
        rows = await db.fetchall(
            "SELECT * FROM active_temp_channels WHERE guild_id = ? ORDER BY created_at ASC",
            (interaction.guild_id,),
        )
        if not rows:
            return await interaction.response.send_message(
                embed=info_embed("Active Rooms", "No temporary voice rooms are active."),
                ephemeral=True,
            )
        lines = []
        for row in rows:
            channel = interaction.guild.get_channel(row["channel_id"])
            label = channel.name if channel else "`missing channel`"
            members = len([m for m in channel.members if not m.bot]) if channel else 0
            lines.append(f"• **{label}** — owner <@{row['owner_id']}> · {members} member(s)")
        await interaction.response.send_message(
            embed=primary_embed(f"📊 Active Rooms ({len(rows)})", "\n".join(lines[:20])),
            ephemeral=True,
        )

    @discord.ui.button(label="Defaults", style=discord.ButtonStyle.secondary, emoji="⚙️", custom_id="adm_vc_btn_defaults", row=1)
    async def btn_defaults(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._admin_guard(interaction):
            return
        cfg = await config_service.get_voice_j2c_config(interaction.guild_id)
        await interaction.response.send_modal(ServerVoiceConfigModal(cfg, interaction.guild))

    @discord.ui.button(label="Reset Configuration", style=discord.ButtonStyle.danger, emoji="🔄", custom_id="adm_vc_btn_reset", row=1)
    async def btn_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._admin_guard(interaction):
            return
        await interaction.response.send_message(
            embed=warning_embed(
                "Confirm Reset",
                "This clears the generator and category configuration for this server.",
            ),
            view=AdminResetConfirmView(interaction.guild_id),
            ephemeral=True,
        )


# ==================== MAIN COG ====================

class VoiceSystem(commands.Cog):
    """Join to Create Voice Channel & Personal VC Suite."""

    voice = app_commands.Group(
        name="voice",
        description="Join to Create voice system and personal room controls",
        guild_only=True,
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._locks: Dict[Tuple[int, int], asyncio.Lock] = {}
        self._empty_tasks: Dict[int, asyncio.Task] = {}
        self._pending_deletes: set = set()
        self._reconciled: set = set()

    def cog_unload(self):
        for task in list(self._empty_tasks.values()):
            if not task.done():
                task.cancel()
        self._empty_tasks.clear()

    def _lock_for(self, guild_id: int, user_id: int) -> asyncio.Lock:
        key = (guild_id, user_id)
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    # ---------------- STARTUP RECONCILIATION ----------------

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            if guild.id in self._reconciled:
                continue
            self._reconciled.add(guild.id)
            try:
                await self.reconcile_guild(guild)
            except Exception:
                logger.exception("Voice reconciliation failed for guild %s", guild.id)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        if guild.id not in self._reconciled:
            self._reconciled.add(guild.id)
            try:
                await self.reconcile_guild(guild)
            except Exception:
                logger.exception("Voice reconciliation failed for new guild %s", guild.id)

    async def reconcile_guild(self, guild: discord.Guild) -> None:
        """Sync persisted temp rooms with live guild state after a restart."""
        rows = await db.fetchall(
            "SELECT * FROM active_temp_channels WHERE guild_id = ?",
            (guild.id,),
        )
        cfg = await self._read_config(guild.id)
        if cfg is None or not cfg.get("generator_channel_id"):
            logger.info(
                "Voice inventory guild %s (%s): %s",
                guild.id,
                guild.name,
                [(c.id, c.name) for c in guild.voice_channels] or "no voice channels",
            )
            cfg = await self._ensure_generator(guild)
        delete_when_empty = bool(cfg.get("delete_when_empty", 1)) if cfg else True

        for row in rows:
            data = dict(row)
            channel = guild.get_channel(data["channel_id"])
            if not isinstance(channel, discord.VoiceChannel):
                await db.execute(
                    "DELETE FROM active_temp_channels WHERE channel_id = ?",
                    (data["channel_id"],),
                )
                logger.info("Dropped stale temp room row %s in guild %s", data["channel_id"], guild.id)
                continue

            humans = [m for m in channel.members if not m.bot]
            too_young = room_age_seconds(data.get("created_at")) < MIN_ROOM_AGE_SECONDS
            if delete_when_empty and not humans and not too_young:
                await self.delete_room(channel, reason="Reconciliation: empty temporary room")

        if cfg and cfg.get("generator_channel_id"):
            generator = guild.get_channel(cfg["generator_channel_id"])
            if not isinstance(generator, discord.VoiceChannel):
                await db.execute(
                    "UPDATE voice_config SET generator_channel_id = NULL, is_enabled = 0 WHERE guild_id = ?",
                    (guild.id,),
                )
                logger.warning("Generator channel missing in guild %s; voice system disabled.", guild.id)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        if not isinstance(channel, discord.VoiceChannel):
            return

        row = await fetch_temp_row(channel.id)
        if row:
            await db.execute(
                "DELETE FROM active_temp_channels WHERE channel_id = ?",
                (channel.id,),
            )
            task = self._empty_tasks.pop(channel.id, None)
            if task and not task.done():
                task.cancel()
            logger.info("Temp room %s was deleted externally; row removed.", channel.id)
            return

        cfg = await db.fetchone(
            "SELECT guild_id FROM voice_config WHERE guild_id = ? AND generator_channel_id = ?",
            (channel.guild.id, channel.id),
        )
        if cfg:
            await db.execute(
                "UPDATE voice_config SET generator_channel_id = NULL, is_enabled = 0 WHERE guild_id = ?",
                (channel.guild.id,),
            )
            logger.warning(
                "Generator channel deleted in guild %s; Join to Create disabled.", channel.guild.id
            )

    # ---------------- CONFIG ACCESS ----------------

    async def _read_config(self, guild_id: int) -> Optional[Dict[str, Any]]:
        row = await db.fetchone(
            "SELECT * FROM voice_config WHERE guild_id = ?",
            (guild_id,),
        )
        return dict(row) if row else None

    async def _write_config(self, guild_id: int, updates: Dict[str, Any],
                            actor: Optional[discord.abc.User] = None) -> Dict[str, Any]:
        return await config_service.update_voice_j2c_config(
            guild_id,
            updates,
            actor_id=actor.id if actor else None,
            actor_tag=str(actor) if actor else None,
            source="DISCORD",
        )

    # ---------------- VOICE STATE ----------------

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        guild = member.guild

        left_id = before.channel.id if before.channel else None
        joined_id = after.channel.id if after.channel else None

        if joined_id and joined_id != left_id and not member.bot:
            await self._maybe_spawn(member, after.channel)

        if left_id and left_id != joined_id:
            if not member.bot and await self._is_room_owner(guild, left_id, member.id):
                self._schedule_owner_departure(guild, left_id, member.id)
            else:
                await self._schedule_empty_check(guild, left_id)

    async def _autodetect_generator(self, guild: discord.Guild) -> Optional[Dict[str, Any]]:
        """Adopt an existing voice channel literally named 'Join to Create'.

        Runs only when the guild has no voice_config row yet, so an admin's
        explicit configuration is never overwritten.
        """
        temp_ids = {
            r["channel_id"]
            for r in await db.fetchall(
                "SELECT channel_id FROM active_temp_channels WHERE guild_id = ?",
                (guild.id,),
            )
        }
        for channel in guild.voice_channels:
            if channel.id in temp_ids:
                continue
            lowered = channel.name.lower()
            if any(hint in lowered for hint in GENERATOR_NAME_HINTS):
                category_id = channel.category.id if channel.category else None
                await self._write_config(
                    guild.id,
                    {
                        "generator_channel_id": channel.id,
                        "category_id": category_id,
                        "is_enabled": True,
                    },
                )
                logger.info(
                    "Auto-detected generator channel '%s' (%s) in guild %s",
                    channel.name, channel.id, guild.id,
                )
                return await self._read_config(guild.id)
        return None

    async def _ensure_generator(self, guild: discord.Guild) -> Optional[Dict[str, Any]]:
        """Adopt an existing generator, or rebuild one for a guild already configured.

        A guild gets a generator recreated only when it has a voice_config row,
        meaning an admin set the system up before and the channel vanished.
        """
        cfg = await self._read_config(guild.id)
        if cfg and cfg.get("generator_channel_id"):
            live = guild.get_channel(cfg["generator_channel_id"])
            if isinstance(live, discord.VoiceChannel):
                return cfg
            # Cache can miss right after a restart; ask the API before rebuilding,
            # otherwise every boot spawns another generator channel.
            try:
                fetched = await guild.fetch_channel(cfg["generator_channel_id"])
            except discord.NotFound:
                fetched = None
            except discord.HTTPException:
                fetched = None
            if isinstance(fetched, discord.VoiceChannel):
                return cfg

        cfg = await self._autodetect_generator(guild)
        if cfg and cfg.get("generator_channel_id"):
            return cfg

        row = await db.fetchone(
            "SELECT guild_id FROM voice_config WHERE guild_id = ?",
            (guild.id,),
        )
        if not row:
            return cfg

        category = None
        if cfg and cfg.get("category_id"):
            existing = guild.get_channel(cfg["category_id"])
            if isinstance(existing, discord.CategoryChannel):
                category = existing

        try:
            channel = await guild.create_voice_channel(
                "🔊・Join to Create",
                category=category,
                reason="Join to Create: rebuilding missing generator channel",
            )
        except discord.Forbidden:
            logger.warning("Missing Manage Channels; cannot rebuild generator in guild %s", guild.id)
            return cfg
        except discord.HTTPException:
            logger.exception("Failed to rebuild generator channel in guild %s", guild.id)
            return cfg

        await self._write_config(
            guild.id,
            {
                "generator_channel_id": channel.id,
                "category_id": channel.category.id if channel.category else None,
                "is_enabled": True,
            },
        )
        logger.info(
            "Rebuilt generator channel '%s' (%s) in guild %s",
            channel.name, channel.id, guild.id,
        )
        return await self._read_config(guild.id)

    async def _maybe_spawn(self, member: discord.Member, channel: discord.abc.GuildChannel) -> None:
        if not isinstance(channel, discord.VoiceChannel):
            return
        cfg = await self._read_config(member.guild.id)
        if not cfg or not cfg.get("generator_channel_id"):
            cfg = await self._ensure_generator(member.guild)
        if not cfg or not cfg.get("is_enabled") or cfg.get("generator_channel_id") != channel.id:
            logger.info(
                "Spawn skipped for %s in guild %s (joined %s, generator %s, enabled %s)",
                member.id, member.guild.id, channel.id,
                (cfg or {}).get("generator_channel_id"),
                (cfg or {}).get("is_enabled"),
            )
            return

        lock = self._lock_for(member.guild.id, member.id)
        async with lock:
            # State can change while waiting on the lock; re-validate.
            current = member.voice.channel if member.voice else None
            if not current or current.id != channel.id:
                return
            cfg = await self._read_config(member.guild.id)
            if not cfg or not cfg.get("is_enabled") or cfg.get("generator_channel_id") != channel.id:
                return

            existing = await db.fetchone(
                "SELECT channel_id FROM active_temp_channels WHERE guild_id = ? AND owner_id = ?",
                (member.guild.id, member.id),
            )
            if existing:
                room = member.guild.get_channel(existing["channel_id"])
                if isinstance(room, discord.VoiceChannel):
                    try:
                        await member.move_to(room, reason="Returned to existing temporary room")
                        return
                    except Exception as exc:
                        logger.warning("Could not move %s to existing room: %s", member.id, exc)
                else:
                    await db.execute(
                        "DELETE FROM active_temp_channels WHERE channel_id = ?",
                        (existing["channel_id"],),
                    )

            await self._create_room(member, channel, cfg)

    async def _create_room(self, member: discord.Member,
                           generator: discord.VoiceChannel,
                           cfg: Dict[str, Any]) -> None:
        guild = member.guild
        ok, reason = bot_can_manage(guild)
        if not ok:
            logger.error("Cannot create temp room in guild %s: %s", guild.id, reason)
            return

        category = None
        if cfg.get("category_id"):
            candidate = guild.get_channel(cfg["category_id"])
            if isinstance(candidate, discord.CategoryChannel):
                category = candidate
        if category is None:
            category = generator.category

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=True, connect=True, speak=True, stream=True, use_voice_activation=True
            ),
            member: discord.PermissionOverwrite(
                view_channel=True,
                connect=True,
                speak=True,
                stream=True,
                manage_channels=True,
                move_members=True,
                mute_members=True,
                deafen_members=True,
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                connect=True,
                speak=True,
                manage_channels=True,
                move_members=True,
                manage_roles=True,
            ),
        }

        name = render_channel_name(cfg.get("channel_name_format"), member)
        bitrate = clamp_bitrate(cfg.get("default_bitrate") or 64000, guild)
        limit = clamp_user_limit(cfg.get("default_user_limit") or 0)

        channel: Optional[discord.VoiceChannel] = None
        try:
            channel = await guild.create_voice_channel(
                name=name,
                category=category,
                overwrites=overwrites,
                user_limit=limit,
                bitrate=bitrate,
                reason=f"Join to Create room for {member}",
            )
            try:
                await member.move_to(channel, reason="Moved into created temporary voice room")
            except discord.Forbidden:
                # Keep the room so the member can join it manually; a missing
                # Move Members permission should not make the channel vanish.
                logger.warning(
                    "Missing Move Members permission in guild %s; room %s left for manual join.",
                    guild.id, channel.id,
                )
                await self._notify_member(
                    member,
                    warning_embed(
                        "Voice Room Created",
                        f"Your room {channel.mention} is ready, but I could not move you into it. "
                        "Join it manually or ask an admin to grant **Move Members**.",
                    ),
                )
            except Exception as exc:
                logger.warning("Move failed for %s, removing spawned room: %s", member.id, exc)
                await channel.delete(reason="Move failed during Join to Create")
                return

            await db.execute(
                "INSERT INTO active_temp_channels (channel_id, guild_id, owner_id) VALUES (?, ?, ?)",
                (channel.id, guild.id, member.id),
            )

            embed = build_control_panel_embed(member, channel)
            try:
                message = await channel.send(embed=embed, view=VoiceControlPanelView())
                await db.execute(
                    "UPDATE active_temp_channels SET control_panel_message_id = ? WHERE channel_id = ?",
                    (message.id, channel.id),
                )
            except Exception as exc:
                logger.warning("Control panel send failed in %s: %s", channel.id, exc)

            logger.info("Spawned temp room %s for %s in guild %s", channel.id, member, guild.id)
        except discord.Forbidden:
            logger.error("Forbidden while creating temp room in guild %s", guild.id)
            await self._notify_member(
                member,
                error_embed(
                    "Voice Setup Failed",
                    "I lack **Manage Channels** or **Move Members**. Ask an admin to fix my permissions.",
                ),
            )
            if channel:
                try:
                    await channel.delete(reason="Join to Create cleanup")
                except Exception:
                    pass
        except Exception as exc:
            logger.exception("Temp room creation failed for %s", member)
            await self._notify_member(
                member,
                error_embed("Voice Setup Failed", f"Could not create your room: `{exc}`"),
            )
            if channel:
                try:
                    await channel.delete(reason="Join to Create cleanup")
                except Exception:
                    pass

    async def _notify_member(self, member: discord.Member, embed: discord.Embed) -> None:
        try:
            await member.send(embed=embed)
        except Exception:
            pass

    async def _is_room_owner(self, guild: discord.Guild, channel_id: int, member_id: int) -> bool:
        row = await fetch_temp_row(channel_id)
        return bool(row) and int(row["owner_id"]) == member_id

    def _schedule_owner_departure(self, guild: discord.Guild, channel_id: int, owner_id: int) -> None:
        existing = self._empty_tasks.get(channel_id)
        if existing and not existing.done():
            return
        task = asyncio.create_task(
            self._delete_after_owner_departure(guild, channel_id, owner_id)
        )
        self._empty_tasks[channel_id] = task

    async def _delete_after_owner_departure(self, guild: discord.Guild,
                                            channel_id: int, owner_id: int) -> None:
        """Owner-driven teardown: the room dies with its owner, not with the last member."""
        try:
            await asyncio.sleep(OWNER_DEPARTURE_GRACE_SECONDS)
            if channel_id in self._pending_deletes:
                return
            row = await fetch_temp_row(channel_id)
            if not row or int(row["owner_id"]) != owner_id:
                return
            channel = guild.get_channel(channel_id)
            if not isinstance(channel, discord.VoiceChannel):
                await db.execute(
                    "DELETE FROM active_temp_channels WHERE channel_id = ?", (channel_id,)
                )
                return
            if any(m.id == owner_id for m in channel.members):
                return
            await self.delete_room(channel, reason="Room owner left the temporary voice room")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Owner departure teardown failed for %s", channel_id)
        finally:
            self._empty_tasks.pop(channel_id, None)

    # ---------------- EMPTY ROOM HANDLING ----------------

    async def _schedule_empty_check(self, guild: discord.Guild, channel_id: int) -> None:
        existing = self._empty_tasks.get(channel_id)
        if existing and not existing.done():
            return
        task = asyncio.create_task(self._empty_check_after_delay(guild, channel_id))
        self._empty_tasks[channel_id] = task

    async def _empty_check_after_delay(self, guild: discord.Guild, channel_id: int) -> None:
        try:
            await asyncio.sleep(EMPTY_GRACE_SECONDS)
            if channel_id in self._pending_deletes:
                return
            row = await fetch_temp_row(channel_id)
            if not row:
                return
            data = dict(row)

            channel = guild.get_channel(channel_id)
            if not isinstance(channel, discord.VoiceChannel):
                await db.execute(
                    "DELETE FROM active_temp_channels WHERE channel_id = ?", (channel_id,)
                )
                return

            if any(not m.bot for m in channel.members):
                return  # somebody rejoined during the grace period

            cfg = await self._read_config(guild.id)
            delete_when_empty = bool(cfg.get("delete_when_empty", 1)) if cfg else True
            if not delete_when_empty:
                return
            if room_age_seconds(data.get("created_at")) < MIN_ROOM_AGE_SECONDS:
                return

            await self.delete_room(channel, reason="Last member left temporary voice room")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Empty room check failed for %s", channel_id)
        finally:
            self._empty_tasks.pop(channel_id, None)

    async def delete_room(self, channel: Optional[discord.VoiceChannel], *, reason: str) -> bool:
        if channel is None:
            return False
        channel_id = channel.id
        if channel_id in self._pending_deletes:
            return False
        self._pending_deletes.add(channel_id)
        try:
            task = self._empty_tasks.pop(channel_id, None)
            if task and not task.done() and task is not asyncio.current_task():
                task.cancel()
            await db.execute(
                "DELETE FROM active_temp_channels WHERE channel_id = ?", (channel_id,)
            )
            try:
                await channel.delete(reason=reason)
            except discord.NotFound:
                pass
            except Exception as exc:
                logger.warning("Channel delete failed for %s: %s", channel_id, exc)
            logger.info("Deleted temporary voice room %s (%s)", channel_id, reason)
            return True
        finally:
            self._pending_deletes.discard(channel_id)

    # ---------------- AUTO SETUP ----------------

    async def auto_setup_guild(self, guild: discord.Guild) -> discord.Embed:
        """Idempotently create/reuse a category and generator channel."""
        ok, reason = bot_can_manage(guild)
        if not ok:
            return error_embed("Missing Permissions", reason)

        cfg = await self._read_config(guild.id)
        if cfg and cfg.get("generator_channel_id"):
            existing = guild.get_channel(cfg["generator_channel_id"])
            if isinstance(existing, discord.VoiceChannel):
                await self._write_config(guild.id, {"is_enabled": True})
                return success_embed(
                    "Already Configured",
                    f"Generator is already {existing.mention}. The system is **enabled**.",
                )

        try:
            category = None
            if cfg and cfg.get("category_id"):
                candidate = guild.get_channel(cfg["category_id"])
                if isinstance(candidate, discord.CategoryChannel):
                    category = candidate
            if category is None:
                for cat in guild.categories:
                    lowered = cat.name.lower()
                    if "voice" in lowered or "j2c" in lowered:
                        category = cat
                        break
            if category is None:
                category = await guild.create_category(
                    "🔊・VOICE CHANNELS", reason="Join to Create category setup"
                )

            generator = await guild.create_voice_channel(
                name="➕・Join to Create",
                category=category,
                reason="Join to Create generator setup",
            )
            await self._write_config(
                guild.id,
                {
                    "generator_channel_id": generator.id,
                    "category_id": category.id,
                    "is_enabled": True,
                },
            )
        except Exception as exc:
            logger.exception("Auto setup failed for guild %s", guild.id)
            return error_embed("Setup Failed", f"Could not complete auto-setup: `{exc}`")

        fmt = (cfg or {}).get("channel_name_format") or DEFAULT_NAME_FORMAT
        return success_embed(
            "Join to Create Configured",
            f"**Join to Create is live.**\n\n"
            f"• Generator: {generator.mention}\n"
            f"• Category: **{category.name}**\n"
            f"• Format: `{fmt}`\n\n"
            f"When a member joins {generator.mention}, a private room with a control panel appears.",
        )

    # ---------------- SLASH COMMANDS ----------------

    @voice.command(name="setup", description="Configure a Join to Create generator channel (or auto-create one)")
    @app_commands.describe(
        channel="Existing voice channel to use as the generator (omit to auto-create)",
        category="Category where temporary rooms spawn",
        name_format="Name template, e.g. 🔊・{username} or {username}'s Room",
        user_limit="Default room capacity, 0 = unlimited",
        bitrate="Default bitrate in kbps (e.g. 64, 96, 128)",
        delete_when_empty="Delete the room automatically when everyone leaves",
    )
    @has_admin_or_owner()
    async def slash_setup(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.VoiceChannel] = None,
        category: Optional[discord.CategoryChannel] = None,
        name_format: Optional[str] = None,
        user_limit: Optional[int] = None,
        bitrate: Optional[int] = None,
        delete_when_empty: Optional[bool] = None,
    ):
        if channel is None:
            await interaction.response.defer(ephemeral=True)
            embed = await self.auto_setup_guild(interaction.guild)
            return await interaction.followup.send(embed=embed, ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        ok, reason = bot_can_manage(guild)
        if not ok:
            return await interaction.followup.send(
                embed=error_embed("Missing Permissions", reason), ephemeral=True
            )

        fmt = (name_format or DEFAULT_NAME_FORMAT).strip()
        fmt_error = validate_name_format(fmt)
        if fmt_error:
            return await interaction.followup.send(
                embed=error_embed("Invalid Name Format", fmt_error), ephemeral=True
            )

        cat = category or channel.category
        updates: Dict[str, Any] = {
            "generator_channel_id": channel.id,
            "category_id": cat.id if cat else None,
            "channel_name_format": fmt,
            "is_enabled": True,
        }
        if user_limit is not None:
            updates["default_user_limit"] = clamp_user_limit(user_limit)
        if bitrate is not None:
            if bitrate < 8 or bitrate * 1000 > int(guild.bitrate_limit):
                return await interaction.followup.send(
                    embed=error_embed(
                        "Invalid Bitrate",
                        f"Use 8-{int(guild.bitrate_limit) // 1000} kbps for this server tier.",
                    ),
                    ephemeral=True,
                )
            updates["default_bitrate"] = clamp_bitrate(bitrate * 1000, guild)
        if delete_when_empty is not None:
            updates["delete_when_empty"] = delete_when_empty

        cfg = await self._write_config(guild.id, updates, actor=interaction.user)

        await interaction.followup.send(
            embed=success_embed(
                "Join to Create Configured",
                f"{channel.mention} is now the generator.\n\n"
                f"• Category: **{cat.name if cat else 'None'}**\n"
                f"• Format: `{cfg.get('channel_name_format')}`\n"
                f"• Capacity: `{clamp_user_limit(cfg.get('default_user_limit') or 0)}`\n"
                f"• Bitrate: `{int((cfg.get('default_bitrate') or 64000) / 1000)} kbps`\n"
                f"• Auto-delete: `{'yes' if cfg.get('delete_when_empty') else 'no'}`",
            ),
            ephemeral=True,
        )

    @voice.command(name="enable", description="Enable the Join to Create system for this server")
    @has_admin_or_owner()
    async def slash_enable(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        cfg = await config_service.get_voice_j2c_config(interaction.guild_id)
        if not cfg.get("generator_channel_id"):
            return await interaction.followup.send(
                embed=warning_embed(
                    "Not Configured",
                    "Run `/voice setup` first so a generator channel exists.",
                ),
                ephemeral=True,
            )
        await self._write_config(interaction.guild_id, {"is_enabled": True}, actor=interaction.user)
        await interaction.followup.send(
            embed=success_embed("System Enabled", "Join to Create is now **enabled**."),
            ephemeral=True,
        )

    @voice.command(name="disable", description="Disable the Join to Create system for this server")
    @has_admin_or_owner()
    async def slash_disable(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self._write_config(interaction.guild_id, {"is_enabled": False}, actor=interaction.user)
        await interaction.followup.send(
            embed=success_embed(
                "System Disabled",
                "Join to Create is now **disabled**. Existing rooms stay until deleted or emptied.",
            ),
            ephemeral=True,
        )

    @voice.command(name="config", description="View the current Join to Create configuration")
    async def slash_config(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        cfg = await config_service.get_voice_j2c_config(guild.id)
        if not cfg.get("generator_channel_id"):
            return await interaction.followup.send(
                embed=info_embed(
                    "Not Configured",
                    "Join to Create is not configured yet. Use `/voice setup` to start.",
                ),
                ephemeral=True,
            )

        generator = guild.get_channel(cfg["generator_channel_id"])
        category = guild.get_channel(cfg["category_id"]) if cfg.get("category_id") else None
        active = await db.fetchone(
            "SELECT COUNT(*) AS c FROM active_temp_channels WHERE guild_id = ?",
            (guild.id,),
        )
        await interaction.followup.send(
            embed=primary_embed(
                "⚙️ Voice Configuration",
                f"• **Status:** {'Enabled 🟢' if cfg.get('is_enabled') else 'Disabled 🔴'}\n"
                f"• **Generator:** {generator.mention if generator else '`deleted channel`'}\n"
                f"• **Category:** {category.name if category else '`none`'}\n"
                f"• **Name Format:** `{cfg.get('channel_name_format')}`\n"
                f"• **Default Capacity:** `{clamp_user_limit(cfg.get('default_user_limit') or 0)}`\n"
                f"• **Default Bitrate:** `{int((cfg.get('default_bitrate') or 64000) / 1000)} kbps`\n"
                f"• **Auto-delete when empty:** `{'yes' if cfg.get('delete_when_empty') else 'no'}`\n"
                f"• **Active Rooms:** `{active['c'] if active else 0}`",
            ),
            ephemeral=True,
        )

    @voice.command(name="panel", description="Post the interactive Join to Create admin panel")
    @has_admin_or_owner()
    async def slash_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎙️ Join to Create — Admin Control Panel",
            description=(
                "Manage the **Join to Create Voice System** for this server.\n\n"
                "• 🔊 **Setup Join to Create** — create or reuse a generator channel\n"
                "• ⚡ **Enable / Disable** — toggle the dynamic voice system\n"
                "• 📊 **Active Rooms** — list current temporary rooms\n"
                "• ⚙️ **Defaults** — name format, capacity, bitrate, auto-delete\n"
                "• 🔄 **Reset Configuration** — clear the generator setup"
            ),
            color=PANEL_COLOR,
        )
        embed.set_footer(text=f"{BOT_NAME} Voice Suite • Admin")
        await interaction.response.send_message(embed=embed, view=AdminVoicePanelView())

    @voice.command(name="stats", description="Show temporary voice room statistics")
    async def slash_stats(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        rows = await db.fetchall(
            "SELECT * FROM active_temp_channels WHERE guild_id = ?",
            (guild.id,),
        )
        total_members = 0
        for row in rows:
            channel = guild.get_channel(row["channel_id"])
            if isinstance(channel, discord.VoiceChannel):
                total_members += len([m for m in channel.members if not m.bot])

        await interaction.followup.send(
            embed=primary_embed(
                "📊 Voice System Statistics",
                f"• **Active Rooms:** `{len(rows)}`\n"
                f"• **Members in Rooms:** `{total_members}`\n"
                f"• **Server Bitrate Ceiling:** `{int(guild.bitrate_limit) // 1000} kbps`\n"
                f"• **Boost Tier:** `Tier {guild.premium_tier}`",
            ),
            ephemeral=True,
        )

    @voice.command(name="reset", description="Reset the Join to Create configuration")
    @has_admin_or_owner()
    async def slash_reset(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=warning_embed(
                "Confirm Reset",
                "This clears the generator channel and category. Active rooms keep running until they empty.",
            ),
            view=AdminResetConfirmView(interaction.guild_id),
            ephemeral=True,
        )

    @voice.command(name="join", description="Connect the bot to your voice channel")
    @app_commands.describe(channel="Voice channel to connect to (defaults to yours)")
    @app_commands.guild_only()
    async def slash_join(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.VoiceChannel] = None,
    ):
        await interaction.response.defer(ephemeral=True)
        member = interaction.user
        target = channel or (member.voice.channel if isinstance(member, discord.Member) and member.voice else None)
        if not target:
            return await interaction.followup.send(
                embed=warning_embed(
                    "Voice Required",
                    "Join a voice channel first or pick one with the `channel` option.",
                ),
                ephemeral=True,
            )

        perms = target.permissions_for(interaction.guild.me)
        if not perms.connect or not perms.speak:
            return await interaction.followup.send(
                embed=error_embed(
                    "Missing Permissions",
                    f"I need **Connect** and **Speak** in {target.mention}.",
                ),
                ephemeral=True,
            )

        voice_client = interaction.guild.voice_client
        try:
            if voice_client and voice_client.is_connected():
                if voice_client.channel.id != target.id:
                    await voice_client.move_to(target)
            else:
                await target.connect(self_deaf=True)
        except Exception as exc:
            return await interaction.followup.send(
                embed=error_embed("Voice Error", f"Could not connect: `{exc}`"),
                ephemeral=True,
            )
        await interaction.followup.send(
            embed=success_embed("Connected", f"Joined {target.mention}."),
            ephemeral=True,
        )

    @voice.command(name="leave", description="Disconnect the bot from voice")
    @app_commands.guild_only()
    async def slash_leave(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_connected():
            channel = voice_client.channel
            await voice_client.disconnect(force=True)
            return await interaction.followup.send(
                embed=info_embed("Disconnected", f"Left {channel.mention if channel else 'voice'}."),
                ephemeral=True,
            )
        await interaction.followup.send(
            embed=warning_embed("Not In Voice", "I am not connected to a voice channel."),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceSystem(bot))
