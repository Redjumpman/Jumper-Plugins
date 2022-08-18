from .casino import Casino
import discord

__red_end_user_data_statement__ = "This cog stores discord IDs as needed for operation."


async def setup(bot):
    cog = Casino(bot)
    if discord.__version__ > "1.7.3":
        await bot.add_cog(cog)
    else:
        bot.add_cog(cog)
    await cog.initialise()
