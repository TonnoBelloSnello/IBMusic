from dotenv import load_dotenv

load_dotenv()

import asyncio
import nextcord
from nextcord.ext import commands
import os

from cogs import music, ibm_site, node_listener
from server import srv
from threading import Thread

cogs = [music, ibm_site, node_listener]

intents = nextcord.Intents().all()
bot = commands.Bot(command_prefix="&", case_insensitive=True, intents=intents, enable_debug_events=True)
bot.remove_command("help")
for cog in cogs:
    cog.setup(bot)


@bot.event
async def on_ready():
    for guild in bot.guilds:
        srv[str(guild.id)] = {
            "ctx": None,
            'queue': [],
            'player': None,
            "last_message": None,
            "loop": False,
            'thread': None,
            'time': 0,
            'pause': False,
            'skipping': False,
        }

    activity = nextcord.Game(name="some music!", type=3)
    await bot.change_presence(activity=activity)
    print(f'{bot.user} joined the game')

@bot.event
async def on_guild_join(guild):
	srv[str(guild.id)] = {
            "ctx": None,
            'queue': [],
            'player': None,
            "last_message": None,
            "loop": False,
            'thread': None,
            'time': 0,
            'pause': False,
            'skipping': False,
        }

def start():
    token = os.getenv("BOT_TOKEN")
    loop = asyncio.get_event_loop()
    loop.create_task(bot.start(token))
    Thread(target=loop.run_forever, daemon=True).start()


if __name__ == '__main__':
    start()

