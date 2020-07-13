from .casino import Casino


async def setup(bot):
    cog = Casino(bot)
    bot.add_cog(cog)
    await cog.initialise()
