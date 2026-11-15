"""NOVEXA - Dropper Channels Service & Server Style Matching Engine.

Automatically creates a complete DEVELOPER category with 16 organized text channels:
1.  💻・FREE-CODE
2.  🛡️・SAFE-CODES
3.  ⚠️・PATCHED-CODE
4.  📁・FREE-PROJECT
5.  🚀・INJECTION-METHOD
6.  🌸・Internal-CS-Files
7.  🌿・Dump-files
8.  📝・String-names
9.  🔧・DLL
10. 📚・LIB
11. 🤖・Bots
12. 💠・TOOLS
13. 🖌️・UI-DESIGN
14. 🔊・SOUND-EFFECT
15. 🖼️・WALLPAPER
16. 🎬・EDITORS-AREA

Features:
- Dynamically detects target server's Unicode font, category heading style, channel separator, and emoji wrappers.
- Safe execution: Reuses existing category, creates only missing channels, never duplicates or deletes.
- Rate limit mitigation with asynchronous backoff.
- Full permission inheritance and audit logging.
"""

import re
import asyncio
import logging
from collections import Counter
from typing import List, Dict, Any, Optional, Tuple
import discord
from database.database import db

logger = logging.getLogger("novexa.dropper")

# ==================== CANONICAL DROPPER CHANNELS ====================
DROPPER_CHANNELS_DATA = [
    ("💻", "FREE-CODE", "free-code"),
    ("🛡️", "SAFE-CODES", "safe-codes"),
    ("⚠️", "PATCHED-CODE", "patched-code"),
    ("📁", "FREE-PROJECT", "free-project"),
    ("🚀", "INJECTION-METHOD", "injection-method"),
    ("🌸", "Internal-CS-Files", "internal-cs-files"),
    ("🌿", "Dump-files", "dump-files"),
    ("📝", "String-names", "string-names"),
    ("🔧", "DLL", "dll"),
    ("📚", "LIB", "lib"),
    ("🤖", "Bots", "bots"),
    ("💠", "TOOLS", "tools"),
    ("🖌️", "UI-DESIGN", "ui-design"),
    ("🔊", "SOUND-EFFECT", "sound-effect"),
    ("🖼️", "WALLPAPER", "wallpaper"),
    ("🎬", "EDITORS-AREA", "editors-area"),
]

# ==================== UNICODE FONT TABLES ====================
NORMAL = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
MATH_BOLD = "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗"
MATH_SANS_BOLD = "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
MONOSPACE = "𝙰𝙱𝙲𝙳𝙴𝙵𝙶𝙷𝙸𝙹𝙺𝙻𝙼𝙽𝙾𝙿𝚀𝚁𝚂𝚃𝚄𝚅𝚆𝚇𝚈𝚉𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿"

SMALL_CAPS_MAP = {
    'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ',
    'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ',
    'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ', 'u': 'ᴜ',
    'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
    'A': 'ᴀ', 'B': 'ʙ', 'C': 'ᴄ', 'D': 'ᴅ', 'E': 'ᴇ', 'F': 'ғ', 'G': 'ɢ',
    'H': 'ʜ', 'I': 'ɪ', 'J': 'ᴊ', 'K': 'ᴋ', 'L': 'ʟ', 'M': 'ᴍ', 'N': 'ɴ',
    'O': 'ᴏ', 'P': 'ᴘ', 'Q': 'ǫ', 'R': 'ʀ', 'S': 's', 'T': 'ᴛ', 'U': 'ᴜ',
    'V': 'ᴠ', 'W': 'ᴡ', 'X': 'x', 'Y': 'ʏ', 'Z': 'ᴢ'
}
REV_SMALL_CAPS = {v: k for k, v in SMALL_CAPS_MAP.items() if k.islower()}

REV_FONTS = {}
for _src, _dst in ((MATH_BOLD, NORMAL), (MATH_SANS_BOLD, NORMAL), (MONOSPACE, NORMAL)):
    REV_FONTS.update(dict(zip(_src, _dst)))

KNOWN_SEPARATORS = ["・", "┃", "│", "〢", "×", "丨", " - ", "-", "_", "~", " "]


def _to_ascii(text: str) -> str:
    """Convert styled Unicode fonts (bold, monospace, small caps) back to plain ASCII."""
    out = []
    for ch in text:
        if ch in REV_SMALL_CAPS:
            out.append(REV_SMALL_CAPS[ch])
        elif ch in REV_FONTS:
            out.append(REV_FONTS[ch])
        else:
            out.append(ch)
    return "".join(out)


class ServerStyleProfile:
    """Encapsulates the detected styling conventions of a Discord server."""

    def __init__(
        self,
        category_prefix: str = "",
        category_suffix: str = "",
        category_font: str = "normal",
        channel_separator: str = "・",
        channel_bracket: Optional[Tuple[str, str]] = None,
        channel_prefix: str = "",
        channel_font: str = "normal",
        channel_casing: str = "original",
        style_description: str = "Default Clean Japanese Dot Style",
    ):
        self.category_prefix = category_prefix
        self.category_suffix = category_suffix
        self.category_font = category_font
        self.channel_separator = channel_separator
        self.channel_bracket = channel_bracket
        self.channel_prefix = channel_prefix
        self.channel_font = channel_font
        self.channel_casing = channel_casing
        self.style_description = style_description

    def apply_font(self, text: str, font_type: str) -> str:
        if font_type == "math_bold":
            return text.translate(str.maketrans(NORMAL, MATH_BOLD))
        elif font_type == "math_sans_bold":
            return text.translate(str.maketrans(NORMAL, MATH_SANS_BOLD))
        elif font_type == "monospace":
            return text.translate(str.maketrans(NORMAL, MONOSPACE))
        elif font_type == "small_caps":
            return "".join(SMALL_CAPS_MAP.get(c, c) for c in text)
        return text

    def format_category_name(self, raw_name: str = "DEVELOPER") -> str:
        name = raw_name
        if self.category_font != "normal":
            name = self.apply_font(name, self.category_font)
        if self.category_prefix or self.category_suffix:
            return f"{self.category_prefix}{name}{self.category_suffix}".strip()
        return name

    def format_channel_name(self, emoji: str, raw_name: str) -> str:
        # 1. Casing
        name = raw_name
        if self.channel_casing == "lower":
            name = name.lower()
        elif self.channel_casing == "upper":
            name = name.upper()
        elif self.channel_casing == "title":
            name = name.title()

        # 2. Font
        if self.channel_font != "normal":
            name = self.apply_font(name, self.channel_font)

        # 3. Emoji wrapping
        if self.channel_bracket:
            b_open, b_close = self.channel_bracket
            emoji_part = f"{b_open}{emoji}{b_close}"
        else:
            emoji_part = emoji

        # 4. Assembly
        sep = self.channel_separator
        prefix = self.channel_prefix
        if prefix:
            res = f"{prefix}{emoji_part}{sep}{name}"
        else:
            res = f"{emoji_part}{sep}{name}"

        return res[:100]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category_prefix": self.category_prefix,
            "category_suffix": self.category_suffix,
            "category_font": self.category_font,
            "channel_separator": self.channel_separator,
            "channel_bracket": f"{self.channel_bracket[0]}...{self.channel_bracket[1]}" if self.channel_bracket else None,
            "channel_prefix": self.channel_prefix,
            "channel_font": self.channel_font,
            "channel_casing": self.channel_casing,
            "style_description": self.style_description,
        }


class ServerStyleDetector:
    """Analyzes a Discord Guild's existing channels and categories to extract style conventions."""

    @classmethod
    def detect_guild(cls, guild: discord.Guild) -> ServerStyleProfile:
        category_names = [c.name for c in guild.categories]
        channel_names = [c.name for c in guild.text_channels]
        return cls.detect_from_names(category_names, channel_names)

    @classmethod
    def detect_from_names(cls, category_names: List[str], channel_names: List[str]) -> ServerStyleProfile:
        profile = ServerStyleProfile()
        detected_features = []

        # 1. Analyze Category Style
        if category_names:
            cat_fonts = Counter()
            cat_decorations = Counter()

            for cat in category_names:
                cat_clean = cat.strip()
                font = cls._detect_font(cat_clean)
                if font != "normal":
                    cat_fonts[font] += 1

                # Check enclosing brackets/decorations
                if cat_clean.startswith("══") and cat_clean.endswith("══"):
                    cat_decorations[("══ ", " ══")] += 1
                elif cat_clean.startswith("『") and cat_clean.endswith("』"):
                    cat_decorations[("『 ", " 』")] += 1
                elif cat_clean.startswith("「") and cat_clean.endswith("」"):
                    cat_decorations[("「 ", " 」")] += 1
                elif cat_clean.startswith("【") and cat_clean.endswith("】"):
                    cat_decorations[("【 ", " 】")] += 1
                elif cat_clean.startswith("──") and cat_clean.endswith("──"):
                    cat_decorations[("── ", " ──")] += 1
                elif cat_clean.startswith("━━") and cat_clean.endswith("━━"):
                    cat_decorations[("━━ ", " ━━")] += 1
                elif cat_clean.startswith("╭・") or cat_clean.startswith("╭-"):
                    cat_decorations[("╭・", "")] += 1
                elif cat_clean.startswith("✦") and cat_clean.endswith("✦"):
                    cat_decorations[("✦ ", " ✦")] += 1

            if cat_fonts and cat_fonts.most_common(1)[0][1] >= 2:
                profile.category_font = cat_fonts.most_common(1)[0][0]
                detected_features.append(f"Category Font: {profile.category_font}")
            if cat_decorations:
                prefix, suffix = cat_decorations.most_common(1)[0][0]
                profile.category_prefix = prefix
                profile.category_suffix = suffix
                detected_features.append(f"Category Wrapper: {prefix.strip()}...{suffix.strip()}")

        # 2. Analyze Channel Style
        if channel_names:
            sep_counts = Counter()
            bracket_counts = Counter()
            prefix_counts = Counter()
            font_counts = Counter()
            casing_counts = Counter()

            for ch in channel_names:
                ch_clean = ch.strip()

                # Detect tree prefix
                if ch_clean.startswith("╭・"):
                    prefix_counts["╭・"] += 1
                    ch_clean = ch_clean[2:]
                elif ch_clean.startswith("│・") or ch_clean.startswith("┃・"):
                    prefix_counts[ch_clean[:2]] += 1
                    ch_clean = ch_clean[2:]

                # Detect bracket wrapping around emoji
                m_bracket = re.match(r"^([『「【\[\(])\s*([^』」】\]\)]+)\s*([』」】\]\)])", ch_clean)
                if m_bracket:
                    bracket_counts[(m_bracket.group(1), m_bracket.group(3))] += 1
                    ch_clean = ch_clean[m_bracket.end():]

                # Detect separator
                for sep in KNOWN_SEPARATORS:
                    if sep in ch_clean:
                        sep_counts[sep] += 1
                        break

                # Detect font
                font = cls._detect_font(ch_clean)
                if font != "normal":
                    font_counts[font] += 1

                # Detect casing
                letters = [c for c in ch_clean if c.isalpha() and c in NORMAL]
                if letters:
                    if all(c.isupper() for c in letters):
                        casing_counts["upper"] += 1
                    elif all(c.islower() for c in letters):
                        casing_counts["lower"] += 1

            if sep_counts:
                profile.channel_separator = sep_counts.most_common(1)[0][0]
                detected_features.append(f"Separator: {profile.channel_separator!r}")
            if bracket_counts and bracket_counts.most_common(1)[0][1] >= 2:
                profile.channel_bracket = bracket_counts.most_common(1)[0][0]
                detected_features.append(f"Emoji Bracket: {profile.channel_bracket[0]}...{profile.channel_bracket[1]}")
            if prefix_counts and prefix_counts.most_common(1)[0][1] >= 2:
                profile.channel_prefix = prefix_counts.most_common(1)[0][0]
                detected_features.append(f"Prefix: {profile.channel_prefix!r}")
            if font_counts and font_counts.most_common(1)[0][1] >= 2:
                profile.channel_font = font_counts.most_common(1)[0][0]
                detected_features.append(f"Channel Font: {profile.channel_font}")
            if casing_counts:
                top_case, cnt = casing_counts.most_common(1)[0]
                if cnt >= len(channel_names) * 0.6:
                    profile.channel_casing = top_case
                    detected_features.append(f"Casing: {top_case}")

        if detected_features:
            profile.style_description = " • ".join(detected_features)
        else:
            profile.style_description = "Standard Discord Dot Style (Clean)"

        return profile

    @classmethod
    def _detect_font(cls, text: str) -> str:
        counts = {"math_bold": 0, "math_sans_bold": 0, "monospace": 0, "small_caps": 0, "normal": 0}
        for ch in text:
            if ch in MATH_BOLD:
                counts["math_bold"] += 1
            elif ch in MATH_SANS_BOLD:
                counts["math_sans_bold"] += 1
            elif ch in MONOSPACE:
                counts["monospace"] += 1
            elif ch in REV_SMALL_CAPS:
                counts["small_caps"] += 1
            elif ch in NORMAL:
                counts["normal"] += 1

        total_styled = counts["math_bold"] + counts["math_sans_bold"] + counts["monospace"] + counts["small_caps"]
        if total_styled >= 3 and total_styled >= counts["normal"]:
            return max(["math_bold", "math_sans_bold", "monospace", "small_caps"], key=lambda k: counts[k])
        return "normal"


def normalize_channel_name(name: str) -> str:
    """Normalize a channel name to its core alphanumeric token for duplicate comparison."""
    clean = _to_ascii(name)
    clean = re.sub(r"[^a-zA-Z0-9\-]", "", clean)
    return clean.lower().strip("-")


def _match_core(norm: str) -> str:
    """Collapse a normalized name to a loose comparison core (hyphens and plural suffix removed)."""
    core = norm.replace("-", "")
    if core.endswith("s") and len(core) > 4:
        core = core[:-1]
    return core


def _is_duplicate(existing_norm: str, canonical_key: str) -> bool:
    """Strict duplicate test: an empty or unrelated name must never match."""
    if not existing_norm or not canonical_key:
        return False
    a = _match_core(existing_norm)
    b = _match_core(canonical_key)
    return bool(a) and a == b


class DropperService:
    """High-level orchestration service for the Dropper Channels feature."""

    @classmethod
    def get_preview(cls, guild: discord.Guild) -> Dict[str, Any]:
        """Generate the style preview and duplicate analysis without making any changes."""
        profile = ServerStyleDetector.detect_guild(guild)
        category_name = profile.format_category_name("DEVELOPER")

        # Check if category already exists (font-aware name comparison)
        category_core = _to_ascii(category_name).lower()
        existing_cat = None
        for cat in guild.categories:
            cat_low = _to_ascii(cat.name).lower()
            if "developer" in cat_low or "dropper" in cat_low or cat_low.strip() == category_core.strip():
                existing_cat = cat
                break

        # The developer category is the only source of truth — channels with the same
        # name elsewhere in the guild must not block creation inside this category.
        cat_norms = [normalize_channel_name(c.name) for c in existing_cat.text_channels] if existing_cat else []

        planned_channels = []
        already_existing_count = 0
        to_create_count = 0

        for emoji, base_name, canonical_key in DROPPER_CHANNELS_DATA:
            formatted_name = profile.format_channel_name(emoji, base_name)
            exists = any(_is_duplicate(norm, canonical_key) for norm in cat_norms)

            if exists:
                already_existing_count += 1
            else:
                to_create_count += 1

            planned_channels.append({
                "emoji": emoji,
                "base_name": base_name,
                "formatted_name": formatted_name,
                "canonical_key": canonical_key,
                "already_exists": exists,
            })

        return {
            "guild_id": guild.id,
            "guild_name": guild.name,
            "category_name": category_name,
            "category_exists": existing_cat is not None,
            "category_id": existing_cat.id if existing_cat else None,
            "style_profile": profile.to_dict(),
            "style_description": profile.style_description,
            "channels": planned_channels,
            "total_channels": len(DROPPER_CHANNELS_DATA),
            "to_create_count": to_create_count,
            "already_existing_count": already_existing_count,
        }

    @classmethod
    async def execute_dropper(cls, guild: discord.Guild, user_id: int, user_name: str, sleep_delay: float = 0.4) -> Dict[str, Any]:
        """Create the DEVELOPER category and 16 text channels safely."""
        preview = cls.get_preview(guild)
        profile = ServerStyleDetector.detect_guild(guild)
        category_name = preview["category_name"]

        # 1. Locate or create category
        category = None
        category_reused = False
        if preview["category_exists"] and preview["category_id"]:
            category = guild.get_channel(preview["category_id"])
            if category:
                category_reused = True

        if category is None:
            # Re-check guild categories (font-aware: 𝐃𝐄𝐕𝐄𝐋𝐎𝐏𝐄𝐑 / 𝗗𝗘𝗩𝗘𝗟𝗢𝗣𝗘𝗥 / DEVELOPER all match)
            category_core = _to_ascii(category_name).lower().strip()
            for cat in guild.categories:
                cat_low = _to_ascii(cat.name).lower()
                if "developer" in cat_low or "dropper" in cat_low or cat_low.strip() == category_core:
                    category = cat
                    category_reused = True
                    break

        if category is None:
            for attempt in range(2):
                try:
                    category = await guild.create_category(
                        name=category_name,
                        reason=f"Novexa Dropper Channels setup requested by {user_name} ({user_id})",
                    )
                    category_reused = False
                    logger.info(f"Created category '{category_name}' in guild {guild.name} ({guild.id})")
                    break
                except discord.Forbidden:
                    raise PermissionError("Bot lacks permission to create categories in this server.")
                except discord.HTTPException as e:
                    if e.status == 429 and attempt == 0:
                        retry_after = getattr(e, "retry_after", None) or 2.0
                        await asyncio.sleep(min(float(retry_after), 5.0))
                        continue
                    raise RuntimeError(f"Failed to create category: {e}")
                except Exception as e:
                    raise RuntimeError(f"Failed to create category: {e}")

        if category is None:
            raise RuntimeError("Failed to create category: unknown error")

        # 2. Create planned channels
        created_channels = []
        skipped_channels = []
        failed_channels = []

        # Track what already exists inside the category (cache + channels created this run)
        existing_cores = set()
        for ch in category.text_channels:
            norm = normalize_channel_name(ch.name)
            if norm:
                existing_cores.add(_match_core(norm))

        for ch_data in preview["channels"]:
            formatted_name = ch_data["formatted_name"]
            canonical_key = ch_data["canonical_key"]
            key_core = _match_core(canonical_key)

            if key_core in existing_cores:
                skipped_channels.append(formatted_name)
                logger.info(f"Skipping existing channel '{formatted_name}' in guild {guild.id}")
                continue

            # Create channel — retry once on rate limit, never raise out of the loop
            created_ok = False
            last_error = "Unknown error"
            for attempt in range(2):
                try:
                    new_ch = await category.create_text_channel(
                        name=formatted_name,
                        topic=f"Dropper Channel • {ch_data['base_name']} • Created by NOVEXA",
                        reason=f"Novexa Dropper Channels setup by {user_name} ({user_id})",
                    )
                    created_channels.append(new_ch.name)
                    existing_cores.add(key_core)
                    created_ok = True
                    logger.info(f"Created text channel '{new_ch.name}' in category '{category.name}'")
                    break
                except discord.Forbidden:
                    last_error = "Bot lacks Manage Channels permission"
                    break
                except discord.HTTPException as e:
                    last_error = str(e)
                    if e.status == 429 and attempt == 0:
                        retry_after = getattr(e, "retry_after", None) or 1.0
                        await asyncio.sleep(min(float(retry_after), 5.0))
                        continue
                    break
                except Exception as e:
                    last_error = str(e)
                    break

            if not created_ok:
                failed_channels.append({"name": formatted_name, "error": last_error})
                logger.warning(f"Failed to create dropper channel '{formatted_name}': {last_error}")
                continue

            # Small pause between creations to stay clear of the channel-create rate limit
            if sleep_delay > 0:
                await asyncio.sleep(sleep_delay)

        # 3. Log to audit database
        try:
            await db.execute(
                """
                INSERT INTO config_audit_logs (guild_id, module_name, changed_by_user_id, changes_json, source)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    guild.id,
                    "dropper_channels",
                    user_id,
                    str({
                        "category": category.name,
                        "category_reused": category_reused,
                        "created_count": len(created_channels),
                        "skipped_count": len(skipped_channels),
                        "failed_count": len(failed_channels),
                    }),
                    "dropper_setup",
                ),
            )
        except Exception as e:
            logger.warning(f"Could not record audit log: {e}")

        return {
            "success": True,
            "guild_id": guild.id,
            "guild_name": guild.name,
            "category_name": category.name,
            "category_reused": category_reused,
            "created_count": len(created_channels),
            "created_channels": created_channels,
            "skipped_count": len(skipped_channels),
            "skipped_channels": skipped_channels,
            "failed_count": len(failed_channels),
            "failed_channels": failed_channels,
            "style_description": profile.style_description,
        }


dropper_service = DropperService()
