import discord
import os
import json
from datetime import datetime
from discord import app_commands


CACHE_FILE = "shifts_cache.json"

def load_cache():
    try:
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_cache(shifts):
    with open(CACHE_FILE, "w") as f:
        json.dump(shifts, f, indent=2)

async def fetch_and_cache():
    from quinyx_scraper import fetch_user_shifts
    shifts = await fetch_user_shifts()
    save_cache(shifts)
    return shifts

def parse_date(date_str):
    try:
        if "," in date_str and "/" in date_str:
            day_name, date_part = date_str.split(",")
            date_obj = datetime.strptime(date_part.strip(), "%d/%m/%Y")
            return date_obj, day_name.strip()
        elif date_str and len(date_str.split()) == 3:
            day_str, day_num, month = date_str.split()
            now = datetime.now()
            date_obj = datetime.strptime(f"{day_num} {month} {now.year}", "%d %b %Y")
            return date_obj, day_str
        elif date_str and len(date_str.split()) == 2:
            day_num, month = date_str.split()
            now = datetime.now()
            date_obj = datetime.strptime(f"{day_num} {month} {now.year}", "%d %b %Y")
            return date_obj, date_obj.strftime("%a")
    except Exception:
        pass
    return None, date_str

def date_to_pretty(date_obj):
    return date_obj.strftime("%d %b %a")

def split_multi_field(field):
    if not field:
        return []
    return [x.strip() for x in field.replace(';', ',').split(',') if x.strip()]

def get_unique(field):
    data = load_cache()
    return sorted(set([s[field] for s in data if s.get(field)]))

async def name_autocomplete(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    shifts = load_cache()
    names = sorted({s["name"] for s in shifts if "name" in s and s["name"]})
    if "," in current:
        prefix = ",".join(current.split(",")[:-1]).strip(", ")
        already = split_multi_field(prefix)
        last = current.split(",")[-1].strip()
    else:
        prefix = ""  # <--- FIX: Always define prefix
        already = []
        last = current.strip()
    candidates = [n for n in names if not any(n.lower() == a.lower() for a in already)]
    starts_with = [n for n in candidates if n.lower().startswith(last.lower())]
    contains = [n for n in candidates if last.lower() in n.lower() and not n.lower().startswith(last.lower())]
    suggestions = starts_with + contains
    return [
        app_commands.Choice(
            name=f"{prefix}, {s}" if prefix else s,
            value=f"{prefix}, {s}" if prefix else s,
        )
        for s in suggestions[:25]
    ]





async def day_autocomplete(interaction: discord.Interaction, current: str):
    shifts = load_cache()
    seen_dates = set()
    date_options = []
    for s in shifts:
        d, day_str = parse_date(s.get("date", ""))
        if d and d.date() not in seen_dates:
            seen_dates.add(d.date())
            pretty = d.strftime("%d %b %a")  # 09 Jun Mon
            date_options.append((d, pretty))
    date_options.sort()  # by date ascending
    return [
        app_commands.Choice(name=pretty, value=pretty)
        for _, pretty in date_options if current.lower() in pretty.lower()
    ][:20]


async def role_autocomplete(interaction: discord.Interaction, current: str):
    # Return a list of roles from the cache, supporting multi selection (comma separated)
    shifts = load_cache()
    roles = set()
    for s in shifts:
        if s.get("role"):
            for r in split_multi_field(s["role"]):
                roles.add(r)
    roles = sorted(list(roles))
    # If user is entering multi, suggest only for the last part they're typing
    if ',' in current or ';' in current:
        entered = split_multi_field(current)
        last = entered[-1] if entered else ""
        suggestions = [r for r in roles if last.lower() in r.lower()]
        # Prepend already entered roles so user can see
        return [app_commands.Choice(name=", ".join(entered[:-1] + [r]), value=", ".join(entered[:-1] + [r])) for r in suggestions[:20]]
    else:
        return [app_commands.Choice(name=r, value=r) for r in roles if current.lower() in r.lower()][:20]
