from .jisho import Jisho


def setup(bot):
    bot.add_cog(Jisho(bot))
