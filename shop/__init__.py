from .shop import Shop

__red_end_user_data_statement__ = "This cog stores discord IDs as needed for operation."


def setup(bot):
    cog = Shop()
    bot.add_cog(cog)
