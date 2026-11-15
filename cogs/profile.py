import discord
from discord.ext import commands
from discord import app_commands
import logging
import re
from typing import Optional
from database.database import db
from utils.embeds import primary_embed, success_embed, error_embed, info_embed
from utils.image_generator import generate_profile_card

logger = logging.getLogger("novexa.profile")


class Profile(commands.Cog):
    """User Profile Customization & Identity Suite."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="profile", description="View custom graphic profile card with rank and statistics")
    @app_commands.describe(user="The user whose profile you want to view")
    async def profile_cmd(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        target = user or interaction.user
        if not isinstance(target, discord.Member):
            return await interaction.response.send_message("Invalid member.", ephemeral=True)

        await interaction.response.defer()

        # Fetch profile customizations
        prof = await db.fetchone(
            "SELECT * FROM user_profiles WHERE guild_id = ? AND user_id = ?",
            (interaction.guild_id, target.id),
        )
        bio = prof["bio"] if prof and prof["bio"] else "Hello! I am using Novexa."
        custom_color = prof["custom_color"] if prof and prof["custom_color"] else "#5865F2"
        custom_avatar = prof["custom_avatar_url"] if prof and prof["custom_avatar_url"] else ""
        custom_banner = prof["custom_banner_url"] if prof and prof["custom_banner_url"] else ""

        # Fetch Leveling data
        lvl_row = await db.fetchone(
            "SELECT xp, level FROM leveling WHERE guild_id = ? AND user_id = ?",
            (interaction.guild_id, target.id),
        )
        current_xp = lvl_row["xp"] if lvl_row else 0
        level = lvl_row["level"] if lvl_row else 0
        # Calculate XP needed for next level: 100 * ((level + 1) ** 1.5)
        xp_next = int(100 * ((level + 1) ** 1.5))

        # Fetch Rank
        rank_row = await db.fetchone(
            "SELECT COUNT(*) as rank FROM leveling WHERE guild_id = ? AND xp > ?",
            (interaction.guild_id, current_xp),
        )
        rank = (rank_row["rank"] if rank_row else 0) + 1

        # Fetch Economy & RPG user profile
        from services.economy_service import economy_service, CURRENCY_NAME, CURRENCY_SYMBOL, GEM_SYMBOL
        eco_user = await economy_service.get_or_create_user(interaction.guild_id, target.id)

        wallet = eco_user["wallet"]
        bank = eco_user["bank"]
        total_wealth = wallet + bank
        gems = eco_user["gems"]
        rep = eco_user["reputation"]
        streak = eco_user["daily_streak"]
        hunts = eco_user["hunts_count"]
        battles_won = eco_user["battles_won"]
        battles_lost = eco_user["battles_lost"]

        # Fetch relationship / marriage
        rel = await economy_service.get_relationship(interaction.guild_id, target.id)
        partner_str = f"💍 Married to <@{rel['partner_id']}>" if rel else "Single"

        # Fetch active pet & weapon
        equipped_pet = await economy_service.get_equipped_pet(interaction.guild_id, target.id)
        pet_str = f"{equipped_pet['emoji']} **{equipped_pet['nickname']}** (Lvl {equipped_pet['level']})" if equipped_pet else "None"

        equipped_items = await economy_service.get_equipped_items(interaction.guild_id, target.id)
        wep = equipped_items.get("weapon")
        wep_str = f"{wep['icon']} **{wep['name']}**" if wep else "None"

        # Fetch zoo counts
        zoo_row = await db.fetchone(
            "SELECT COUNT(DISTINCT animal_id) as species, SUM(count) as total FROM economy_user_animals WHERE guild_id = ? AND user_id = ?",
            (interaction.guild_id, target.id),
        )
        zoo_total = zoo_row["total"] if zoo_row and zoo_row["total"] else 0
        zoo_species = zoo_row["species"] if zoo_row and zoo_row["species"] else 0

        # Fetch achievements count
        ach_row = await db.fetchone(
            "SELECT COUNT(*) as count FROM economy_user_achievements WHERE guild_id = ? AND user_id = ?",
            (interaction.guild_id, target.id),
        )
        ach_count = ach_row["count"] if ach_row else 0

        embed = primary_embed(title=f"👑 NOVEXA PROFILE — {target.display_name}")
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="💰 Wealth", value=f"• Wallet: **{wallet:,}** {CURRENCY_SYMBOL}\n• Bank: **{bank:,}** {CURRENCY_SYMBOL}\n• Total: **{total_wealth:,}** {CURRENCY_NAME}\n• Gems: **{gems:,}** {GEM_SYMBOL}", inline=True)
        embed.add_field(name="⭐ Level & Rank", value=f"• Server Rank: **#{rank}**\n• Level: **Lvl {level}**\n• Total XP: **{current_xp:,}**\n• Next Lvl: **{xp_next:,}**", inline=True)
        embed.add_field(name="🐾 Safari & Zoo", value=f"• Hunts Done: **{hunts:,}**\n• Animals: **{zoo_total:,}** ({zoo_species} species)\n• Active Pet: {pet_str}\n• Equipped: {wep_str}", inline=True)
        embed.add_field(name="⚔️ Arena Combat", value=f"• Victories: **{battles_won:,}** 🏆\n• Defeats: **{battles_lost:,}** 💀", inline=True)
        embed.add_field(name="🌟 Social Status", value=f"• Reputation: **+{rep:,}**\n• Daily Streak: **{streak} Days** 🔥\n• Partner: {partner_str}\n• Achievements: **{ach_count} Unlocked** 🏆", inline=True)
        embed.add_field(name="📝 Bio", value=f"*{bio}*", inline=False)

        # Generate Profile Card Graphic if available
        try:
            card_file = await generate_profile_card(
                member=target,
                level=level,
                xp=current_xp,
                xp_next=xp_next,
                rank=rank,
                wallet=wallet,
                bio=bio,
                custom_color=custom_color,
                custom_avatar_url=custom_avatar,
                custom_banner_url=custom_banner,
            )
            embed.set_image(url=f"attachment://{card_file.filename}")
            await interaction.followup.send(embed=embed, file=card_file)
        except Exception as e:
            logger.warning(f"Image generator unavailable, sending rich profile embed: {e}")
            await interaction.followup.send(embed=embed)

    profile_custom = app_commands.Group(name="profile-set", description="Customize profile card bio, colors, and visuals")

    @profile_custom.command(name="bio", description="Update your personal bio displayed on your profile card")
    @app_commands.describe(bio="Your new biography (up to 120 characters)")
    async def setbio(self, interaction: discord.Interaction, bio: str):
        if len(bio) > 120:
            return await interaction.response.send_message(
                embed=error_embed("Bio Too Long", "Please keep your bio within 120 characters."),
                ephemeral=True,
            )

        await db.execute(
            """
            INSERT INTO user_profiles (guild_id, user_id, bio)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET bio = excluded.bio
            """,
            (interaction.guild_id, interaction.user.id, bio),
        )
        await interaction.response.send_message(
            embed=success_embed("Bio Updated", f"Your new bio:\n*{bio}*"),
            ephemeral=True,
        )

    @profile_custom.command(name="color", description="Set custom accent color for your profile card")
    @app_commands.describe(hex_code="Hex color code (e.g. #5865F2, #FF0055, #00FFCC)")
    async def setcolor(self, interaction: discord.Interaction, hex_code: str):
        hex_code = hex_code.strip()
        if not hex_code.startswith("#"):
            hex_code = f"#{hex_code}"

        if not re.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$", hex_code):
            return await interaction.response.send_message(
                embed=error_embed("Invalid Hex", "Please enter a valid 6-character hex code, e.g. `#5865F2`."),
                ephemeral=True,
            )

        await db.execute(
            """
            INSERT INTO user_profiles (guild_id, user_id, custom_color)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET custom_color = excluded.custom_color
            """,
            (interaction.guild_id, interaction.user.id, hex_code),
        )
        await interaction.response.send_message(
            embed=success_embed("Color Updated", f"Your profile accent color has been set to `{hex_code}`."),
            ephemeral=True,
        )

    @profile_custom.command(name="avatar", description="Set a custom avatar for your bot profile card")
    @app_commands.describe(
        image="Upload an image file for your profile card",
        image_url="Direct image link (PNG/JPG)"
    )
    async def setavatar(
        self,
        interaction: discord.Interaction,
        image: Optional[discord.Attachment] = None,
        image_url: Optional[str] = None,
    ):
        target_url = image.url if image else image_url
        if not target_url:
            return await interaction.response.send_message(
                embed=error_embed("Missing Image", "Please attach an image or provide an image URL."),
                ephemeral=True,
            )

        await db.execute(
            """
            INSERT INTO user_profiles (guild_id, user_id, custom_avatar_url)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET custom_avatar_url = excluded.custom_avatar_url
            """,
            (interaction.guild_id, interaction.user.id, target_url),
        )
        await interaction.response.send_message(
            embed=success_embed("Profile Avatar Updated", "Your custom profile card avatar has been set!"),
            ephemeral=True,
        )

    @profile_custom.command(name="banner", description="Set a custom banner for your bot profile card")
    @app_commands.describe(
        image="Upload a banner image file for your profile card",
        image_url="Direct image link (PNG/JPG)"
    )
    async def setbanner(
        self,
        interaction: discord.Interaction,
        image: Optional[discord.Attachment] = None,
        image_url: Optional[str] = None,
    ):
        target_url = image.url if image else image_url
        if not target_url:
            return await interaction.response.send_message(
                embed=error_embed("Missing Image", "Please attach a banner image or provide a banner image URL."),
                ephemeral=True,
            )

        await db.execute(
            """
            INSERT INTO user_profiles (guild_id, user_id, custom_banner_url)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET custom_banner_url = excluded.custom_banner_url
            """,
            (interaction.guild_id, interaction.user.id, target_url),
        )
        await interaction.response.send_message(
            embed=success_embed("Profile Banner Updated", "Your custom profile card banner has been set!"),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Profile(bot))

