from .race import Race

__red_end_user_data_statement__ = "This cog stores discord IDs as needed for operation."


def setup(bot):
    await bot.add_cog(Race())
