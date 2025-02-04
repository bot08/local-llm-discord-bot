from config import Config
from services.llm_service import LLMService
from services.discord_bot import DiscordBot

def main():
    config = Config()
    
    llm_service = LLMService(config)
    llm_service.initialize_model()
    
    bot = DiscordBot(config, llm_service)
    
    @bot.command()
    async def ping(ctx):
        latency = bot.latency * 1000
        await ctx.send(f"🏓 Pong! {latency:.2f}ms")
    
    bot.run(config.discord_token)

if __name__ == "__main__":
    main()