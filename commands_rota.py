from discord import app_commands
import discord
from utils import load_cache, parse_date, date_to_pretty, split_multi_field, day_autocomplete, name_autocomplete, role_autocomplete
from datetime import datetime, timedelta

def register_rota_commands(bot):
    tree = bot.tree

    # (Paste your rota_cmd implementation here, using helpers from utils.py)
    # Include autocomplete and all logic from your main bot previously
    # Example (trimmed):
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
                    day_obj = now.replace(day=now.day + 1)
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
                results = [s for s in results if any(r.lower() in (s.get("role") or "").lower() for r in roles)
                ]


        from collections import defaultdict
        type_colors = {
            "Managers": discord.Color.dark_blue(),
            "Floor": discord.Color.gold(),
            "FAB": discord.Color.red(),
            "Other": discord.Color.light_grey(),
        }

        grouped_by_day = defaultdict(lambda: defaultdict(list))

        for s in results:
            d, _ = parse_date(s.get("date") or "")
            if not d:
                continue
            date_key = d.strftime("%A %d %b")
            shift_line = f"**{s['name']}**: {s['start']}–{s['end']} ({s['role']})"

            role = (s.get("role") or "").lower()
            if "manager" in role or "cem" in role:
                grouped_by_day[date_key]["Managers"].append(shift_line)
            elif "ushering" in role:
                grouped_by_day[date_key]["Floor"].append(shift_line)
            elif "fab" in role:
                grouped_by_day[date_key]["FAB"].append(shift_line)
            else:
                grouped_by_day[date_key]["Other"].append(shift_line)

        embeds = []
        for date, sections in grouped_by_day.items():
            color = (
                type_colors["Managers"]
                if "Managers" in sections else
                type_colors["Floor"]
                if "Floor" in sections else
                type_colors["FAB"]
                if "FAB" in sections else
                type_colors["Other"]
            )
            embed = discord.Embed(title=date, color=color)
            for section, lines in sections.items():
                embed.add_field(name=section, value="\n".join(lines), inline=False)
            embeds.append(embed)

        if not embeds:
            await interaction.response.send_message("No shifts found for your query.", ephemeral=True)
        else:
            await interaction.response.send_message(embeds=embeds, ephemeral=False)
        if len(embeds) > 10:
            txt = ""
            for d, items in fields.items():
                txt += f"\n{d}\n" + "\n".join(items) + "\n"
            await interaction.response.send_message(
                "Too many results, sent as file instead.",
                file=discord.File(fp=io.StringIO(txt), filename="shifts.txt"),
                ephemeral=True
            )
        elif not fields:
            await interaction.response.send_message("No shifts found for your query.", ephemeral=True)
        else:
            await interaction.response.send_message(embeds=embeds, ephemeral=False)
