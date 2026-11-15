"""NOVEXA - Dropper Role & Developer Channels Permission Management Suite.

Features:
- Dedicated Dropper Role Creation & Sync:
  - Role: "💧・Dropper" (or custom role)
  - Automatically identifies "DEVELOPER" category and developer channels
  - Configures safe permissions without dangerous admin privileges:
    • View Channel (Read Messages)
    • Send Messages & Send in Threads
    • Read Message History
    • Attach Files (Code / APK / ZIP / DLL / CS / Lib files)
    • Embed Links
    • Add Reactions
    • Use External Emojis & Use External Stickers
  - Explicitly leaves dangerous administrative permissions DISABLED:
    • No Administrator
    • No Manage Server
    • No Manage Channels
    • No Manage Roles
    • No Manage Webhooks / Bots
    • No Kick / Ban
- Slash Commands:
  - `/dropper setup` -> Automatically creates role & configures developer category/channels
  - `/dropper add`   -> Assigns dropper role to a member with confirmation
  - `/dropper remove`-> Removes dropper role from a member
  - `/dropper list`  -> Lists all configured droppers and channels
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
import json
import re
from typing import Optional, Union, Tuple

from database.database import db
from utils.embeds import primary_embed, success_embed, error_embed, warning_embed, info_embed
from utils.permissions import has_admin_or_owner

logger = logging.getLogger("novexa.dropper")

COLOR_DROPPER = 0x3498DB  # Aesthetic Blue


async def apply_dropper_permissions(
    channel_or_category: Union[discord.abc.GuildChannel, discord.CategoryChannel, discord.TextChannel],
    dropper_role: discord.Role,
    reason: str = "NOVEXA Dropper Developer Permissions",
) -> bool:
    """Apply safe file-sharing & messaging permissions for Developer channels without any admin perms."""
    try:
        # Category overwrite
        if isinstance(channel_or_category, discord.CategoryChannel):
            cat_ow = channel_or_category.overwrites_for(dropper_role)
            cat_ow.view_channel = True
            cat_ow.read_messages = True
            cat_ow.read_message_history = True
            cat_ow.send_messages = True
            cat_ow.send_messages_in_threads = True
            cat_ow.embed_links = True
            cat_ow.attach_files = True
            cat_ow.add_reactions = True
            cat_ow.use_external_emojis = True
            cat_ow.use_external_stickers = True
            await channel_or_category.set_permissions(dropper_role, overwrite=cat_ow, reason=reason)

            # Apply to child channels
            for child in channel_or_category.channels:
                child_ow = child.overwrites_for(dropper_role)
                child_ow.view_channel = True
                child_ow.read_messages = True
                child_ow.read_message_history = True
                child_ow.send_messages = True
                child_ow.send_messages_in_threads = True
                child_ow.embed_links = True
                child_ow.attach_files = True
                child_ow.add_reactions = True
                child_ow.use_external_emojis = True
                child_ow.use_external_stickers = True
                await child.set_permissions(dropper_role, overwrite=child_ow, reason=reason)
            return True

        # TextChannel overwrite
        if getattr(channel_or_category, "category", None):
            parent_cat = channel_or_category.category
            cat_ow = parent_cat.overwrites_for(dropper_role)
            if not cat_ow.view_channel:
                cat_ow.view_channel = True
                await parent_cat.set_permissions(dropper_role, overwrite=cat_ow, reason=f"{reason} (Category View)")

        ow = channel_or_category.overwrites_for(dropper_role)
        ow.view_channel = True
        ow.read_messages = True
        ow.read_message_history = True
        ow.send_messages = True
        ow.send_messages_in_threads = True
        ow.embed_links = True
        ow.attach_files = True
        ow.add_reactions = True
        ow.use_external_emojis = True
        ow.use_external_stickers = True
        await channel_or_category.set_permissions(dropper_role, overwrite=ow, reason=reason)
        return True
    except Exception as e:
        logger.error(f"Error applying dropper permissions to {getattr(channel_or_category, 'name', 'Channel')}: {e}")
        return False


async def resolve_dropper_role(guild: discord.Guild) -> Optional[discord.Role]:
    """Configured Dropper role, falling back to any role with 'dropper' in the name."""
    cfg = await db.fetchone("SELECT role_id FROM dropper_config WHERE guild_id = ?", (guild.id,))
    if cfg and cfg["role_id"]:
        role = guild.get_role(cfg["role_id"])
        if role:
            return role
    for r in guild.roles:
        if "dropper" in r.name.lower():
            return r
    return None


async def grant_dropper_role(
    guild: discord.Guild,
    member: discord.Member,
    actor: Union[discord.Member, discord.User],
) -> Tuple[bool, str]:
    """Assign the Dropper role and record it. Returns (ok, human message)."""
    if member.bot:
        return False, "Bots cannot be given the Dropper role."

    role = await resolve_dropper_role(guild)
    if not role:
        return False, "No Dropper role is configured yet. An admin must run `/dropper setup` first."
    if guild.me and role >= guild.me.top_role:
        return False, f"{role.mention} sits above my role, so I cannot assign it."
    if role in member.roles:
        return True, f"{member.mention} already has {role.mention}."

    try:
        await member.add_roles(role, reason=f"[NOVEXA Dropper] granted by {actor}")
    except discord.Forbidden:
        return False, f"I lack permission to assign {role.mention}."

    await db.execute(
        """
        INSERT INTO server_droppers (guild_id, user_id, added_by)
        VALUES (?, ?, ?)
        ON CONFLICT(guild_id, user_id) DO UPDATE SET added_by = excluded.added_by
        """,
        (guild.id, member.id, actor.id),
    )
    return True, (
        f"{member.mention} now has {role.mention} — upload access to Developer channels granted."
    )


async def revoke_dropper_role(guild, member, actor) -> Tuple[bool, str]:
    """Remove the Dropper role from a member and clear their database record."""
    role = await resolve_dropper_role(guild)
    if role and role in member.roles:
        try:
            await member.remove_roles(role, reason=f"[NOVEXA Dropper] revoked by {actor}")
        except discord.Forbidden:
            return False, f"I cannot remove {role.mention} because it sits above my role."
    await db.execute(
        "DELETE FROM server_droppers WHERE guild_id = ? AND user_id = ?",
        (guild.id, member.id),
    )
    return True, f"Removed Dropper permissions from {member.mention}."


class Dropper(commands.Cog):
    """Dropper Role & Developer Channels Permission Management Suite."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    dropper_group = app_commands.Group(
        name="dropper",
        description="Dropper Role & Developer Channels Suite",
    )

    # ---------------- /dropper setup ----------------
    @dropper_group.command(
        name="setup",
        description="Setup Dropper role and apply safe upload/link perms to Developer channels",
    )
    @app_commands.describe(
        role="Select existing role or leave empty to auto-create '💧・Dropper'",
        category="Target category (defaults to DEVELOPER category if found)",
    )
    @has_admin_or_owner()
    async def slash_dropper_setup(
        self,
        interaction: discord.Interaction,
        role: Optional[discord.Role] = None,
        category: Optional[discord.CategoryChannel] = None,
    ):
        await interaction.response.defer(ephemeral=False)
        guild = interaction.guild

        # 1. Resolve or Create Dropper Role
        dropper_role = role
        if not dropper_role:
            for r in guild.roles:
                if r.name.lower() in ("💧・dropper", "dropper", "💧 dropper"):
                    dropper_role = r
                    break

        if not dropper_role:
            try:
                dropper_role = await guild.create_role(
                    name="💧・Dropper",
                    color=discord.Color(COLOR_DROPPER),
                    mentionable=True,
                    reason="Auto-created by NOVEXA Dropper Suite",
                )
            except Exception as e:
                return await interaction.followup.send(
                    embed=error_embed("Role Creation Failed", f"Could not create Dropper role: `{e}`")
                )

        # 2. Find Developer Category
        target_cat = category
        if not target_cat:
            for cat in guild.categories:
                if "dev" in cat.name.lower() or "drop" in cat.name.lower():
                    target_cat = cat
                    break

        applied_count = 0
        cat_id = None
        chan_ids = []

        if target_cat:
            cat_id = target_cat.id
            success = await apply_dropper_permissions(target_cat, dropper_role)
            if success:
                applied_count = len(target_cat.channels)
                chan_ids = [c.id for c in target_cat.channels]
        else:
            # Fallback: scan channels containing code/free/dll/script keywords
            for ch in guild.text_channels:
                if any(k in ch.name.lower() for k in ("code", "dll", "dump", "file", "method", "project", "tool")):
                    await apply_dropper_permissions(ch, dropper_role)
                    chan_ids.append(ch.id)
                    applied_count += 1

        # 3. Save to database
        await db.execute(
            """
            INSERT INTO dropper_config (guild_id, role_id, category_id, channels_list)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                role_id = excluded.role_id,
                category_id = excluded.category_id,
                channels_list = excluded.channels_list
            """,
            (guild.id, dropper_role.id, cat_id, json.dumps(chan_ids)),
        )

        embed = success_embed(
            "💧 Dropper Role Configured",
            f"**Role:** {dropper_role.mention}\n"
            f"**Target Area:** {target_cat.name if target_cat else 'Detected Developer Channels'}\n"
            f"**Channels Synced:** `{applied_count}` channels\n\n"
            f"**Allowed Permissions:**\n"
            f"• 📁 Attach Files (Code / APK / DLL / CS / Lib files)\n"
            f"• 🔗 Embed Links\n"
            f"• 💬 Send Messages & Threads\n"
            f"• 🎨 External Emojis & Stickers\n"
            f"• 👀 View & Message History\n\n"
            f"🔒 **Security Guarantee:** No Administrator or Server Management permissions were granted.",
        )
        await interaction.followup.send(embed=embed)

    # ---------------- /dropper add ----------------
    @dropper_group.command(
        name="add",
        description="Assign the Dropper role to a member with upload access to Developer channels",
    )
    @app_commands.describe(member="Member to promote to Dropper")
    @has_admin_or_owner()
    async def slash_dropper_add(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer(ephemeral=False)
        guild = interaction.guild

        # 1. Fetch Config
        cfg = await db.fetchone("SELECT * FROM dropper_config WHERE guild_id = ?", (guild.id,))
        role = None
        if cfg and cfg["role_id"]:
            role = guild.get_role(cfg["role_id"])

        if not role:
            for r in guild.roles:
                if "dropper" in r.name.lower():
                    role = r
                    break

        if not role:
            return await interaction.followup.send(
                embed=error_embed(
                    "Dropper Not Setup",
                    "No Dropper role found! Run `/dropper setup` first to configure.",
                )
            )

        if role in member.roles:
            return await interaction.followup.send(
                embed=info_embed("Already Dropper", f"{member.mention} already has the {role.mention} role.")
            )

        try:
            await member.add_roles(role, reason=f"Added as Dropper by {interaction.user}")
        except discord.Forbidden:
            return await interaction.followup.send(
                embed=error_embed(
                    "Hierarchy Error",
                    f"I cannot assign {role.mention} because it is placed higher than my bot role in server settings.",
                )
            )

        # 2. Record in database
        await db.execute(
            """
            INSERT INTO server_droppers (guild_id, user_id, added_by)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET added_by = excluded.added_by
            """,
            (guild.id, member.id, interaction.user.id),
        )

        embed = success_embed(
            "💧 Dropper Role Assigned",
            f"{member.mention} has been given {role.mention}!\n\n"
            f"**Privileges:**\n"
            f"• Can post scripts, codes, zip/apk/dll files, links & stickers in Developer channels.\n"
            f"• No administrative or bot-adding permissions.",
        )
        await interaction.followup.send(embed=embed)

    # ---------------- /dropper remove ----------------
    @dropper_group.command(
        name="remove",
        description="Remove Dropper role and developer channel access from a member",
    )
    @app_commands.describe(member="Member to remove Dropper role from")
    @has_admin_or_owner()
    async def slash_dropper_remove(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer(ephemeral=False)
        ok, message = await revoke_dropper_role(interaction.guild, member, interaction.user)
        if not ok:
            return await interaction.followup.send(embed=error_embed("Hierarchy Error", message))
        embed = success_embed(
            "💧 Dropper Role Removed",
            f"Removed Dropper permissions and role from {member.mention}.",
        )
        await interaction.followup.send(embed=embed)

    # ---------------- /dropper list ----------------
    @dropper_group.command(
        name="list",
        description="List all active Droppers and configured developer channels",
    )
    async def slash_dropper_list(self, interaction: discord.Interaction):
        guild = interaction.guild
        cfg = await db.fetchone("SELECT * FROM dropper_config WHERE guild_id = ?", (guild.id,))
        rows = await db.fetchall("SELECT * FROM server_droppers WHERE guild_id = ?", (guild.id,))

        role_str = "`Not configured`"
        if cfg and cfg["role_id"]:
            r = guild.get_role(cfg["role_id"])
            if r:
                role_str = r.mention

        dropper_list = []
        for row in rows:
            m = guild.get_member(row["user_id"])
            if m:
                dropper_list.append(f"• {m.mention} (`{m.id}`)")
            else:
                dropper_list.append(f"• `<Left Server>` (`{row['user_id']}`)")

        desc = f"**Dropper Role:** {role_str}\n\n"
        if dropper_list:
            desc += "**Active Droppers:**\n" + "\n".join(dropper_list)
        else:
            desc += "*No members currently assigned to Dropper role.*"

        embed = primary_embed("💧 Dropper Suite Status", desc)
        await interaction.response.send_message(embed=embed)

    # ---------------- PREFIX: dropper @user ----------------
    @commands.command(name="dropper")
    @commands.has_permissions(manage_roles=True)
    async def prefix_dropper(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        """Shorthand: `dropper @user` assigns the Dropper role in one step."""
        if member is None:
            role = await resolve_dropper_role(ctx.guild)
            return await ctx.send(
                f"Usage: `n!dropper @user`\n"
                f"Current Dropper role: {role.mention if role else '*not configured*'}"
            )

        if member == ctx.author:
            return await ctx.send("You cannot give yourself the Dropper role.", delete_after=10)

        ok, text = await grant_dropper_role(ctx.guild, member, ctx.author)
        await ctx.send(text, mention_author=False)

    # ---------------- TICKET AUTO-GRANT ----------------
    _REQUEST_PATTERNS = (
        re.compile(r"\bdropper\b", re.IGNORECASE),
        re.compile(r"\bdrop\s+role\b", re.IGNORECASE),
    )
    _GRANT_PATTERN = re.compile(r"^dropper\s+<@!?(\d+)>", re.IGNORECASE)

    def _asks_for_dropper(self, content: str) -> bool:
        return any(p.search(content) for p in self._REQUEST_PATTERNS)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Inside an open ticket: requester asks for Dropper -> auto-grant.
        Support staff typing `dropper @user` -> grant to that member."""
        if not message.guild or message.author.bot:
            return
        content = message.content.strip()
        if not content or "dropper" not in content.lower():
            return

        ticket = await db.fetchone(
            "SELECT author_id, status FROM tickets WHERE channel_id = ?",
            (message.channel.id,),
        )
        if not ticket or ticket["status"] != "open":
            return

        grant_match = self._GRANT_PATTERN.match(content)
        if grant_match:
            if not message.author.guild_permissions.manage_roles:
                return
            target = message.guild.get_member(int(grant_match.group(1)))
            if not target:
                return await message.reply("Member not found in this server.", mention_author=False)
            ok, text = await grant_dropper_role(message.guild, target, message.author)
            return await message.reply(text, mention_author=False)

        if message.author.id != ticket["author_id"]:
            return
        if not self._asks_for_dropper(content):
            return
        ok, text = await grant_dropper_role(message.guild, message.author, message.author)
        await message.reply(text, mention_author=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Dropper(bot))

