from .pokedex import Pokedex


def setup(bot):
    cog = Pokedex()
    bot.add_cog(cog)
