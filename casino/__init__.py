from .casino import Casino


def setup(bot):
    bot.add_cog(Casino(bot))
