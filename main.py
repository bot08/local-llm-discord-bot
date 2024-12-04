import discord
from discord.ext import commands
from discord import Intents
from dotenv import load_dotenv
import os
from ai_functions import load_model, get_chat_response
import asyncio

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
ONLY_DM = os.getenv('OnlyDM', 'true').lower() == 'true'

intents = Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

isAnswering = False

async def keep_typing(channel, typing_interval=5):
    while True:
        async with channel.typing():
            await asyncio.sleep(typing_interval)

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name='DM me'))
    print(f'{bot.user.name} Bot online')

@bot.event
async def on_message(message):
    global isAnswering

    if message.author == bot.user or ONLY_DM and not isinstance(message.channel, discord.DMChannel):
        return

    if not message.content.startswith(bot.command_prefix) and not isAnswering:
        print(f"Message from {message.author}: {message.content}")
        isAnswering = True

        try:
            typing_task = asyncio.create_task(keep_typing(message.channel))
            response = await asyncio.to_thread(get_chat_response, message.content)
            typing_task.cancel()
            await message.channel.send(response)
        except Exception as e:
            print(f"Error: {e}")
            await message.channel.send("Error occurred while processing your request.")
        finally:
            isAnswering = False

    await bot.process_commands(message)

@bot.command()
async def ping(ctx):
    latency = bot.latency * 1000
    await ctx.send(f'Ping: {latency:.2f} ms')

load_model()
bot.run(TOKEN)