import discord
from functools import wraps
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import re


def resolve_emoji(ctx, emoji_str: str):
    emoji = discord.utils.get(ctx.guild.emojis, name=emoji_str)
    if emoji:
        return str(emoji)
    # Jeśli to custom emoji <...:id>
    else:
        return f":{emoji_str}:"


def requires_roles(*roles):
    def decorator(func):
        @wraps(func)
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            user_roles = [role.name for role in interaction.user.roles]
            print(user_roles)
            print(roles)
            if any(role in user_roles for role in roles):
                return await func(interaction, *args, **kwargs)
            else:
                await interaction.response.send_message(
                    "Nie masz wymaganej roli, aby użyc tej komendy",
                    ephemeral=True, delete_after=10
                )
        return wrapper
    return decorator

DAYS_MAP = {
    "poniedzialek": 0,
    "wtorek": 1,
    "sroda": 2,
    "czwartek": 3,
    "piatek": 4,
    "sobota": 5,
    "niedziela": 6
}

def event_date_helper(user_input: str, tz="Europe/Warsaw"):
    parts = user_input.lower().split()
    day_name, time_str = parts[0], parts[1]
    hour, minute = parse_time_input(time_str)

    today = datetime.now(ZoneInfo(tz))
    target_weekday = DAYS_MAP[day_name]

    # Ile dni do najbliższego dnia tygodnia
    days_ahead = (target_weekday - today.weekday() + 7) % 7
    if days_ahead == 0 and (hour, minute) <= (today.hour, today.minute):
        # Jeśli to dzisiaj, ale godzina już minęła -> następny tydzień
        days_ahead = 7

    event_date = today + timedelta(days=days_ahead)
    return event_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

def parse_time_input(time_str: str):
    """
    Parsuje tekstowy input czasu (np. '19:30' lub '19') i zwraca (hour, minute).
    Jeśli użytkownik poda tylko godzinę, minute ustawiane są na 0.
    """
    time_str = time_str.strip()

    try:
        parts = time_str.split(":")
        if len(parts) == 1:
            # Podano tylko godzinę
            hour = int(parts[0])
            minute = 0
        elif len(parts) == 2:
            hour = int(parts[0])
            minute = int(parts[1])
        else:
            raise ValueError("Zły format czasu")

        # Walidacja
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("Nieprawidłowa godzina lub minuta")

        return hour, minute

    except ValueError:
        raise ValueError("Nieprawidłowy format czasu. Użyj formatu HH lub HH:MM.")

def parse_duration(user_input: str) -> timedelta:
    """
    Parsuje czas trwania podany w formacie tekstowym (np. '2h', '1h 30min', '45 minut')
    i zwraca wartość w minutach (int).
    """
    duration_str = user_input.lower().strip()

    # Szukamy godzin i minut w tekście
    hours = 0
    minutes = 0

    # Dopasowanie godzin
    h_match = re.search(r"(\d+)\s*(h|godz|godziny|godzin)", duration_str)
    if h_match:
        hours = int(h_match.group(1))

    # Dopasowanie minut
    m_match = re.search(r"(\d+)\s*(m|min|minut|minuty|minuty)", duration_str)
    if m_match:
        minutes = int(m_match.group(1))

    total_minutes = hours * 60 + minutes
    return total_minutes
