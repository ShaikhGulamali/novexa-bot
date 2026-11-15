"""NOVEXA - Advanced Role Management, Dynamic Panels, Hierarchy & Interactive Stylish Role Wizard.

Features:
- Dynamic self-role button panels
- Automatic autorole granting on join
- Hierarchy validation
- Interactive Multi-Step Stylish Role Creation Wizard:
  - Custom role name with real-time Unicode font converters (Crown, Sparkles, Diamond, Japanese, Fraktur, Double-Struck, Small Caps, Bold Sans, Brackets, Plain)
  - Color palette selection (Presets or custom Hex)
  - Interactive Channel Selector dropdown (specific channels or All Server Channels)
  - Interactive Permission Selector (View, Send, Files/Media, Embeds, Reactions, External Emojis/Stickers, Voice, Moderate) + Presets (Chat, VIP, Mod)
  - Automatic creation and channel overwrite deployment across all chosen channels & categories
- Full Slash Command & Prefix Command Suite (/role create, n!role create)
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
import re
import asyncio
from typing import Optional, List, Dict, Any, Tuple, Set, Union
from database.database import db
from utils.embeds import primary_embed, success_embed, error_embed, warning_embed, info_embed
from utils.permissions import check_role_hierarchy, has_admin_or_owner
from utils.helpers import PaginatorView
from config import BOT_NAME, BOT_PREFIX

logger = logging.getLogger("novexa.roles")

COLOR_PRIMARY = 0x5865F2
COLOR_SUCCESS = 0x2ECC71
COLOR_WARNING = 0xF1C40F
COLOR_ERROR = 0xE74C3C

# ==================== UNICODE FONT TRANSLATION MAPS ====================

ROLE_FONT_MAPS = {
    "small_caps": str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ",
    ),
    "bold_sans": str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵",
    ),
    "fraktur": str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "𝖆𝖇𝖈𝖉𝖊𝖋𝖌𝖍𝖎𝖏𝖐𝖑𝖒𝖓𝖔𝖕𝖖𝖗𝖘𝖙𝖚𝖛𝖜𝖝𝖞𝖟𝕬𝕭𝕮𝕯𝕰𝕱𝕲𝕳𝕴𝕵𝕶𝕷𝕸𝕹𝕺𝕻𝕼𝕽𝕾𝕿𝖀𝖁𝖂𝖃𝖄𝖅",
    ),
    "double_struck": str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "𝕒𝕓𝕔𝕕𝕖𝕗𝕘𝕙𝕚𝕛𝕜𝕝𝕞𝕟𝕠𝕡𝕢𝕣𝕤𝕥𝕦𝕧𝕨𝕩𝕪𝕫𝔸𝔹ℂ𝔻𝔼𝔽𝔾ℍ𝕀𝕁𝕂𝕃𝕄ℕ𝕆ℙℚℝ𝕊𝕋𝕌𝕍𝕎𝕏𝕐ℤ𝟘𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡",
    ),
    "monospace": str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝖒𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣𝙰𝙱𝙲𝙳𝙴𝙵𝙶𝙷𝙸𝙹𝙺𝙻𝙼𝙽𝙾𝙿𝚀𝚁𝚂𝚃𝚄𝚅𝚆𝚇𝚈𝚉𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿",
    ),
}

ROLE_STYLES: Dict[str, Tuple[str, str]] = {
    "crown_small": ("👑 ┃ {text}", "small_caps"),
    "sparkle_small": ("✨ ┃ {text}", "small_caps"),
    "diamond_small": ("💎 ┃ {text}", "small_caps"),
    "japanese_bold": ("【 {text} 】", "bold_sans"),
    "star_fraktur": ("✦ {text} ✦", "fraktur"),
    "double_struck": ("{text}", "double_struck"),
    "pure_small_caps": ("{text}", "small_caps"),
    "bold_sans": ("{text}", "bold_sans"),
    "bracket_small": ("「 {text} 」", "small_caps"),
    "plain": ("{text}", "plain"),
}


def apply_role_font_styling(raw_name: str, style_key: str = "crown_small") -> str:
    """Transform regular text into aesthetic typography with optional icon badge."""
    template, font_type = ROLE_STYLES.get(style_key, ROLE_STYLES["crown_small"])
    if font_type in ROLE_FONT_MAPS:
        converted = raw_name.translate(ROLE_FONT_MAPS[font_type])
    else:
        converted = raw_name
    return template.replace("{text}", converted).strip()


# Available Channel Permissions with Overwrites Mapping
AVAILABLE_PERMISSIONS: Dict[str, Dict[str, Any]] = {
    "view": {
        "label": "View Channel & Read History",
        "emoji": "👁️",
        "desc": "Access and read messages in the channel",
        "overwrites": {"view_channel": True, "read_messages": True, "read_message_history": True},
    },
    "send": {
        "label": "Send Messages & Threads",
        "emoji": "💬",
        "desc": "Chat in channel and inside active threads",
        "overwrites": {"send_messages": True, "send_messages_in_threads": True},
    },
    "media": {
        "label": "Attach Files & Upload Media",
        "emoji": "📎",
        "desc": "Upload images, videos, audio, and attachments",
        "overwrites": {"attach_files": True},
    },
    "links": {
        "label": "Embed Links",
        "emoji": "🔗",
        "desc": "Show rich embeds and link previews",
        "overwrites": {"embed_links": True},
    },
    "react": {
        "label": "Add Reactions",
        "emoji": "👍",
        "desc": "React to messages with emojis",
        "overwrites": {"add_reactions": True},
    },
    "emojis": {
        "label": "External Emojis & Stickers",
        "emoji": "😃",
        "desc": "Use custom emojis and stickers from other servers",
        "overwrites": {"use_external_emojis": True, "use_external_stickers": True},
    },
    "voice": {
        "label": "Voice Connect & Speak",
        "emoji": "🔊",
        "desc": "Join voice channels and speak",
        "overwrites": {"connect": True, "speak": True},
    },
    "mod": {
        "label": "Manage Messages (Pin / Delete)",
        "emoji": "🛡️",
        "desc": "Pin or delete messages (Moderation)",
        "overwrites": {"manage_messages": True},
    },
}

PRESETS: Dict[str, Set[str]] = {
    "chat": {"view", "send", "links", "react"},
    "vip": {"view", "send", "media", "links", "react", "emojis"},
    "mod": {"view", "send", "media", "links", "react", "emojis", "voice", "mod"},
}


# ==================== INTERACTIVE ROLE WIZARD VIEWS ====================

class RoleWizardStyleSelect(discord.ui.Select):
    """Dropdown selector to change font style live in Stage 1."""

    def __init__(self, wizard_view: "StylishRoleWizardView"):
        options = [
            discord.SelectOption(label="Crown: 👑 ┃ Text", value="crown_small", description="Royal crown badge + small caps", emoji="👑", default=(wizard_view.current_style == "crown_small")),
            discord.SelectOption(label="Sparkle: ✨ ┃ Text", value="sparkle_small", description="Sparkle badge + small caps", emoji="✨", default=(wizard_view.current_style == "sparkle_small")),
            discord.SelectOption(label="Diamond: 💎 ┃ Text", value="diamond_small", description="Diamond badge + small caps", emoji="💎", default=(wizard_view.current_style == "diamond_small")),
            discord.SelectOption(label="Japanese: 【 Text 】", value="japanese_bold", description="Japanese brackets + bold text", emoji="🏮", default=(wizard_view.current_style == "japanese_bold")),
            discord.SelectOption(label="Fraktur: ✦ Text ✦", value="star_fraktur", description="Gothic fraktur font + stars", emoji="⭐", default=(wizard_view.current_style == "star_fraktur")),
            discord.SelectOption(label="Double-Struck: 𝕋𝕖𝕩𝕥", value="double_struck", description="Blackboard math typography", emoji="✒️", default=(wizard_view.current_style == "double_struck")),
            discord.SelectOption(label="Small Caps: ᴛᴇxᴛ", value="pure_small_caps", description="Clean aesthetic small capital letters", emoji="🔤", default=(wizard_view.current_style == "pure_small_caps")),
            discord.SelectOption(label="Bold Sans: 𝗧𝗲𝘅𝘁", value="bold_sans", description="Modern bold sans-serif", emoji="🅱️", default=(wizard_view.current_style == "bold_sans")),
            discord.SelectOption(label="Bracket: 「 Text 」", value="bracket_small", description="Japanese corner brackets", emoji="🔖", default=(wizard_view.current_style == "bracket_small")),
            discord.SelectOption(label="Plain: Text", value="plain", description="Standard regular Discord font", emoji="📄", default=(wizard_view.current_style == "plain")),
        ]
        super().__init__(
            placeholder="🎨 Choose role name style & font...",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )
        self.wizard_view = wizard_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.wizard_view.author.id:
            return await interaction.response.send_message("Sirf command chalane wala user ye style change kar sakta hai.", ephemeral=True)

        self.wizard_view.current_style = self.values[0]
        self.wizard_view.styled_name = apply_role_font_styling(self.wizard_view.raw_name, self.wizard_view.current_style)
        self.wizard_view.setup_stage1()
        await interaction.response.edit_message(embed=self.wizard_view.build_stage1_embed(), view=self.wizard_view)


class RoleWizardChannelSelect(discord.ui.ChannelSelect):
    """Multi-channel dropdown selector for Step 1 of Role Wizard."""

    def __init__(self, wizard_view: "StylishRoleWizardView"):
        super().__init__(
            placeholder="Select specific channels/categories (up to 25)...",
            min_values=1,
            max_values=25,
            channel_types=[
                discord.ChannelType.text,
                discord.ChannelType.news,
                discord.ChannelType.voice,
                discord.ChannelType.stage_voice,
                discord.ChannelType.forum,
                discord.ChannelType.category,
            ],
            row=1,
        )
        self.wizard_view = wizard_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.wizard_view.author.id:
            return await interaction.response.send_message("Sirf command chalane wala user channels select kar sakta hai.", ephemeral=True)

        self.wizard_view.selected_channels = [ch.id for ch in self.values]
        self.wizard_view.all_channels = False
        await interaction.response.edit_message(embed=self.wizard_view.build_stage1_embed(), view=self.wizard_view)


class RoleWizardPermSelect(discord.ui.Select):
    """Multi-select dropdown for Step 2 of Role Wizard."""

    def __init__(self, wizard_view: "StylishRoleWizardView"):
        options = []
        for key, pinfo in AVAILABLE_PERMISSIONS.items():
            options.append(
                discord.SelectOption(
                    label=pinfo["label"],
                    value=key,
                    emoji=pinfo["emoji"],
                    description=pinfo["desc"][:100],
                    default=(key in wizard_view.selected_permissions),
                )
            )
        super().__init__(
            placeholder="Choose permissions to grant in selected channels...",
            min_values=1,
            max_values=len(options),
            options=options,
            row=0,
        )
        self.wizard_view = wizard_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.wizard_view.author.id:
            return await interaction.response.send_message("Sirf command chalane wala user permissions set kar sakta hai.", ephemeral=True)

        self.wizard_view.selected_permissions = set(self.values)
        self.wizard_view.setup_stage2()
        await interaction.response.edit_message(embed=self.wizard_view.build_stage2_embed(), view=self.wizard_view)


class StylishRoleWizardView(discord.ui.View):
    """Multi-Step Interactive Wizard to configure channels and permissions before creating a stylish role."""

    def __init__(
        self,
        author: Union[discord.Member, discord.User],
        guild: discord.Guild,
        raw_name: str,
        current_style: str,
        styled_name: str,
        color: discord.Color,
        hoist: bool,
    ):
        super().__init__(timeout=300)
        self.author = author
        self.guild = guild
        self.raw_name = raw_name
        self.current_style = current_style
        self.styled_name = styled_name
        self.color = color
        self.hoist = hoist

        self.stage = 1  # 1 = Channels, 2 = Permissions
        self.selected_channels: List[int] = []
        self.all_channels: bool = False
        self.selected_permissions: Set[str] = set(PRESETS["vip"])

        self.setup_stage1()

    def setup_stage1(self):
        """Construct Step 1 UI: Font Style & Channel Selection."""
        self.clear_items()
        self.stage = 1
        self.add_item(RoleWizardStyleSelect(self))
        self.add_item(RoleWizardChannelSelect(self))

        btn_all = discord.ui.Button(label="🌐 All Server Channels", style=discord.ButtonStyle.secondary, row=2, custom_id="btn_all_ch")
        btn_all.callback = self.cb_all_channels
        self.add_item(btn_all)

        btn_next = discord.ui.Button(label="Next: Configure Permissions ➡️", style=discord.ButtonStyle.primary, row=2, custom_id="btn_next_perms")
        btn_next.callback = self.cb_next_stage
        self.add_item(btn_next)

        btn_cancel = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.danger, row=2, custom_id="btn_cancel_wiz")
        btn_cancel.callback = self.cb_cancel
        self.add_item(btn_cancel)

    def setup_stage2(self):
        """Construct Step 2 UI: Permission Selection."""
        self.clear_items()
        self.stage = 2
        self.add_item(RoleWizardPermSelect(self))

        btn_chat = discord.ui.Button(label="💬 Chat Preset", style=discord.ButtonStyle.secondary, row=1)
        btn_chat.callback = self.cb_preset_chat
        self.add_item(btn_chat)

        btn_vip = discord.ui.Button(label="🌟 VIP/Media Preset", style=discord.ButtonStyle.secondary, row=1)
        btn_vip.callback = self.cb_preset_vip
        self.add_item(btn_vip)

        btn_mod = discord.ui.Button(label="🛡️ Mod Preset", style=discord.ButtonStyle.secondary, row=1)
        btn_mod.callback = self.cb_preset_mod
        self.add_item(btn_mod)

        btn_create = discord.ui.Button(label="🚀 Create Role & Deploy!", style=discord.ButtonStyle.success, row=2)
        btn_create.callback = self.cb_finalize
        self.add_item(btn_create)

        btn_back = discord.ui.Button(label="⬅️ Back to Channels", style=discord.ButtonStyle.secondary, row=2)
        btn_back.callback = self.cb_back
        self.add_item(btn_back)

        btn_cancel = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.danger, row=2)
        btn_cancel.callback = self.cb_cancel
        self.add_item(btn_cancel)

    def build_stage1_embed(self) -> discord.Embed:
        if self.all_channels:
            ch_summary = "🌐 **All Server Channels & Categories Selected**"
        elif self.selected_channels:
            ch_mentions = [f"<#{cid}>" for cid in self.selected_channels[:8]]
            extra = f" and {len(self.selected_channels)-8} more..." if len(self.selected_channels) > 8 else ""
            ch_summary = f"✅ **Selected Channels ({len(self.selected_channels)}):** {', '.join(ch_mentions)}{extra}"
        else:
            ch_summary = "⚠️ *Koi channel select nahi kiya hai.* Dropdown se channels select karein ya `🌐 All Server Channels` dabayein."

        embed = discord.Embed(
            title="👑 Stylish Role Creation Wizard (Step 1/2: Channels)",
            description=(
                f"**Role Specifications:**\n"
                f"• **Styled Name:** `{self.styled_name}`\n"
                f"• **Role Color:** `{str(self.color)}`\n"
                f"• **Hoisted (Separated in Member List):** {'✅ Yes' if self.hoist else 'No'}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👇 **Step 1: Channels Select Karein**\n"
                f"Ye role server ke konse channels me permissions payega?\n\n"
                f"**Current Channel Selection:**\n{ch_summary}\n\n"
                f"• *Style dropdown se font / badge live change kar sakte hain.*\n"
                f"• *Channel dropdown se specific channels select karein ya `🌐 All Server Channels` dabayein.*\n"
                f"• *Channels select hone ke baad **'Next: Configure Permissions ➡️'** dabayein.*"
            ),
            color=self.color if self.color.value != 0 else COLOR_PRIMARY,
        )
        embed.set_footer(text="Step 1: Channel Assignment • NOVEXA Dynamic Role Engine")
        return embed

    def build_stage2_embed(self) -> discord.Embed:
        if self.all_channels:
            ch_str = "🌐 **All Channels & Categories in Server**"
        elif self.selected_channels:
            mentions = [f"<#{cid}>" for cid in self.selected_channels[:8]]
            extra = f" and {len(self.selected_channels)-8} more..." if len(self.selected_channels) > 8 else ""
            ch_str = f"**{len(self.selected_channels)} Channels:** {', '.join(mentions)}{extra}"
        else:
            ch_str = "*(None selected)*"

        active_perms = [
            f"{AVAILABLE_PERMISSIONS[k]['emoji']} `{AVAILABLE_PERMISSIONS[k]['label']}`"
            for k in self.selected_permissions if k in AVAILABLE_PERMISSIONS
        ]

        embed = discord.Embed(
            title="👑 Stylish Role Creation Wizard (Step 2/2: Permissions)",
            description=(
                f"**Role Preview:** `{self.styled_name}`\n"
                f"**Target Channels:**\n{ch_str}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👇 **Step 2: In Channels me kya Permissions honi chahiye?**\n\n"
                f"**Currently Active Permissions ({len(active_perms)}):**\n"
                + ("\n".join(f"• {p}" for p in active_perms) if active_perms else "*No permissions selected.*") + "\n\n"
                f"• *Dropdown se permissions select ya unselect karein.*\n"
                f"• *Ya niche diye gaye quick preset buttons (`💬 Chat`, `🌟 VIP`, `🛡️ Mod`) use karein.*\n"
                f"• *Finalize karne ke liye **'🚀 Create Role & Deploy!'** click karein.*"
            ),
            color=self.color if self.color.value != 0 else COLOR_PRIMARY,
        )
        embed.set_footer(text="Step 2: Permission Overwrites • Click '🚀 Create Role & Deploy' when ready")
        return embed

    async def cb_all_channels(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("Sirf command chalane wala user ye configure kar sakta hai.", ephemeral=True)
        self.all_channels = True
        self.selected_channels = []
        self.setup_stage2()
        await interaction.response.edit_message(embed=self.build_stage2_embed(), view=self)

    async def cb_next_stage(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("Sirf command chalane wala user ye configure kar sakta hai.", ephemeral=True)
        if not self.selected_channels and not self.all_channels:
            return await interaction.response.send_message(
                "⚠️ Pehle dropdown se channels select karein ya '🌐 All Server Channels' button dabayein!",
                ephemeral=True
            )
        self.setup_stage2()
        await interaction.response.edit_message(embed=self.build_stage2_embed(), view=self)

    async def cb_back(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("Sirf command chalane wala user ye configure kar sakta hai.", ephemeral=True)
        self.setup_stage1()
        await interaction.response.edit_message(embed=self.build_stage1_embed(), view=self)

    async def cb_cancel(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("Sirf command chalane wala user ye cancel kar sakta hai.", ephemeral=True)
        self.stop()
        await interaction.response.edit_message(content="❌ Role creation wizard cancelled.", embed=None, view=None)

    async def cb_preset_chat(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("Sirf command chalane wala user ye configure kar sakta hai.", ephemeral=True)
        self.selected_permissions = set(PRESETS["chat"])
        self.setup_stage2()
        await interaction.response.edit_message(embed=self.build_stage2_embed(), view=self)

    async def cb_preset_vip(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("Sirf command chalane wala user ye configure kar sakta hai.", ephemeral=True)
        self.selected_permissions = set(PRESETS["vip"])
        self.setup_stage2()
        await interaction.response.edit_message(embed=self.build_stage2_embed(), view=self)

    async def cb_preset_mod(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("Sirf command chalane wala user ye configure kar sakta hai.", ephemeral=True)
        self.selected_permissions = set(PRESETS["mod"])
        self.setup_stage2()
        await interaction.response.edit_message(embed=self.build_stage2_embed(), view=self)

    async def cb_finalize(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("Sirf command chalane wala user ye configure kar sakta hai.", ephemeral=True)

        await interaction.response.defer()
        guild = self.guild

        # 1. Create Role in Discord
        try:
            new_role = await guild.create_role(
                name=self.styled_name,
                color=self.color,
                hoist=self.hoist,
                mentionable=True,
                reason=f"Created via NOVEXA Role Wizard by {self.author}",
            )
        except discord.Forbidden:
            return await interaction.followup.send(
                embed=error_embed("Creation Failed", "Bot lacks permission to create roles or role hierarchy is blocked.")
            )
        except Exception as e:
            return await interaction.followup.send(embed=error_embed("Creation Error", str(e)))

        # 2. Compile Overwrites
        overwrites_kwargs = {}
        for pkey in self.selected_permissions:
            pinfo = AVAILABLE_PERMISSIONS.get(pkey)
            if pinfo:
                overwrites_kwargs.update(pinfo["overwrites"])

        # 3. Apply Overwrites to Channels
        success_channels = 0
        target_channels = []

        if self.all_channels:
            target_channels = list(guild.categories) + [c for c in guild.channels if not isinstance(c, discord.CategoryChannel)]
        else:
            for cid in self.selected_channels:
                ch = guild.get_channel(cid)
                if ch:
                    target_channels.append(ch)

        for ch in target_channels:
            try:
                # Ensure parent category allows view if viewing is granted
                if getattr(ch, "category", None) and overwrites_kwargs.get("view_channel"):
                    parent_cat = ch.category
                    cat_ow = parent_cat.overwrites_for(new_role)
                    if not cat_ow.view_channel:
                        cat_ow.view_channel = True
                        await parent_cat.set_permissions(new_role, overwrite=cat_ow, reason=f"Parent category view for {new_role.name}")

                current_ow = ch.overwrites_for(new_role)
                for k, v in overwrites_kwargs.items():
                    setattr(current_ow, k, v)
                await ch.set_permissions(new_role, overwrite=current_ow, reason=f"NOVEXA Role Wizard perms for {new_role.name}")
                success_channels += 1
            except Exception as e:
                logger.debug(f"Error setting perms on {getattr(ch, 'name', 'ch')}: {e}")

        perm_labels = [
            f"{AVAILABLE_PERMISSIONS[k]['emoji']} **{AVAILABLE_PERMISSIONS[k]['label']}**"
            for k in self.selected_permissions if k in AVAILABLE_PERMISSIONS
        ]

        embed = discord.Embed(
            title="🎉 Stylish Role Created & Configured!",
            description=(
                f"Successfully built and deployed {new_role.mention} across **{success_channels} channels**!\n\n"
                f"**👑 Role Overview:**\n"
                f"• **Role Name:** `{new_role.name}`\n"
                f"• **Role Mention:** {new_role.mention}\n"
                f"• **Role ID:** `{new_role.id}`\n"
                f"• **Color:** `{str(new_role.color)}`\n"
                f"• **Hoisted (Separated in Member List):** {'✅ Yes' if new_role.hoist else 'No'}\n\n"
                f"**📡 Channels Configured ({success_channels}):**\n"
                + ("🌐 **All Server Channels & Categories**" if self.all_channels else f"Applied to **{success_channels} selected channels**") + "\n\n"
                f"**🛡️ Granted Permissions in Selected Channels:**\n"
                + ("\n".join(f"• {lbl}" for lbl in perm_labels) if perm_labels else "*Default permissions.*")
            ),
            color=self.color if self.color.value != 0 else COLOR_SUCCESS,
        )
        embed.set_footer(text=f"Created by {self.author.display_name} • NOVEXA Dynamic Role Engine")

        self.stop()
        try:
            await interaction.edit_original_response(embed=embed, view=None)
        except Exception:
            try:
                if interaction.message:
                    await interaction.message.edit(embed=embed, view=None)
            except Exception as e:
                logger.debug(f"Error updating wizard message: {e}")


# ==================== DYNAMIC ROLE BUTTONS & PANELS ====================

class DynamicRoleButton(discord.ui.Button):
    def __init__(self, role_id: int, label: str, style: discord.ButtonStyle = discord.ButtonStyle.primary, emoji: Optional[str] = None):
        super().__init__(style=style, label=label, emoji=emoji, custom_id=f"gulamali_rolebtn_{role_id}")
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        role = guild.get_role(self.role_id)
        if not role:
            return await interaction.response.send_message("This role no longer exists.", ephemeral=True)

        member = interaction.user
        if not isinstance(member, discord.Member):
            return

        if role in member.roles:
            try:
                await member.remove_roles(role, reason="Self-role panel removal")
                await interaction.response.send_message(f"Removed role {role.mention}.", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("Failed to remove role: Missing permissions.", ephemeral=True)
        else:
            try:
                await member.add_roles(role, reason="Self-role panel assignment")
                await interaction.response.send_message(f"Assigned role {role.mention}.", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("Failed to assign role: Missing permissions or hierarchy.", ephemeral=True)


class DynamicRolePanelView(discord.ui.View):
    """Dynamic persistent view for role selection panels."""

    def __init__(self):
        super().__init__(timeout=None)


# ==================== MAIN ROLES COG ====================

class Roles(commands.Cog):
    """Advanced Server Role Management, Hierarchy Validation, Auto-Roles & Interactive Stylish Role Wizard."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Automatically assign configured autoroles when a new member joins."""
        if member.bot:
            return

        rows = await db.fetchall("SELECT role_id FROM auto_roles WHERE guild_id = ?", (member.guild.id,))
        for r in rows:
            role = member.guild.get_role(r["role_id"])
            if role and role < member.guild.me.top_role:
                try:
                    await member.add_roles(role, reason="Automatic Join Role (Autorole)")
                except Exception as e:
                    logger.warning(f"Failed to add autorole {role.id} to {member.id}: {e}")

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Catch persistent custom_id for role buttons across bot restarts."""
        if interaction.type != discord.InteractionType.component:
            return
        custom_id = interaction.data.get("custom_id", "")
        if custom_id.startswith("gulamali_rolebtn_"):
            try:
                role_id = int(custom_id.replace("gulamali_rolebtn_", ""))
                guild = interaction.guild
                role = guild.get_role(role_id) if guild else None
                if not role:
                    return await interaction.response.send_message("This role does not exist.", ephemeral=True)

                member = interaction.user
                if not isinstance(member, discord.Member):
                    return

                if role in member.roles:
                    await member.remove_roles(role, reason="Self-role panel toggle")
                    await interaction.response.send_message(f"➖ Removed role {role.mention}.", ephemeral=True)
                else:
                    await member.add_roles(role, reason="Self-role panel toggle")
                    await interaction.response.send_message(f"➕ Added role {role.mention}.", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("Bot lacks permissions to modify this role.", ephemeral=True)
            except Exception as e:
                logger.error(f"Error handling dynamic role button: {e}")

    async def launch_wizard(
        self,
        ctx_or_interaction: Union[commands.Context, discord.Interaction],
        name: Optional[str] = None,
        style_key: str = "crown_small",
        color_hex: Optional[str] = None,
        hoist: bool = True,
    ):
        """Launch the Interactive Stylish Role Creation Wizard."""
        is_interaction = isinstance(ctx_or_interaction, discord.Interaction)
        guild = ctx_or_interaction.guild
        author = ctx_or_interaction.user if is_interaction else ctx_or_interaction.author

        # If name is not provided, prompt the user for it
        if not name:
            prompt_embed = discord.Embed(
                title="👑 Stylish Role Creation Wizard",
                description=(
                    "**Aapko kis name ka role banana hai?**\n\n"
                    "Niche role ka name type karke reply karein *(jaise: `VIP`, `Staff`, `Moderator`)*\n"
                    "*(Cancel karne ke liye `cancel` likhein)*"
                ),
                color=COLOR_PRIMARY,
            )
            if is_interaction:
                await ctx_or_interaction.response.send_message(embed=prompt_embed)
            else:
                await ctx_or_interaction.send(embed=prompt_embed)

            channel = ctx_or_interaction.channel

            def check(m: discord.Message):
                return m.author.id == author.id and m.channel.id == channel.id

            try:
                msg = await self.bot.wait_for("message", check=check, timeout=60.0)
                raw_name = msg.content.strip()
                if raw_name.lower() in ["cancel", "exit", "stop"]:
                    return await channel.send("❌ Role creation cancelled.")
                name = raw_name
            except asyncio.TimeoutError:
                return await channel.send("⏱️ Time out ho gaya. Role banane ke liye command dobara run karein.")

        styled_name = apply_role_font_styling(name, style_key)
        role_color = discord.Color(0xF1C40F)  # Gold default
        if color_hex:
            clean_hex = color_hex.strip().lstrip("#")
            if re.match(r"^[0-9a-fA-F]{6}$", clean_hex):
                role_color = discord.Color(int(clean_hex, 16))

        wizard = StylishRoleWizardView(
            author=author,
            guild=guild,
            raw_name=name,
            current_style=style_key,
            styled_name=styled_name,
            color=role_color,
            hoist=hoist,
        )
        embed = wizard.build_stage1_embed()

        if is_interaction:
            if ctx_or_interaction.response.is_done():
                await ctx_or_interaction.followup.send(embed=embed, view=wizard)
            else:
                await ctx_or_interaction.response.send_message(embed=embed, view=wizard)
        else:
            await ctx_or_interaction.send(embed=embed, view=wizard)

    # ==================== SLASH COMMAND GROUP: /role ====================

    role_group = app_commands.Group(name="role", description="Manage server roles, self-roles, and hierarchy")

    @role_group.command(name="create", description="Design & create a role with stylish fonts, channel picker & custom perms")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.describe(
        name="Role name (e.g. VIP, Moderator, Supporter)",
        style="Aesthetic font & decoration style",
        color="Color preset (or enter custom hex code in color_hex)",
        color_hex="Optional custom hex color code (e.g. #FF007F)",
        hoist="Display role members separately in the sidebar (Default: True)",
    )
    @app_commands.choices(style=[
        app_commands.Choice(name="👑 Crown + Small Caps: 👑 ┃ ᴠɪᴘ", value="crown_small"),
        app_commands.Choice(name="✨ Sparkle + Small Caps: ✨ ┃ ᴠɪᴘ", value="sparkle_small"),
        app_commands.Choice(name="💎 Diamond + Small Caps: 💎 ┃ ᴠɪᴘ", value="diamond_small"),
        app_commands.Choice(name="「 」Bracket + Small Caps: 「 ᴠɪᴘ 」", value="bracket_small"),
        app_commands.Choice(name="【 】Japanese + Bold: 【 𝗩𝗜𝗣 】", value="japanese_bold"),
        app_commands.Choice(name="✦ Star + Fraktur: ✦ 𝖁𝕴𝕻 ✦", value="star_fraktur"),
        app_commands.Choice(name="Double-Struck: 𝕍𝕀ℙ", value="double_struck"),
        app_commands.Choice(name="Pure Small Caps: ᴠɪᴘ", value="pure_small_caps"),
        app_commands.Choice(name="Bold Sans: 𝗩𝗜𝗣", value="bold_sans"),
        app_commands.Choice(name="Plain (Original Text): VIP", value="plain"),
    ])
    @app_commands.choices(color=[
        app_commands.Choice(name="🟡 Royal Gold (#F1C40F)", value="#F1C40F"),
        app_commands.Choice(name="🟣 Royal Purple (#9B59B6)", value="#9B59B6"),
        app_commands.Choice(name="🟢 Emerald Green (#2ECC71)", value="#2ECC71"),
        app_commands.Choice(name="🔴 Crimson Red (#E74C3C)", value="#E74C3C"),
        app_commands.Choice(name="🔵 Aqua / Cyan (#00FFFF)", value="#00FFFF"),
        app_commands.Choice(name="💖 Neon Pink (#FF69B4)", value="#FF69B4"),
        app_commands.Choice(name="🟠 Flame Orange (#E67E22)", value="#E67E22"),
        app_commands.Choice(name="⚪ Pure White (#FFFFFF)", value="#FFFFFF"),
    ])
    async def role_create(
        self,
        interaction: discord.Interaction,
        name: str,
        style: Optional[app_commands.Choice[str]] = None,
        color: Optional[app_commands.Choice[str]] = None,
        color_hex: Optional[str] = None,
        hoist: bool = True,
    ):
        chosen_style = style.value if style else "crown_small"
        chosen_color = color_hex or (color.value if color else None)
        await self.launch_wizard(
            ctx_or_interaction=interaction,
            name=name,
            style_key=chosen_style,
            color_hex=chosen_color,
            hoist=hoist,
        )

    @role_group.command(name="add", description="Add a role to a member with hierarchy checks")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.describe(user="The member to receive the role", role="The role to assign")
    async def role_add(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        allowed, error_msg = check_role_hierarchy(interaction.user, role, interaction.guild.me)
        if not allowed:
            return await interaction.response.send_message(embed=error_embed("Permission Denied", error_msg), ephemeral=True)

        if role in user.roles:
            return await interaction.response.send_message(
                embed=warning_embed("Already Has Role", f"{user.mention} already has the {role.mention} role."),
                ephemeral=True,
            )

        try:
            await user.add_roles(role, reason=f"Assigned by {interaction.user}")
            await interaction.response.send_message(
                embed=success_embed("Role Added", f"Assigned {role.mention} to {user.mention}."),
            )
        except discord.Forbidden:
            await interaction.response.send_message(embed=error_embed("Error", "Missing permissions to add this role."), ephemeral=True)

    @role_group.command(name="remove", description="Remove a role from a member with hierarchy checks")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.describe(user="The member to lose the role", role="The role to remove")
    async def role_remove(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        allowed, error_msg = check_role_hierarchy(interaction.user, role, interaction.guild.me)
        if not allowed:
            return await interaction.response.send_message(embed=error_embed("Permission Denied", error_msg), ephemeral=True)

        if role not in user.roles:
            return await interaction.response.send_message(
                embed=warning_embed("Role Not Present", f"{user.mention} does not have the {role.mention} role."),
                ephemeral=True,
            )

        try:
            await user.remove_roles(role, reason=f"Removed by {interaction.user}")
            await interaction.response.send_message(
                embed=success_embed("Role Removed", f"Removed {role.mention} from {user.mention}."),
            )
        except discord.Forbidden:
            await interaction.response.send_message(embed=error_embed("Error", "Missing permissions to remove this role."), ephemeral=True)

    @role_group.command(name="delete", description="Delete an existing role")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.describe(role="The role to delete")
    async def role_delete(self, interaction: discord.Interaction, role: discord.Role):
        allowed, error_msg = check_role_hierarchy(interaction.user, role, interaction.guild.me)
        if not allowed:
            return await interaction.response.send_message(embed=error_embed("Permission Denied", error_msg), ephemeral=True)

        role_name = role.name
        try:
            await role.delete(reason=f"Role deleted by {interaction.user}")
            await interaction.response.send_message(embed=success_embed("Role Deleted", f"Role **@{role_name}** has been deleted."))
        except discord.Forbidden:
            await interaction.response.send_message(embed=error_embed("Error", "Bot lacks permission to delete this role."), ephemeral=True)

    @role_group.command(name="info", description="View detailed information about a role")
    @app_commands.describe(role="Role to inspect")
    async def role_info(self, interaction: discord.Interaction, role: discord.Role):
        embed = primary_embed(title=f"Role Information: @{role.name}")
        embed.color = role.color.value if role.color.value != 0 else discord.Color.blurple().value
        embed.add_field(name="ID", value=str(role.id), inline=True)
        embed.add_field(name="Color Hex", value=str(role.color), inline=True)
        embed.add_field(name="Position", value=str(role.position), inline=True)
        embed.add_field(name="Members with Role", value=str(len(role.members)), inline=True)
        embed.add_field(name="Hoisted (Separated)", value="Yes" if role.hoist else "No", inline=True)
        embed.add_field(name="Mentionable", value="Yes" if role.mentionable else "No", inline=True)
        embed.add_field(name="Created At", value=role.created_at.strftime("%b %d, %Y"), inline=True)

        key_perms = []
        if role.permissions.administrator:
            key_perms.append("Administrator")
        if role.permissions.manage_guild:
            key_perms.append("Manage Server")
        if role.permissions.manage_roles:
            key_perms.append("Manage Roles")
        if role.permissions.manage_channels:
            key_perms.append("Manage Channels")
        if role.permissions.ban_members:
            key_perms.append("Ban Members")
        if role.permissions.kick_members:
            key_perms.append("Kick Members")

        embed.add_field(name="Key Permissions", value=", ".join(key_perms) or "Standard Permissions", inline=False)
        await interaction.response.send_message(embed=embed)

    @role_group.command(name="list", description="List all server roles ordered by hierarchy")
    async def role_list(self, interaction: discord.Interaction):
        guild = interaction.guild
        roles = [r for r in reversed(guild.roles) if not r.is_default()]
        if not roles:
            return await interaction.response.send_message("No custom roles found.", ephemeral=True)

        pages = []
        chunk_size = 15
        for i in range(0, len(roles), chunk_size):
            chunk = roles[i : i + chunk_size]
            embed = primary_embed(title=f"📜 Roles in {guild.name} ({len(roles)} total)")
            lines = [f"`{r.position}.` {r.mention} — `{len(r.members)} members`" for r in chunk]
            embed.description = "\n".join(lines)
            pages.append(embed)

        if len(pages) == 1:
            await interaction.response.send_message(embed=pages[0])
        else:
            view = PaginatorView(pages, interaction.user.id)
            await interaction.response.send_message(embed=pages[0], view=view)

    @role_group.command(name="color", description="Change a role's color")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.describe(role="Role to modify", hex_color="New hex color (e.g. #00FFAA)")
    async def role_color(self, interaction: discord.Interaction, role: discord.Role, hex_color: str):
        allowed, error_msg = check_role_hierarchy(interaction.user, role, interaction.guild.me)
        if not allowed:
            return await interaction.response.send_message(embed=error_embed("Permission Denied", error_msg), ephemeral=True)

        clean_hex = hex_color.strip().lstrip("#")
        if not re.match(r"^[0-9a-fA-F]{6}$", clean_hex):
            return await interaction.response.send_message(embed=error_embed("Invalid Color", "Please enter a valid 6-character hex code."), ephemeral=True)

        new_color = discord.Color(int(clean_hex, 16))
        await role.edit(color=new_color, reason=f"Color updated by {interaction.user}")
        await interaction.response.send_message(
            embed=success_embed("Role Color Updated", f"Changed color of {role.mention} to `#{clean_hex}`.")
        )

    @role_group.command(name="panel_create", description="Create an interactive Button Role panel for members to self-assign roles")
    @has_admin_or_owner()
    @app_commands.describe(
        title="Panel Embed Title",
        description="Instructions for users",
        role="The role to toggle with the button",
        button_label="Label shown on the button",
        button_emoji="Emoji on the button",
    )
    async def panel_create(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str,
        role: discord.Role,
        button_label: str = "Get Role",
        button_emoji: Optional[str] = "🏷️",
    ):
        allowed, error_msg = check_role_hierarchy(interaction.user, role, interaction.guild.me)
        if not allowed:
            return await interaction.response.send_message(embed=error_embed("Permission Denied", error_msg), ephemeral=True)

        embed = primary_embed(title=title, description=description)
        embed.set_footer(text="Click the button to claim or remove this role.")

        view = DynamicRolePanelView()
        btn = DynamicRoleButton(role.id, label=button_label, emoji=button_emoji)
        view.add_item(btn)

        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message(
            embed=success_embed("Self-Role Panel Created", f"Panel for {role.mention} is live!"),
            ephemeral=True,
        )

    @role_group.command(name="autorole", description="Configure roles automatically given to new members")
    @has_admin_or_owner()
    @app_commands.choices(action=[
        app_commands.Choice(name="Add Autorole", value="add"),
        app_commands.Choice(name="Remove Autorole", value="remove"),
        app_commands.Choice(name="List Autoroles", value="list"),
    ])
    async def role_autorole(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        role: Optional[discord.Role] = None,
    ):
        guild = interaction.guild
        if action.value == "list":
            rows = await db.fetchall("SELECT role_id FROM auto_roles WHERE guild_id = ?", (guild.id,))
            if not rows:
                return await interaction.response.send_message("No autoroles currently set.", ephemeral=True)
            mentions = [f"• <@&{r['role_id']}>" for r in rows]
            embed = primary_embed(title="🤖 Active Join Autoroles", description="\n".join(mentions))
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if not role:
            return await interaction.response.send_message("Please specify a role.", ephemeral=True)

        if action.value == "add":
            await db.execute(
                "INSERT OR IGNORE INTO auto_roles (guild_id, role_id) VALUES (?, ?)",
                (guild.id, role.id),
            )
            await interaction.response.send_message(
                embed=success_embed("Autorole Added", f"{role.mention} will now be granted to new members."),
                ephemeral=True,
            )
        else:
            await db.execute(
                "DELETE FROM auto_roles WHERE guild_id = ? AND role_id = ?",
                (guild.id, role.id),
            )
            await interaction.response.send_message(
                embed=warning_embed("Autorole Removed", f"{role.mention} removed from autoroles."),
                ephemeral=True,
            )

    # ==================== PREFIX COMMAND SUITE ====================

    @commands.group(name="role", invoke_without_command=True)
    @commands.has_permissions(manage_roles=True)
    async def prefix_role(self, ctx: commands.Context):
        """Role management prefix commands."""
        embed = primary_embed(
            title="🛡️ Role Management Suite",
            description=(
                f"• `{BOT_PREFIX}role create [name]` — Open Stylish Role Creation Wizard (Font + Channels + Permissions)\n"
                f"• `{BOT_PREFIX}role add <@user> <@role>` — Assign role to member\n"
                f"• `{BOT_PREFIX}role remove <@user> <@role>` — Remove role from member\n"
                f"• `{BOT_PREFIX}role list` — List server roles in hierarchy order\n"
                f"• `{BOT_PREFIX}role color <@role> <#hex>` — Change role color\n"
                f"• `{BOT_PREFIX}role info <@role>` — Inspect role permissions & metadata\n"
            )
        )
        await ctx.send(embed=embed)

    @prefix_role.command(name="create", aliases=["new", "stylish", "wizard"])
    @commands.has_permissions(manage_roles=True)
    async def prefix_role_create(self, ctx: commands.Context, *, name: Optional[str] = None):
        """Interactive Stylish Role Creation Wizard via n!role create."""
        await self.launch_wizard(ctx_or_interaction=ctx, name=name)

    @prefix_role.command(name="add")
    @commands.has_permissions(manage_roles=True)
    async def prefix_role_add(self, ctx: commands.Context, member: discord.Member, role: discord.Role):
        """Assign a role to a member."""
        allowed, error_msg = check_role_hierarchy(ctx.author, role, ctx.guild.me)
        if not allowed:
            return await ctx.send(embed=error_embed("Permission Denied", error_msg))

        if role in member.roles:
            return await ctx.send(embed=warning_embed("Already Has Role", f"{member.mention} already has {role.mention}."))

        try:
            await member.add_roles(role, reason=f"Assigned by {ctx.author}")
            await ctx.send(embed=success_embed("Role Added", f"Assigned {role.mention} to {member.mention}."))
        except discord.Forbidden:
            await ctx.send(embed=error_embed("Error", "Bot lacks permissions to assign this role."))

    @prefix_role.command(name="remove")
    @commands.has_permissions(manage_roles=True)
    async def prefix_role_remove(self, ctx: commands.Context, member: discord.Member, role: discord.Role):
        """Remove a role from a member."""
        allowed, error_msg = check_role_hierarchy(ctx.author, role, ctx.guild.me)
        if not allowed:
            return await ctx.send(embed=error_embed("Permission Denied", error_msg))

        if role not in member.roles:
            return await ctx.send(embed=warning_embed("Role Not Present", f"{member.mention} does not have {role.mention}."))

        try:
            await member.remove_roles(role, reason=f"Removed by {ctx.author}")
            await ctx.send(embed=success_embed("Role Removed", f"Removed {role.mention} from {member.mention}."))
        except discord.Forbidden:
            await ctx.send(embed=error_embed("Error", "Bot lacks permissions to remove this role."))

    @prefix_role.command(name="list")
    async def prefix_role_list(self, ctx: commands.Context):
        """List server roles in hierarchy order."""
        roles = [r for r in reversed(ctx.guild.roles) if not r.is_default()]
        if not roles:
            return await ctx.send("No custom roles found.")

        pages = []
        chunk_size = 15
        for i in range(0, len(roles), chunk_size):
            chunk = roles[i : i + chunk_size]
            embed = primary_embed(title=f"📜 Roles in {ctx.guild.name} ({len(roles)} total)")
            lines = [f"`{r.position}.` {r.mention} — `{len(r.members)} members`" for r in chunk]
            embed.description = "\n".join(lines)
            pages.append(embed)

        if len(pages) == 1:
            await ctx.send(embed=pages[0])
        else:
            view = PaginatorView(pages, ctx.author.id)
            await ctx.send(embed=pages[0], view=view)

    @prefix_role.command(name="color")
    @commands.has_permissions(manage_roles=True)
    async def prefix_role_color(self, ctx: commands.Context, role: discord.Role, hex_color: str):
        """Change a role's color."""
        allowed, error_msg = check_role_hierarchy(ctx.author, role, ctx.guild.me)
        if not allowed:
            return await ctx.send(embed=error_embed("Permission Denied", error_msg))

        clean_hex = hex_color.strip().lstrip("#")
        if not re.match(r"^[0-9a-fA-F]{6}$", clean_hex):
            return await ctx.send(embed=error_embed("Invalid Color", "Please enter a valid 6-character hex code."))

        new_color = discord.Color(int(clean_hex, 16))
        await role.edit(color=new_color, reason=f"Color updated by {ctx.author}")
        await ctx.send(embed=success_embed("Role Color Updated", f"Changed color of {role.mention} to `#{clean_hex}`."))

    @prefix_role.command(name="info")
    async def prefix_role_info(self, ctx: commands.Context, role: discord.Role):
        """Inspect role details and key permissions."""
        embed = primary_embed(title=f"Role Information: @{role.name}")
        embed.color = role.color.value if role.color.value != 0 else discord.Color.blurple().value
        embed.add_field(name="ID", value=str(role.id), inline=True)
        embed.add_field(name="Color Hex", value=str(role.color), inline=True)
        embed.add_field(name="Position", value=str(role.position), inline=True)
        embed.add_field(name="Members with Role", value=str(len(role.members)), inline=True)
        embed.add_field(name="Hoisted (Separated)", value="Yes" if role.hoist else "No", inline=True)
        embed.add_field(name="Mentionable", value="Yes" if role.mentionable else "No", inline=True)
        embed.add_field(name="Created At", value=role.created_at.strftime("%b %d, %Y"), inline=True)

        key_perms = []
        if role.permissions.administrator:
            key_perms.append("Administrator")
        if role.permissions.manage_guild:
            key_perms.append("Manage Server")
        if role.permissions.manage_roles:
            key_perms.append("Manage Roles")
        if role.permissions.manage_channels:
            key_perms.append("Manage Channels")
        if role.permissions.ban_members:
            key_perms.append("Ban Members")
        if role.permissions.kick_members:
            key_perms.append("Kick Members")

        embed.add_field(name="Key Permissions", value=", ".join(key_perms) or "Standard Permissions", inline=False)
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Roles(bot))
