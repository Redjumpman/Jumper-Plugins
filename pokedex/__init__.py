from redbot.core import data_manager
from .pokedex import Pokedex


def setup(bot):
    cog = Pokedex()
    data_manager.load_bundled_data(cog, __file__)
    bot.add_cog(cog)
