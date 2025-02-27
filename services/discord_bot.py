import discord
from discord.ext import commands
import asyncio
from typing import Dict
import aiohttp
import aiofiles

class DiscordBot(commands.Bot):
    def __init__(self, config, llm_service):
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix=config.bot_config['command_prefix'],
            intents=intents,
            help_command=None
        )
        
        self.config = config
        self.llm = llm_service
        self.typing_tasks: Dict[str, asyncio.Task] = {}
        self.user_locks: Dict[str, asyncio.Lock] = {}

    async def start_typing(self, channel):
        try:
            while True:
                async with channel.typing():
                    await asyncio.sleep(4.5)
        except asyncio.CancelledError:
            pass

    async def safe_send(self, channel, content):
        print(f"Message from Bot: {content}") if self.config.full_log else None

        if len(content) < 2000:
            return await channel.send(content)
        
        # Handling long messages by splitting into parts
        parts = [content[i:i+1900] for i in range(0, len(content), 1900)]
        for part in parts:
            await channel.send(part)
            await asyncio.sleep(0.5)

    async def process_message(self, message: discord.Message):
        user_id = str(message.author.id)
        
        # Get or create a lock for the user
        lock = self.user_locks.setdefault(user_id, asyncio.Lock())
        
        async with lock:
            try:
                if not self.config.stream_mode:
                    typing_task = asyncio.create_task(self.start_typing(message.channel))
                    self.typing_tasks[user_id] = typing_task
                
                response = await asyncio.to_thread(
                    self.llm.get_response,
                    user_id,
                    message.content,
                    message.author.name
                )
                
                if self.config.stream_mode:
                    # Stream mode
                    sent_message = await message.channel.send("▌")
                    current_response = ""
                    for chunk in response:
                        current_response += chunk
                        await sent_message.edit(content=current_response + " ▌")
                        #await asyncio.sleep(0.5)
                    await sent_message.edit(content=current_response)
                else:
                    # No stream
                    full_response = ''.join(response)
                    await self.send_voice(message.channel, full_response)
                    #await self.safe_send(message.channel, ''.join(response))
    
            except Exception as e:
                print(f"Critical error: {str(e)}")
                await message.channel.send(f"🚨 Critical error: {str(e)}")
                
            finally:
                typing_task.cancel()
                self.typing_tasks.pop(user_id, None)

    async def on_ready(self):
        await self.change_presence(activity=discord.Game(name="DM me"))
        print(f"Bot {self.user} is online")

    async def on_message(self, message):
        if message.author == self.user:
            return
            
        if self.config.bot_config['only_dm'] and not isinstance(message.channel, discord.DMChannel):
            return
        
        print(f"Message from {message.author}: {message.content}") if self.config.full_log else None

        ctx = await self.get_context(message)
        if not ctx.valid:
            await self.process_message(message)
            
        await self.process_commands(message)

    async def generate_voice(self, text):
        params = {
            'words': text,
            'speaker': self.config.default_speaker,
            'sample_rate': self.config.sample_rate
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.config.voice_service_url}/get_audio_file",
                params=params,
                headers={'accept': 'application/json'}
            ) as response:
                if response.status != 200:
                    return None
                
                temp_file = "voice.mp3"
                async with aiofiles.open(temp_file, 'wb') as f:
                    await f.write(await response.read())
                return temp_file

    async def send_voice(self, channel, text):
        voice_file = await self.generate_voice(text)
        if voice_file:
            await channel.send(file=discord.File(voice_file))
        else:
            await self.safe_send(channel, f"🔇 Text: {text}")