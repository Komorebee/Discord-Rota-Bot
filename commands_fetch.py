from discord import app_commands
import discord
from utils import fetch_and_cache

def register_fetch_command(bot):
    tree = bot.tree

    @tree.command(name="fetch", description="Webscrape and cache the latest rota.")
    async def fetch_cmd(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await fetch_and_cache()
        await interaction.followup.send("✅ Fetched and cached the latest shifts!")
