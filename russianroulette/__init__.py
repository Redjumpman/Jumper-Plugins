from .russianroulette import RussianRoulette

__red_end_user_data_statement__ = "This cog stores Discord IDs as needed for operation temporarily during the game which are automatically deleted when it ends."


def setup(bot):
    bot.add_cog(RussianRoulette())
