from discord import app_commands
import discord
from utils import load_cache, parse_date, date_to_pretty, split_multi_field, day_autocomplete, name_autocomplete, role_autocomplete
from datetime import datetime, timedelta

def register_swap_command(bot):
    tree = bot.tree

    @tree.command(name="swap", description="Find who can swap into a shift (filters: name, day, role).")
    @app_commands.describe(
        name="Staff full name (optional)",
        day="Day (e.g., 09 Jun Mon or today, optional)",
        role="Role(s), e.g. FAB Serving, FAB Kitchen Assistant (comma-separated, optional)"
    )
    @app_commands.autocomplete(name=name_autocomplete, day=day_autocomplete, role=role_autocomplete)
    async def swap_cmd(
        interaction: discord.Interaction,
        name: str = None,
        day: str = None,
        role: str = None,
    ):
        shifts = load_cache()
        if not shifts:
            await interaction.response.send_message("❌ No shift data. Please run `/fetch` first.", ephemeral=True)
            return

        # Find the target shift
        now = datetime.now()
        results = shifts
        if name:
            results = [s for s in results if name.lower() in s["name"].lower()]
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
            role_filters = split_multi_field(role)
            results = [
                s for s in results
                if any(r.lower() in (s.get("role") or "").lower() for r in role_filters)
            ]

        if len(results) == 0:
            await interaction.response.send_message("No shift found with those filters.", ephemeral=True)
            return
        elif len(results) > 1:
            await interaction.response.send_message("More than one shift matches. Please refine your filters.", ephemeral=True)
            return

        shift = results[0]
        target_date_obj, _ = parse_date(shift.get("date") or "")
        if not target_date_obj:
            await interaction.response.send_message("Target shift has an invalid or missing date.", ephemeral=True)
            return

        # Shift time parsing
        try:
            shift_start = datetime.combine(target_date_obj.date(), datetime.strptime(shift['start'], "%H:%M").time())
            shift_end = datetime.combine(target_date_obj.date(), datetime.strptime(shift['end'], "%H:%M").time())
            if shift_end < shift_start:
                # If end time is after midnight
                shift_end = shift_end.replace(day=shift_end.day + 1)
        except Exception as e:
            await interaction.response.send_message("Target shift has invalid start/end time.", ephemeral=True)
            return

        all_names = set(s['name'] for s in shifts if s.get('name') and s['name'] != shift['name'])
        ineligible_names = set()

        # 1. Anyone with a shift on that same day (excluding the original person)
        for s in shifts:
            d, _ = parse_date(s.get("date") or "")
            if not d or s['name'] == shift['name']:
                continue
            if d.date() == target_date_obj.date():
                ineligible_names.add(s['name'])

        # 2. Anyone with a shift previous day that ENDS less than 11.5h before this shift starts
        prev_date = target_date_obj.replace(day=target_date_obj.day - 1)
        eleven_half = 11.5 * 60 * 60  # seconds
        for s in shifts:
            d, _ = parse_date(s.get("date") or "")
            if not d or s['name'] == shift['name']:
                continue
            if d.date() == prev_date.date():
                try:
                    prev_end = datetime.combine(d.date(), datetime.strptime(s['end'], "%H:%M").time())
                    if prev_end < shift_start and (shift_start - prev_end).total_seconds() < eleven_half:
                        ineligible_names.add(s['name'])
                except:
                    continue

        # 3. Anyone with a shift next day that STARTS less than 11.5h after this shift ends
        next_date = target_date_obj.replace(day=target_date_obj.day + 1)
        for s in shifts:
            d, _ = parse_date(s.get("date") or "")
            if not d or s['name'] == shift['name']:
                continue
            if d.date() == next_date.date():
                try:
                    next_start = datetime.combine(d.date(), datetime.strptime(s['start'], "%H:%M").time())
                    if next_start > shift_end and (next_start - shift_end).total_seconds() < eleven_half:
                        ineligible_names.add(s['name'])
                except:
                    continue

        swappable_names = sorted(all_names - ineligible_names)
        if not swappable_names:
            msg = "No eligible staff can swap into this shift (based on rest rules & no double shift)."
        else:
            msg = "Eligible to swap in:\n" + "\n".join(f"• {n}" for n in swappable_names)

        embed = discord.Embed(
            title=f"Swap Candidates",
            description=f"Shift: **{shift['name']}** {shift.get('date','?')} {shift.get('start')}–{shift.get('end')} ({shift.get('role')})\n\n{msg}",
            color=discord.Color.green() if swappable_names else discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
