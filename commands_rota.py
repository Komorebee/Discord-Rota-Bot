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

        # Sort by date (chronological), then start time
        def sort_key(s):
            d, _ = parse_date(s.get("date") or "")
            d = d or datetime.max
            st = s.get("start") or ""
            try:
                st_dt = datetime.strptime(st, "%H:%M")
            except Exception:
                st_dt = datetime.strptime("23:59", "%H:%M")
            return (d, st_dt)
        results.sort(key=sort_key)

        # Group by date (prettified)
        fields = {}
        for s in results:
            d, _ = parse_date(s.get("date") or "")
            date_str = date_to_pretty(d) if d else (s.get("date") or "Unknown")
            if date_str not in fields:
                fields[date_str] = []
            fields[date_str].append(f"**{s['name']}**: {s['start']}–{s['end']} ({s['role']})")

        import io
        embeds = []
        embed = discord.Embed(
            title="Cinema Shifts",
            description=f"Results for: " +
                        (f"**{name}**" if name else "*All staff*") +
                        (f", **{day}**" if day else "") +
                        (f", **{role}**" if role else ""),
            color=discord.Color.blue()
        )
        total_chars = len(embed.title) + len(embed.description)
        max_embed_chars = 6000
        max_fields = 25

        for d, items in fields.items():
            chunk = []
            chunk_len = 0
            chunk_index = 1
            for line in items:
                if chunk_len + len(line) + 1 > 1024:
                    field_val = "\n".join(chunk)
                    if (len(embed.fields) >= max_fields or total_chars + len(field_val) > max_embed_chars):
                        embeds.append(embed)
                        embed = discord.Embed(color=discord.Color.blue())
                        total_chars = 0
                    embed.add_field(name=f"{d} (cont'd {chunk_index})", value=field_val, inline=False)
                    total_chars += len(f"{d} (cont'd {chunk_index})") + len(field_val)
                    chunk = []
                    chunk_len = 0
                    chunk_index += 1
                chunk.append(line)
                chunk_len += len(line) + 1
            if chunk:
                field_name = f"{d}" if chunk_index == 1 else f"{d} (cont'd {chunk_index})"
                field_val = "\n".join(chunk)
                if (len(embed.fields) >= max_fields or total_chars + len(field_val) > max_embed_chars):
                    embeds.append(embed)
                    embed = discord.Embed(color=discord.Color.blue())
                    total_chars = 0
                embed.add_field(name=field_name, value=field_val, inline=False)
                total_chars += len(field_name) + len(field_val)

        if len(embed.fields) > 0 or len(embeds) == 0:
            embeds.append(embed)

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
