from config import Config
from services.llm_service import LLMService
from services.discord_bot import DiscordBot

import discord
from discord.ext import commands

config = Config()

llm_service = LLMService(config)
llm_service.initialize_model()

bot = DiscordBot(config, llm_service)

@bot.command()
async def send(ctx, user_id: str, *, message: str):
    """Отправить сообщение пользователю в ЛС (только для админов)"""
    try:
        user = await bot.fetch_user(int(user_id))
        await user.send(message)
        await ctx.send(f"✅ Сообщение отправлено пользователю {user.mention}")
    except ValueError:
        await ctx.send("❌ Неверный формат ID пользователя")
    except discord.NotFound:
        await ctx.send("❌ Пользователь не найден")
    except discord.Forbidden:
        await ctx.send("❌ Не могу отправить сообщение (закрытые ЛС или отсутствие прав)")
    except Exception as e:
        await ctx.send(f"⚠️ Ошибка: {str(e)}")

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