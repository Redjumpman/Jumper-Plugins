from .russianroulette import RussianRoulette

__red_end_user_data_statement__ = "This cog does store Discord IDs as needed for operation temporary during the game, which are automatically deleted when it ends."


def setup(bot):
    bot.add_cog(RussianRoulette())
