import discord
from config import DISCORD_TOKEN
import asyncio
from database.database import db
from services.economy_service import economy_service

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    await db.connect()
    guild = client.guilds[0]
    user = guild.members[0] if guild.members else guild.owner
    user_id = user.id if user else 12345
    
    # Test hunt
    h = await economy_service.hunt(guild.id, user_id)
    print("hunt result:", h.get("success", False))

    # Test zoo
    z = await economy_service.get_user_zoo(guild.id, user_id)
    print("zoo count:", len(z))

    # Test daily
    d = await economy_service.daily(guild.id, user_id)
    print("daily result:", d.get("success", False))

    await db.close()
    await client.close()

asyncio.run(client.start(DISCORD_TOKEN))
