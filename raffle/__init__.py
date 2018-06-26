from .raffle import Raffle


def setup(bot):
    bot.add_cog(Raffle(bot))
