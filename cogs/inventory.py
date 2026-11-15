"""NOVEXA - Weapons, Gear & Inventory Management Cog.

Features:
- Interactive Shop with category selection dropdown, pagination, and purchase flows
- Equipment slots (Weapon, Shield, Armor, Hunting Tool)
- Item stats inspection, item usage (potions, feasts, boosters), and selling
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional, List, Dict, Any
from database.database import db
from services.economy_service import (
    economy_service,
    CURRENCY_NAME,
    CURRENCY_SYMBOL,
    GEM_NAME,
    GEM_SYMBOL,
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
from utils.helpers import PaginatorView

logger = logging.getLogger("novexa.inventory")

ITEM_CATEGORIES = [
    ("All Items", "all"),
    ("⚔️ Swords", "swords"),
    ("🔫 Guns", "guns"),
    ("🏹 Bows", "bows"),
    ("🛡️ Shields", "shields"),
    ("🦺 Armor", "armor"),
    ("🕸️ Hunting Gear", "hunting"),
    ("🔮 Boosters", "boosters"),
    ("✨ Special & Rings", "special"),
    ("📦 Crates", "crates"),
    ("👑 Collectibles", "collectibles"),
]


class ShopCategorySelect(discord.ui.Select):
    """Dropdown for filtering the shop by item category."""

    def __init__(self, current_category: str):
        options = [
            discord.SelectOption(
                label=label,
                value=val,
                default=(val == current_category),
            )
            for label, val in ITEM_CATEGORIES
        ]
        super().__init__(placeholder="Select Shop Category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_category = self.values[0]
        embeds = await generate_shop_embeds(interaction.guild_id, selected_category)
        if not embeds:
            return await interaction.response.send_message("No items found in this category.", ephemeral=True)

        view = ShopView(interaction.user.id, selected_category, embeds)
        await interaction.response.edit_message(embed=embeds[0], view=view)


class ShopView(discord.ui.View):
    """Interactive Shop View with category selector and page buttons."""

    def __init__(self, author_id: int, current_category: str, pages: List[discord.Embed]):
        super().__init__(timeout=120.0)
        self.author_id = author_id
        self.current_category = current_category
        self.pages = pages
        self.current_page = 0

        self.add_item(ShopCategorySelect(current_category))
        self.update_buttons()

    def update_buttons(self):
        self.prev_btn.disabled = (self.current_page == 0)
        self.next_btn.disabled = (self.current_page >= len(self.pages) - 1)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ This shop view belongs to someone else!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.secondary, custom_id="shop_prev")
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.secondary, custom_id="shop_next")
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)


async def generate_shop_embeds(guild_id: int, category: str = "all") -> List[discord.Embed]:
    """Generate paginated embed catalog for the shop."""
    query = "SELECT * FROM economy_items WHERE buy_price > 0"
    params: List[Any] = []
    if category != "all":
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY category, buy_price ASC"
    rows = await db.fetchall(query, tuple(params))
    if not rows:
        return []

    embeds: List[discord.Embed] = []
    chunk_size = 5
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i : i + chunk_size]
        embed = economy_embed(
            title=f"🛒 NOVEXA SHOP — {category.upper()}",
            description="Purchase equipment using `/buy <item_id> [quantity]`.\n",
            color=COLOR_ECO_GOLD,
        )
        for it in chunk:
            price_str = f"**{it['buy_price']:,}** {CURRENCY_SYMBOL}"
            if it["gem_price"] > 0:
                price_str += f" or **{it['gem_price']}** {GEM_SYMBOL}"

            stats_parts = []
            if it["attack_bonus"]:
                stats_parts.append(f"+{it['attack_bonus']} ATK")
            if it["defense_bonus"]:
                stats_parts.append(f"+{it['defense_bonus']} DEF")
            if it["hunt_luck"]:
                stats_parts.append(f"+{it['hunt_luck']}% Hunt Luck")

            stats_str = f" | `{', '.join(stats_parts)}`" if stats_parts else ""
            embed.add_field(
                name=f"{it['icon']} {it['name']} (`{it['item_id']}`)",
                value=f"**Price:** {price_str}{stats_str}\n"
                      f"*{it['description']}*\n"
                      f"**Ability:** {it['special_ability'] or 'None'}",
                inline=False,
            )
        embed.set_footer(text=f"Page {len(embeds) + 1} of {((len(rows) - 1) // chunk_size) + 1} • Run /buy <item_id> to purchase")
        embeds.append(embed)

    return embeds


class Inventory(commands.Cog):
    """NOVEXA Weapons, Armor, Tools, and Shop."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="shop", description="Open the interactive NOVEXA item, weapons, and armor shop")
    @app_commands.choices(category=[
        app_commands.Choice(name=label, value=val) for label, val in ITEM_CATEGORIES
    ])
    @app_commands.describe(category="Filter items by category")
    async def shop(self, interaction: discord.Interaction, category: Optional[app_commands.Choice[str]] = None):
        if not await check_channel_allowed(interaction, "marketplace"):
            return

        cat_val = category.value if category else "all"
        embeds = await generate_shop_embeds(interaction.guild_id, cat_val)
        if not embeds:
            return await interaction.response.send_message("No items found in this shop category.", ephemeral=True)

        view = ShopView(interaction.user.id, cat_val, embeds)
        await interaction.response.send_message(embed=embeds[0], view=view)

    @app_commands.command(name="buy", description="Purchase equipment or consumables from the shop")
    @app_commands.describe(item_id="Item identifier (e.g. wooden_sword, basic_net, diamond_ring)", quantity="Number of items to purchase")
    async def buy(self, interaction: discord.Interaction, item_id: str, quantity: int = 1):
        if not await check_channel_allowed(interaction, "marketplace"):
            return

        success, msg = await economy_service.buy_item(interaction.guild_id, interaction.user.id, item_id.lower().strip(), quantity)
        if success:
            embed = economy_embed("🛍️ Purchase Successful", msg, COLOR_ECO_SUCCESS)
            await interaction.response.send_message(embed=embed)
        else:
            embed = economy_embed("❌ Purchase Failed", msg, COLOR_ECO_ERROR)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="sell", description="Sell items from your inventory for coins (50% of purchase price)")
    @app_commands.describe(item_id="Item ID to sell", quantity="Quantity to sell")
    async def sell(self, interaction: discord.Interaction, item_id: str, quantity: int = 1):
        if not await check_channel_allowed(interaction, "marketplace"):
            return

        clean_id = item_id.lower().strip()
        item = await db.fetchone("SELECT * FROM economy_items WHERE item_id = ?", (clean_id,))
        if not item:
            return await interaction.response.send_message(f"Item `{clean_id}` not found.", ephemeral=True)

        inv = await db.fetchone(
            "SELECT quantity FROM economy_inventory WHERE guild_id = ? AND user_id = ? AND item_id = ?",
            (interaction.guild_id, interaction.user.id, clean_id),
        )
        if not inv or inv["quantity"] < quantity:
            return await interaction.response.send_message(f"You don't have **{quantity}x** `{clean_id}` in your inventory!", ephemeral=True)

        sell_price = item["sell_price"] if item["sell_price"] > 0 else (item["buy_price"] // 2)
        total_coins = sell_price * quantity

        await economy_service.remove_item(interaction.guild_id, interaction.user.id, clean_id, quantity)
        await economy_service.modify_wallet(interaction.guild_id, interaction.user.id, total_coins, tx_type="item_sell", description=f"Sold {quantity}x {item['name']}")

        embed = economy_embed(
            "💰 Item Sold",
            f"Sold **{quantity}x {item['icon']} {item['name']}** for **+{total_coins:,} {CURRENCY_NAME}**!",
            COLOR_ECO_SUCCESS,
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="inventory", description="Display your or another member's item inventory and equipped gear")
    @app_commands.choices(category=[
        app_commands.Choice(name=label, value=val) for label, val in ITEM_CATEGORIES
    ])
    @app_commands.describe(user="Member whose inventory to view", category="Filter by category")
    async def inventory(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.Member] = None,
        category: Optional[app_commands.Choice[str]] = None,
    ):
        if not await check_channel_allowed(interaction, "marketplace"):
            return

        target = user or interaction.user
        cat_val = category.value if category else "all"
        items = await economy_service.get_user_inventory(interaction.guild_id, target.id, cat_val)

        if not items:
            embed = economy_embed(
                f"🎒 Inventory - {target.display_name}",
                "Your inventory is currently empty! Visit the `/shop` to browse equipment and supplies.",
                COLOR_ECO_INFO,
            )
            return await interaction.response.send_message(embed=embed)

        pages: List[discord.Embed] = []
        chunk_size = 6
        for i in range(0, len(items), chunk_size):
            chunk = items[i : i + chunk_size]
            embed = economy_embed(
                title=f"🎒 Inventory - {target.display_name} ({len(items)} Items)",
                color=COLOR_ECO_PRIMARY,
            )
            embed.set_thumbnail(url=target.display_avatar.url)
            lines: List[str] = []
            for it in chunk:
                equipped_tag = " `[EQUIPPED]`" if it.get("is_equipped") else ""
                stats_list = []
                if it["attack_bonus"]:
                    stats_list.append(f"+{it['attack_bonus']} ATK")
                if it["defense_bonus"]:
                    stats_list.append(f"+{it['defense_bonus']} DEF")
                if it["hunt_luck"]:
                    stats_list.append(f"+{it['hunt_luck']}% Luck")
                stats_str = f" | `{', '.join(stats_list)}`" if stats_list else ""

                lines.append(
                    f"{it['icon']} **{it['name']}**{equipped_tag} — **x{it['quantity']}** (`{it['item_id']}`)\n"
                    f"Rarity: `{it['rarity']}`{stats_str}\n"
                    f"*{it['description']}*"
                )
            embed.description = "\n\n".join(lines)
            embed.set_footer(text=f"Use /equip <item_id> to equip gear • Page {len(pages) + 1} of {((len(items) - 1) // chunk_size) + 1}")
            pages.append(embed)

        if len(pages) == 1:
            await interaction.response.send_message(embed=pages[0])
        else:
            view = PaginatorView(pages, interaction.user.id)
            await interaction.response.send_message(embed=pages[0], view=view)

    @app_commands.command(name="equip", description="Equip a weapon, shield, armor, or hunting gear from inventory")
    @app_commands.describe(item_id="Item ID to equip (e.g. iron_sword, master_net, dragon_scale_armor)")
    async def equip(self, interaction: discord.Interaction, item_id: str):
        if not await check_channel_allowed(interaction, "marketplace"):
            return

        success, msg = await economy_service.equip_item(interaction.guild_id, interaction.user.id, item_id.lower().strip())
        if success:
            embed = economy_embed("⚔️ Gear Equipped", msg, COLOR_ECO_SUCCESS)
            await interaction.response.send_message(embed=embed)
        else:
            embed = economy_embed("❌ Cannot Equip", msg, COLOR_ECO_ERROR)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="unequip", description="Unequip an item or empty an equipment slot")
    @app_commands.describe(slot_or_item="Slot name ('weapon', 'shield', 'armor', 'hunting_tool') or Item ID")
    async def unequip(self, interaction: discord.Interaction, slot_or_item: str):
        if not await check_channel_allowed(interaction, "marketplace"):
            return

        success, msg = await economy_service.unequip_item(interaction.guild_id, interaction.user.id, slot_or_item)
        if success:
            embed = economy_embed("🛡️ Unequipped", msg, COLOR_ECO_INFO)
            await interaction.response.send_message(embed=embed)
        else:
            embed = economy_embed("❌ Error", msg, COLOR_ECO_ERROR)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    weapon_group = app_commands.Group(name="weapon", description="Inspect equipped weapon and weapons catalog")

    @weapon_group.command(name="equipped", description="Inspect your or another warrior's currently equipped weapon")
    @app_commands.describe(user="Member to inspect")
    async def weapon(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        if not await check_channel_allowed(interaction, "marketplace"):
            return

        target = user or interaction.user
        equipped = await economy_service.get_equipped_items(interaction.guild_id, target.id)
        wep = equipped.get("weapon")

        if not wep:
            embed = economy_embed(
                f"⚔️ Weapon - {target.display_name}",
                "No weapon is currently equipped! Visit `/shop swords` or `/shop guns` to arm yourself.",
                COLOR_ECO_INFO,
            )
            return await interaction.response.send_message(embed=embed)

        embed = economy_embed(
            title=f"{wep['icon']} Equipped Weapon: {wep['name']}",
            description=wep["description"],
            color=COLOR_ECO_GOLD,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="Category", value=wep["category"].title(), inline=True)
        embed.add_field(name="Rarity", value=f"`{wep['rarity']}`", inline=True)
        embed.add_field(name="Attack Bonus", value=f"🗡️ **+{wep['attack_bonus']}** ATK", inline=True)
        embed.add_field(name="Special Ability", value=f"✨ {wep['special_ability']}", inline=False)
        await interaction.response.send_message(embed=embed)

    @weapon_group.command(name="info", description="Look up weapons catalog details")
    @app_commands.describe(item_id="Weapon ID (e.g. shadow_blade, plasma_pistol, celestial_blade)")
    async def weapon_info(self, interaction: discord.Interaction, item_id: str):
        row = await db.fetchone(
            "SELECT * FROM economy_items WHERE item_id = ? AND category IN ('swords', 'guns', 'bows')",
            (item_id.lower().strip(),),
        )
        if not row:
            return await interaction.response.send_message("Weapon not found in catalog.", ephemeral=True)

        wep = dict(row)
        embed = economy_embed(
            title=f"{wep['icon']} {wep['name']} Specifications",
            description=wep["description"],
            color=COLOR_ECO_PRIMARY,
        )
        embed.add_field(name="Weapon ID", value=f"`{wep['item_id']}`", inline=True)
        embed.add_field(name="Rarity", value=f"`{wep['rarity']}`", inline=True)
        embed.add_field(name="Attack Bonus", value=f"🗡️ **+{wep['attack_bonus']}** ATK", inline=True)
        embed.add_field(name="Shop Price", value=f"**{wep['buy_price']:,}** {CURRENCY_SYMBOL}", inline=True)
        embed.add_field(name="Special Ability", value=f"✨ {wep['special_ability']}", inline=False)
        await interaction.response.send_message(embed=embed)

    # Prefix compatibility commands
    @commands.command(name="weapon")
    async def prefix_weapon(self, ctx: commands.Context, user: Optional[discord.Member] = None):
        target = user or ctx.author
        equipped = await economy_service.get_equipped_items(ctx.guild.id, target.id)
        wep = equipped.get("weapon")
        if not wep:
            embed = economy_embed(
                f"⚔️ Weapon - {target.display_name}",
                f"No weapon is currently equipped! Visit `{BOT_PREFIX}shop swords` or `/shop`.",
                COLOR_ECO_INFO,
            )
            return await ctx.send(embed=embed)
        embed = economy_embed(
            title=f"{wep['icon']} Equipped Weapon: {wep['name']}",
            description=wep["description"],
            color=COLOR_ECO_GOLD,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="Attack Bonus", value=f"🗡️ **+{wep['attack_bonus']}** ATK", inline=True)
        embed.add_field(name="Special Ability", value=f"✨ {wep['special_ability']}", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="weapon-info")
    async def prefix_weapon_info(self, ctx: commands.Context, item_id: str):
        row = await db.fetchone(
            "SELECT * FROM economy_items WHERE item_id = ? AND category IN ('swords', 'guns', 'bows')",
            (item_id.lower().strip(),),
        )
        if not row:
            return await ctx.send("Weapon not found in catalog.")
        wep = dict(row)
        embed = economy_embed(
            title=f"{wep['icon']} {wep['name']} Specifications",
            description=wep["description"],
            color=COLOR_ECO_PRIMARY,
        )
        embed.add_field(name="Weapon ID", value=f"`{wep['item_id']}`", inline=True)
        embed.add_field(name="Attack Bonus", value=f"🗡️ **+{wep['attack_bonus']}** ATK", inline=True)
        embed.add_field(name="Shop Price", value=f"**{wep['buy_price']:,}** {CURRENCY_SYMBOL}", inline=True)
        await ctx.send(embed=embed)

    @app_commands.command(name="item-info", description="Inspect comprehensive statistics and effects of any item")
    @app_commands.describe(item_id="Item ID (e.g. lucky_charm, master_net, exp_booster)")
    async def item_info(self, interaction: discord.Interaction, item_id: str):
        row = await db.fetchone("SELECT * FROM economy_items WHERE item_id = ?", (item_id.lower().strip(),))
        if not row:
            return await interaction.response.send_message(f"Item `{item_id}` not found.", ephemeral=True)

        it = dict(row)
        embed = economy_embed(
            title=f"{it['icon']} {it['name']} Details",
            description=it["description"],
            color=COLOR_ECO_PRIMARY,
        )
        embed.add_field(name="Category", value=it["category"].title(), inline=True)
        embed.add_field(name="Rarity", value=f"`{it['rarity']}`", inline=True)
        embed.add_field(name="Buy Price", value=f"**{it['buy_price']:,}** {CURRENCY_SYMBOL}", inline=True)
        embed.add_field(name="Sell Price", value=f"**{it['sell_price']:,}** {CURRENCY_SYMBOL}", inline=True)
        embed.add_field(name="Consumable", value="Yes" if it["consumable"] else "No (Equipment / Trophy)", inline=True)
        embed.add_field(name="Equipment Slot", value=it["slot"] or "None", inline=True)
        embed.add_field(name="Special Ability / Effect", value=f"✨ {it['special_ability'] or 'None'}", inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="use-item", description="Consume a potion, booster scroll, or feast from your inventory")
    @app_commands.describe(item_id="Consumable Item ID to use (e.g. exp_booster, lucky_charm)")
    async def use_item(self, interaction: discord.Interaction, item_id: str):
        clean_id = item_id.lower().strip()
        inv = await db.fetchone(
            "SELECT quantity FROM economy_inventory WHERE guild_id = ? AND user_id = ? AND item_id = ?",
            (interaction.guild_id, interaction.user.id, clean_id),
        )
        if not inv or inv["quantity"] <= 0:
            return await interaction.response.send_message(f"You don't have any `{clean_id}` in your inventory!", ephemeral=True)

        if clean_id == "exp_booster":
            await economy_service.remove_item(interaction.guild_id, interaction.user.id, clean_id, 1)
            leveled, new_lvl, r_coins, r_gems = await economy_service.add_xp(interaction.guild_id, interaction.user.id, 1000)
            msg = "📜 You unrolled the Ancient Wisdom Scroll and absorbed **+1,000 XP**!"
            if leveled:
                msg += f"\n🎉 **Level Up!** You reached **Level {new_lvl}**!"
            await interaction.response.send_message(embed=economy_embed("✨ Item Used", msg, COLOR_ECO_SUCCESS))

        elif clean_id == "lucky_charm":
            await economy_service.remove_item(interaction.guild_id, interaction.user.id, clean_id, 1)
            # Grants instant 1,000 coins bonus
            await economy_service.modify_wallet(interaction.guild_id, interaction.user.id, 1200, tx_type="item_use", description="Used Lucky Clover")
            await interaction.response.send_message(
                embed=economy_embed("🍀 Lucky Charm Consumed", "The four-leaf clover blessed your wallet with **+1,200 Novexa Coins**!", COLOR_ECO_SUCCESS)
            )

        elif clean_id in ("common_crate", "rare_crate", "epic_crate", "legendary_crate"):
            success, results, summary = await economy_service.open_crate(interaction.guild_id, interaction.user.id, clean_id, 1)
            if success:
                await interaction.response.send_message(embed=economy_embed("🎁 Crate Opened", summary, COLOR_ECO_GOLD))
            else:
                await interaction.response.send_message(summary, ephemeral=True)

        else:
            await interaction.response.send_message(f"Item `{clean_id}` cannot be used directly with `/use-item`.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Inventory(bot))

