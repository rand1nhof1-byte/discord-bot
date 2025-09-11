import discord
from discord import Interaction
from discord.ui import View, Button
from discord.ui.button import ButtonStyle
from DataModel import Poll, PollOption, Vote
from Helpers import resolve_emoji
import psycopg2
from datetime import timedelta


class PollView(View):
    def __init__(self, interaction, poll: Poll, options: list[PollOption], db_conn):
        super().__init__(timeout=None)
        self.poll = poll
        self.options = options
        self.db_conn = db_conn
        self.interaction = interaction

        row = 0
        i = 0
        for opt in options:
            if i % 4 == 0 and i > 0:
                row += 1
            i += 1
            button = Button(
                style=ButtonStyle.secondary,
                label=opt.option_text,
                emoji=resolve_emoji(interaction, opt.emoji),
                row=row,
                custom_id=f"{poll.poll_id}_{opt.option_id}"
            )
            button.callback = self.make_callback(opt)
            self.add_item(button)

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        if not self.poll.is_currently_active():
            await interaction.response.send_message(
                "Ankieta się zakończyła!", ephemeral=True, delete_after=5
            )
            return False
        return True


    def make_callback(self, option):
        async def callback(interaction: discord.Interaction):
            user_id = interaction.user.id
            user_name = interaction.user.display_name

            if not all(role in [x.name for x in interaction.user.roles] for role in option.required_roles.split(',')):
                await interaction.response.send_message(
                f":x: Brak wymaganej roli, żeby wybrać **{option.option_text}**",
                ephemeral=True, delete_after=5)
                return

            cursor = self.db_conn.cursor()

            cursor.execute("DELETE FROM dbo.Votes WHERE poll_id = ? AND discord_user_id = ?", (self.poll.poll_id, user_id))

            new_vote = Vote(vote_id=None, poll_id=self.poll.poll_id, option_id=option.option_id, discord_user_id=user_id, user_display_name=user_name)
            cursor.execute(
                "INSERT INTO Votes (poll_id, option_id, discord_user_id, voted_at, user_display_name) VALUES (?, ?, ?, ?, ?)",
                (new_vote.poll_id, new_vote.option_id, new_vote.discord_user_id, new_vote.voted_at, new_vote.user_display_name)
            )
            self.db_conn.commit()

            await interaction.response.send_message(
                f"✅ Zapisałeś się do **{option.option_text}**",
                ephemeral=True, delete_after=10
            )
            await self.update_poll_message(interaction)

        return callback


    async def update_poll_message(self, interaction: discord.Interaction):
        cursor = self.db_conn.cursor()
        cursor.execute("""
                    SELECT o.option_text, o.emoji, o.option_id, string_agg(v.user_display_name, ',') votes
                    FROM PollOptions o
                    LEFT JOIN Votes v ON o.option_id = v.option_id
                    WHERE o.poll_id = ?
                    GROUP BY o.option_text, o.emoji, o.option_id
                """, self.poll.poll_id)

        results = cursor.fetchall()

        embed = discord.Embed(
            title=self.poll.title,
            description=self.poll.description,
            color=discord.Color.blue()
        )

        embed.add_field(
            name="📅",
            value=f"<t:{int(self.poll.start_time.timestamp())}:F> - <t:{int((self.poll.start_time + timedelta(minutes=self.poll.duration_minutes)).timestamp())}:t>\n"
                  f"⏰ <t:{int(self.poll.start_time.timestamp())}:R>",  # Format Discorda → pełna data/godzina
            inline=False
        )

        for row in sorted(results, key=lambda x: x.option_id):
            votes_str = ""
            if row.votes:
                votes_str = '\n'.join(row.votes.split(','))
            embed.add_field(
                name=f"{resolve_emoji(self.interaction, row.emoji)} {row.option_text}",
                value=votes_str,
                inline=True
            )
        message = interaction.message
        await message.edit(embed=embed, view=self)




