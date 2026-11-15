import discord
from discord import app_commands
from config import OWNER_IDS
from typing import Optional, Tuple


def is_bot_owner(user_id: int) -> bool:
    """Check if a Discord user ID belongs to the bot owner."""
    return user_id in OWNER_IDS


def check_hierarchy(
    moderator: discord.Member,
    target: discord.Member,
    bot_member: discord.Member,
) -> Tuple[bool, Optional[str]]:
    """Validate role hierarchy for moderation actions.
    
    Returns (True, None) if action is allowed, or (False, error_message).
    """
    if target.id == moderator.id:
        return False, "You cannot perform this moderation action on yourself."

    if target.id == moderator.guild.owner_id:
        return False, "You cannot perform moderation actions on the Server Owner."

    if moderator.id != moderator.guild.owner_id:
        if moderator.top_role <= target.top_role:
            return False, f"You cannot moderate {target.mention} because their highest role is equal to or higher than yours."

    if bot_member.top_role <= target.top_role:
        return False, f"I cannot moderate {target.mention} because my highest role is equal to or lower than theirs."

    return True, None


def check_role_hierarchy(
    executor: discord.Member,
    role: discord.Role,
    bot_member: discord.Member,
) -> Tuple[bool, Optional[str]]:
    """Validate if an executor and bot can manage/assign a specific role."""
    if role.is_default():
        return False, "Cannot modify the @everyone role."

    if role.managed:
        return False, "Cannot modify an integrated / bot-managed role."

    if executor.id != executor.guild.owner_id and executor.top_role <= role:
        return False, f"You cannot manage the role {role.name} because it is higher than or equal to your highest role."

    if bot_member.top_role <= role:
        return False, f"I cannot manage the role {role.name} because it is higher than or equal to my highest role."

    return True, None


def has_admin_or_owner():
    """Slash command check: User must be server owner or have Administrator permission."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.guild:
            return False
        if is_bot_owner(interaction.user.id) or interaction.user.id == interaction.guild.owner_id:
            return True
        if isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator:
            return True
        raise app_commands.AppCommandError("You need Administrator permissions to use this command.")
    return app_commands.check(predicate)

