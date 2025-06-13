from discord import app_commands
import discord
from utils import load_cache, parse_date, date_to_pretty, split_multi_field, day_autocomplete, name_autocomplete, role_autocomplete
from datetime import datetime, timedelta
from collections import defaultdict
import io

def register_rota_commands(bot):
    tree = bot.tree

    @tree.command(name="rota", description="Cinema rota: filter by name, day, role (multi-role allowed).")
    @app_commands.describe(
        name="Staff full name (optional)",
        day="Day (e.g., 09 Jun Mon or today, optional)",
        role="Role(s), e.g. FAB Serving, FAB Kitchen Assistant (comma-separated, optional)"
    )
    @app_commands.autocomplete(name=name_autocomplete, day=day_autocomplete, role=role_autocomplete)
    async def rota_cmd(
        interaction: discord.Interaction,
        name: str = None,
        day: str = None,
        role: str = None,
    ):
        shifts = load_cache()
        if not shifts:
            await interaction.response.send_message("❌ No shift data. Please run `/fetch` first.", ephemeral=True)
            return

        now = datetime.now()
        # If no args: show today, all names, all roles
        if not name and not day and not role:
            day_obj = now
            filtered_shifts = []
            for s in shifts:
                d, _ = parse_date(s.get("date", ""))
                if d and d.date() == day_obj.date():
                    filtered_shifts.append(s)
            results = filtered_shifts
            day = now.strftime("%d %b %a")
        else:
            results = shifts
            if name:
                names = split_multi_field(name)
                results = [s for s in results if any(n.lower() in s["name"].lower() for n in names)]
            if day:
                # Accepts "today", "tomorrow", or "09 Jun" or "09 Jun Mon"
                if day.lower() == "today":
                    day_obj = now
                elif day.lower() == "tomorrow":
                    day_obj = now + timedelta(days=1)
                else:
                    try:
                        date_parts = day.split()
                        if len(date_parts) >= 2:
                            day_num, month = date_parts[0], date_parts[1]
                            year = now.year
                            day_obj = datetime.strptime(f"{day_num} {month} {year}", "%d %b %Y")
                        else:
                            day_obj = None
                    except Exception:
                        day_obj = None
                if day_obj:
                    results = [
                        s for s in results
                        if "date" in s and s["date"] and
                        parse_date(s["date"])[0] and
                        parse_date(s["date"])[0].date() == day_obj.date()
                    ]
                else:
                    results = [s for s in results if day.lower() in (s.get("date") or "").lower()]
            if role:
                roles = split_multi_field(role)
                results = [s for s in results if any(r.lower() in (s.get("role") or "").lower() for r in roles)]

        type_colors = {
            "Managers": discord.Color.dark_blue(),
            "Floor": discord.Color.gold(),
            "FAB": discord.Color.red(),
            "Costa": discord.Color.green(),
            "Other": discord.Color.light_grey(),
        }

        # Group by date -> type -> person -> list of shifts
        grouped = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

        for s in results:
            d, _ = parse_date(s.get("date") or "")
            if not d:
                continue
            date_key = d.strftime("%A %d %b %Y")
            shift_str = f"{s['start']}–{s['end']} ({s['role']})"
            name_key = s["name"]
            role_str = (s.get("role") or "").lower()
            # Categorization logic
            if "manager" in role_str or "cem" in role_str:
                cat = "Managers"
            elif "ushering" in role_str:
                cat = "Floor"
            elif "barista" in role_str:
                cat = "Costa"
            elif "fab" in role_str or "kitchen" in role_str or "kiosk" in role_str:
                cat = "FAB"
            else:
                cat = "Other"
            grouped[date_key][cat][name_key].append(shift_str)

        # Sort by date
        for date_key in sorted(grouped.keys()):
            await interaction.response.send_message(f"**Rota for {date_key}:**", ephemeral=False)
            # For each category, build an embed
            for cat in ["Managers", "Floor", "FAB", "Costa", "Other"]:
                if cat not in grouped[date_key]:
                    continue
                embed = discord.Embed(title=cat, color=type_colors[cat])
                for name_key, shifts_list in grouped[date_key][cat].items():
                    embed.add_field(
                        name=name_key,
                        value="\n".join(shifts_list),
                        inline=False
                    )
                await interaction.followup.send(embed=embed, ephemeral=False)
