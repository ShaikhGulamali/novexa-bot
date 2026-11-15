"""NOVEXA - Pet Companion System Cog.

Features:
- Pet adoption from shelter catalog
- Pet feeding, happiness meters, XP progression and leveling
- Active companion equipping granting passive perks to hunting and combat
- Pet renaming and profile displays
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional, List
from database.database import db
from services.economy_service import (
    economy_service,
    CURRENCY_NAME,
    CURRENCY_SYMBOL,
)
from utils.economy_checks import (
    check_channel_allowed,
    economy_embed,
    COLOR_ECO_PRIMARY,
    COLOR_ECO_GOLD,
    COLOR_ECO_SUCCESS,
    COLOR_ECO_ERROR,
    COLOR_ECO_INFO,
)

logger = logging.getLogger("novexa.pets")


class Pets(commands.Cog):
    """NOVEXA Collectible Pet Companions."""

    pet_group = app_commands.Group(name="pet", description="Pet companion adoption, equipping, and training")

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @pet_group.command(name="list", description="View all pets you or another member have adopted")
    @app_commands.describe(user="Member whose pets to view")
    async def pets_list(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        if not await check_channel_allowed(interaction, "marketplace"):
            return

        target = user or interaction.user
        pets_list = await economy_service.get_user_pets(interaction.guild_id, target.id)

        if not pets_list:
            embed = economy_embed(
                f"🐾 Pet Menagerie - {target.display_name}",
                "No pets adopted yet! Run `/pet adopt` to adopt your first loyal companion.",
                COLOR_ECO_INFO,
            )
            return await interaction.response.send_message(embed=embed)

        embed = economy_embed(
            title=f"🐾 Pet Menagerie - {target.display_name} ({len(pets_list)} Companions)",
            color=COLOR_ECO_PRIMARY,
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        for p in pets_list:
            active_badge = " `[ACTIVE COMPANION]`" if p.get("is_equipped") else ""
            bonus_pct = round(p["bonus_value"] * p["level"], 1)
            bonus_label = p["bonus_type"].replace("_", " ").title()

            embed.add_field(
                name=f"{p['emoji']} {p['nickname']}{active_badge}",
                value=f"**Level:** {p['level']} (`{p['xp']}/{p['level'] * 100} XP`)\n"
                      f"**Happiness:** {p['happiness']}%\n"
                      f"**Active Perk:** +{bonus_pct}% {bonus_label}\n"
                      f"**Species:** `{p['pet_type']}` ({p['rarity']})",
                inline=False,
            )

        embed.set_footer(text="Use /pet equip <type> to set your active pet, and /pet feed to keep them happy!")
        await interaction.response.send_message(embed=embed)

    @pet_group.command(name="equipped", description="View detailed inspection of your currently active equipped pet")
    @app_commands.describe(user="Member to inspect")
    async def pet_equipped(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        if not await check_channel_allowed(interaction, "marketplace"):
            return

        target = user or interaction.user
        active = await economy_service.get_equipped_pet(interaction.guild_id, target.id)

        if not active:
            embed = economy_embed(
                f"🐾 Active Pet - {target.display_name}",
                "No pet is currently equipped! Run `/pet list` to view your pets, and `/pet equip <type>` to select one.",
                COLOR_ECO_INFO,
            )
            return await interaction.response.send_message(embed=embed)

        bonus_pct = round(active["bonus_value"] * active["level"], 1)
        bonus_name = active["bonus_type"].replace("_", " ").title()

        embed = economy_embed(
            title=f"{active['emoji']} Active Companion: {active['nickname']}",
            color=COLOR_ECO_GOLD,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="Level", value=f"⭐ **Lvl {active['level']}**", inline=True)
        embed.add_field(name="Experience", value=f"**{active['xp']} / {active['level'] * 100}** XP", inline=True)
        embed.add_field(name="Happiness", value=f"❤️ **{active['happiness']}%**", inline=True)
        embed.add_field(name="Combat & Safari Buff", value=f"✨ **+{bonus_pct}%** {bonus_name}", inline=False)
        embed.add_field(name="Species Rarity", value=f"`{active['rarity']}`", inline=True)
        embed.set_footer(text="Keep happiness above 50% with /pet feed to maintain full bonuses!")

        await interaction.response.send_message(embed=embed)

    @pet_group.command(name="adopt", description="Adopt a new pet companion into your collection (2,000 Coins)")
    @app_commands.describe(
        pet_type="Select pet species",
        nickname="Optional custom name for your pet",
    )
    @app_commands.choices(pet_type=[
        app_commands.Choice(name="🐕 Loyal Shiba Inu (+Hunt Luck)", value="pet_dog"),
        app_commands.Choice(name="🐱 Lucky Calico Cat (+Coin Boost)", value="pet_cat"),
        app_commands.Choice(name="🐺 Frost Direwolf (+Battle ATK)", value="pet_wolf"),
        app_commands.Choice(name="🦉 Mystic Astral Owl (+XP Boost)", value="pet_owl"),
        app_commands.Choice(name="🐻 Armored Bear (+Battle DEF)", value="pet_bear"),
        app_commands.Choice(name="🦊 Nine-Tailed Kitsune (+Hunt Luck & Crit)", value="pet_fox"),
        app_commands.Choice(name="🦅 Golden High Griffin (+Battle ATK & Coins)", value="pet_griffin"),
        app_commands.Choice(name="🔥 Immortal Solar Phoenix (+Battle ATK)", value="pet_phoenix"),
        app_commands.Choice(name="🐉 Novexa Void Wyrm (+All Stats)", value="pet_dragon"),
    ])
    async def adopt(
        self,
        interaction: discord.Interaction,
        pet_type: app_commands.Choice[str],
        nickname: Optional[str] = None,
    ):
        if not await check_channel_allowed(interaction, "marketplace"):
            return

        success, msg = await economy_service.adopt_pet(
            interaction.guild_id, interaction.user.id, pet_type.value, nickname
        )
        if success:
            embed = economy_embed("🎉 Adoption Finalized!", msg, COLOR_ECO_SUCCESS)
            await interaction.response.send_message(embed=embed)
        else:
            embed = economy_embed("❌ Adoption Failed", msg, COLOR_ECO_ERROR)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @pet_group.command(name="equip", description="Set a pet as your active companion to activate its bonuses")
    @app_commands.describe(pet_type="Pet type identifier (e.g. pet_dog, pet_wolf, pet_dragon)")
    async def pet_equip(self, interaction: discord.Interaction, pet_type: str):
        if not await check_channel_allowed(interaction, "marketplace"):
            return

        success, msg = await economy_service.equip_pet(interaction.guild_id, interaction.user.id, pet_type.lower().strip())
        if success:
            embed = economy_embed("🐾 Companion Set", msg, COLOR_ECO_SUCCESS)
            await interaction.response.send_message(embed=embed)
        else:
            embed = economy_embed("❌ Error", msg, COLOR_ECO_ERROR)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @pet_group.command(name="feed", description="Feed your pet Gourmet Pet Feast or 75 coins to restore happiness and grant XP")
    @app_commands.describe(pet_type="Pet species to feed")
    async def pet_feed(self, interaction: discord.Interaction, pet_type: str):
        if not await check_channel_allowed(interaction, "marketplace"):
            return

        success, msg = await economy_service.feed_pet(interaction.guild_id, interaction.user.id, pet_type.lower().strip())
        if success:
            embed = economy_embed("🍖 Feeding Time", msg, COLOR_ECO_SUCCESS)
            await interaction.response.send_message(embed=embed)
        else:
            embed = economy_embed("❌ Cannot Feed", msg, COLOR_ECO_ERROR)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @pet_group.command(name="rename", description="Rename an adopted pet in your menagerie")
    @app_commands.describe(pet_type="Pet species", new_name="New custom nickname for this pet")
    async def pet_rename(self, interaction: discord.Interaction, pet_type: str, new_name: str):
        if not await check_channel_allowed(interaction, "marketplace"):
            return

        success, msg = await economy_service.rename_pet(interaction.guild_id, interaction.user.id, pet_type.lower().strip(), new_name)
        if success:
            embed = economy_embed("🏷️ Pet Renamed", msg, COLOR_ECO_SUCCESS)
            await interaction.response.send_message(embed=embed)
        else:
            embed = economy_embed("❌ Rename Failed", msg, COLOR_ECO_ERROR)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @pet_group.command(name="info", description="View species profile, rarity, and base scaling for any pet")
    @app_commands.describe(pet="Pet species ID (e.g. pet_dog, pet_dragon, pet_phoenix)")
    async def pet_info(self, interaction: discord.Interaction, pet: str):
        row = await db.fetchone("SELECT * FROM economy_pets WHERE pet_type = ? OR LOWER(name) LIKE ?", (pet.lower().strip(), f"%{pet.lower()}%"))
        if not row:
            return await interaction.response.send_message(f"Pet species `{pet}` not found.", ephemeral=True)

        p = dict(row)
        embed = economy_embed(
            title=f"{p['emoji']} {p['name']} Pet Encyclopedia",
            description=p["description"],
            color=COLOR_ECO_PRIMARY,
        )
        embed.add_field(name="Species ID", value=f"`{p['pet_type']}`", inline=True)
        embed.add_field(name="Rarity", value=f"`{p['rarity']}`", inline=True)
        embed.add_field(name="Per-Level Scaling", value=f"+{p['bonus_value']}% {p['bonus_type'].replace('_', ' ').title()}", inline=True)
        await interaction.response.send_message(embed=embed)

    @pet_group.command(name="level", description="View XP progression status and requirements to level up your pet")
    @app_commands.describe(pet_type="Pet species")
    async def pet_level(self, interaction: discord.Interaction, pet_type: str):
        row = await db.fetchone(
            "SELECT * FROM economy_user_pets WHERE guild_id = ? AND user_id = ? AND pet_type = ?",
            (interaction.guild_id, interaction.user.id, pet_type.lower().strip()),
        )
        if not row:
            return await interaction.response.send_message(f"You don't own a pet of species `{pet_type}`.", ephemeral=True)

        p = dict(row)
        needed = p["level"] * 100
        embed = economy_embed(
            title=f"⭐ {p['nickname']} Level Progression",
            description=f"Current Level: **Level {p['level']}**\n"
                        f"XP Progress: **{p['xp']} / {needed} XP**\n"
                        f"Happiness: **{p['happiness']}%**\n\n"
                        f"*Feed your pet using `/pet feed {p['pet_type']}` to grant +25 XP per meal!*",
            color=COLOR_ECO_GOLD,
        )
        await interaction.response.send_message(embed=embed)

    # Prefix Commands for backward compatibility
    @commands.command(name="pets")
    async def prefix_pets(self, ctx: commands.Context, user: Optional[discord.Member] = None):
        target = user or ctx.author
        pets_list = await economy_service.get_user_pets(ctx.guild.id, target.id)
        if not pets_list:
            embed = economy_embed(f"🐾 Pet Menagerie - {target.display_name}", f"No pets adopted yet! Run `{BOT_PREFIX}adopt`.", COLOR_ECO_INFO)
            return await ctx.send(embed=embed)
        embed = economy_embed(title=f"🐾 Pet Menagerie - {target.display_name} ({len(pets_list)} Companions)", color=COLOR_ECO_PRIMARY)
        embed.set_thumbnail(url=target.display_avatar.url)
        for p in pets_list:
            active_badge = " `[ACTIVE COMPANION]`" if p.get("is_equipped") else ""
            bonus_pct = round(p["bonus_value"] * p["level"], 1)
            bonus_label = p["bonus_type"].replace("_", " ").title()
            embed.add_field(name=f"{p['emoji']} {p['nickname']}{active_badge}", value=f"**Level:** {p['level']} (`{p['xp']}/{p['level'] * 100} XP`)\n**Perk:** +{bonus_pct}% {bonus_label}", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="pet")
    async def prefix_pet(self, ctx: commands.Context, user: Optional[discord.Member] = None):
        target = user or ctx.author
        active = await economy_service.get_equipped_pet(ctx.guild.id, target.id)
        if not active:
            embed = economy_embed(f"🐾 Active Pet - {target.display_name}", f"No pet equipped! Run `{BOT_PREFIX}pets` to view.", COLOR_ECO_INFO)
            return await ctx.send(embed=embed)
        embed = economy_embed(title=f"{active['emoji']} Active Companion: {active['nickname']}", color=COLOR_ECO_GOLD)
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="Level", value=f"⭐ **Lvl {active['level']}**", inline=True)
        embed.add_field(name="Happiness", value=f"❤️ **{active['happiness']}%**", inline=True)
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Pets(bot))

