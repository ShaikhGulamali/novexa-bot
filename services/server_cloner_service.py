"""NOVEXA Public & Internal Server Structure Cloner Service.

Provides multi-tier source access resolution:
- Method A: Bot-based source scan (Full if Admin, Public if Member).
- Method B: Discord Public Widget API & Public Guild Preview / Invite resolution.
- Method C: Official Discord Server Templates (discord.new/...) & Authorized Structure JSON Import/Export.

Complies strictly with official Discord Developer Terms of Service and official Discord API endpoints.
"""

import asyncio
import json
import logging
import re
import time
from typing import Optional, Dict, List, Any, Tuple, Callable, Coroutine
import aiohttp
import discord
from discord.ext import commands

from database.database import db
from config import BOT_NAME, DISCORD_TOKEN

logger = logging.getLogger("novexa.cloner_service")


# ==================== QUERY EXTRACTORS ====================

def extract_template_code(input_str: str) -> Optional[str]:
    """Extract Discord server template code from link or string."""
    clean = input_str.strip()
    match = re.search(r"(?:discord\.new/|discord\.com/template/)([a-zA-Z0-9_-]+)", clean, re.IGNORECASE)
    if match:
        return match.group(1)
    if re.fullmatch(r"[a-zA-Z0-9_-]{6,32}", clean) and not clean.isdigit():
        return clean
    return None


def extract_guild_id(input_str: str) -> Optional[int]:
    """Extract numeric Discord Snowflake Guild ID."""
    clean = input_str.strip()
    if clean.isdigit() and 17 <= len(clean) <= 21:
        return int(clean)
    # Check if inside an invite or widget URL or markdown
    match = re.search(r"\b(\d{17,21})\b", clean)
    if match:
        return int(match.group(1))
    return None


def extract_invite_code(input_str: str) -> Optional[str]:
    """Extract invite vanity or code from Discord invite URL."""
    clean = input_str.strip()
    match = re.search(r"(?:discord\.gg/|discord\.com/invite/)([a-zA-Z0-9_-]+)", clean, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


class ServerClonerService:
    """Enterprise Discord Server Structure Scanner & Cloner Engine."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ==================== 1. MULTI-TIER SOURCE ACCESS RESOLVER ====================

    async def resolve_source_access(
        self, source_query: str, user_id: int
    ) -> Tuple[bool, str, Dict[str, Any], Optional[Dict[str, Any]]]:
        """Multi-tier source access resolver supporting Bot, Widget, Template, and Invite methods.

        Returns:
            success (bool): True if structure is retrieved and ready.
            access_mode (str): Identifies resolution method (e.g. BOT_INTERNAL_FULL, DISCORD_TEMPLATE, PUBLIC_WIDGET_API).
            report (dict): Metadata, access status, or scan availability report.
            structure (dict | None): Normalized NOVEXA architecture structure.
        """
        source_clean = source_query.strip()
        logger.info(f"Resolving source access for query: {source_clean} (requested by user {user_id})")

        # ------------------------------------------------------------------
        # 1. Check Method C: Official Discord Server Template (discord.new/...)
        # ------------------------------------------------------------------
        tmpl_code = extract_template_code(source_clean)
        if tmpl_code:
            logger.info(f"Detected template code '{tmpl_code}'. Querying Discord Template API...")
            tmpl_success, tmpl_data, tmpl_err = await self._fetch_discord_template(tmpl_code)
            if tmpl_success and tmpl_data:
                structure = self.parse_template_data(tmpl_data, user_id)
                report = {
                    "source_input": source_clean,
                    "access_mode": "DISCORD_TEMPLATE",
                    "access_mode_display": "Official Discord Server Template (discord.new)",
                    "server_name": structure["source_guild_name"],
                    "template_code": tmpl_code,
                    "roles_count": len(structure["roles"]),
                    "categories_count": len(structure["categories"]),
                    "channels_count": len(structure["text_channels"]) + len(structure["voice_channels"]),
                    "unavailable_items": structure.get("unavailable_items", []),
                }
                return True, "DISCORD_TEMPLATE", report, structure
            elif not extract_guild_id(source_clean):
                # If query was purely a template code and failed
                report = {
                    "source_input": source_clean,
                    "status_code": "TEMPLATE_NOT_FOUND",
                    "status_summary": f"Unknown or expired Discord Server Template code: `{tmpl_code}`.",
                    "available_methods": [
                        "1. Verify that the Discord template code is valid (e.g. `discord.new/abc`)",
                        "2. Enter a Source Server ID where NOVEXA is installed",
                        "3. Upload a structure JSON export using `/clone import`",
                    ],
                }
                return False, "ACCESS_RESTRICTED", report, None

        # ------------------------------------------------------------------
        # 2. Check Method A: Bot-based scan if NOVEXA is in source guild
        # ------------------------------------------------------------------
        guild_id = extract_guild_id(source_clean)
        if guild_id and self.bot:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                try:
                    guild = await self.bot.fetch_guild(guild_id)
                except Exception:
                    guild = None

            if guild:
                # Bot is present in source server! Check user authorization
                member = guild.get_member(user_id)
                if not member:
                    try:
                        member = await guild.fetch_member(user_id)
                    except Exception:
                        member = None

                is_admin_or_owner = False
                is_member = member is not None

                if member:
                    is_owner = member.id == guild.owner_id
                    has_admin = member.guild_permissions.administrator
                    has_manage = member.guild_permissions.manage_guild
                    is_admin_or_owner = is_owner or has_admin or has_manage

                if is_admin_or_owner:
                    # Full structure scan with all roles, channels, and private overwrites
                    structure = self.scan_server_structure(guild, public_only=False)
                    structure["access_method"] = "BOT_INTERNAL_FULL"
                    structure["access_method_display"] = "Bot Internal Scan (Administrator Authorized)"
                    report = {
                        "source_input": str(guild.id),
                        "access_mode": "BOT_INTERNAL_FULL",
                        "access_mode_display": "Bot Internal Scan (Administrator Authorized)",
                        "server_name": guild.name,
                        "server_id": guild.id,
                        "roles_count": len(structure["roles"]),
                        "categories_count": len(structure["categories"]),
                        "channels_count": len(structure["text_channels"]) + len(structure["voice_channels"]),
                        "unavailable_items": [],
                    }
                    return True, "BOT_INTERNAL_FULL", report, structure
                else:
                    # Public structure scan (Public channels & categories visible to @everyone)
                    # "Do not require Administrator permission when a less privileged authorized method is sufficient."
                    structure = self.scan_server_structure(guild, public_only=True)
                    structure["access_method"] = "BOT_INTERNAL_PUBLIC"
                    structure["access_method_display"] = "Bot Internal Scan (Public Member Access)"
                    structure["unavailable_items"] = [
                        "Private / Administrative channels omitted (Administrator permission required for private channels)",
                        "Server audit logs and private member overwrites omitted",
                    ]
                    report = {
                        "source_input": str(guild.id),
                        "access_mode": "BOT_INTERNAL_PUBLIC",
                        "access_mode_display": "Bot Internal Scan (Public Member Access)",
                        "server_name": guild.name,
                        "server_id": guild.id,
                        "roles_count": len(structure["roles"]),
                        "categories_count": len(structure["categories"]),
                        "channels_count": len(structure["text_channels"]) + len(structure["voice_channels"]),
                        "unavailable_items": structure["unavailable_items"],
                    }
                    return True, "BOT_INTERNAL_PUBLIC", report, structure

        # ------------------------------------------------------------------
        # 3. Check Method B1: Discord Public Server Widget API
        # ------------------------------------------------------------------
        if guild_id:
            logger.info(f"Bot not in guild {guild_id}. Probing Discord Public Widget API...")
            widget_success, widget_data = await self._fetch_guild_widget(guild_id)
            if widget_success and widget_data:
                structure = self.parse_widget_data(widget_data, guild_id)
                report = {
                    "source_input": str(guild_id),
                    "access_mode": "PUBLIC_WIDGET_API",
                    "access_mode_display": "Discord Public Server Widget API",
                    "server_name": structure["source_guild_name"],
                    "server_id": guild_id,
                    "roles_count": 0,
                    "categories_count": len(structure["categories"]),
                    "channels_count": len(structure["text_channels"]) + len(structure["voice_channels"]),
                    "unavailable_items": structure.get("unavailable_items", []),
                }
                return True, "PUBLIC_WIDGET_API", report, structure

        # ------------------------------------------------------------------
        # 4. Check Method B2: Discord Invite Resolution
        # ------------------------------------------------------------------
        inv_code = extract_invite_code(source_clean)
        if inv_code:
            logger.info(f"Resolving Discord invite '{inv_code}'...")
            inv_success, inv_data = await self._fetch_invite(inv_code)
            if inv_success and inv_data:
                target_g_id = int(inv_data.get("guild", {}).get("id", 0))
                g_name = inv_data.get("guild", {}).get("name", "Unknown Server")
                if target_g_id:
                    # Check widget on discovered guild id
                    w_ok, w_data = await self._fetch_guild_widget(target_g_id)
                    if w_ok and w_data:
                        structure = self.parse_widget_data(w_data, target_g_id)
                        report = {
                            "source_input": source_clean,
                            "access_mode": "PUBLIC_WIDGET_API",
                            "access_mode_display": f"Discord Public Widget API (via invite '{inv_code}')",
                            "server_name": structure["source_guild_name"],
                            "server_id": target_g_id,
                            "roles_count": 0,
                            "categories_count": len(structure["categories"]),
                            "channels_count": len(structure["text_channels"]) + len(structure["voice_channels"]),
                            "unavailable_items": structure.get("unavailable_items", []),
                        }
                        return True, "PUBLIC_WIDGET_API", report, structure

        # ------------------------------------------------------------------
        # 5. Method B3: Discord Public Guild Preview Check
        # ------------------------------------------------------------------
        preview_guild_name = None
        if guild_id:
            p_ok, p_data = await self._fetch_guild_preview(guild_id)
            if p_ok and p_data:
                preview_guild_name = p_data.get("name")

        # ------------------------------------------------------------------
        # 6. Fallback: Source is Inaccessible / Private Server
        # ------------------------------------------------------------------
        report = {
            "source_input": source_clean,
            "server_id": guild_id,
            "server_name": preview_guild_name or "Private / Unreachable Server",
            "bot_present": False,
            "widget_enabled": False,
            "status_code": "ACCESS_RESTRICTED",
            "status_summary": (
                f"Source server (`{source_clean}`) does not have NOVEXA installed and has "
                f"Server Widget disabled. Discord's official Security API strictly restricts reading "
                f"channel structures of private servers without authorization."
            ),
            "available_methods": [
                "1. 🔗 Discord Server Template: Create a template in Source Server Settings -> Server Template and paste the link (`discord.new/...`).",
                "2. 📁 Structure Import: Upload an authorized `.json` server structure file using `/clone import`.",
                "3. 🌐 Enable Server Widget: Ask the source server admin to enable 'Server Widget' in Server Settings -> Widget.",
                "4. 🤖 Invite NOVEXA: Add NOVEXA to the source server so it can scan accessible channels directly.",
            ],
        }
        return False, "ACCESS_RESTRICTED", report, None

    # ==================== 2. HTTP & DISCORD API HELPERS ====================

    async def _fetch_discord_template(self, code: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Fetch serialized guild structure from official Discord Template API."""
        url = f"https://discord.com/api/v10/guilds/templates/{code}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return True, data, None
                    elif resp.status == 404:
                        return False, None, "Unknown or expired server template."
                    else:
                        return False, None, f"Discord API returned status {resp.status}."
        except Exception as e:
            logger.error(f"Error fetching Discord template {code}: {e}")
            return False, None, str(e)

    async def _fetch_guild_widget(self, guild_id: int) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Fetch public channels and server info from official Discord Widget API."""
        url = f"https://discord.com/api/v10/guilds/{guild_id}/widget.json"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=6)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return True, data
                    return False, None
        except Exception as e:
            logger.warning(f"Error fetching widget for guild {guild_id}: {e}")
            return False, None

    async def _fetch_guild_preview(self, guild_id: int) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Fetch public guild discovery info using Bot token authorization."""
        url = f"https://discord.com/api/v10/guilds/{guild_id}/preview"
        headers = {"Authorization": f"Bot {DISCORD_TOKEN}"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=6)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return True, data
                    return False, None
        except Exception as e:
            logger.warning(f"Error fetching preview for guild {guild_id}: {e}")
            return False, None

    async def _fetch_invite(self, code: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Resolve a Discord invite code to obtain public guild info."""
        url = f"https://discord.com/api/v10/invites/{code}?with_counts=true"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=6)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return True, data
                    return False, None
        except Exception as e:
            logger.warning(f"Error resolving invite {code}: {e}")
            return False, None

    # ==================== 3. STRUCTURE NORMALIZERS ====================

    def parse_template_data(self, template_data: Dict[str, Any], creator_id: int) -> Dict[str, Any]:
        """Convert Discord official Guild Template JSON into normalized NOVEXA architecture structure."""
        ser_guild = template_data.get("serialized_source_guild", {})
        name = ser_guild.get("name", template_data.get("name", "Cloned Template"))
        source_guild_id = int(template_data.get("source_guild_id", 0))

        structure: Dict[str, Any] = {
            "source_guild_id": source_guild_id,
            "source_guild_name": name,
            "access_method": "DISCORD_TEMPLATE",
            "access_method_display": "Official Discord Server Template (discord.new)",
            "description": ser_guild.get("description") or template_data.get("description", ""),
            "icon_url": None,
            "banner_url": None,
            "afk_timeout": ser_guild.get("afk_timeout", 300),
            "default_notifications": ser_guild.get("default_message_notifications", 0),
            "scanned_at": int(time.time()),
            "roles": [],
            "categories": [],
            "text_channels": [],
            "voice_channels": [],
            "everyone_permissions": 0,
            "unavailable_items": [
                "Member message history and attachments (Discord API Security Boundary)",
                "Server boost level and bot-specific integration roles",
                "Server ownership",
            ],
        }

        # 1. Parse Roles
        for r in ser_guild.get("roles", []):
            if r.get("name") == "@everyone":
                structure["everyone_permissions"] = int(r.get("permissions", 0))
                continue
            structure["roles"].append({
                "id": int(r.get("id", 0)),
                "name": r.get("name", "Role"),
                "color": int(r.get("color", 0)),
                "hoist": bool(r.get("hoist", False)),
                "mentionable": bool(r.get("mentionable", False)),
                "permissions": int(r.get("permissions", 0)),
                "position": 0,
            })

        # 2. Parse Categories (type == 4)
        cat_map: Dict[int, str] = {}
        for ch in sorted(ser_guild.get("channels", []), key=lambda c: c.get("position", 0)):
            if ch.get("type") == 4:
                cat_map[ch["id"]] = ch["name"]
                overwrites = [
                    {
                        "target_type": "role" if ow.get("type") == 0 else "member",
                        "target_id": int(ow.get("id", 0)),
                        "is_default": int(ow.get("id", 0)) == 0,
                        "allow": int(ow.get("allow", 0)),
                        "deny": int(ow.get("deny", 0)),
                    }
                    for ow in ch.get("permission_overwrites", [])
                ]
                structure["categories"].append({
                    "id": ch["id"],
                    "name": ch["name"],
                    "position": ch.get("position", 0),
                    "overwrites": overwrites,
                })

        # 3. Parse Text and Voice Channels
        for ch in sorted(ser_guild.get("channels", []), key=lambda c: c.get("position", 0)):
            ch_type = ch.get("type", 0)
            parent_id = ch.get("parent_id")
            overwrites = [
                {
                    "target_type": "role" if ow.get("type") == 0 else "member",
                    "target_id": int(ow.get("id", 0)),
                    "is_default": int(ow.get("id", 0)) == 0,
                    "allow": int(ow.get("allow", 0)),
                    "deny": int(ow.get("deny", 0)),
                }
                for ow in ch.get("permission_overwrites", [])
            ]

            if ch_type in (0, 5):  # Text or Announcement
                structure["text_channels"].append({
                    "id": ch["id"],
                    "name": ch["name"],
                    "category_id": parent_id,
                    "category_name": cat_map.get(parent_id),
                    "position": ch.get("position", 0),
                    "topic": ch.get("topic") or "",
                    "slowmode": ch.get("rate_limit_per_user", 0),
                    "nsfw": ch.get("nsfw", False),
                    "type": "news" if ch_type == 5 else "text",
                    "overwrites": overwrites,
                })
            elif ch_type in (2, 13):  # Voice or Stage
                structure["voice_channels"].append({
                    "id": ch["id"],
                    "name": ch["name"],
                    "category_id": parent_id,
                    "category_name": cat_map.get(parent_id),
                    "position": ch.get("position", 0),
                    "user_limit": ch.get("user_limit", 0),
                    "bitrate": ch.get("bitrate", 64000),
                    "overwrites": overwrites,
                })

        return structure

    def parse_widget_data(self, widget_data: Dict[str, Any], guild_id: int) -> Dict[str, Any]:
        """Convert Discord Server Widget JSON into normalized NOVEXA architecture structure."""
        guild_name = widget_data.get("name", f"Public Server {guild_id}")
        raw_channels = widget_data.get("channels", [])
        members = widget_data.get("members", [])

        # Voice channels in widget often have active members with channel_id
        active_voice_ids = {m.get("channel_id") for m in members if m.get("channel_id")}

        structure: Dict[str, Any] = {
            "source_guild_id": guild_id,
            "source_guild_name": guild_name,
            "access_method": "PUBLIC_WIDGET_API",
            "access_method_display": "Discord Public Server Widget API",
            "description": f"Public structure imported via Discord Server Widget for {guild_name}",
            "icon_url": None,
            "banner_url": None,
            "afk_timeout": 300,
            "default_notifications": 0,
            "scanned_at": int(time.time()),
            "roles": [],
            "categories": [
                {
                    "id": 999999001,
                    "name": "📁 PUBLIC CHANNELS",
                    "position": 0,
                    "overwrites": [],
                }
            ],
            "text_channels": [],
            "voice_channels": [],
            "everyone_permissions": 0,
            "unavailable_items": [
                "Role names, colors, and hierarchy (Discord Widget API restriction - not exposed publicly)",
                "Channel topics, slowmode, and NSFW settings (Omitted by Discord widget endpoint)",
                "Private and restricted channels (Hidden by source server administrator)",
            ],
        }

        for idx, ch in enumerate(raw_channels):
            ch_id = int(ch.get("id", idx + 1))
            ch_name = ch.get("name", f"channel-{idx + 1}")
            pos = ch.get("position", idx)

            is_voice = (
                str(ch_id) in active_voice_ids
                or ch_id in active_voice_ids
                or "voice" in ch_name.lower()
                or "vc" in ch_name.lower()
                or "lounge" in ch_name.lower()
            )

            if is_voice:
                structure["voice_channels"].append({
                    "id": ch_id,
                    "name": ch_name,
                    "category_id": 999999001,
                    "category_name": "📁 PUBLIC CHANNELS",
                    "position": pos,
                    "user_limit": 0,
                    "bitrate": 64000,
                    "overwrites": [],
                })
            else:
                structure["text_channels"].append({
                    "id": ch_id,
                    "name": ch_name,
                    "category_id": 999999001,
                    "category_name": "📁 PUBLIC CHANNELS",
                    "position": pos,
                    "topic": "",
                    "slowmode": 0,
                    "nsfw": False,
                    "type": "text",
                    "overwrites": [],
                })

        return structure

    def parse_imported_json(
        self, json_content: str, creator_id: int
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Validate and normalize user-provided JSON structure export."""
        try:
            data = json.loads(json_content)
        except Exception as e:
            return False, f"Invalid JSON syntax: {e}", None

        if not isinstance(data, dict):
            return False, "Imported file must contain a root JSON object.", None

        # Check if user uploaded a raw Discord template export
        if "serialized_source_guild" in data:
            structure = self.parse_template_data(data, creator_id)
            return True, "Valid Discord template JSON imported.", structure

        # Check for minimum required keys
        if "text_channels" not in data and "voice_channels" not in data and "categories" not in data:
            return (
                False,
                "Invalid structure schema: JSON must contain at least 'text_channels', 'voice_channels', or 'categories'.",
                None,
            )

        name = data.get("source_guild_name") or data.get("name") or "Imported Structure"
        s_id = int(data.get("source_guild_id", 0))

        structure: Dict[str, Any] = {
            "source_guild_id": s_id,
            "source_guild_name": name,
            "access_method": "USER_EXPORT",
            "access_method_display": "Authorized Server Structure JSON Export",
            "description": data.get("description", ""),
            "icon_url": data.get("icon_url"),
            "banner_url": data.get("banner_url"),
            "afk_timeout": data.get("afk_timeout", 300),
            "default_notifications": data.get("default_notifications", 0),
            "scanned_at": int(time.time()),
            "roles": data.get("roles", []),
            "categories": data.get("categories", []),
            "text_channels": data.get("text_channels", []),
            "voice_channels": data.get("voice_channels", []),
            "everyone_permissions": data.get("everyone_permissions", 0),
            "unavailable_items": data.get(
                "unavailable_items", ["Private messages and sensitive member data omitted"]
            ),
        }
        return True, "Structure JSON validated and normalized successfully.", structure

    def export_structure_json(self, structure: Dict[str, Any]) -> str:
        """Export standardized structure into formatted JSON."""
        return json.dumps(structure, indent=2, ensure_ascii=False)

    # ==================== 4. BOT INTERNAL SCANNER ====================

    def scan_server_structure(self, guild: discord.Guild, public_only: bool = False) -> Dict[str, Any]:
        """Deep scan the source server to extract roles, categories, channels, and permissions."""
        structure: Dict[str, Any] = {
            "source_guild_id": guild.id,
            "source_guild_name": guild.name,
            "description": guild.description or "",
            "icon_url": guild.icon.url if guild.icon else None,
            "banner_url": guild.banner.url if guild.banner else None,
            "afk_timeout": guild.afk_timeout,
            "default_notifications": guild.default_notifications.value,
            "scanned_at": int(time.time()),
            "roles": [],
            "categories": [],
            "text_channels": [],
            "voice_channels": [],
            "everyone_permissions": guild.default_role.permissions.value,
            "unavailable_items": [],
        }

        # 1. Extract Roles (filtered & sorted by position ascending)
        for role in sorted(guild.roles, key=lambda r: r.position):
            if role.is_default():
                continue
            if role.managed:
                continue

            structure["roles"].append({
                "id": role.id,
                "name": role.name,
                "color": role.color.value,
                "hoist": role.hoist,
                "mentionable": role.mentionable,
                "permissions": role.permissions.value,
                "position": role.position,
            })

        def _serialize_overwrites(channel: discord.abc.GuildChannel) -> List[Dict[str, Any]]:
            serialized = []
            for target, overwrite in channel.overwrites.items():
                allow_pair, deny_pair = overwrite.pair()
                target_type = "role" if isinstance(target, discord.Role) else "member"
                serialized.append({
                    "target_type": target_type,
                    "target_id": target.id,
                    "target_name": target.name,
                    "is_default": getattr(target, "is_default", lambda: False)(),
                    "allow": allow_pair.value,
                    "deny": deny_pair.value,
                })
            return serialized

        def _is_channel_public(ch: discord.abc.GuildChannel) -> bool:
            # Check if default role has view permission
            perms = ch.permissions_for(guild.default_role)
            return perms.view_channel

        # 2. Extract Categories
        for cat in sorted(guild.categories, key=lambda c: c.position):
            if public_only and not _is_channel_public(cat):
                continue
            structure["categories"].append({
                "id": cat.id,
                "name": cat.name,
                "position": cat.position,
                "overwrites": _serialize_overwrites(cat),
            })

        # 3. Extract Text Channels
        for ch in sorted(guild.text_channels, key=lambda c: c.position):
            if public_only and not _is_channel_public(ch):
                continue
            structure["text_channels"].append({
                "id": ch.id,
                "name": ch.name,
                "category_id": ch.category_id,
                "position": ch.position,
                "topic": ch.topic or "",
                "slowmode": ch.slowmode_delay,
                "nsfw": ch.nsfw,
                "type": "news" if ch.is_news() else "text",
                "overwrites": _serialize_overwrites(ch),
            })

        # 4. Extract Voice Channels
        for vch in sorted(guild.voice_channels, key=lambda c: c.position):
            if public_only and not _is_channel_public(vch):
                continue
            structure["voice_channels"].append({
                "id": vch.id,
                "name": vch.name,
                "category_id": vch.category_id,
                "position": vch.position,
                "user_limit": vch.user_limit,
                "bitrate": vch.bitrate,
                "overwrites": _serialize_overwrites(vch),
            })

        return structure

    # ==================== 5. DESTINATION VALIDATION ====================

    async def validate_source_server(
        self, source_guild_id: int, user_id: int
    ) -> Tuple[bool, str, Optional[discord.Guild]]:
        """Validate source server accessibility and user authorization."""
        guild = self.bot.get_guild(source_guild_id)
        if not guild:
            try:
                guild = await self.bot.fetch_guild(source_guild_id)
            except Exception:
                guild = None

        if not guild:
            return (
                False,
                f"NOVEXA is not installed in the source server (ID: `{source_guild_id}`). "
                f"Use a Discord Server Template link (`discord.new/...`) or Widget import instead.",
                None,
            )

        member = guild.get_member(user_id)
        if not member:
            try:
                member = await guild.fetch_member(user_id)
            except Exception:
                member = None

        if not member:
            # User is not a member, but bot is; can still perform public structure scan
            return True, "Public structure available.", guild

        return True, "Source server validated successfully.", guild

    async def validate_destination_server(
        self, dest_guild_id: int, user_id: int, source_guild_id: Optional[int] = None
    ) -> Tuple[bool, str, Optional[discord.Guild]]:
        """Validate destination server permissions, bot hierarchy, and user authorization."""
        if source_guild_id and dest_guild_id == source_guild_id:
            return False, "Source server and Destination server cannot be the same.", None

        guild = self.bot.get_guild(dest_guild_id)
        if not guild:
            try:
                guild = await self.bot.fetch_guild(dest_guild_id)
            except Exception:
                guild = None

        if not guild:
            return (
                False,
                f"NOVEXA is not installed in the destination server (ID: `{dest_guild_id}`). "
                f"Please invite NOVEXA to the destination server first.",
                None,
            )

        member = guild.get_member(user_id)
        if not member:
            try:
                member = await guild.fetch_member(user_id)
            except Exception:
                member = None

        if not member:
            return (
                False,
                f"You are not a member of the destination server (**{guild.name}**).",
                None,
            )

        is_owner = member.id == guild.owner_id
        has_admin = member.guild_permissions.administrator
        has_manage = member.guild_permissions.manage_guild

        if not (is_owner or has_admin or has_manage):
            return (
                False,
                f"Access Denied: You do not have `Administrator` or `Manage Server` permissions "
                f"in destination server **{guild.name}**.",
                None,
            )

        bot_member = guild.me
        if not bot_member:
            return False, "Bot member could not be resolved in destination server.", None

        missing_perms = []
        if not bot_member.guild_permissions.manage_roles:
            missing_perms.append("Manage Roles")
        if not bot_member.guild_permissions.manage_channels:
            missing_perms.append("Manage Channels")
        if not bot_member.guild_permissions.view_channel:
            missing_perms.append("View Channels")

        if missing_perms:
            return (
                False,
                f"NOVEXA lacks required permissions in **{guild.name}**: "
                f"`{', '.join(missing_perms)}`. Please grant these permissions to the bot.",
                None,
            )

        return True, "Destination server validated successfully.", guild

    # ==================== 6. COMPATIBILITY & PREVIEW ====================

    def generate_clone_preview(
        self, structure: Dict[str, Any], dest_guild: discord.Guild
    ) -> Dict[str, Any]:
        """Compute compatibility, capacity checks, bitrate clamping, and preview stats."""
        warnings: List[str] = []
        unsupported: List[str] = list(structure.get("unavailable_items", []))

        total_source_roles = len(structure.get("roles", []))
        total_source_cats = len(structure.get("categories", []))
        total_source_text = len(structure.get("text_channels", []))
        total_source_voice = len(structure.get("voice_channels", []))
        total_source_channels = total_source_cats + total_source_text + total_source_voice

        # Check Discord Role Limits (Max 250 roles per guild)
        current_roles_count = len(dest_guild.roles)
        projected_roles = current_roles_count + total_source_roles
        if projected_roles > 250:
            warnings.append(
                f"Role Capacity Limit: Destination currently has {current_roles_count} roles. "
                f"Adding {total_source_roles} roles exceeds Discord's 250-role ceiling."
            )

        # Check Discord Channel Limits (Max 500 channels per guild)
        current_channels_count = len(dest_guild.channels)
        projected_channels = current_channels_count + total_source_channels
        if projected_channels > 500:
            warnings.append(
                f"Channel Capacity Limit: Destination currently has {current_channels_count} channels. "
                f"Adding {total_source_channels} channels exceeds Discord's 500-channel limit."
            )

        # Bitrate clamping check
        max_bitrate = dest_guild.bitrate_limit
        clamped_voice = sum(
            1 for v in structure.get("voice_channels", []) if v.get("bitrate", 64000) > max_bitrate
        )
        if clamped_voice > 0:
            warnings.append(
                f"Bitrate Clamped: {clamped_voice} voice channels exceed destination tier limit "
                f"({int(max_bitrate / 1000)} kbps). They will be automatically clamped."
            )

        # Hierarchy Check
        if not dest_guild.me.guild_permissions.administrator:
            warnings.append(
                "Bot lacks Administrator permission in destination. "
                "Ensure NOVEXA's role is positioned at the top of the role list."
            )

        # Default security reminders
        if not any("Message history" in u for u in unsupported):
            unsupported.append("Message history & attachments cannot be transferred (Discord Security Boundary).")
        if not any("Server ownership" in u for u in unsupported):
            unsupported.append("Server ownership cannot be transferred.")

        return {
            "source_name": structure.get("source_guild_name", "Unknown Source"),
            "source_id": structure.get("source_guild_id", 0),
            "access_method_display": structure.get("access_method_display", "Direct Bot Scan"),
            "dest_name": dest_guild.name,
            "dest_id": dest_guild.id,
            "roles_count": total_source_roles,
            "categories_count": total_source_cats,
            "text_channels_count": total_source_text,
            "voice_channels_count": total_source_voice,
            "total_channels": total_source_channels,
            "warnings": warnings,
            "unsupported": unsupported,
            "dest_bitrate_limit": max_bitrate,
        }

    # ==================== 7. TEMPLATE PERSISTENCE ====================

    async def save_template(
        self, structure: Dict[str, Any], creator_id: int, custom_name: Optional[str] = None
    ) -> str:
        """Persist the scanned server structure as a reusable custom template."""
        s_id = structure.get("source_guild_id", 0)
        template_id = f"clone_{s_id}_{int(time.time())}"
        name = custom_name or f"{structure.get('source_guild_name', 'Cloned')} Clone Template"

        await db.execute(
            """
            INSERT OR REPLACE INTO cloned_templates 
            (template_id, source_guild_id, source_guild_name, template_name, creator_id, structure_json)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (
                template_id,
                s_id,
                structure.get("source_guild_name", "Unknown Server"),
                name,
                creator_id,
                json.dumps(structure),
            ),
        )
        logger.info(f"Saved custom template '{name}' (ID: {template_id})")
        return template_id

    async def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a saved clone template from SQLite."""
        row = await db.fetchone(
            "SELECT structure_json, template_name FROM cloned_templates WHERE template_id = ?;",
            (template_id,),
        )
        if row and row["structure_json"]:
            data = json.loads(row["structure_json"])
            data["template_name"] = row["template_name"]
            return data
        return None

    async def list_templates(self, creator_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """List all saved cloned templates."""
        if creator_id:
            rows = await db.fetchall(
                "SELECT template_id, source_guild_name, template_name, created_at FROM cloned_templates WHERE creator_id = ? ORDER BY created_at DESC;",
                (creator_id,),
            )
        else:
            rows = await db.fetchall(
                "SELECT template_id, source_guild_name, template_name, created_at FROM cloned_templates ORDER BY created_at DESC LIMIT 25;"
            )
        return [dict(r) for r in rows]

    async def delete_template(self, template_id: str) -> bool:
        """Delete a saved clone template."""
        res = await db.execute("DELETE FROM cloned_templates WHERE template_id = ?;", (template_id,))
        return bool(res)

    # ==================== 8. CLONE EXECUTION ENGINE ====================

    async def execute_clone(
        self,
        structure: Dict[str, Any],
        dest_guild: discord.Guild,
        user_id: int,
        mode: str = "add",
        progress_cb: Optional[Callable[[str, float], Coroutine]] = None,
    ) -> Dict[str, Any]:
        """Reconstruct accessible source structure in the destination server."""
        start_time = time.perf_counter()
        created_role_ids: List[int] = []
        created_cat_ids: List[int] = []
        created_ch_ids: List[int] = []
        applied_overwrites = 0
        warnings_or_skips: List[str] = []

        async def _update_progress(msg: str, pct: float):
            if progress_cb:
                try:
                    await progress_cb(msg, pct)
                except Exception:
                    pass

        # ----------------------------------------------------
        # Mode: REPLACE -> Clean destination safely
        # ----------------------------------------------------
        if mode == "replace":
            await _update_progress("🧹 Cleaning existing channels in destination server...", 0.05)
            for ch in list(dest_guild.channels):
                try:
                    await ch.delete(reason="NOVEXA Cloner: Replace Mode Purge")
                    await asyncio.sleep(0.35)
                except Exception as e:
                    warnings_or_skips.append(f"Could not delete channel {ch.name}: {e}")

            await _update_progress("🧹 Cleaning existing custom roles...", 0.10)
            bot_top = dest_guild.me.top_role
            for r in list(dest_guild.roles):
                if not r.is_default() and not r.managed and r < bot_top:
                    try:
                        await r.delete(reason="NOVEXA Cloner: Replace Mode Purge")
                        await asyncio.sleep(0.35)
                    except Exception as e:
                        warnings_or_skips.append(f"Could not delete role {r.name}: {e}")

        # ----------------------------------------------------
        # Step 1: Create Roles & Map IDs
        # ----------------------------------------------------
        await _update_progress("🛡️ [1/6] Creating roles in destination...", 0.15)
        role_id_map: Dict[int, discord.Role] = {}
        s_id = structure.get("source_guild_id", 0)
        role_id_map[s_id] = dest_guild.default_role
        role_id_map[0] = dest_guild.default_role

        roles_list = structure.get("roles", [])
        total_roles = len(roles_list)

        for idx, r_data in enumerate(roles_list):
            role_name = r_data.get("name", f"Role-{idx + 1}")
            color = discord.Colour(r_data.get("color", 0))
            hoist = r_data.get("hoist", False)
            mentionable = r_data.get("mentionable", False)
            perms = discord.Permissions(r_data.get("permissions", 0))

            # Restrict permissions if destination bot doesn't have them
            perms_to_apply = discord.Permissions(perms.value & dest_guild.me.guild_permissions.value)

            try:
                existing = discord.utils.get(dest_guild.roles, name=role_name)
                if mode == "add" and existing and existing < dest_guild.me.top_role and not existing.managed:
                    role_id_map[r_data.get("id", idx)] = existing
                    created_role_ids.append(existing.id)
                else:
                    new_role = await dest_guild.create_role(
                        name=role_name,
                        colour=color,
                        hoist=hoist,
                        mentionable=mentionable,
                        permissions=perms_to_apply,
                        reason="NOVEXA Server Cloner: Role Sync",
                    )
                    role_id_map[r_data.get("id", idx)] = new_role
                    created_role_ids.append(new_role.id)
                    await asyncio.sleep(0.4)
            except discord.Forbidden:
                warnings_or_skips.append(f"Permission Denied creating role: {role_name}")
            except Exception as e:
                warnings_or_skips.append(f"Failed to create role {role_name}: {e}")

            if total_roles > 0:
                pct = 0.15 + (0.15 * (idx + 1) / total_roles)
                await _update_progress(f"🛡️ [1/6] Created role {idx + 1}/{total_roles}: {role_name}", pct)

        # ----------------------------------------------------
        # Step 2: Reconstruct Role Hierarchy
        # ----------------------------------------------------
        if total_roles > 0:
            await _update_progress("⚖️ [2/6] Aligning role hierarchy positions...", 0.35)
            try:
                bot_top = dest_guild.me.top_role
                positions_to_edit: Dict[discord.Role, int] = {}
                for idx, r_data in enumerate(roles_list):
                    new_role = role_id_map.get(r_data.get("id", idx))
                    if new_role and new_role < bot_top and not new_role.is_default():
                        pos = r_data.get("position", idx + 1)
                        positions_to_edit[new_role] = min(pos, bot_top.position - 1)

                if positions_to_edit and dest_guild.me.guild_permissions.manage_roles:
                    await dest_guild.edit_role_positions(positions=positions_to_edit)
                    await asyncio.sleep(0.5)
            except Exception as e:
                warnings_or_skips.append(f"Hierarchy alignment note: {e}")

        # ----------------------------------------------------
        # Step 3: Create Categories
        # ----------------------------------------------------
        await _update_progress("📁 [3/6] Creating categories...", 0.40)
        category_id_map: Dict[int, discord.CategoryChannel] = {}
        cats_list = structure.get("categories", [])
        total_cats = len(cats_list)

        for idx, cat_data in enumerate(cats_list):
            cat_name = cat_data.get("name", f"Category {idx + 1}")
            try:
                new_cat = await dest_guild.create_category(
                    name=cat_name,
                    position=cat_data.get("position", idx),
                    reason="NOVEXA Server Cloner: Category Sync",
                )
                category_id_map[cat_data.get("id", idx)] = new_cat
                created_cat_ids.append(new_cat.id)
                await asyncio.sleep(0.4)
            except Exception as e:
                warnings_or_skips.append(f"Failed to create category {cat_name}: {e}")

            if total_cats > 0:
                pct = 0.40 + (0.15 * (idx + 1) / total_cats)
                await _update_progress(f"📁 [3/6] Created category {idx + 1}/{total_cats}: {cat_name}", pct)

        # ----------------------------------------------------
        # Step 4: Create Text Channels
        # ----------------------------------------------------
        await _update_progress("💬 [4/6] Creating text channels...", 0.55)
        channel_id_map: Dict[int, discord.abc.GuildChannel] = {}
        text_list = structure.get("text_channels", [])
        total_text = len(text_list)

        for idx, ch_data in enumerate(text_list):
            ch_name = ch_data.get("name", f"text-{idx + 1}")
            parent_cat = category_id_map.get(ch_data.get("category_id"))
            topic = ch_data.get("topic") or None
            slowmode = ch_data.get("slowmode", 0)
            nsfw = ch_data.get("nsfw", False)

            try:
                new_ch = await dest_guild.create_text_channel(
                    name=ch_name,
                    category=parent_cat,
                    topic=topic,
                    slowmode_delay=slowmode,
                    nsfw=nsfw,
                    position=ch_data.get("position", idx),
                    reason="NOVEXA Server Cloner: Text Channel Sync",
                )
                channel_id_map[ch_data.get("id", idx)] = new_ch
                created_ch_ids.append(new_ch.id)
                await asyncio.sleep(0.4)
            except Exception as e:
                warnings_or_skips.append(f"Failed to create text channel {ch_name}: {e}")

            if total_text > 0:
                pct = 0.55 + (0.15 * (idx + 1) / total_text)
                await _update_progress(f"💬 [4/6] Created text channel {idx + 1}/{total_text}: #{ch_name}", pct)

        # ----------------------------------------------------
        # Step 5: Create Voice Channels
        # ----------------------------------------------------
        await _update_progress("🔊 [5/6] Creating voice channels...", 0.70)
        voice_list = structure.get("voice_channels", [])
        total_voice = len(voice_list)
        max_bitrate = dest_guild.bitrate_limit

        for idx, v_data in enumerate(voice_list):
            v_name = v_data.get("name", f"Voice-{idx + 1}")
            parent_cat = category_id_map.get(v_data.get("category_id"))
            user_limit = v_data.get("user_limit", 0)
            bitrate = min(v_data.get("bitrate", 64000), max_bitrate)

            try:
                new_vch = await dest_guild.create_voice_channel(
                    name=v_name,
                    category=parent_cat,
                    user_limit=user_limit,
                    bitrate=bitrate,
                    position=v_data.get("position", idx),
                    reason="NOVEXA Server Cloner: Voice Channel Sync",
                )
                channel_id_map[v_data.get("id", idx)] = new_vch
                created_ch_ids.append(new_vch.id)
                await asyncio.sleep(0.4)
            except Exception as e:
                warnings_or_skips.append(f"Failed to create voice channel {v_name}: {e}")

            if total_voice > 0:
                pct = 0.70 + (0.15 * (idx + 1) / total_voice)
                await _update_progress(f"🔊 [5/6] Created voice channel {idx + 1}/{total_voice}: 🔊 {v_name}", pct)

        # ----------------------------------------------------
        # Step 6: Map & Apply Permission Overwrites
        # ----------------------------------------------------
        await _update_progress("🔒 [6/6] Mapping and applying permission overwrites...", 0.85)

        all_channels_data = (
            [(cat_data, category_id_map.get(cat_data.get("id"))) for cat_data in cats_list]
            + [(ch_data, channel_id_map.get(ch_data.get("id"))) for ch_data in text_list]
            + [(v_data, channel_id_map.get(v_data.get("id"))) for v_data in voice_list]
        )

        for source_data, dest_channel in all_channels_data:
            if not dest_channel:
                continue

            overwrites_list = source_data.get("overwrites", [])
            if not overwrites_list:
                continue

            new_overwrites: Dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {}
            for ow in overwrites_list:
                target = None
                t_type = ow.get("target_type")
                t_id = ow.get("target_id")

                if t_type == "role" or "allow" in ow:
                    if ow.get("is_default") or t_id in (0, s_id):
                        target = dest_guild.default_role
                    else:
                        target = role_id_map.get(t_id)
                elif t_type == "member":
                    target = dest_guild.get_member(t_id)

                if target:
                    allow_perms = discord.Permissions(int(ow.get("allow", 0)))
                    deny_perms = discord.Permissions(int(ow.get("deny", 0)))
                    overwrite_obj = discord.PermissionOverwrite.from_pair(allow_perms, deny_perms)
                    new_overwrites[target] = overwrite_obj

            if new_overwrites and dest_guild.me.guild_permissions.manage_roles:
                try:
                    for tgt, ow_obj in new_overwrites.items():
                        await dest_channel.set_permissions(
                            tgt, overwrite=ow_obj, reason="NOVEXA Server Cloner: Overwrite Sync"
                        )
                        applied_overwrites += 1
                        await asyncio.sleep(0.25)
                except Exception as e:
                    warnings_or_skips.append(f"Overwrites on #{dest_channel.name}: {e}")

        elapsed_sec = time.perf_counter() - start_time
        await _update_progress("✨ [Finalizing] Verifying created architecture and logs...", 0.98)

        # ----------------------------------------------------
        # Step 7: Final Verification Report & Database Audit Log
        # ----------------------------------------------------
        report = {
            "source_guild_name": structure.get("source_guild_name", "Unknown Source"),
            "source_guild_id": s_id,
            "access_method_display": structure.get("access_method_display", "Direct Bot Scan"),
            "dest_guild_name": dest_guild.name,
            "dest_guild_id": dest_guild.id,
            "mode": mode,
            "roles_created": len(created_role_ids),
            "categories_created": len(created_cat_ids),
            "channels_created": len(created_ch_ids),
            "overwrites_applied": applied_overwrites,
            "duration_seconds": round(elapsed_sec, 2),
            "warnings_count": len(warnings_or_skips),
            "warnings": warnings_or_skips[:15],
            "unavailable_items": structure.get("unavailable_items", []),
        }

        # Store in clone history
        try:
            await db.execute(
                """
                INSERT INTO server_clone_history 
                (source_guild_id, source_guild_name, dest_guild_id, dest_guild_name, user_id, mode, created_roles, created_categories, created_channels, report_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    s_id,
                    structure.get("source_guild_name", "Unknown Source"),
                    dest_guild.id,
                    dest_guild.name,
                    user_id,
                    mode,
                    json.dumps(created_role_ids),
                    json.dumps(created_cat_ids),
                    json.dumps(created_ch_ids),
                    json.dumps(report),
                ),
            )
        except Exception as e:
            logger.warning(f"Could not record clone history to DB: {e}")

        logger.info(
            f"Successfully cloned structure from '{structure.get('source_guild_name')}' "
            f"to '{dest_guild.name}' in {elapsed_sec:.2f}s ({len(created_ch_ids)} channels, {len(created_role_ids)} roles)."
        )

        return report
