import os
import asyncio
import discord
from discord.ext import commands, tasks
from discord import app_commands
from utils import fetch_and_cache, clear_cache
from commands_rota import register_rota_commands
from commands_free import register_free_command
from commands_swap import register_swap_command
from commands_fetch import register_fetch_command
from commands_iam import register_iam_command
import json
from datetime import datetime, timedelta

TOKEN = os.getenv("DISCORD_TOKEN") or "YOUR_DISCORD_BOT_TOKEN"
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


async def scheduled_fetch(bot):
    await asyncio.sleep(4 * 60 * 60)  # 4 hours in seconds
    from utils import fetch_and_cache
    await fetch_and_cache()
    print("Auto-fetched shifts after 4 hours.")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print("Error syncing commands:", e)


    # Start with a blank cache and fetch the latest shifts
    clear_cache()
    await fetch_and_cache()

    # Schedule automatic refresh every 4 hours
    asyncio.create_task(scheduled_fetch(bot))


# Register all commands (cleanly modularized)
register_fetch_command(bot)
register_iam_command(bot)
register_rota_commands(bot)
register_free_command(bot)
register_swap_command(bot)

bot.run(TOKEN)
