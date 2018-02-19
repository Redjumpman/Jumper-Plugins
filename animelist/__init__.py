from .animelist import AnimeList


def setup(bot):
    bot.add_cog(AnimeList(bot))
