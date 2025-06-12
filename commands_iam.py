from discord import app_commands
import discord
import json

USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(data):
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def register_iam_command(bot):
    tree = bot.tree

    @tree.command(name="iam", description="Bind your Discord user to your real name for rota lookup.")
    @app_commands.describe(full_name="Your full name as on the rota")
    async def iam_cmd(interaction: discord.Interaction, full_name: str):
        users = load_users()
        users[str(interaction.user.id)] = full_name
        save_users(users)
        await interaction.response.send_message(f"✅ Bound you to '{full_name}'.", ephemeral=True)
