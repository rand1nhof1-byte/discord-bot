# import pyodbc
import psycopg2
import os
from DataModel import *
from DataModel import Template


class Database:
    def __init__(self, cnn_string):
        """
        Inicjalizacja obiektu bazy danych.
        :param server: nazwa serwera SQL (np. "localhost\\SQLEXPRESS")
        :param database: nazwa bazy danych
        :param driver: domyślny sterownik ODBC
        """
        self.connection_string = cnn_string
        self.DB_HOST = os.environ["DB_HOST"]
        self.DB_PORT = os.environ["DB_PORT"]
        self.DB_NAME = os.environ["DB_NAME"]
        self.DB_USER = os.environ["DB_USER"]
        self.DB_PASS = os.environ["DB_PASS"]
        # self.connection_string = (
        #     "Driver={ODBC Driver 17 for SQL Server};"
        #     "Server=DESKTOP-VV9JD6R\\SQLEXPRESS;"   # np. "localhost\\SQLEXPRESS"
        #     "Database=discordBot;"
        #     "Trusted_Connection=yes;"
        # )

    def map_row_to_dataclass(self, cls, row):
        return cls(**{field: getattr(row, field) for field in cls.__dataclass_fields__.keys() if hasattr(row, field)})

    def connect(self):
        conn = psycopg2.connect(
        host=self.DB_HOST,
        port=self.DB_PORT,
        database=self.DB_NAME,
        user=self.DB_USER,
        password=self.DB_PASS
        )
        return conn

    def get_all(self, table, cls):
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute(f"SELECT * FROM dbo.{table}")
            items = []
            for row in cursor.fetchall():
                items.append(self.map_row_to_dataclass(cls, row))

            return items
        except Exception as e:
            print(e)
            raise
        finally:
            conn.close()

    def get_template(self, template_id):
        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute(f"""SELECT t.template_id, t.name, t.description, t.created_at, o.template_option_id, o.emoji, o.option_text, o.required_roles
            FROM Templates t
            LEFT JOIN TemplateOptions o ON t.template_id = o.template_id
            WHERE t.template_id = ?""", (template_id))
            template = None

            for row in cursor.fetchall():
                if not template:
                    template = Template(
                        template_id=row.template_id,
                        name=row.name,
                        description=row.description,
                        created_at=row.created_at,
                        options=[]
                    )
                if row.template_option_id is not None:
                    option = TemplateOption(
                        template_option_id=row.template_option_id,
                        template_id=row.template_id,
                        emoji=row.emoji,
                        option_text=row.option_text,
                        required_roles=row.required_roles
                    )
                    template.options.append(option)
            return template

        except Exception as e:
            print("ERROR: ", e)
        finally:
            conn.close()


    def insert_template(self, template):
        conn = self.connect()
        cursor = conn.cursor()

        try:
            print(template)
            cursor.execute(f"""
            INSERT INTO dbo.Templates (name, description, created_at)
            VALUES (?, ?, ?)
            """,
                           (template.name, template.description, template.created_at))
            conn.commit()
        except Exception as e:
            conn.rollback()
            print("Error inserting data:", e)
            raise
        finally:
            conn.close()

    def get_template_option(self, id):
        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM dbo.TemplateOptions where template_option_id = ?", (id))
            result = cursor.fetchone()
            return result
        except Exception as e:
            print("get_template_option:ERROR: ", e)
        finally:
            conn.close()

    def insert_template_option(self, template_option):
        conn = self.connect()
        cursor = conn.cursor()

        try:
            print(template_option)
            cursor.execute("INSERT INTO TemplateOptions (template_id, emoji, option_text, required_roles) VALUES (?, ?, ?, ?)",
                           (template_option.template_id, template_option.emoji, template_option.option_text, template_option.required_roles))

            conn.commit()
        except Exception as e:
            conn.rollback()
            print("insert_template_option:Error inserting data: ", e)
            raise
        finally:
            conn.close()

    def insert_poll(self, poll):
        conn = self.connect()
        cursor = conn.cursor()

        try:
            print(poll)
            cursor.execute(f"""
               INSERT INTO dbo.Polls (channel_id, title, description, created_at, is_active, start_time, duration_minutes)
               OUTPUT INSERTED.poll_id
               VALUES (?, ?, ?, ?, ?, ?, ?)
               """,
                           (poll.channel_id, poll.title, poll.description, poll.created_at, poll.is_active, poll.start_time, poll.duration_minutes))
            new_id = cursor.fetchone()[0]
            conn.commit()

            return new_id
        except Exception as e:
            conn.rollback()
            print("Error inserting data:", e)
            raise
        finally:
            conn.close()

    def insert_poll_options(self, options, poll_id):
        conn = self.connect()
        cursor = conn.cursor()

        try:
            for option in options:
                print(option)
                cursor.execute(f"""
                               INSERT INTO dbo.PollOptions (poll_id, emoji, option_text, required_roles)
                               VALUES (?, ?, ?, ?)
                               """,
                               (
                               poll_id, option.emoji, option.option_text, option.required_roles))
                conn.commit()
        except Exception as e:
            conn.rollback()
            print("Error inserting data:", e)
            raise
        finally:
            conn.close()


    def save_poll_message_id(self, poll_id, message_id):
        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute(f"""
                           UPDATE dbo.Polls SET message_id = ?
                           WHERE poll_id = ?
                           """,
                           (
                           message_id, poll_id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            print("Error inserting data:", e)
            raise
        finally:
            conn.close()

    def get_poll_by_id(self, poll_id):
        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute(f"""
                                   SELECT * FROM Polls where poll_id = ?
                                   """,
                           poll_id)
            row = cursor.fetchone()
            return Poll(poll_id=row.poll_id, channel_id=row.channel_id, title=row.title, description=row.description, message_id=row.message_id, start_time=row.start_time, duration_minutes=row.duration_minutes)
        except Exception as e:
            conn.rollback()
            print("Error inserting data:", e)
            raise
        finally:
            conn.close()

    def get_poll_options(self, poll_id):
        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute(f"""
                                           SELECT * FROM PollOptions where poll_id = ?
                                           """,
                           poll_id)
            results = []
            for row in cursor.fetchall():
                results.append(
                    PollOption(
                        poll_id=row.poll_id,
                        option_id=row.option_id,
                        emoji=row.emoji,
                        option_text=row.option_text,
                        required_roles=row.required_roles
                    )
                )
            return results
        except Exception as e:
            conn.rollback()
            print("Error inserting data:", e)
            raise
        finally:
            conn.close()

    def get_active_polls(self):
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute(f"SELECT * FROM dbo.Polls where is_active = 1")
            items = []
            for row in cursor.fetchall():
                items.append(self.map_row_to_dataclass(Poll, row))

            return items
        except Exception as e:
            print(e)
            raise
        finally:
            conn.close()

