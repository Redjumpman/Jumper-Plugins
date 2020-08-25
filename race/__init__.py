from .race import Race

__red_end_user_data_statement__ = "This cog does store discord IDs as needed for operation."


def setup(bot):
    bot.add_cog(Race())
