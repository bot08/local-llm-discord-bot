from config import Config
from services.llm_service import LLMService
from services.discord_bot import DiscordBot

config = Config()

llm_service = LLMService(config)
llm_service.initialize_model()

bot = DiscordBot(config, llm_service)

@bot.command()
async def ping(ctx):
    latency = bot.latency * 1000
    await ctx.send(f"🏓 Pong! {latency:.2f}ms")

@bot.command()
async def clear(ctx):
    user_id = str(ctx.author.id)
    if bot.llm.clear_history(user_id):
        await ctx.send("✅ Message history cleared.")
    else:
        await ctx.send("ℹ️ No message history.")

bot.run(config.discord_token)