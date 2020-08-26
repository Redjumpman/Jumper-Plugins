from .casino import Casino

__red_end_user_data_statement__ = "This cog stores discord IDs as needed for operation."


async def setup(bot):
    cog = Casino(bot)
    bot.add_cog(cog)
    await cog.initialise()
