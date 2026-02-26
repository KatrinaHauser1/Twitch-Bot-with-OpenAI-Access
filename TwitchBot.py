
import asyncio
import logging
import random
from typing import TYPE_CHECKING

import asqlite

import twitchio
from twitchio import eventsub
from twitchio.ext import commands

if TYPE_CHECKING:
    import sqlite3

import os
from openai import OpenAI

#get this key from openai.com
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


LOGGER: logging.Logger = logging.getLogger("Bot")

CLIENT_ID: str = "xxx" # explained in twitch io tutorial, is your clientID when you generate a twitch token
CLIENT_SECRET: str = "xxx" # client secret generated when registering a twitch bot
BOT_ID = "xxx" # twitch user ID of bot account
OWNER_ID = "xxx"  #twitch user ID of your (whoever is hosting the bot) account


class Bot(commands.AutoBot):
    def __init__(self, *, token_database: asqlite.Pool, subs: list[eventsub.SubscriptionPayload]) -> None:
        self.token_database = token_database

        super().__init__(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            bot_id=BOT_ID,
            owner_id=OWNER_ID,
            prefix="!",
            subscriptions=subs,
            force_subscribe=True,
        )

    async def setup_hook(self) -> None:
        await self.add_component(MyComponent(self))

    async def event_oauth_authorized(self, payload: twitchio.authentication.UserTokenPayload) -> None:
        await self.add_token(payload.access_token, payload.refresh_token)

        if not payload.user_id:
            return

        if payload.user_id == self.bot_id:
            return

        subs: list[eventsub.SubscriptionPayload] = [
            eventsub.ChatMessageSubscription(broadcaster_user_id=payload.user_id, user_id=self.bot_id),
        ]

        resp: twitchio.MultiSubscribePayload = await self.multi_subscribe(subs)
        if resp.errors:
            LOGGER.warning("Failed to subscribe to: %r, for user: %s", resp.errors, payload.user_id)

    async def add_token(self, token: str, refresh: str) -> twitchio.authentication.ValidateTokenPayload:
        resp: twitchio.authentication.ValidateTokenPayload = await super().add_token(token, refresh)

        query = """
        INSERT INTO tokens (user_id, token, refresh)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET
            token = excluded.token,
            refresh = excluded.refresh;
        """
        async with self.token_database.acquire() as connection:
            await connection.execute(query, (resp.user_id, token, refresh))

        LOGGER.info("Added token to the database for user: %s", resp.user_id)
        return resp

    async def event_ready(self) -> None:
        LOGGER.info("Successfully logged in as: %s", self.bot_id)


class MyComponent(commands.Component):


    def __init__(self, bot: Bot) -> None:

        self.bot = bot

    #a bunch of sample/basic commands
    @commands.Component.listener()
    async def event_message(self, payload: twitchio.ChatMessage) -> None:
        print(f"[{payload.broadcaster.name}] - {payload.chatter.name}: {payload.text}")

        ##!! UNCOMMENT IF DESIRED, optional feature: have bot reply to any message that mentions it

        #checks that the bot doesnt reply to itself and get stuck in an infinite loop
        #if payload.chatter.id == BOT_ID:
        #    return

        #if any(user.id == BOT_ID for user in payload.mentions):
        # Remove the mention from the message before sending to the LLM
            #cleaned_message = payload.text.replace(f"@{BOT_ID}", "").strip()

            #response = await ask_llm(cleaned_message)

            #channel_user = self.bot.create_partialuser(OWNER_ID)

            #await channel_user.send_message(sender=self.bot.create_partialuser(BOT_ID), message=response[:450])

    @commands.command()
    async def hi(self, ctx: commands.Context) -> None:
        await ctx.reply(f"Hi {ctx.chatter}!")

    @commands.command()
    async def say(self, ctx: commands.Context, *, message: str) -> None:
        await ctx.send(message)

    @commands.command()
    async def add(self, ctx: commands.Context, left: int, right: int) -> None:
        await ctx.reply(f"{left} + {right} = {left + right}")

    @commands.command()
    async def choice(self, ctx: commands.Context, *choices: str) -> None:
        await ctx.reply(f"You provided {len(choices)} choices, I choose: {random.choice(choices)}")

    @commands.command(aliases=["thanks", "thank"])
    async def give(self, ctx: commands.Context, user: twitchio.User, amount: int, *, message: str | None = None) -> None:
        """A more advanced example of a command which has makes use of the powerful argument parsing, argument converters and
        aliases.

        The first argument will be attempted to be converted to a User.
        The second argument will be converted to an integer if possible.
        The third argument is optional and will consume the reast of the message.

        !give <@user|user_name> <number> [message]
        !thank <@user|user_name> <number> [message]
        !thanks <@user|user_name> <number> [message]
        """
        msg = f"with message: {message}" if message else ""
        await ctx.send(f"{ctx.chatter.mention} gave {amount} thanks to {user.mention} {msg}")

    @commands.group(invoke_fallback=True)
    async def socials(self, ctx: commands.Context) -> None:
        """Group command for our social links.

        !socials
        """
        await ctx.send("discord.gg/..., youtube.com/..., twitch.tv/...")


    # !! This is the fucntion to access the AI bot. do !ask "question" in chat and the bot will reply.
    # !! Resposes can be tailored, like what the bot should respond with to an empty question
    # !! limits the bot to only provide answers that dont violate the twitch message length (message would fail to send otherwise)

    @commands.command()
    async def ask(self, ctx: commands.Context):
        full_message = ctx.message.text

        question = full_message.split(" ", 1)

        if len(question) < 2:
            await ctx.send("youre gonna need to ask me something")
            return

        question = question[1].strip()

        answer = await ask_llm(question)


        await ctx.send(answer[:450])


    @socials.command(name="discord")
    async def socials_discord(self, ctx: commands.Context) -> None:
        """Sub command of socials that sends only our discord invite.

        !socials discord
        """
        await ctx.send("discord.gg/...")

    

    #!!! This connect you with the openAI. You should have defined your key in the terminal already using export OPENAI_API_KEY="your key"
    #!!! - Can change model, is currenlty using 4o mini since this doesnt need to be very powerful
    #!!! - Prompt can be completely modified to change the personality. I recommend this basic one, but anything can be added to tailor responses
    # for example: eextremely short precise responses, funnny bot that makes jokes, ....
    #      to be in a specific tone/be extremly short. 
    #      EXAMPLE PROMPT: !ask whats 5+5? 
    #      RESPONSE:  5 + 5 equals 10!  Do you have any other questions?
    #!!! Token max to make sure the bot doesnt use too many tokens answering one simple question/request
    #!!! Exception should only happen if something is wrong with the AI account OR OpenAI is down
    # IF you give this bot moderator in the channel, you can use normal /user timeout and /user ban to give it moderation power



async def ask_llm(question: str) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful Twitch chatbot. You can fetch information about the streamer from their twitch or fossabot page. Keep answers short (twitch has a message limit) and conversational."},
                {"role": "user", "content": question}
            ],
            max_tokens=150,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print("LLM error:", e)
        #this usually happens when your OPENAI account ran out of credits/doesnt have any. There are free credit you get after signing up but those will run out at some point.
        return "something went wrong please dont shut me down"


async def setup_database(db: asqlite.Pool) -> tuple[list[tuple[str, str]], list[eventsub.SubscriptionPayload]]:
    # Create our token table, if it doesn't exist..
    # You should add the created files to .gitignore or potentially store them somewhere safer
    # This is just for example purposes...

    query = """CREATE TABLE IF NOT EXISTS tokens(user_id TEXT PRIMARY KEY, token TEXT NOT NULL, refresh TEXT NOT NULL)"""
    async with db.acquire() as connection:
        await connection.execute(query)

        # Fetch any existing tokens...
        rows: list[sqlite3.Row] = await connection.fetchall("""SELECT * from tokens""")

        tokens: list[tuple[str, str]] = []
        subs: list[eventsub.SubscriptionPayload] = []

        for row in rows:
            tokens.append((row["token"], row["refresh"]))

            if row["user_id"] == BOT_ID:
                continue

            subs.extend([eventsub.ChatMessageSubscription(broadcaster_user_id=row["user_id"], user_id=BOT_ID)])

    return tokens, subs


def main() -> None:
    twitchio.utils.setup_logging(level=logging.INFO)

    async def runner() -> None:
        async with asqlite.create_pool("tokens.db") as tdb:
            tokens, subs = await setup_database(tdb)

            async with Bot(token_database=tdb, subs=subs) as bot:
                for pair in tokens:
                    await bot.add_token(*pair)

                await bot.start(load_tokens=False)

    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        LOGGER.warning("Shutting down due to KeyboardInterrupt")


if __name__ == "__main__":
    main()
