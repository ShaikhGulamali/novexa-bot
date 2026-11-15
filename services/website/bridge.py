"""NOVEXA - Web <-> Bot bridge.

Exposes the live slash-command tree to the web console and executes any
command from the browser by building a synthetic interaction, so the
dashboard and the Discord client share one code path.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

import discord
from discord import app_commands

logger = logging.getLogger("novexa.bridge")

OPTION_TYPES = {
    3: "string",
    4: "integer",
    5: "boolean",
    6: "user",
    7: "channel",
    8: "role",
    9: "mentionable",
    10: "number",
    11: "attachment",
}


# ==================== CATALOG ====================

def _walk(commands, prefix: str = ""):
    # In discord.py 2.7 Group is not a Command subclass, so groups are checked first.
    for cmd in commands:
        if isinstance(cmd, app_commands.Group):
            yield from _walk(cmd.commands, f"{prefix}{cmd.name} ")
        elif isinstance(cmd, app_commands.Command):
            yield f"{prefix}{cmd.name}", cmd


def _option_payload(param) -> Dict[str, Any]:
    type_id = getattr(param.type, "value", param.type)
    channel_types: List[str] = []
    if param.channel_types:
        channel_types = [getattr(ct, "name", str(ct)) for ct in param.channel_types]
    description = param.description or ""
    if description.strip() in ("…", "..."):
        description = ""
    return {
        "name": param.display_name,
        "description": description,
        "type": OPTION_TYPES.get(int(type_id), "string"),
        "required": bool(param.required),
        "choices": [{"name": c.name, "value": c.value} for c in (param.choices or [])],
        "channel_types": channel_types,
        "min": param.min_value,
        "max": param.max_value,
        "default": param.default if isinstance(param.default, (str, int, float, bool)) else None,
    }


def _tree_commands(bot, guild: Optional[discord.Guild]):
    tree = getattr(bot, "tree", None)
    if tree is None:
        return []
    if guild is not None:
        scoped = tree.get_commands(guild=guild)
        if scoped:
            return scoped
    return tree.get_commands()


def build_catalog(bot, guild: Optional[discord.Guild] = None) -> List[Dict[str, Any]]:
    """Every slash command the bot registers, grouped by owning cog."""
    commands = _tree_commands(bot, guild)
    seen: Dict[str, Dict[str, Any]] = {}

    for name, cmd in _walk(commands):
        if name in seen:
            continue
        cog = cmd.binding.__class__.__name__ if getattr(cmd, "binding", None) else "Core"
        seen[name] = {
            "name": name,
            "description": cmd.description or "",
            "category": cog,
            "options": [_option_payload(p) for p in cmd.parameters],
            "nsfw": bool(getattr(cmd, "nsfw", False)),
        }
    return sorted(seen.values(), key=lambda c: (c["category"], c["name"]))


def find_command(bot, guild: Optional[discord.Guild], name: str):
    for full, cmd in _walk(_tree_commands(bot, guild)):
        if full == name:
            return cmd
    return None


# ==================== SYNTHETIC INTERACTION ====================

class _CapturedResponse:
    def __init__(self, sink: "CaptureSink"):
        self._sink = sink
        self._done = False

    def is_done(self) -> bool:
        return self._done

    async def defer(self, *, ephemeral: bool = False, thinking: bool = False):
        self._done = True

    async def send_message(self, content=None, *, embed=None, embeds=None, view=None,
                           ephemeral: bool = False, file=None, files=None,
                           allowed_mentions=None, delete_after=None, suppress_embeds=False):
        self._done = True
        self._sink.add(content, embed, embeds, view)

    async def edit_message(self, *, content=None, embed=None, embeds=None, view=None,
                           allowed_mentions=None, attachments=None):
        self._done = True
        self._sink.add(content, embed, embeds, view)

    async def send_modal(self, modal):
        self._done = True
        self._sink.add("_This command opens a Discord modal. Run it inside Discord._")


class _CapturedFollowup:
    def __init__(self, sink: "CaptureSink"):
        self._sink = sink

    async def send(self, content=None, *, embed=None, embeds=None, view=None,
                   ephemeral: bool = False, file=None, files=None,
                   allowed_mentions=None, wait: bool = False):
        self._sink.add(content, embed, embeds, view)
        return None


class _OriginalMessage:
    async def edit(self, **kwargs):
        return None

    async def delete(self):
        return None


class CaptureSink:
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []

    def add(self, content=None, embed=None, embeds=None, view=None):
        blocks = []
        if embed is not None:
            blocks.append(embed)
        if embeds:
            blocks.extend(embeds)
        self.messages.append({
            "content": str(content) if content is not None else None,
            "embeds": [e.to_dict() for e in blocks if hasattr(e, "to_dict")],
            "has_view": bool(view) and not isinstance(view, type(None)),
        })


class WebInteraction:
    """Minimal stand-in for discord.Interaction, good enough for command bodies."""

    def __init__(self, bot, guild: discord.Guild, actor: discord.Member, command):
        self.client = bot
        self._state = getattr(bot, "_connection", None)
        self.guild = guild
        self.guild_id = guild.id
        self.channel = guild.system_channel or (guild.text_channels[0] if guild.text_channels else None)
        self.channel_id = self.channel.id if self.channel else None
        self.user = actor
        self.command = command
        self.command_name = getattr(command, "qualified_name", getattr(command, "name", ""))
        self.application_id = bot.application_id
        self.type = discord.InteractionType.application_command
        self.created_at = discord.utils.utcnow()
        self.locale = discord.Locale.american_english
        self.guild_locale = discord.Locale.american_english
        self.permissions = getattr(actor, "guild_permissions", None)
        self.extras = {}
        self.sink = CaptureSink()
        self.response = _CapturedResponse(self.sink)
        self.followup = _CapturedFollowup(self.sink)

    async def original_response(self):
        return _OriginalMessage()

    async def edit_original_response(self, **kwargs):
        self.sink.add(kwargs.get("content"), kwargs.get("embed"), kwargs.get("embeds"), kwargs.get("view"))
        return None


# ==================== EXECUTION ====================

async def resolve_actor(bot, guild: discord.Guild, user_id: int) -> Optional[discord.Member]:
    member = guild.get_member(user_id)
    if member is not None:
        return member
    try:
        return await guild.fetch_member(user_id)
    except Exception:
        return None


def actor_can_manage(guild: discord.Guild, member: discord.Member, user_id: int, owner_ids) -> bool:
    if user_id in owner_ids or guild.owner_id == user_id:
        return True
    perms = member.guild_permissions
    return bool(perms.administrator or perms.manage_guild)


async def _coerce(bot, guild: discord.Guild, opt: Dict[str, Any], raw: Any):
    kind = opt["type"]
    if raw is None or raw == "":
        return None
    if kind in ("string",):
        return str(raw)
    if kind == "integer":
        return int(raw)
    if kind == "number":
        return float(raw)
    if kind == "boolean":
        return bool(raw) if isinstance(raw, bool) else str(raw).lower() in ("1", "true", "yes", "on")
    try:
        snowflake = int(raw)
    except (TypeError, ValueError):
        raise ValueError(f"`{opt['name']}` expects an ID.")
    if kind == "role":
        role = guild.get_role(snowflake)
        if role is None:
            raise ValueError(f"Role {snowflake} not found in this server.")
        return role
    if kind == "channel":
        channel = guild.get_channel_or_thread(snowflake)
        if channel is None:
            raise ValueError(f"Channel {snowflake} not found in this server.")
        return channel
    if kind in ("user", "mentionable"):
        member = await resolve_actor(bot, guild, snowflake)
        if member is not None:
            return member
        if kind == "mentionable":
            role = guild.get_role(snowflake)
            if role is not None:
                return role
        user = bot.get_user(snowflake)
        if user is not None:
            return user
        try:
            return await bot.fetch_user(snowflake)
        except Exception:
            raise ValueError(f"User {snowflake} not found.")
    raise ValueError(f"`{opt['name']}` uses an unsupported option type.")


async def run_command(bot, guild: discord.Guild, actor: discord.Member,
                      name: str, options: Dict[str, Any]) -> Dict[str, Any]:
    command = find_command(bot, guild, name)
    if command is None:
        return {"ok": False, "error": f"Unknown command `{name}`."}

    values: Dict[str, Any] = {}
    for param in command.parameters:
        raw = options.get(param.display_name)
        if raw is None or raw == "":
            if param.required:
                return {"ok": False, "error": f"`{param.display_name}` is required."}
            values[param.name] = param.default
            continue
        try:
            values[param.name] = await _coerce(bot, guild, _option_payload(param), raw)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

    interaction = WebInteraction(bot, guild, actor, command)
    try:
        if not await command._check_can_run(interaction):
            return {"ok": False, "error": "Your Discord roles do not grant access to this command."}
        await asyncio.wait_for(command._do_call(interaction, values), timeout=120)
    except asyncio.TimeoutError:
        return {"ok": False, "error": "Command exceeded the 120s web timeout. Check Discord for partial results."}
    except app_commands.CheckFailure as exc:
        return {"ok": False, "error": str(exc) or "You do not have permission for this command."}
    except app_commands.CommandInvokeError as exc:
        original = exc.original
        logger.warning("Web command '%s' failed: %s", name, original)
        return {"ok": False, "error": f"Command failed: {type(original).__name__}: {original}"}
    except Exception as exc:
        logger.warning("Web command '%s' crashed: %s", name, exc, exc_info=True)
        return {"ok": False, "error": f"Command crashed: {type(exc).__name__}: {exc}"}

    return {"ok": True, "messages": interaction.sink.messages}
