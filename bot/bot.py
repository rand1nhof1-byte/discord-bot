import zoneinfo

import discord
from discord.ext import commands
from discord.ext import tasks
from discord import app_commands
import json

from psycopg2.extras import NamedTupleCursor

from Database import Database
from DataModel import *
from discord.ui import View, Button
from discord.ui.button import ButtonStyle
from discord.interactions import Interaction
from Helpers import resolve_emoji, requires_roles, event_date_helper, parse_duration
from PollView import PollView
from zoneinfo import ZoneInfo
import os
from dotenv import load_dotenv


# source_options_file = "source_options.json"
# with open(source_options_file, "r", encoding="UTF-8") as f:
#     options = json.load(f)
#
#     print(f"JSON CONTENT: {options}")

    # for key, value in options.items():
    #     print(f"{key}: {value}")

load_dotenv()

BOT_TOKEN = os.getenv('TOKEN')
GUILD_ID = os.getenv('GUILD_ID')
# GUILD_ID = 1279520097521762408
user_tz = ZoneInfo("Europe/Warsaw")
# cnn_string = os.get['cnn_string']

database_client = Database()
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())


@tasks.loop(minutes=1)
async def check_polls():
    polls = database_client.get_active_polls()
    now = datetime.now()
    if polls:
        for poll in polls:
            if poll.ready_to_ping():
                print("poll_ready_to_ping")
                conn = database_client.connect()
                cursor = conn.cursor(cursor_factory=NamedTupleCursor)
                cursor.execute(f"""select discord_user_id
                                    from dbo.PollOptions p
                                    left join dbo.Votes v
                                    on p.option_id = v.option_id and p.poll_id = v.poll_id
                                    where p.poll_id = {poll.poll_id} and p.option_text != 'Nieobecny' and discord_user_id is not null """)
                users = cursor.fetchall()
                str = " ".join([f"<@{uid[0]}>" for uid in users])
                print(str)
                msg = await bot.get_channel(poll.channel_id).fetch_message(poll.message_id)

                if not msg.thread:
                    thread = await msg.create_thread(
                        name=f"Event {poll.title} startuje za 15 minut!",
                        auto_archive_duration=60
                    )
                    if str:
                        await thread.send(str)


async def setup_hook():
    # odczytaj z bazy wszystkie aktywne ankiety
    with database_client.connect().cursor(cursor_factory=NamedTupleCursor) as cursor:
        cursor.execute("SELECT poll_id FROM dbo.Polls WHERE is_active=TRUE")
        for row in cursor.fetchall():
            poll = database_client.get_poll_by_id(row.poll_id)

            # wyciągnij opcje ankiety z bazy
            options = database_client.get_poll_options(poll.poll_id)
            # options = [TemplateOption(*r) for r in cursor.fetchall()]
            channel = await bot.fetch_channel(poll.channel_id)
            if not channel:
                return
            message = await channel.fetch_message(poll.message_id)
            if not message:
                return
            # zarejestruj persistent view
            bot.add_view(PollView(await bot.get_context(message), poll, options, database_client.connect()))


# SEND DM MESSAGE AND WAIT
async def wait_for_dm(interaction: discord.Interaction, prompt, timeout=120):
    user = interaction.user
    await user.send(prompt)

    def check(msg):
        return msg.author == user and isinstance(msg.channel, discord.DMChannel)

    msg = await interaction.client.wait_for("message", check=check, timeout=timeout)
    return msg.content.strip()


## BOT LOGIN
@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user}')
    await bot.tree.sync()
    await setup_hook()
    check_polls.start()


@requires_roles("Właściciel", "Admin")
@bot.tree.command(name="templates")
async def templates(interaction: discord.Interaction):
    # if not any(role.name in allowed_roles for role in interaction.user.roles):
    #     await interaction.response.send_message("Nie masz uprawnień do edycji szablonów!", ephemeral=True, delete_after=5)
    #     return
    templates = database_client.get_all("Templates", Template)
    if not templates:
        await interaction.response.send_message("Nie znaleziono żadnych szablonów.", ephemeral=True, delete_after=5)
        return
    await interaction.response.send_message("Wysłałem Ci wiadomość!", ephemeral=True, delete_after=5)
    msg_list = "\n".join([f"{row.template_id}: {row.name} - {row.description}" for row in templates])
    response = await wait_for_dm(interaction, f"Wybierz szablon do edycji wpisując jego ID:\n{msg_list}")

    try:
        template_id = int(response)
        template_info = database_client.get_template(template_id)
        if not template_info:
            await interaction.user.send("Nie znaleziono szablonu o podanym ID.")
            return
    except Exception as e:
        print("ERROR", e)
        return

    while True:
        template_info = database_client.get_template(template_id)
        print(template_info)
        options_text = "\n".join([f"{opt.emoji} - {opt.option_text}" for opt in template_info.options])
        menu_msg = (
            f"Szablon: {template_info.name}\nOpis: {template_info.description}\nOpcje:\n{options_text}\n\n"
            "Co chcesz zrobić?\n"
            # "1: Zmień nazwę\n"
            # "2: Zmień opis\n"
            "3: Dodaj opcję\n"
            "4: Edytuj opcję\n"
            "5: Usuń opcję\n"
            "0: Zakończ"
        )
        choice = await wait_for_dm(interaction, menu_msg)

        if choice == "3":
            emoji = await wait_for_dm(interaction, "Podaj emoji dla nowej opcji:")
            text = await wait_for_dm(interaction, "Podaj tekst dla nowej opcji:")
            required_roles = await wait_for_dm(interaction, "Podaj wymagane role (oddzielone przecinkiem), lub zostaw puste jeśli opcja ma być bez ograniczeń:")
            template_opt = TemplateOption(template_option_id=None, template_id=template_id, emoji=emoji, option_text=text, required_roles=required_roles)
            database_client.insert_template_option(template_opt)
            await interaction.user.send(f"Dodano opcję: {emoji} - {text}")
        elif choice == "0":
            await interaction.user.send("Edycja szablonu zakończona.")
            break


@bot.tree.command(name="template-create")
@requires_roles("Właściciel", "Admin")
async def template_create(interaction: discord.Interaction):
    # if not any(role.name in allowed_roles for role in interaction.user.roles):
    #     await interaction.response.send_message("Nie masz uprawnień do tworzenia szablonów!", ephemeral=True, delete_after=5)
    #     return
    await interaction.response.send_message("Wysłałem Ci wiadomość!", ephemeral=True, delete_after=5)
    title = await wait_for_dm(interaction, "Podaj nazwe szablonu")
    description = await wait_for_dm(interaction, "Podaj opis")
    template = Template(template_id=None, name=title, description=description)

    database_client.insert_template(template)
    await interaction.user.send("Pomyślnie utworzono szablon!")


@bot.tree.command(name="poll")
@requires_roles("Właściciel", "Admin", "F1 Koordynator Ligi")
# @bot.command()
async def poll(interaction: discord.Interaction):
    """
    Tworzy ankietę na podanym kanale na podstawie szablonu
    """
    # if not any(role.name in allowed_roles for role in interaction.user.roles):
    #     await interaction.response.send_message("Nie masz uprawnień do tworzenia ankiet!", ephemeral=True, delete_after=5)
    #     return
    channel = interaction.channel
    if not channel:
        await interaction.response.send_message("Nie znaleziono kanału o podanym ID!", ephemeral=True, delete_after=5)
        return

    templates = database_client.get_all("Templates", Template)
    if not templates:
        await interaction.response.send_message("Nie znaleziono żadnych szablonów.", ephemeral=True, delete_after=5)
        return
    await interaction.response.send_message("Wysłałem Ci wiadomość!", ephemeral=True, delete_after=5)
    msg_list = "\n".join([f"{row.template_id}: {row.name} - {row.description}" for row in templates])
    response = await wait_for_dm(interaction, f"Wybierz szablon do edycji wpisując jego ID:\n{msg_list}")
    if response is None:
        await interaction.user.send("Nie wybrałeś ID na czas")
        return
    template_id = int(response)
    template_info = database_client.get_template(template_id)

    print(template_info)




    try:
        title = await wait_for_dm(interaction, "Podaj tytuł:")
        description = await wait_for_dm(interaction, "Podaj opis:")
        start_time = await wait_for_dm(interaction, "Podaj date rozpoczęcia w formacie 'dzien godzina, np poniedzialek 19:30")
        event_start = event_date_helper(start_time)
        duration = await wait_for_dm(interaction, "Podaj czas trwania eventu w formacie(h min: 1h30min")
        event_duration = parse_duration(duration)
        try:
            poll = Poll(poll_id=None,
                        channel_id=interaction.channel.id,
                        title=title,
                        description=description,
                        message_id=None,
                        start_time=event_start.replace(tzinfo=user_tz),
                        duration_minutes=int(event_duration))
        except Exception as e:
            print(e)
            await interaction.user.send(f"Błąd tworzenia ankiety {e.args}")
            return

        poll_id = database_client.insert_poll(poll)
        database_client.insert_poll_options(template_info.options, poll_id)

        poll_db = database_client.get_poll_by_id(poll_id)
        options_db = database_client.get_poll_options(poll_id)

        view = PollView(interaction, poll_db, options_db, database_client.connect())

        print(view)

        # Tworzenie osadzonej wiadomości (embed)
        embed = discord.Embed(title=poll_db.title,
                              description=poll_db.description,
                              color=discord.Color.blue(),
                              timestamp=datetime.now())

        print(f"Created poll with start datetime: {poll.start_time}")
        embed.add_field(
            name="📅",
            value=f"<t:{int(poll.start_time.timestamp())}:F> - <t:{int((poll.start_time+timedelta(minutes=poll.duration_minutes)).timestamp())}:t>\n" 
                  f"⏰ <t:{int(poll.start_time.timestamp())}:R>",  # Format Discorda → pełna data/godzina
            inline=False
        )
        embed.add_field(name="", value="\n", inline=False)

        for option in options_db:
            embed.add_field(name=f"{resolve_emoji(interaction, option.emoji)} {option.option_text}", value="", inline=True)

        # for key, value in poll_options.items():
        #     if key == "reserve":
        #         embed.add_field(name="", value="\n\n\n", inline=False)
        #     embed.add_field(name=f"{value['emoji']} {value['option']}", value="", inline=True)
    #

        message = await interaction.channel.send(embed=embed, view=view)
        # sent_message = await interaction.original_response()
        database_client.save_poll_message_id(poll_id, message.id)


        # for option in template_info.options:
        #     print(resolve_emoji(ctx, option.emoji))
        #     await message.add_reaction(resolve_emoji(ctx, option.emoji))


    #
    #     # poll_votes[message.id] = {}
    #     # for key, value in poll_options.items():
    #     #     poll_votes[message.id][key] = set()
    #     #     await message.add_reaction(value['emoji'])
    #
    #
    #
    #
    #     # print(poll_votes)
    #
    #     print(message.embeds[0].fields)
    #
    #     # print(poll_options['redbull'])
    #
    except TimeoutError:
        await interaction.user.send("Timeout")
    except ValueError as e:
        await interaction.user.send(str(e.args))
        await interaction.user.send("Anulowano tworzenie ankiety")


@bot.tree.command(name="tracks")
@requires_roles("Właściciel", "Admin", "Komentator")
async def tracks(interaction: discord.Interaction, track_number: int | None = None):
    print("get all tracks from DB")
    track_list = database_client.get_all_tracks()
    description = "\n".join([f"{x['TrackID']} - {x['TrackName']}" for x in track_list])
    if track_number is None:
        embed = discord.Embed(
            title="STATYSTYKI TORÓW",
            description=description
        )
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message(
            f"Wyświetlono listę torów",
            ephemeral=True, delete_after=10
        )
        return


    if track_number in [x['TrackID'] for x in track_list]:
        track_info = database_client.get_track_by_id(track_number)
        embed = discord.Embed(
            title=track_info.track.upper(),
            description="Statystyki toru"
        )
        embed.add_field(name="Liczba wyścigów", value=track_info.total_races, inline=False)
        embed.add_field(name="Rekord toru", value=track_info.track_record, inline=False)
        embed.add_field(name="Najszybsze okrążenie w wyścigu", value=track_info.fastest_race_lap, inline=False)
        embed.add_field(name="Najwięcej zwycięstw", value=track_info.most_wins_driver, inline=False)
        embed.add_field(name="Najwięcej podium", value=track_info.most_podiums_driver, inline=False)
        embed.add_field(name="SC/VSC", value=track_info.safety_cars, inline=False)
        embed.add_field(name="Najszybsze okrążenie kwalifikacyjne", value=track_info.fastest_quali_lap, inline=False)
        embed.add_field(name="Najwięcej pole position", value=track_info.most_poles_driver, inline=False)
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message(
            f"Wyświetlono statystyki dla {track_info.track}",
            ephemeral=True, delete_after=10
        )
    else:
        await interaction.response.send_message(
            f"Nie znaleziono toru o podanym ID",
            ephemeral=True, delete_after=10
        )

#
# @bot.event
# async def on_reaction_add(reaction, user):
#     if user.bot:
#         return
#
#     message_id = reaction.message.id
#     guild = reaction.message.guild
#     member = guild.get_member(user.id)
#
#     for required_role in poll_options[reaction.emoji.name]['roles']:
#         print(f"Checking role: {required_role}")
#         print(member.roles)
#         if not any(role.name == required_role for role in member.roles):
#             await reaction.message.remove_reaction(reaction.emoji, user)
#             await user.send(f"Nie masz wymaganej roli `{required_role}`")
#             return
#
#
#     for r in reaction.message.reactions:
#         if r.emoji.name == reaction.emoji.name:
#             if r.count > 3:
#                 await reaction.message.remove_reaction(poll_options[reaction.emoji.name]['emoji'], user)
#                 print(reaction.message.reactions)
#                 return
#     # print(reaction.message.reactions)
#
#     if message_id in poll_votes:
#         for emoji in poll_votes[message_id]:
#             if user.id in poll_votes[message_id][emoji] and emoji != reaction.emoji.name:
#                 print(f"User {user} selected other option. The {emoji} will be removed")
#                 await reaction.message.remove_reaction(poll_options[emoji]['emoji'], user)
#
#         poll_votes[message_id][reaction.emoji.name].add(user.id)
#         # print(poll_votes)
#         # print(reaction.message.reactions)
#
#         # new_text = "".join(f"""{value['emoji']} {value['option']}\n {','.join([f"{value['emoji']} {bot.get_user(x).display_name}" for x in poll_votes[message_id][key]])} \n\n""" for key, value in poll_options.items())
#         await update_poll_voters(reaction)
#
# @bot.event
# async def on_reaction_remove(reaction, user):
#     if user.bot:
#         return
#
#     message_id = reaction.message.id
#
#     try:
#         poll_votes[message_id][reaction.emoji.name].remove(user.id)
#     except:
#         print("User already removed")
#     print(f"Removing user reaction: {user}")
#     # print(poll_votes)
#     # print(reaction.message.reactions)
#
#     # new_text = "".join(
#     #     f"{value['emoji']} {value['option']}\n {','.join([bot.get_user(x).display_name for x in poll_votes[message_id][key]])} \n"
#     #     for key, value in poll_options.items())
#     await update_poll_voters(reaction)
#
# async def update_poll_voters(reaction):
#     embed = reaction.message.embeds[0]
#     message_id = reaction.message.id
#
#     for i in range(0, len(embed.fields)):
#         if embed.fields[i].name == f"{poll_options[reaction.emoji.name]['emoji']} {poll_options[reaction.emoji.name]['option']}":
#             print("before poll update")
#             print(poll_votes)
#             key = reaction.emoji.name
#             embed.set_field_at(i,
#                                name=f"{poll_options[reaction.emoji.name]['emoji']} {poll_options[reaction.emoji.name]['option']}",
#                                value="\n".join([f"{poll_options[reaction.emoji.name]['emoji']} {bot.get_user(x).display_name}" for x in poll_votes[message_id][key]]),
#                                inline=True
#                                )
#             await reaction.message.edit(embed=embed)
#             print("EMBED FIELD MATCH")
#             print(reaction.message.embeds[0].fields)
#
#     await reaction.message.edit(embed=embed)
#
bot.run(BOT_TOKEN)




