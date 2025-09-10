import discord
from functools import wraps


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
