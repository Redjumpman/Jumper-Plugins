from .shop import Shop


def setup(bot):
    cog = Shop()
    bot.add_cog(cog)
