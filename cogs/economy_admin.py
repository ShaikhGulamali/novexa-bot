"""NOVEXA - Administrator Economy Control & Channel Provisioning Cog.

Features:
- Automated channel generator provisioning the 5 suggested economy categories & text channels
- Selective assignment of existing channels to economy categories
- Channel restriction toggles and reset
- Balance adjustments (/add-coins, /remove-coins, /set-coins)
- Inventory management (/give-item, /remove-item)
- Level assignment (/set-level)
- Server-wide economy resets with double confirmation dialog
- Economy analytics and circulation statistics (/economy-stats)
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
    GEM_NAME,
    GEM_SYMBOL,
)
from utils.permissions import has_admin_or_owner
from utils.economy_checks import (
    economy_embed,
    COLOR_ECO_PRIMARY,
    COLOR_ECO_GOLD,
    COLOR_ECO_SUCCESS,
    COLOR_ECO_ERROR,
    COLOR_ECO_INFO,
)

logger = logging.getLogger("novexa.economy_admin")

SUGGESTED_CATEGORIES = [
    {
        "category": "💰 ECONOMY",
        "type": "economy",
        "channels": ["💰・balance", "🎁・daily-rewards", "💼・work", "🏦・bank", "💸・transactions"],
    },
    {
        "category": "🐾 HUNTING",
        "type": "hunting",
        "channels": ["🐾・hunt", "🦊・animals", "🐉・zoo", "⚔️・battles"],
    },
    {
        "category": "🛒 MARKETPLACE",
        "type": "marketplace",
        "channels": ["🛒・shop", "🎒・inventory", "💎・gems", "🎁・crates", "🔄・trading"],
    },
    {
        "category": "🎮 GAMES",
        "type": "games",
        "channels": ["🎰・games", "🎲・casino", "🏆・leaderboards", "👤・profiles"],
    },
]


class ResetConfirmationView(discord.ui.View):
    """Safety confirmation view for resetting economy balances."""

    def __init__(self, author_id: int, guild_id: int, target_user: Optional[discord.Member]):
        super().__init__(timeout=45.0)
        self.author_id = author_id
        self.guild_id = guild_id
        self.target_user = target_user

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ You are not authorized to confirm this reset.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="⚠️ CONFIRM WIPE", style=discord.ButtonStyle.danger, custom_id="confirm_wipe")
    async def confirm_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        for child in self.children:
            child.disabled = True

        if self.target_user:
            # Wipe single user
            await db.execute("DELETE FROM economy_users WHERE guild_id = ? AND user_id = ?", (self.guild_id, self.target_user.id))
            await db.execute("DELETE FROM economy_inventory WHERE guild_id = ? AND user_id = ?", (self.guild_id, self.target_user.id))
            await db.execute("DELETE FROM economy_user_animals WHERE guild_id = ? AND user_id = ?", (self.guild_id, self.target_user.id))
            await db.execute("DELETE FROM economy_user_pets WHERE guild_id = ? AND user_id = ?", (self.guild_id, self.target_user.id))
            await db.execute("DELETE FROM economy WHERE guild_id = ? AND user_id = ?", (self.guild_id, self.target_user.id))

            embed = economy_embed(
                "🗑️ User Economy Wiped",
                f"Successfully wiped all economy balances, inventory, zoo animals, and pets for {self.target_user.mention}.",
                COLOR_ECO_SUCCESS,
            )
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            # Wipe entire server
            await db.execute("DELETE FROM economy_users WHERE guild_id = ?", (self.guild_id,))
            await db.execute("DELETE FROM economy_inventory WHERE guild_id = ?", (self.guild_id,))
            await db.execute("DELETE FROM economy_user_animals WHERE guild_id = ?", (self.guild_id,))
            await db.execute("DELETE FROM economy_user_pets WHERE guild_id = ?", (self.guild_id,))
            await db.execute("DELETE FROM economy_relationships WHERE guild_id = ?", (self.guild_id,))
            await db.execute("DELETE FROM economy WHERE guild_id = ?", (self.guild_id,))

            embed = economy_embed(
                "💥 SERVER ECONOMY RESET COMPLETE",
                "All user wallets, banks, inventories, pets, and zoos have been completely reset to zero for this server.",
                COLOR_ECO_SUCCESS,
            )
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, custom_id="cancel_wipe")
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            embed=economy_embed("Operation Cancelled", "Economy reset was aborted safely.", COLOR_ECO_INFO),
            view=self,
        )


class EconomySetupView(discord.ui.View):
    """Interactive control center for /economy-setup."""

    def __init__(self, author_id: int, guild: discord.Guild):
        super().__init__(timeout=180.0)
        self.author_id = author_id
        self.guild = guild

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Only the administrator who initiated setup can use these controls.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🚀 Auto-Create All Suggested Channels", style=discord.ButtonStyle.primary, custom_id="auto_create_channels")
    async def auto_create_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        created_summary = []
        for cat_info in SUGGESTED_CATEGORIES:
            cat_name = cat_info["category"]
            cat_type = cat_info["type"]
            category_channel = await self.guild.create_category(name=cat_name)

            for chan_name in cat_info["channels"]:
                text_channel = await self.guild.create_text_channel(name=chan_name, category=category_channel)
                # Map to database
                await db.execute(
                    """
                    INSERT INTO economy_channel_settings (guild_id, channel_id, category_type)
                    VALUES (?, ?, ?)
                    ON CONFLICT(guild_id, channel_id, category_type) DO NOTHING
                    """,
                    (self.guild.id, text_channel.id, cat_type),
                )

            created_summary.append(f"• **{cat_name}** ({len(cat_info['channels'])} channels)")

        # Enable channel enforcement
        await db.execute(
            """
            INSERT INTO economy_guild_settings (guild_id, channel_enforcement)
            VALUES (?, 1)
            ON CONFLICT(guild_id) DO UPDATE SET channel_enforcement = 1
            """,
            (self.guild.id,),
        )

        button.disabled = True
        embed = economy_embed(
            title="🎉 Economy Channels Generated!",
            description="All recommended categories and text channels have been automatically created and registered:\n\n" +
                        "\n".join(created_summary) +
                        "\n\n*Channel enforcement is now **ENABLED**! Commands will be cleanly routed to their designated zones.*",
            color=COLOR_ECO_SUCCESS,
        )
        await interaction.followup.send(embed=embed)

    @discord.ui.button(label="🔄 Toggle Channel Enforcement", style=discord.ButtonStyle.secondary, custom_id="toggle_enforce")
    async def toggle_enforce_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        row = await db.fetchone("SELECT channel_enforcement FROM economy_guild_settings WHERE guild_id = ?", (self.guild.id,))
        current = row["channel_enforcement"] if row else 0
        new_val = 0 if current else 1

        await db.execute(
            """
            INSERT INTO economy_guild_settings (guild_id, channel_enforcement)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET channel_enforcement = ?
            """,
            (self.guild.id, new_val, new_val),
        )

        status_str = "**ENABLED** (commands restricted to designated channels)" if new_val else "**DISABLED** (commands allowed in all channels)"
        embed = economy_embed("⚙️ Enforcement Toggled", f"Channel restriction enforcement is now {status_str}.", COLOR_ECO_INFO)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🧹 Reset Channel Configurations", style=discord.ButtonStyle.danger, custom_id="reset_channels")
    async def reset_channels_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await db.execute("DELETE FROM economy_channel_settings WHERE guild_id = ?", (self.guild.id,))
        await db.execute("UPDATE economy_guild_settings SET channel_enforcement = 0 WHERE guild_id = ?", (self.guild.id,))

        embed = economy_embed("🧹 Channel Configuration Reset", "All economy channel bindings cleared and enforcement turned off.", COLOR_ECO_INFO)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class EconomyAdmin(commands.Cog):
    """NOVEXA Economy Administration & Channel Provisioning."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    eco_admin = app_commands.Group(name="economy-admin", description="Master economy administration dashboard & tools")

    # ==================== CHANNEL SETUP ====================

    @app_commands.command(name="economy-setup", description="Configure economy channels, automatic category generation, or existing channel assignments")
    @has_admin_or_owner()
    async def economy_setup(self, interaction: discord.Interaction):
        # Fetch current bindings
        bindings = await db.fetchall(
            "SELECT channel_id, category_type FROM economy_channel_settings WHERE guild_id = ?",
            (interaction.guild_id,),
        )
        g_row = await db.fetchone("SELECT channel_enforcement FROM economy_guild_settings WHERE guild_id = ?", (interaction.guild_id,))
        enforce_status = "Enabled (Strict)" if (g_row and g_row["channel_enforcement"]) else "Disabled (Allow Everywhere)"

        lines = [f"• <#{b['channel_id']}>: `{b['category_type'].upper()}`" for b in bindings]

        embed = economy_embed(
            title="🛠️ NOVEXA ECONOMY CHANNEL DASHBOARD",
            description=f"**Current Server:** {interaction.guild.name}\n"
                        f"**Channel Enforcement:** `{enforce_status}`\n"
                        f"**Bound Channels:** {len(bindings)}\n\n"
                        f"### Active Channel Bindings:\n" +
                        ("\n".join(lines[:12]) if lines else "*No specific channels configured. Commands permitted in all text channels.*") +
                        f"\n\n### Options Below:\n"
                        f"• **Auto-Create All Suggested Channels:** Creates all 4 categories (💰 Economy, 🐾 Hunting, 🛒 Marketplace, 🎮 Games) with neat emojis.\n"
                        f"• **Toggle Channel Enforcement:** Turn strict channel checks ON or OFF.\n"
                        f"• **Reset Channel Config:** Clear all bindings.",
            color=COLOR_ECO_PRIMARY,
        )
        view = EconomySetupView(interaction.user.id, interaction.guild)
        await interaction.response.send_message(embed=embed, view=view)

    @eco_admin.command(name="bind-channel", description="Assign an existing channel to an economy category")
    @has_admin_or_owner()
    @app_commands.choices(category=[
        app_commands.Choice(name="All Economy Systems", value="all"),
        app_commands.Choice(name="💰 Economy & Banking", value="economy"),
        app_commands.Choice(name="🐾 Hunting & Zoo", value="hunting"),
        app_commands.Choice(name="🛒 Marketplace & Shop", value="marketplace"),
        app_commands.Choice(name="🎮 Games of Chance & Leaderboard", value="games"),
    ])
    @app_commands.describe(channel="Channel to assign", category="Economy category")
    async def bind_channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        category: app_commands.Choice[str],
    ):
        await db.execute(
            """
            INSERT INTO economy_channel_settings (guild_id, channel_id, category_type)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, channel_id, category_type) DO NOTHING
            """,
            (interaction.guild_id, channel.id, category.value),
        )

        embed = economy_embed(
            "✅ Channel Bound",
            f"Successfully assigned {channel.mention} to category `{category.name}`!",
            COLOR_ECO_SUCCESS,
        )
        await interaction.response.send_message(embed=embed)

    # ==================== ADMIN BALANCE & INVENTORY CONTROLS ====================

    @eco_admin.command(name="overview", description="Administrator overview of economy status and administrative actions")
    @has_admin_or_owner()
    async def economy_admin_overview(self, interaction: discord.Interaction):
        stats = await db.fetchone(
            """
            SELECT COUNT(*) as users_count, SUM(wallet) as total_wallet, SUM(bank) as total_bank, SUM(gems) as total_gems
            FROM economy_users
            WHERE guild_id = ?
            """,
            (interaction.guild_id,),
        )
        users = stats["users_count"] if stats else 0
        wallet_sum = stats["total_wallet"] if stats and stats["total_wallet"] else 0
        bank_sum = stats["total_bank"] if stats and stats["total_bank"] else 0
        total_circulation = wallet_sum + bank_sum
        gems_sum = stats["total_gems"] if stats and stats["total_gems"] else 0

        embed = economy_embed(
            title="🛡️ NOVEXA ECONOMY ADMIN OVERVIEW",
            color=COLOR_ECO_PRIMARY,
        )
        embed.add_field(name="Registered Accounts", value=f"**{users:,}** Members", inline=True)
        embed.add_field(name="Coins in Circulation", value=f"**{total_circulation:,}** {CURRENCY_SYMBOL}", inline=True)
        embed.add_field(name="Total Gems Distributed", value=f"**{gems_sum:,}** {GEM_SYMBOL}", inline=True)
        embed.add_field(
            name="Available Management Commands",
            value="• `/add-coins <user> <amount>`\n"
                  "• `/remove-coins <user> <amount>`\n"
                  "• `/set-coins <user> <amount>`\n"
                  "• `/give-item <user> <item_id>`\n"
                  "• `/remove-item <user> <item_id>`\n"
                  "• `/set-level <user> <level>`\n"
                  "• `/reset-economy [user]`\n"
                  "• `/economy-config`\n"
                  "• `/economy-stats`",
            inline=False,
        )
        await interaction.response.send_message(embed=embed)

    @eco_admin.command(name="add-coins", description="Add virtual coins to a user's wallet or bank account")
    @has_admin_or_owner()
    @app_commands.choices(destination=[
        app_commands.Choice(name="Wallet", value="wallet"),
        app_commands.Choice(name="Bank", value="bank"),
    ])
    @app_commands.describe(user="Target member", amount="Amount of coins to credit", destination="Wallet or Bank")
    async def add_coins(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        amount: int,
        destination: Optional[app_commands.Choice[str]] = None,
    ):
        if amount <= 0:
            return await interaction.response.send_message("Amount must be positive.", ephemeral=True)

        dest = destination.value if destination else "wallet"
        if dest == "wallet":
            await economy_service.modify_wallet(
                interaction.guild_id, user.id, amount,
                tx_type="admin_add",
                description=f"Admin {interaction.user.name} added {amount} coins to wallet",
            )
        else:
            await economy_service.modify_bank(
                interaction.guild_id, user.id, amount,
                tx_type="admin_add",
                description=f"Admin {interaction.user.name} added {amount} coins to bank",
            )

        embed = economy_embed(
            "✅ Coins Credited",
            f"Added **+{amount:,} {CURRENCY_NAME}** to {user.mention}'s `{dest}`.\nAuthorized by {interaction.user.mention}.",
            COLOR_ECO_SUCCESS,
        )
        await interaction.response.send_message(embed=embed)

    @eco_admin.command(name="remove-coins", description="Deduct virtual coins from a user's wallet or bank account")
    @has_admin_or_owner()
    @app_commands.choices(source=[
        app_commands.Choice(name="Wallet", value="wallet"),
        app_commands.Choice(name="Bank", value="bank"),
    ])
    @app_commands.describe(user="Target member", amount="Amount of coins to deduct", source="Wallet or Bank")
    async def remove_coins(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        amount: int,
        source: Optional[app_commands.Choice[str]] = None,
    ):
        if amount <= 0:
            return await interaction.response.send_message("Amount must be positive.", ephemeral=True)

        src = source.value if source else "wallet"
        if src == "wallet":
            await economy_service.modify_wallet(
                interaction.guild_id, user.id, -amount,
                allow_negative=False,
                tx_type="admin_remove",
                description=f"Admin {interaction.user.name} removed {amount} coins from wallet",
            )
        else:
            await economy_service.modify_bank(
                interaction.guild_id, user.id, -amount,
                allow_negative=False,
                tx_type="admin_remove",
                description=f"Admin {interaction.user.name} removed {amount} coins from bank",
            )

        embed = economy_embed(
            "⚠️ Coins Deducted",
            f"Deducted **-{amount:,} {CURRENCY_NAME}** from {user.mention}'s `{src}`.\nAuthorized by {interaction.user.mention}.",
            COLOR_ECO_INFO,
        )
        await interaction.response.send_message(embed=embed)

    @eco_admin.command(name="set-coins", description="Explicitly set a member's exact wallet or bank coin balance")
    @has_admin_or_owner()
    @app_commands.choices(destination=[
        app_commands.Choice(name="Wallet", value="wallet"),
        app_commands.Choice(name="Bank", value="bank"),
    ])
    @app_commands.describe(user="Target member", amount="Exact balance amount", destination="Wallet or Bank")
    async def set_coins(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        amount: int,
        destination: Optional[app_commands.Choice[str]] = None,
    ):
        if amount < 0:
            return await interaction.response.send_message("Balance cannot be negative.", ephemeral=True)

        await economy_service.get_or_create_user(interaction.guild_id, user.id)
        dest = destination.value if destination else "wallet"

        if dest == "wallet":
            await db.execute("UPDATE economy_users SET wallet = ? WHERE guild_id = ? AND user_id = ?", (amount, interaction.guild_id, user.id))
            await db.execute("UPDATE economy SET wallet = ? WHERE guild_id = ? AND user_id = ?", (amount, interaction.guild_id, user.id))
        else:
            await db.execute("UPDATE economy_users SET bank = ? WHERE guild_id = ? AND user_id = ?", (amount, interaction.guild_id, user.id))
            await db.execute("UPDATE economy SET bank = ? WHERE guild_id = ? AND user_id = ?", (amount, interaction.guild_id, user.id))

        embed = economy_embed(
            "✅ Balance Adjusted",
            f"Set {user.mention}'s `{dest}` balance exactly to **{amount:,} {CURRENCY_NAME}**.",
            COLOR_ECO_SUCCESS,
        )
        await interaction.response.send_message(embed=embed)

    @eco_admin.command(name="give-item", description="Give equipment or crate items to a user's inventory")
    @has_admin_or_owner()
    @app_commands.describe(user="Target member", item_id="Item ID from catalog", quantity="Quantity to give")
    async def give_item_cmd(self, interaction: discord.Interaction, user: discord.Member, item_id: str, quantity: int = 1):
        clean_id = item_id.lower().strip()
        item = await db.fetchone("SELECT * FROM economy_items WHERE item_id = ?", (clean_id,))
        if not item:
            return await interaction.response.send_message(f"Item `{clean_id}` not found in catalog.", ephemeral=True)

        await economy_service.give_item(interaction.guild_id, user.id, clean_id, quantity)
        embed = economy_embed(
            "🎁 Item Granted",
            f"Gave **{quantity}x {item['icon']} {item['name']}** to {user.mention}.",
            COLOR_ECO_SUCCESS,
        )
        await interaction.response.send_message(embed=embed)

    @eco_admin.command(name="remove-item", description="Remove items from a user's inventory")
    @has_admin_or_owner()
    @app_commands.describe(user="Target member", item_id="Item ID", quantity="Quantity to remove")
    async def remove_item_cmd(self, interaction: discord.Interaction, user: discord.Member, item_id: str, quantity: int = 1):
        clean_id = item_id.lower().strip()
        removed = await economy_service.remove_item(interaction.guild_id, user.id, clean_id, quantity)
        if removed:
            embed = economy_embed(
                "🗑️ Item Removed",
                f"Removed **{quantity}x** `{clean_id}` from {user.mention}'s inventory.",
                COLOR_ECO_INFO,
            )
            await interaction.response.send_message(embed=embed)
        else:
            embed = economy_embed("❌ Error", f"{user.display_name} does not have {quantity}x `{clean_id}`.", COLOR_ECO_ERROR)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @eco_admin.command(name="set-level", description="Set a member's RPG level and adjust their required XP")
    @has_admin_or_owner()
    @app_commands.describe(user="Target member", level="New level to assign")
    async def set_level_cmd(self, interaction: discord.Interaction, user: discord.Member, level: int):
        if level < 1:
            return await interaction.response.send_message("Level must be 1 or higher.", ephemeral=True)

        await economy_service.get_or_create_user(interaction.guild_id, user.id)
        req_xp = economy_service.xp_for_level(level)

        await db.execute(
            "UPDATE economy_users SET level = ?, xp = ? WHERE guild_id = ? AND user_id = ?",
            (level, req_xp, interaction.guild_id, user.id),
        )
        await db.execute(
            "UPDATE leveling SET level = ?, xp = ? WHERE guild_id = ? AND user_id = ?",
            (level, req_xp, interaction.guild_id, user.id),
        )

        embed = economy_embed(
            "⭐ Level Updated",
            f"Set {user.mention}'s level to **Level {level}** (`{req_xp:,} XP`).",
            COLOR_ECO_SUCCESS,
        )
        await interaction.response.send_message(embed=embed)

    @eco_admin.command(name="reset-economy", description="Reset economy balances and inventories for a single user or the entire server")
    @has_admin_or_owner()
    @app_commands.describe(user="Optional: member to reset. If omitted, resets ENTIRE server.")
    async def reset_economy(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        target_name = user.display_name if user else f"ENTIRE SERVER ({interaction.guild.name})"
        embed = economy_embed(
            title="⚠️ CONFIRM ECONOMY RESET",
            description=f"Are you absolutely certain you want to wipe economy data for **{target_name}**?\n\n"
                        f"**This will permanently erase:**\n"
                        f"• Wallet & Bank Balances\n"
                        f"• Inventory items, weapons, & armor\n"
                        f"• Zoo animal collections\n"
                        f"• Adopted pet companions\n\n"
                        f"*This action CANNOT be undone.*",
            color=COLOR_ECO_ERROR,
        )
        view = ResetConfirmationView(interaction.user.id, interaction.guild_id, user)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @eco_admin.command(name="stats", description="Detailed server-wide economic circulation, wealth distribution, and health metrics")
    @has_admin_or_owner()
    async def economy_stats(self, interaction: discord.Interaction):
        # High level metrics
        users_row = await db.fetchone(
            """
            SELECT COUNT(*) as total_users,
                   SUM(wallet) as total_wallet,
                   SUM(bank) as total_bank,
                   AVG(wallet + bank) as avg_wealth,
                   MAX(wallet + bank) as top_wealth
            FROM economy_users
            WHERE guild_id = ?
            """,
            (interaction.guild_id,),
        )
        hunts_row = await db.fetchone(
            "SELECT SUM(hunts_count) as total_hunts FROM economy_users WHERE guild_id = ?",
            (interaction.guild_id,),
        )
        battles_row = await db.fetchone(
            "SELECT COUNT(*) as total_duels FROM economy_battles WHERE guild_id = ?",
            (interaction.guild_id,),
        )

        tot_users = users_row["total_users"] if users_row else 0
        w_sum = users_row["total_wallet"] or 0
        b_sum = users_row["total_bank"] or 0
        circulation = w_sum + b_sum
        avg_w = int(users_row["avg_wealth"] or 0)
        top_w = users_row["top_wealth"] or 0
        tot_hunts = hunts_row["total_hunts"] or 0
        tot_duels = battles_row["total_duels"] or 0

        embed = economy_embed(
            title=f"📊 Macroeconomic Analytics - {interaction.guild.name}",
            color=COLOR_ECO_GOLD,
        )
        embed.add_field(name="Total Accounts", value=f"**{tot_users:,}** Citizens", inline=True)
        embed.add_field(name="Coins in Circulation", value=f"**{circulation:,}** {CURRENCY_SYMBOL}", inline=True)
        embed.add_field(name="Average Net Worth", value=f"**{avg_w:,}** {CURRENCY_SYMBOL}", inline=True)
        embed.add_field(name="Richest Player Net Worth", value=f"**{top_w:,}** {CURRENCY_SYMBOL}", inline=True)
        embed.add_field(name="Wild Animals Hunted", value=f"**{tot_hunts:,}** Hunts", inline=True)
        embed.add_field(name="Arena Duels Fought", value=f"**{tot_duels:,}** Battles", inline=True)

        await interaction.response.send_message(embed=embed)

    @eco_admin.command(name="config", description="Configure work/crime cooldowns, hunt timers, and daily reward scales")
    @has_admin_or_owner()
    @app_commands.describe(
        work_cooldown="Work cooldown in seconds (default 300)",
        crime_cooldown="Crime cooldown in seconds (default 600)",
        hunt_cooldown="Hunt cooldown in seconds (default 15)",
        daily_reward_min="Minimum daily reward coins (default 500)",
        daily_reward_max="Maximum daily reward coins (default 1000)",
    )
    async def economy_config(
        self,
        interaction: discord.Interaction,
        work_cooldown: Optional[int] = None,
        crime_cooldown: Optional[int] = None,
        hunt_cooldown: Optional[int] = None,
        daily_reward_min: Optional[int] = None,
        daily_reward_max: Optional[int] = None,
    ):
        cfg = await db.fetchone("SELECT * FROM economy_guild_settings WHERE guild_id = ?", (interaction.guild_id,))
        w_cd = work_cooldown if work_cooldown is not None else (cfg["work_cooldown"] if cfg else 300)
        c_cd = crime_cooldown if crime_cooldown is not None else (cfg["crime_cooldown"] if cfg else 600)
        h_cd = hunt_cooldown if hunt_cooldown is not None else (cfg["hunt_cooldown"] if cfg else 15)
        d_min = daily_reward_min if daily_reward_min is not None else (cfg["daily_reward_min"] if cfg else 500)
        d_max = daily_reward_max if daily_reward_max is not None else (cfg["daily_reward_max"] if cfg else 1000)

        await db.execute(
            """
            INSERT INTO economy_guild_settings (guild_id, work_cooldown, crime_cooldown, hunt_cooldown, daily_reward_min, daily_reward_max)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                work_cooldown = excluded.work_cooldown,
                crime_cooldown = excluded.crime_cooldown,
                hunt_cooldown = excluded.hunt_cooldown,
                daily_reward_min = excluded.daily_reward_min,
                daily_reward_max = excluded.daily_reward_max
            """,
            (interaction.guild_id, w_cd, c_cd, h_cd, d_min, d_max),
        )

        embed = economy_embed(
            title="⚙️ Server Economy Configuration Updated",
            description=f"• **Work Cooldown:** `{w_cd}s`\n"
                        f"• **Crime Cooldown:** `{c_cd}s`\n"
                        f"• **Hunt Cooldown:** `{h_cd}s`\n"
                        f"• **Daily Reward Range:** `{d_min:,} - {d_max:,}` Coins",
            color=COLOR_ECO_SUCCESS,
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(EconomyAdmin(bot))
