"""NOVEXA - Advanced Animal Hunting & Zoo System.

Features:
- 50+ diverse animals across Common, Uncommon, Rare, Epic, Legendary, Mythical
- Dynamic catch probabilities boosted by hunting weapons and pets
- Interactive Discord embed with buttons: [Hunt Again], [View Collection], [Animal Details], [Sell Duplicate]
- Strict user-validation and rate-limiting on interactive buttons to prevent spam/exploits
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
    format_remaining,
    economy_embed,
    COLOR_ECO_PRIMARY,
    COLOR_ECO_GOLD,
    COLOR_ECO_SUCCESS,
    COLOR_ECO_ERROR,
    COLOR_ECO_INFO,
)
from utils.helpers import PaginatorView

logger = logging.getLogger("novexa.hunt")

RARITY_COLORS = {
    "Common": 0x95A5A6,     # Gray
    "Uncommon": 0x2ECC71,   # Green
    "Rare": 0x3498DB,       # Blue
    "Epic": 0x9B59B6,       # Purple
    "Legendary": 0xF1C40F,  # Gold
    "Mythical": 0xE74C3C,   # Crimson Mythic
}


class HuntActionView(discord.ui.View):
    """Interactive Discord Action Buttons for Animal Hunts."""

    def __init__(self, author_id: int, guild_id: int, encounter: dict, is_duplicate: bool):
        super().__init__(timeout=90.0)
        self.author_id = author_id
        self.guild_id = guild_id
        self.encounter = encounter
        self.is_duplicate = is_duplicate

        # If not duplicate, disable Sell Duplicate button initially
        if not is_duplicate:
            self.sell_dupe_btn.disabled = True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ Only the hunter who initiated this hunt can use these buttons!",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="🎯 Hunt Again", style=discord.ButtonStyle.primary, custom_id="hunt_again")
    async def hunt_again_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Trigger another hunt
        res = await economy_service.hunt(self.guild_id, self.author_id)
        if not res["success"]:
            rem = format_remaining(res["remaining_seconds"])
            return await interaction.response.send_message(
                f"⏳ Hunting cooldown active! Wait **{rem}**.",
                ephemeral=True,
            )

        if not res["caught"]:
            embed = economy_embed(
                "🐾 Hunt Encounter: Escaped!",
                f"A wild **{res['encounter']['emoji']} {res['encounter']['name']}** appeared, but escaped into the wild!",
                COLOR_ECO_INFO,
            )
            view = HuntActionView(self.author_id, self.guild_id, res["encounter"], False)
            await interaction.response.edit_message(embed=embed, view=view)
            return

        enc = res["encounter"]
        color = RARITY_COLORS.get(enc["rarity"], COLOR_ECO_PRIMARY)
        embed = economy_embed(
            title=f"🎯 Hunt Successful! You caught a {enc['name']}!",
            color=color,
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="Animal", value=f"{enc['emoji']} **{enc['name']}**", inline=True)
        embed.add_field(name="Rarity", value=f"`{enc['rarity']}`", inline=True)
        embed.add_field(name="Sell Value", value=f"**{enc['base_value']:,}** {CURRENCY_SYMBOL}", inline=True)
        embed.add_field(name="XP Earned", value=f"**+{res['xp_gain']}** XP", inline=True)
        embed.add_field(name="Ability", value=f"✨ *{enc['ability']}*", inline=True)
        embed.add_field(name="In Zoo", value=f"**{res['count']} Owned**" + (" *(Duplicate)*" if res["is_duplicate"] else " *(New!)*"), inline=True)
        embed.description = f"*{enc['description']}*"

        new_view = HuntActionView(self.author_id, self.guild_id, enc, res["is_duplicate"])
        await interaction.response.edit_message(embed=embed, view=new_view)

    @discord.ui.button(label="🐾 View Collection", style=discord.ButtonStyle.secondary, custom_id="view_zoo")
    async def view_zoo_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        zoo = await economy_service.get_user_zoo(self.guild_id, self.author_id)
        if not zoo:
            return await interaction.response.send_message("Your zoo is currently empty!", ephemeral=True)

        lines: List[str] = []
        for a in zoo[:15]:
            fav = "⭐ " if a.get("is_favorite") else ""
            lines.append(f"{fav}{a['emoji']} **{a['name']}** (`{a['rarity']}`) — x{a['count']} | Value: {a['base_value']:,} {CURRENCY_SYMBOL}")

        embed = economy_embed(
            title=f"🐾 Zoo Collection - {interaction.user.display_name} ({len(zoo)} Species)",
            description="\n".join(lines),
            color=COLOR_ECO_GOLD,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="📜 Animal Details", style=discord.ButtonStyle.secondary, custom_id="animal_details")
    async def animal_details_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        enc = self.encounter
        embed = economy_embed(
            title=f"{enc['emoji']} {enc['name']} Details",
            description=enc["description"],
            color=RARITY_COLORS.get(enc["rarity"], COLOR_ECO_PRIMARY),
        )
        embed.add_field(name="Rarity", value=f"`{enc['rarity']}`", inline=True)
        embed.add_field(name="Base Value", value=f"**{enc['base_value']:,}** {CURRENCY_SYMBOL}", inline=True)
        embed.add_field(name="Base XP", value=f"**+{enc['base_xp']}** XP", inline=True)
        embed.add_field(name="Special Ability", value=f"✨ {enc['ability']}", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="💰 Sell Duplicate", style=discord.ButtonStyle.danger, custom_id="sell_dupe")
    async def sell_dupe_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        enc = self.encounter
        success, sold_count, earned, msg = await economy_service.sell_animal(
            self.guild_id, self.author_id, enc["animal_id"], count_target="duplicates"
        )
        if success:
            button.disabled = True
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(
                embed=economy_embed("💰 Duplicate Sold", msg, COLOR_ECO_SUCCESS),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                embed=economy_embed("❌ Cannot Sell", msg, COLOR_ECO_ERROR),
                ephemeral=True,
            )


class Hunt(commands.Cog):
    """NOVEXA Animal Hunting & Zoo Collection."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="hunt", description="Hunt in the wilderness to catch wild animals, earn XP, and expand your zoo")
    async def hunt(self, interaction: discord.Interaction):
        if not await check_channel_allowed(interaction, "hunting"):
            return

        res = await economy_service.hunt(interaction.guild_id, interaction.user.id)
        if not res["success"]:
            rem = format_remaining(res["remaining_seconds"])
            embed = economy_embed(
                "⏳ Hunting Cooldown",
                f"You're catching your breath from the last hunt! Try again in **{rem}**.",
                COLOR_ECO_INFO,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if not res["caught"]:
            enc = res["encounter"]
            embed = economy_embed(
                "🐾 Hunt Encounter: Escaped!",
                f"A wild **{enc['emoji']} {enc['name']}** appeared, but proved too agile and escaped into the brush!",
                COLOR_ECO_INFO,
            )
            embed.set_footer(text="Tip: Equip higher rarity hunting nets or bows to boost catch rate!")
            view = HuntActionView(interaction.user.id, interaction.guild_id, enc, False)
            return await interaction.response.send_message(embed=embed, view=view)

        enc = res["encounter"]
        color = RARITY_COLORS.get(enc["rarity"], COLOR_ECO_PRIMARY)
        embed = economy_embed(
            title=f"🎯 Hunt Successful! You caught a {enc['name']}!",
            color=color,
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="Animal", value=f"{enc['emoji']} **{enc['name']}**", inline=True)
        embed.add_field(name="Rarity", value=f"`{enc['rarity']}`", inline=True)
        embed.add_field(name="Sell Value", value=f"**{enc['base_value']:,}** {CURRENCY_SYMBOL}", inline=True)
        embed.add_field(name="XP Gained", value=f"**+{res['xp_gain']}** XP", inline=True)
        embed.add_field(name="Special Ability", value=f"✨ *{enc['ability']}*", inline=True)
        embed.add_field(name="Zoo Inventory", value=f"**{res['count']} Owned**" + (" *(Duplicate)*" if res["is_duplicate"] else " *(New Addition!)*"), inline=True)
        embed.description = f"*{enc['description']}*"

        if res["leveled_up"]:
            embed.add_field(name="🎉 Level Up!", value=f"You reached **Level {res['new_level']}**!", inline=False)

        view = HuntActionView(interaction.user.id, interaction.guild_id, enc, res["is_duplicate"])
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="zoo", description="Display your or another member's animal sanctuary collection")
    @app_commands.describe(user="Member whose zoo to inspect")
    async def zoo(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        if not await check_channel_allowed(interaction, "hunting"):
            return

        target = user or interaction.user
        zoo = await economy_service.get_user_zoo(interaction.guild_id, target.id)

        if not zoo:
            embed = economy_embed(
                f"🐾 Zoo - {target.display_name}",
                "No animals have been caught yet! Run `/hunt` to begin your collection.",
                COLOR_ECO_INFO,
            )
            return await interaction.response.send_message(embed=embed)

        total_animals = sum(a["count"] for a in zoo)
        total_value = sum(a["count"] * a["base_value"] for a in zoo)

        pages: List[discord.Embed] = []
        chunk_size = 8
        for i in range(0, len(zoo), chunk_size):
            chunk = zoo[i : i + chunk_size]
            embed = economy_embed(
                title=f"🦁 Imperial Zoo - {target.display_name} ({len(zoo)} Species, {total_animals:,} Total Animals)",
                color=COLOR_ECO_GOLD,
            )
            embed.set_thumbnail(url=target.display_avatar.url)
            lines: List[str] = []
            for a in chunk:
                fav = "⭐ " if a.get("is_favorite") else ""
                lines.append(
                    f"{fav}{a['emoji']} **{a['name']}** (`{a['rarity']}`)\n"
                    f"Count: **{a['count']}x** | Value: **{a['base_value']:,}** {CURRENCY_SYMBOL} | Ability: *{a['ability']}*"
                )
            embed.description = "\n\n".join(lines)
            embed.set_footer(text=f"Total Zoo Value: {total_value:,} Coins • Page {len(pages) + 1} of {((len(zoo) - 1) // chunk_size) + 1}")
            pages.append(embed)

        if len(pages) == 1:
            await interaction.response.send_message(embed=pages[0])
        else:
            view = PaginatorView(pages, interaction.user.id)
            await interaction.response.send_message(embed=pages[0], view=view)

    @app_commands.command(name="animals", description="List summary of your collected animals categorized by rarity")
    @app_commands.describe(user="Member to inspect")
    async def animals(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        # Alias/Complement to /zoo with compact rarity counts
        if not await check_channel_allowed(interaction, "hunting"):
            return

        target = user or interaction.user
        zoo = await economy_service.get_user_zoo(interaction.guild_id, target.id)

        rarity_counts = {"Mythical": 0, "Legendary": 0, "Epic": 0, "Rare": 0, "Uncommon": 0, "Common": 0}
        for a in zoo:
            rarity = a.get("rarity", "Common")
            if rarity in rarity_counts:
                rarity_counts[rarity] += a["count"]

        embed = economy_embed(
            title=f"🐾 Animals Breakdown - {target.display_name}",
            color=COLOR_ECO_PRIMARY,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="👑 Mythical", value=f"**{rarity_counts['Mythical']}** Animals", inline=True)
        embed.add_field(name="⚡ Legendary", value=f"**{rarity_counts['Legendary']}** Animals", inline=True)
        embed.add_field(name="🔮 Epic", value=f"**{rarity_counts['Epic']}** Animals", inline=True)
        embed.add_field(name="💎 Rare", value=f"**{rarity_counts['Rare']}** Animals", inline=True)
        embed.add_field(name="🌿 Uncommon", value=f"**{rarity_counts['Uncommon']}** Animals", inline=True)
        embed.add_field(name="🍂 Common", value=f"**{rarity_counts['Common']}** Animals", inline=True)
        embed.add_field(name="📊 Total Captured", value=f"**{sum(rarity_counts.values()):,} Animals**", inline=False)
        embed.set_footer(text="Use /zoo to view full detailed pages with abilities and sell values.")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="animal-info", description="Inspect comprehensive details about an animal species")
    @app_commands.describe(animal="Animal name or ID (e.g. dragon, lion, phoenix)")
    async def animal_info(self, interaction: discord.Interaction, animal: str):
        if not await check_channel_allowed(interaction, "hunting"):
            return

        row = await db.fetchone(
            "SELECT * FROM economy_animals WHERE animal_id = ? OR LOWER(name) LIKE ?",
            (animal.lower(), f"%{animal.lower()}%"),
        )
        if not row:
            return await interaction.response.send_message(
                embed=economy_embed("❌ Not Found", f"No animal matching `{animal}` found in the encyclopedia.", COLOR_ECO_ERROR),
                ephemeral=True,
            )

        enc = dict(row)
        embed = economy_embed(
            title=f"{enc['emoji']} {enc['name']} Encyclopedia Profile",
            description=enc["description"],
            color=RARITY_COLORS.get(enc["rarity"], COLOR_ECO_PRIMARY),
        )
        embed.add_field(name="Species ID", value=f"`{enc['animal_id']}`", inline=True)
        embed.add_field(name="Rarity", value=f"`{enc['rarity']}`", inline=True)
        embed.add_field(name="Market Value", value=f"**{enc['base_value']:,}** {CURRENCY_SYMBOL}", inline=True)
        embed.add_field(name="Catch XP", value=f"**+{enc['base_xp']}** XP", inline=True)
        embed.add_field(name="Rarity Weight", value=f"`{enc['catch_weight']}`", inline=True)
        embed.add_field(name="Special Ability", value=f"✨ {enc['ability']}", inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="sell-animal", description="Sell animals from your zoo for Novexa Coins")
    @app_commands.describe(animal="Animal ID or Name", count="Number of animals, 'all', or 'duplicates'")
    async def sell_animal(self, interaction: discord.Interaction, animal: str, count: str = "1"):
        if not await check_channel_allowed(interaction, "hunting"):
            return

        success, sold_count, earned, msg = await economy_service.sell_animal(
            interaction.guild_id, interaction.user.id, animal, count
        )
        if success:
            embed = economy_embed("💰 Animals Sold", msg, COLOR_ECO_SUCCESS)
            await interaction.response.send_message(embed=embed)
        else:
            embed = economy_embed("❌ Sell Failed", msg, COLOR_ECO_ERROR)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="favorite-animal", description="Star and pin a favorite animal in your zoo collection")
    @app_commands.describe(animal_id="The ID of the animal to favorite")
    async def favorite_animal(self, interaction: discord.Interaction, animal_id: str):
        if not await check_channel_allowed(interaction, "hunting"):
            return

        success, msg = await economy_service.favorite_animal(interaction.guild_id, interaction.user.id, animal_id)
        if success:
            embed = economy_embed("⭐ Favorite Updated", msg, COLOR_ECO_GOLD)
            await interaction.response.send_message(embed=embed)
        else:
            embed = economy_embed("❌ Favorite Failed", msg, COLOR_ECO_ERROR)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="hunt-stats", description="View your comprehensive hunting analytics, catch rate, and zoo value")
    @app_commands.describe(user="Member to inspect")
    async def hunt_stats(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        if not await check_channel_allowed(interaction, "hunting"):
            return

        target = user or interaction.user
        data = await economy_service.get_or_create_user(interaction.guild_id, target.id)
        zoo = await economy_service.get_user_zoo(interaction.guild_id, target.id)

        total_animals = sum(a["count"] for a in zoo)
        unique_species = len(zoo)
        total_val = sum(a["count"] * a["base_value"] for a in zoo)

        equipped_items = await economy_service.get_equipped_items(interaction.guild_id, target.id)
        equipped_pet = await economy_service.get_equipped_pet(interaction.guild_id, target.id)

        hunt_luck = 0
        for it in equipped_items.values():
            hunt_luck += it.get("hunt_luck", 0)
        if equipped_pet and equipped_pet["bonus_type"] == "hunt_luck":
            hunt_luck += int(equipped_pet["bonus_value"] * equipped_pet["level"])

        embed = economy_embed(
            title=f"🏹 Hunting Analytics - {target.display_name}",
            color=COLOR_ECO_PRIMARY,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="Total Hunts Conducted", value=f"**{data['hunts_count']:,}** Hunts", inline=True)
        embed.add_field(name="Current Catch Rate Boost", value=f"**+{hunt_luck}%** Luck", inline=True)
        embed.add_field(name="Unique Species Discovered", value=f"**{unique_species}** Species", inline=True)
        embed.add_field(name="Total Animals in Zoo", value=f"**{total_animals:,}** Animals", inline=True)
        embed.add_field(name="Total Zoo Valuation", value=f"**{total_val:,}** {CURRENCY_NAME}", inline=True)
        embed.add_field(name="Equipped Hunting Tool", value=f"**{equipped_items.get('hunting_tool', {}).get('name', 'None')}**", inline=True)

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Hunt(bot))

