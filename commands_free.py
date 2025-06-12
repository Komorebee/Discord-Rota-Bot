from discord import app_commands
import discord
from utils import load_cache, parse_date, date_to_pretty, split_multi_field, day_autocomplete, name_autocomplete, role_autocomplete
from datetime import datetime, timedelta
from collections import defaultdict




def register_free_command(bot):
    tree = bot.tree

    @tree.command(name="free", description="Find when all selected staff are simultaneously free.")
    @app_commands.describe(names="Comma-separated staff names (use autocomplete)")
    @app_commands.autocomplete(names=name_autocomplete)
    async def free_cmd(interaction: discord.Interaction, names: str):
        """
        Finds days and times when all specified staff are free.
        Shows for each day all available gaps where none have a shift.
        """
        shifts = load_cache()
        if not shifts:
            await interaction.response.send_message("No cached data. Please run `/fetch` first.", ephemeral=True)
            return

        staff_list = [n.strip() for n in names.split(",") if n.strip()]
        if not staff_list:
            await interaction.response.send_message("Please specify at least one staff name.", ephemeral=True)
            return

        # Build: date -> list of (start, end) for any of the staff
        day_shifts = defaultdict(list)
        for s in shifts:
            name = s.get("name")
            date_obj, _ = parse_date(s.get("date", ""))
            start, end = s.get("start"), s.get("end")
            if name and date_obj and start and end:
                for staff in staff_list:
                    if staff.lower() == name.lower():
                        try:
                            st = datetime.strptime(start, "%H:%M").time()
                            en = datetime.strptime(end, "%H:%M").time()
                            st_min = max(time_to_minutes(st), 8 * 60)
                            en_min = min(time_to_minutes(en), 24 * 60)
                            if en_min <= st_min:
                                en_min = 24 * 60  # assume midnight finish
                            day_shifts[date_obj.date()].append((st_min, en_min))
                        except Exception:
                            continue

        all_dates = sorted({parse_date(s.get("date", ""))[0].date()
                            for s in shifts if parse_date(s.get("date", ""))[0]})

        results = []
        for day in all_dates:
            intervals = sorted(day_shifts.get(day, []))
            # Merge all intervals for all selected staff, then find the intersection (when all are free)
            # 1. Build busy timeline for all staff for that day
            timeline = [0] * ((24-8) * 60)  # 8:00 to 24:00 in minutes
            for st, en in intervals:
                st_idx = max(0, st - 8*60)
                en_idx = min((24-8)*60, en - 8*60)
                for i in range(st_idx, en_idx):
                    timeline[i] += 1
            # 2. Free blocks are places where timeline is zero
            # 2. Free blocks are places where timeline is zero
            free_blocks = []
            start_idx = None
            for i, val in enumerate(timeline):
                if val == 0:
                    if start_idx is None:
                        start_idx = i
                else:
                    if start_idx is not None:
                        if i - start_idx >= 120:  # Only show 2hr+ blocks
                            block_st = 8*60 + start_idx
                            block_en = 8*60 + i
                            free_blocks.append((block_st, block_en))
                        start_idx = None
            # End edge case
            if start_idx is not None and ((24-8)*60 - start_idx) >= 120:
                block_st = 8*60 + start_idx
                block_en = 24*60
                free_blocks.append((block_st, block_en))


            date_str = date_to_pretty(datetime.combine(day, datetime.min.time()))
            if not intervals:
                results.append(f"**{date_str}:** Completely free")
            elif free_blocks:
                times = ", ".join(f"{minutes_to_time(st)}–{minutes_to_time(en)}"
                                for st, en in free_blocks)
                if times:
                    results.append(f"**{date_str}:** Free: {times}")

        if not results:
            await interaction.response.send_message(
                f"No free blocks found for: {', '.join(staff_list)}", ephemeral=True)
        else:
            msg = f"**Shared free times for:** {', '.join(staff_list)}\n\n" + "\n".join(results[:15])
            if len(msg) > 2000:
                msg = msg[:1900] + "\n... (truncated)"
            await interaction.response.send_message(msg, ephemeral=False)
