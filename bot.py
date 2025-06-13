import os
import asyncio
import discord
from discord.ext import commands, tasks
from discord import app_commands
from utils import load_cache, fetch_and_cache, parse_date, date_to_pretty, split_multi_field
from commands_rota import register_rota_commands
from commands_free import register_free_command
from commands_swap import register_swap_command
from commands_fetch import register_fetch_command
from commands_iam import register_iam_command

TOKEN = os.getenv("DISCORD_TOKEN") or "YOUR_DISCORD_BOT_TOKEN"
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

SHIFTS_CACHE_FILE = "shifts_cache.json"

async def scheduled_fetch(bot):
    await asyncio.sleep(4 * 60 * 60)  # 4 hours in seconds
    # Import fetch_and_cache here (to avoid circular import)
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

    from utils import fetch_and_cache

    cache_valid = False

    try:
        if os.path.exists("shifts_cache.json"):
            with open("shifts_cache.json", 'r', encoding='utf-8') as f:
                data = json.load(f)
            shift_dates = set()
            for entry in data:
                date_obj, _ = parse_date(entry.get("date", ""))
                if date_obj:
                    shift_dates.add(date_obj.date())

            today = datetime.today().date()
            next_thursday = today + timedelta(
                days=(3 - today.weekday() + 7) % 7 + 4 if today.weekday() > 3 else 3 - today.weekday()
            )

            if today in shift_dates and next_thursday in shift_dates:
                cache_valid = True
    except Exception as e:
        print("Error reading cache:", e)

    if not cache_valid:
        print("Cache is outdated or incomplete. Fetching shifts now...")
        await fetch_and_cache()
    else:
        print("Cache is up to date. Scheduling auto-fetch in 4 hours...")
        asyncio.create_task(scheduled_fetch(bot))


    # Check if cache contains today and next Thursday
    cache_valid = False
    if os.path.exists(SHIFTS_CACHE_FILE):
        try:
            with open(SHIFTS_CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            shift_dates = set()
            for entry in data:
                date_obj, _ = parse_date(entry.get("date", ""))
                if date_obj:
                    shift_dates.add(date_obj.date())
            today = datetime.today().date()
            next_thursday = today + timedelta(days=(3 - today.weekday() + 7) % 7 + 4 if today.weekday() > 3 else 3 - today.weekday())
            if today in shift_dates and next_thursday in shift_dates:
                cache_valid = True
        except Exception as e:
            print("Error reading cache:", e)

    if not cache_valid:
        print("Cache is outdated or incomplete. Fetching shifts now...")
        from utils import fetch_and_cache
        await fetch_and_cache()
    else:
        print("Cache is up to date. Scheduling auto-fetch in 4 hours...")
        asyncio.create_task(scheduled_fetch(bot))

    except Exception as e:
        print("Error syncing commands:", e)

    # Only schedule fetch if the cache already exists (i.e., don't fetch immediately on launch)
    if os.path.exists(SHIFTS_CACHE_FILE):
        print("Scheduling auto-fetch in 4 hours...")
        asyncio.create_task(scheduled_fetch(bot))
    else:
        print("No cache exists yet. Manual /fetch required before auto-fetch is scheduled.")

# Register all commands (cleanly modularized)
register_fetch_command(bot)
register_iam_command(bot)
register_rota_commands(bot)
register_free_command(bot)
register_swap_command(bot)

bot.run(TOKEN)
