from redbot.core import data_manager
from .shop import Shop


def setup(bot):
    cog = Shop()
    data_manager.load_bundled_data(cog, __file__)
    bot.add_cog(cog)
