
from discord import app_commands
import discord
from utils import load_cache, parse_date, date_to_pretty, split_multi_field, day_autocomplete, name_autocomplete, role_autocomplete
from datetime import datetime, timedelta
from collections import defaultdict

def register_free_command(bot):
    tree = bot.tree

    @tree.command(name="free", description="Find when staff are free on specific days or overall.")
    @app_commands.describe(names="Comma-separated staff names (optional)", days="Comma-separated days (e.g. Monday, Tuesday)")
    @app_commands.autocomplete(names=name_autocomplete, days=day_autocomplete)
    async def free_cmd(interaction: discord.Interaction, names: str = "", days: str = ""):
        shifts = load_cache()
        if not shifts:
            await interaction.response.send_message("No cached data. Please run `/fetch` first.", ephemeral=True)
            return

        staff_list = [n.strip().title() for n in names.split(",") if n.strip()]
        day_list = [d.strip().capitalize() for d in days.split(",") if d.strip()]
        all_names = sorted(set(s["name"] for s in shifts if s.get("name")))

        if not staff_list and not day_list:
            await interaction.response.send_message("Please provide at least a name or a day.", ephemeral=True)
            return

        from datetime import date as Date
        shifts_by_name = defaultdict(lambda: defaultdict(list))
        shift_details = defaultdict(lambda: defaultdict(list))

        for s in shifts:
            name = s.get("name", "").title()
            date_obj, _ = parse_date(s.get("date", ""))
            start, end, typ = s.get("start"), s.get("end"), s.get("type", "Shift")
            if name and date_obj and start and end:
                try:
                    st = datetime.strptime(start, "%H:%M").time()
                    en = datetime.strptime(end, "%H:%M").time()
                    shifts_by_name[name][date_obj.date()].append((st, en))
                    shift_details[name][date_obj.date()].append((st, en, typ))
                except:
                    continue

        all_dates = sorted({parse_date(s.get("date", ""))[0].date() for s in shifts if parse_date(s.get("date", ""))[0]})

        def day_header(date: Date) -> str:
            return date.strftime("%A %d-%m-%y")

        embeds = []
        for day in all_dates:
            if day_list and day.strftime("%A") not in day_list:
                continue

            lines = []
            has_primary = False
            for name in (staff_list if staff_list else all_names):
                if shifts_by_name[name].get(day):
                    st, en, typ = shift_details[name][day][0]
                    if name in staff_list:
                        lines.append(f"❌ **{name}** is working ({st.strftime('%H:%M')}–{en.strftime('%H:%M')}, **{typ}**)")
                        has_primary = True
                    else:
                        lines.append(f"  ❌ {name} has a shift.")
                else:
                    lines.append(f"✅ {name} is free.")

            if not lines:
                continue

            embed = discord.Embed(
                title=day_header(day),
                description="\n".join(lines),
                color=0xABCDEF if has_primary else 0xDDDDDD
            )
            embeds.append(embed)

        if not embeds:
            if day_list and staff_list:
                await interaction.response.send_message(
                    f"{', '.join(staff_list)} are working on {', '.join(day_list)}.", ephemeral=False)
            else:
                await interaction.response.send_message("No free days found for the given criteria.", ephemeral=False)
        else:
            for e in embeds:
                await interaction.followup.send(embed=e, ephemeral=False)
